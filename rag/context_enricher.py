import copy
import logging
from rag.retriever import buscar_por_contexto
from rag.web_agent import buscar_web_por_contexto
from rag.source_validator import validar_resultados
from rag.source_filter import resumir_fuentes_para_llm

logger = logging.getLogger(__name__)

# Número máximo de caracteres del resumen por clave de contexto
MAX_CHARS_RESUMEN = 2_000


# =====================================================
# HELPERS
# =====================================================

def _resumir_documentos_locales(documentos):
    """
    Convierte lista de documentos FAISS en texto para el LLM.
    Incluye la fuente de cada documento para trazabilidad.
    """
    if not documentos:
        return ""

    bloques = []
    for doc in documentos:
        fuente  = doc.get("fuente", "desconocida")
        periodo = doc.get("periodo", "")
        texto   = doc.get("texto", "").strip()

        if not texto:
            continue

        encabezado = f"[Fuente: {fuente}"
        if periodo:
            encabezado += f" | Periodo: {periodo}"
        encabezado += "]"

        bloques.append(f"{encabezado}\n{texto}")

    resumen = "\n\n".join(bloques)

    # Truncar si excede el límite
    if len(resumen) > MAX_CHARS_RESUMEN:
        resumen = resumen[:MAX_CHARS_RESUMEN] + "..."

    return resumen


def _construir_bloque_vacio():
    """Retorna un bloque de contexto vacío estándar."""
    return {
        "local":      [],
        "web":        [],
        "resumen":    "",
        "advertencias": [],
    }


def _combinar_fuentes(docs_locales, docs_web):
    """
    Combina documentos locales y web en un resumen unificado.
    Prioridad: local > web (los locales aparecen primero).
    """
    resumen_local = _resumir_documentos_locales(docs_locales)
    resumen_web   = resumir_fuentes_para_llm(docs_web) if docs_web else ""

    partes = []
    if resumen_local:
        partes.append(f"CONTEXTO LOCAL CURADO:\n{resumen_local}")
    if resumen_web:
        partes.append(f"CONTEXTO WEB VERIFICADO:\n{resumen_web}")

    return "\n\n".join(partes) if partes else ""


# =====================================================
# ENRIQUECIMIENTO PRINCIPAL
# =====================================================

def enriquecer_contexto_rag(contexto, usar_web=True):
    """
    Enriquece el contexto con fuentes locales (FAISS) y web verificada.

    Organiza el contexto por clave (sector, subsector, producto)
    para que generator.py sepa exactamente qué contexto usar
    en cada párrafo del reporte.

    Parámetros:
        contexto:  dict del orquestador con sector, periodo,
                   productos_alta_incidencia, etc.
        usar_web:  bool — si False, solo usa corpus local.
                   Útil cuando los datos son confidenciales.

    Retorna:
        contexto enriquecido con campo 'contexto_rag' organizado
        por clave: sector / subsector / subsector__producto
    """
    contexto_enriquecido = copy.deepcopy(contexto)
    advertencias_globales = []

    # =====================================================
    # 1. RECUPERACIÓN LOCAL (FAISS)
    # =====================================================
    docs_locales = {}
    try:
        docs_locales = buscar_por_contexto(contexto)
        logger.info(
            f"FAISS: {sum(len(v) for v in docs_locales.values())} "
            f"documentos recuperados en {len(docs_locales)} claves."
        )
    except FileNotFoundError:
        logger.warning(
            "Índice FAISS no disponible. "
            "Ejecuta 'python scripts/build_index.py' para construirlo. "
            "Continuando solo con fuentes web."
        )
    except Exception as e:
        logger.warning(f"Error en recuperación FAISS: {e}")

    # =====================================================
    # 2. BÚSQUEDA WEB (opcional)
    # =====================================================
    docs_web        = {}
    advertencias_web = []

    if usar_web:
        try:
            resultado_web    = buscar_web_por_contexto(contexto)
            docs_web_crudos  = resultado_web.get("resultados", {})
            advertencias_web = resultado_web.get("advertencias", [])

            # Validar cada grupo de resultados web
            for clave, resultados in docs_web_crudos.items():
                periodo = contexto.get("periodo", "")
                validos, advs = validar_resultados(resultados, periodo)
                docs_web[clave] = validos
                advertencias_web.extend(advs)

            advertencias_web = list(dict.fromkeys(advertencias_web))
            advertencias_globales.extend(advertencias_web)

            logger.info(
                f"Web: {sum(len(v) for v in docs_web.values())} "
                f"documentos válidos en {len(docs_web)} claves."
            )
        except Exception as e:
            logger.warning(f"Error en búsqueda web: {e}")

    # =====================================================
    # 3. ENSAMBLAR CONTEXTO POR CLAVE
    # =====================================================
    # Las claves son: 'sector', 'mineria_metalica', 'hidrocarburos',
    # 'mineria_metalica__cobre', 'hidrocarburos__gas_natural', etc.

    todas_las_claves = set(docs_locales.keys()) | set(docs_web.keys())
    contexto_rag     = {}

    for clave in todas_las_claves:
        locales = docs_locales.get(clave, [])
        web     = docs_web.get(clave, [])

        if not locales and not web:
            continue

        resumen = _combinar_fuentes(locales, web)

        # Recopilar advertencias específicas de esta clave
        advs_clave = []
        for doc in web:
            advs_clave.extend(doc.get("advertencias", []))

        contexto_rag[clave] = {
            "local":        locales,
            "web":          web,
            "resumen":      resumen,
            "advertencias": list(dict.fromkeys(advs_clave)),
        }

    # Si no hay ningún contexto recuperado
    if not contexto_rag:
        logger.warning(
            "No se recuperó contexto RAG de ninguna fuente. "
            "Los párrafos de fundamentación estarán vacíos."
        )

    # =====================================================
    # 4. RESUMEN PLANO PARA COMPATIBILIDAD
    # =====================================================
    # Mantener contexto_local y contexto_web para compatibilidad
    # con el sistema anterior mientras se migra completamente.

    resumen_local_plano = _resumir_documentos_locales(
        [doc for docs in docs_locales.values() for doc in docs]
    )
    resumen_web_plano = resumir_fuentes_para_llm(
        [doc for docs in docs_web.values() for doc in docs]
    ) if docs_web else ""

    contexto_enriquecido["contexto_rag"]   = contexto_rag
    contexto_enriquecido["contexto_local"] = {
        "fuentes":          [doc for docs in docs_locales.values() for doc in docs],
        "resumen_para_llm": resumen_local_plano or "No se encontró contexto local.",
    }
    contexto_enriquecido["contexto_web"] = {
        "fuentes":          [doc for docs in docs_web.values() for doc in docs],
        "resumen_para_llm": resumen_web_plano or "No se encontraron fuentes web relevantes.",
        "advertencias":     advertencias_globales,
    }

    logger.info(
        f"Contexto RAG ensamblado: {len(contexto_rag)} claves, "
        f"{len(advertencias_globales)} advertencias."
    )

    return contexto_enriquecido