import logging
import numpy as np
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# =====================================================
# CONSTANTES
# =====================================================

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Umbral de similitud coseno para considerar un párrafo fundamentado
# < 0.40 → alucinación probable
# 0.40–0.60 → evidencia débil
# > 0.60 → bien fundamentado
# > 0.75 → muy bien fundamentado
UMBRAL_ALUCINACION  = 0.40
UMBRAL_DEBIL        = 0.60
UMBRAL_BUENO        = 0.75


# =====================================================
# MODELO
# =====================================================

@lru_cache(maxsize=1)
def _get_modelo():
    """Carga el modelo de embeddings una sola vez."""
    return SentenceTransformer(MODEL_NAME)


# =====================================================
# CÁLCULO DE GROUNDING
# =====================================================

def _similitud_parrafo_contexto(parrafo, textos_contexto):
    """
    Calcula la similitud coseno entre un párrafo y
    cada texto del contexto recuperado.

    Retorna el score máximo encontrado — si al menos
    un documento del corpus respalda el párrafo,
    el grounding es válido.
    """
    if not parrafo or not parrafo.strip():
        return 0.0

    if not textos_contexto:
        return 0.0

    modelo = _get_modelo()

    emb_parrafo   = modelo.encode([parrafo],         normalize_embeddings=True)
    emb_contextos = modelo.encode(textos_contexto,   normalize_embeddings=True)

    similitudes = cosine_similarity(emb_parrafo, emb_contextos)[0]
    return float(np.max(similitudes))


def _extraer_textos_contexto(bloque_rag):
    """
    Extrae los textos de un bloque del contexto RAG.
    Combina documentos locales y web.
    """
    textos = []

    for doc in bloque_rag.get("local", []):
        texto = doc.get("texto", "").strip()
        if texto:
            textos.append(texto)

    for doc in bloque_rag.get("web", []):
        contenido = doc.get("contenido", "").strip()
        if contenido:
            textos.append(contenido)

    return textos


def _clasificar_score(score):
    """
    Clasifica el score de grounding en una categoría.
    """
    if score >= UMBRAL_BUENO:
        return "bien_fundamentado"
    elif score >= UMBRAL_DEBIL:
        return "evidencia_debil"
    elif score >= UMBRAL_ALUCINACION:
        return "evidencia_minima"
    else:
        return "posible_alucinacion"


# =====================================================
# VERIFICACIÓN POR PÁRRAFO
# =====================================================

def verificar_fundamentacion(parrafo, clave_rag, contexto_rag):
    """
    Verifica el grounding de un párrafo de fundamentación
    contra el contexto RAG recuperado para esa clave.

    Parámetros:
        parrafo:     texto del párrafo de fundamentación
        clave_rag:   clave del contexto ('mineria_metalica',
                     'mineria_metalica__cobre', etc.)
        contexto_rag: dict completo del contexto enriquecido

    Retorna:
        dict con score, clasificacion, advertencia
    """
    # Buscar el bloque RAG correspondiente a esta clave
    bloque = contexto_rag.get(clave_rag, {})
    textos = _extraer_textos_contexto(bloque)

    # Si no hay contexto recuperado para esta clave,
    # buscar en claves más generales
    if not textos:
        # ej: si no hay contexto para 'mineria_metalica__cobre',
        # buscar en 'mineria_metalica'
        clave_padre = clave_rag.split("__")[0] if "__" in clave_rag else None
        if clave_padre:
            bloque_padre = contexto_rag.get(clave_padre, {})
            textos = _extraer_textos_contexto(bloque_padre)

    if not textos:
        logger.debug(
            f"Sin contexto RAG para clave '{clave_rag}' — "
            "grounding no verificable."
        )
        return {
            "score":          None,
            "clasificacion":  "sin_contexto",
            "advertencia":    (
                f"No hay contexto RAG para '{clave_rag}'. "
                "No es posible verificar el grounding."
            ),
            "verificable":    False,
        }

    score         = _similitud_parrafo_contexto(parrafo, textos)
    clasificacion = _clasificar_score(score)
    advertencia   = ""

    if clasificacion == "posible_alucinacion":
        advertencia = (
            f"Posible alucinación en fundamentación de '{clave_rag}' "
            f"(score={score:.2f}). El párrafo podría no estar respaldado "
            "por el corpus recuperado."
        )
    elif clasificacion == "evidencia_minima":
        advertencia = (
            f"Evidencia mínima para fundamentación de '{clave_rag}' "
            f"(score={score:.2f}). Verificar manualmente."
        )
    elif clasificacion == "evidencia_debil":
        advertencia = (
            f"Evidencia débil para fundamentación de '{clave_rag}' "
            f"(score={score:.2f})."
        )

    return {
        "score":         round(score, 3),
        "clasificacion": clasificacion,
        "advertencia":   advertencia,
        "verificable":   True,
    }


# =====================================================
# VERIFICACIÓN DEL REPORTE COMPLETO
# =====================================================

def verificar_grounding_reporte(fundamentaciones, contexto_rag):
    """
    Verifica el grounding de todas las fundamentaciones
    generadas para un reporte.

    Parámetros:
        fundamentaciones: dict {clave: texto_parrafo}
                          retornado por generator.py
        contexto_rag:     dict del contexto enriquecido

    Retorna:
        dict con:
            - score_global:      float — promedio de scores verificables
            - resultados:        dict por clave con score y clasificación
            - advertencias:      list de advertencias
            - valido:            bool — True si score_global >= UMBRAL_DEBIL
    """
    if not fundamentaciones:
        return {
            "score_global":  None,
            "resultados":    {},
            "advertencias":  [],
            "valido":        True,  # sin fundamentaciones = no hay qué verificar
        }

    if not contexto_rag:
        logger.warning(
            "No hay contexto RAG disponible para verificar grounding. "
            "Activar RAG para habilitar esta métrica."
        )
        return {
            "score_global":  None,
            "resultados":    {},
            "advertencias":  ["RAG no activado — grounding no verificable."],
            "valido":        True,
        }

    resultados   = {}
    advertencias = []
    scores       = []

    for clave, parrafo in fundamentaciones.items():
        if not parrafo or not parrafo.strip():
            continue

        resultado = verificar_fundamentacion(
            parrafo=parrafo,
            clave_rag=clave,
            contexto_rag=contexto_rag,
        )
        resultados[clave] = resultado

        if resultado["verificable"] and resultado["score"] is not None:
            scores.append(resultado["score"])

        if resultado["advertencia"]:
            advertencias.append(resultado["advertencia"])

    # Score global: promedio de scores verificables
    score_global = round(float(np.mean(scores)), 3) if scores else None

    valido = (
        score_global is None or
        score_global >= UMBRAL_ALUCINACION
    )

    logger.info(
        f"Grounding verificado: {len(resultados)} fundamentaciones, "
        f"score_global={score_global}, valido={valido}"
    )

    return {
        "score_global":  score_global,
        "resultados":    resultados,
        "advertencias":  advertencias,
        "valido":        valido,
    }


# =====================================================
# RESUMEN PARA LA UI
# =====================================================

def resumen_grounding(resultado_grounding):
    """
    Genera un resumen legible del resultado de grounding
    para mostrar en la interfaz al analista.

    Retorna lista de strings con el diagnóstico por clave.
    """
    lineas = []
    resultados = resultado_grounding.get("resultados", {})

    for clave, res in resultados.items():
        nombre = clave.replace("__", " → ").replace("_", " ").title()
        score  = res.get("score")
        clasif = res.get("clasificacion", "")

        if not res.get("verificable"):
            lineas.append(f"⚪ {nombre}: sin contexto RAG")
            continue

        emoji = {
            "bien_fundamentado":  "🟢",
            "evidencia_debil":    "🟡",
            "evidencia_minima":   "🟠",
            "posible_alucinacion": "🔴",
        }.get(clasif, "⚪")

        lineas.append(
            f"{emoji} {nombre}: score={score:.2f} ({clasif.replace('_', ' ')})"
        )

    return lineas