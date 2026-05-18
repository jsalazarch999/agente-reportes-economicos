import logging
import numpy as np
from sentence_transformers import SentenceTransformer

from rag.indexer import cargar_indice, _get_modelo

logger = logging.getLogger(__name__)

# =====================================================
# CONSTANTES
# =====================================================

# Número de candidatos que FAISS retorna antes de filtrar por metadata
TOP_K_CANDIDATOS = 20

# Número máximo de documentos que llegan al LLM por consulta
TOP_K_FINAL = 4

# Tolerancia temporal: el documento puede ser de hasta N meses antes del periodo
TOLERANCIA_MESES = 3


# =====================================================
# HELPERS
# =====================================================

def _periodo_a_int(periodo):
    """Convierte '202502' a entero comparable: 20250200."""
    try:
        return int(str(periodo)[:6])
    except (ValueError, TypeError):
        return 0


def _es_temporalmente_relevante(doc_periodo, periodo_consulta, tolerancia=TOLERANCIA_MESES):
    """
    Verifica que el documento sea del periodo consultado
    o de hasta `tolerancia` meses antes.
    No acepta documentos futuros al periodo analizado.

    Ejemplo: periodo_consulta=202502, tolerancia=3
    → acepta documentos de 202502, 202501, 202412, 202411
    """
    if not doc_periodo or not periodo_consulta:
        return True  # si no hay fecha, no filtrar

    try:
        anio_doc  = int(str(doc_periodo)[:4])
        mes_doc   = int(str(doc_periodo)[4:6])
        anio_cons = int(str(periodo_consulta)[:4])
        mes_cons  = int(str(periodo_consulta)[4:6])

        # Convertir a meses absolutos para comparar
        meses_doc  = anio_doc  * 12 + mes_doc
        meses_cons = anio_cons * 12 + mes_cons

        diferencia = meses_cons - meses_doc

        # El documento debe ser del periodo o anterior (no futuro)
        # y dentro de la tolerancia
        return 0 <= diferencia <= tolerancia

    except (ValueError, TypeError):
        return True


def _filtrar_por_metadata(documentos, filtros):
    """
    Filtra lista de documentos por campos de metadata exactos.
    Solo filtra los campos que están presentes en `filtros` y
    tienen valor no nulo.

    filtros puede contener: sector, subsector, producto, tipo, periodo
    """
    resultado = []

    for doc in documentos:
        cumple = True

        for campo, valor in filtros.items():
            if valor is None:
                continue

            if campo == "periodo":
                # Filtro temporal con tolerancia
                if not _es_temporalmente_relevante(doc.get("periodo"), valor):
                    cumple = False
                    break
            else:
                # Filtro exacto (case-insensitive)
                valor_doc = doc.get(campo, "")
                if valor_doc and str(valor_doc).lower() != str(valor).lower():
                    cumple = False
                    break

        if cumple:
            resultado.append(doc)

    return resultado


def _construir_query(subsector=None, producto=None,
                     periodo_texto=None, sector=None):
    """
    Construye el texto de consulta para el embedding.
    Cuanto más específica, mejor la recuperación semántica.
    """
    partes = []

    if sector:
        partes.append(sector)
    if subsector:
        partes.append(subsector.replace("_", " "))
    if producto:
        partes.append(producto)
    if periodo_texto:
        partes.append(periodo_texto)

    partes.append("producción coyuntura variación")

    return " ".join(partes)


# =====================================================
# BÚSQUEDA PRINCIPAL
# =====================================================

def buscar_documentos(
    sector,
    periodo,
    periodo_texto=None,
    subsector=None,
    producto=None,
    tipo=None,
    top_k=TOP_K_FINAL,
):
    """
    Busca los documentos más relevantes en el índice FAISS
    para un sector, periodo y contexto específicos.

    Flujo:
        1. Construye query semántica
        2. FAISS retorna top_k_candidatos más cercanos
        3. Filtra por metadata (sector, periodo, subsector, producto)
        4. Retorna top_k documentos finales

    Parámetros:
        sector:        nombre del sector (ej. "mineria_hidrocarburos")
        periodo:       periodo en formato YYYYMM (ej. "202502")
        periodo_texto: texto del periodo (ej. "febrero de 2025")
        subsector:     subsector específico o None para todo el sector
        producto:      producto específico o None para todo el subsector
        tipo:          tipo de documento ('coyuntural', 'institucional', 'precio')
                       o None para todos
        top_k:         número máximo de documentos a retornar

    Retorna:
        lista de dicts con metadata + texto, ordenados por relevancia
    """
    try:
        indice, documentos = cargar_indice()
    except FileNotFoundError as e:
        logger.warning(f"Índice no disponible: {e}")
        return []

    if indice.ntotal == 0:
        logger.warning("El índice FAISS está vacío.")
        return []

    # 1. Construir query y generar embedding
    query = _construir_query(
        subsector=subsector,
        producto=producto,
        periodo_texto=periodo_texto,
        sector=sector,
    )

    modelo = _get_modelo()
    query_embedding = modelo.encode(
        [query],
        normalize_embeddings=True
    ).astype("float32")

    # 2. Búsqueda FAISS — recuperar candidatos
    k_busqueda = min(TOP_K_CANDIDATOS, indice.ntotal)
    scores, indices = indice.search(query_embedding, k_busqueda)

    candidatos = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(documentos):
            continue
        doc = documentos[idx].copy()
        doc["_score_semantico"] = round(float(score), 4)
        candidatos.append(doc)

    # 3. Filtrar por metadata
    filtros = {
        "sector":    sector,
        "periodo":   periodo,
        "subsector": subsector,
        "producto":  producto,
        "tipo":      tipo,
    }
    candidatos_filtrados = _filtrar_por_metadata(candidatos, filtros)

    # Si el filtro es muy restrictivo y no hay resultados,
    # relajar subsector y producto pero mantener sector y periodo
    if not candidatos_filtrados and (subsector or producto):
        logger.info(
            f"Sin resultados con filtro específico "
            f"(subsector={subsector}, producto={producto}). "
            f"Relajando a nivel de sector."
        )
        filtros_relajados = {"sector": sector, "periodo": periodo}
        candidatos_filtrados = _filtrar_por_metadata(candidatos, filtros_relajados)

    # 4. Retornar top_k ordenados por score semántico
    candidatos_filtrados.sort(key=lambda x: x["_score_semantico"], reverse=True)
    resultado = candidatos_filtrados[:top_k]

    logger.info(
        f"Recuperación: query='{query[:60]}...', "
        f"candidatos={len(candidatos)}, "
        f"filtrados={len(candidatos_filtrados)}, "
        f"retornados={len(resultado)}"
    )

    return resultado


# =====================================================
# BÚSQUEDA POR CONTEXTO COMPLETO
# =====================================================

def buscar_por_contexto(contexto):
    """
    Punto de entrada principal desde context_enricher.py.
    Recibe el contexto del orquestador y lanza búsquedas
    focalizadas por subsector y por productos de alta incidencia.

    Retorna dict con documentos organizados por subsector y producto.
    """
    sector         = contexto.get("sector", {}).get("nombre", "")
    periodo        = contexto.get("periodo", "")
    periodo_texto  = contexto.get("periodo_texto", "")
    alta_incidencia = contexto.get("productos_alta_incidencia", {})

    # Normalizar nombre del sector para coincidir con carpeta
    sector_carpeta = (
        sector.lower()
        .replace(" e ", "_")
        .replace(" ", "_")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("á", "a")
        .replace("ú", "u")
    )

    resultados = {}

    # Búsqueda general del sector
    resultados["sector"] = buscar_documentos(
        sector=sector_carpeta,
        periodo=periodo,
        periodo_texto=periodo_texto,
        tipo="institucional",
        top_k=2,
    )

    # Búsqueda por subsector
    for subsector, productos in alta_incidencia.items():
        resultados[subsector] = buscar_documentos(
            sector=sector_carpeta,
            periodo=periodo,
            periodo_texto=periodo_texto,
            subsector=subsector,
            tipo="coyuntural",
            top_k=3,
        )

        # Búsqueda focalizada por cada producto de alta incidencia
        for producto in productos:
            clave = f"{subsector}__{producto.lower()}"
            resultados[clave] = buscar_documentos(
                sector=sector_carpeta,
                periodo=periodo,
                periodo_texto=periodo_texto,
                subsector=subsector,
                producto=producto,
                top_k=2,
            )

    total = sum(len(v) for v in resultados.values())
    logger.info(f"Recuperación total por contexto: {total} documentos")

    return resultados