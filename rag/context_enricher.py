import copy
import logging
from rag.web_search import buscar_contexto_web
from rag.local_search import buscar_contexto_local
from rag.source_filter import priorizar_fuentes, resumir_fuentes_para_llm

logger = logging.getLogger(__name__)


def enriquecer_contexto_rag(contexto, max_fuentes=3):
    """
    Enriquece el contexto con fuentes locales y web.

    Prioridad:
    1. Archivos locales curados
    2. Fuentes web complementarias

    Si alguna fuente falla, continúa con la que esté disponible
    en vez de interrumpir el flujo completo.
    """
    contexto_enriquecido = copy.deepcopy(contexto)

    # 1. Contexto local curado
    try:
        resultado_local = buscar_contexto_local(contexto)
        contexto_enriquecido["contexto_local"] = {
            "fuentes":         resultado_local.get("fuentes", []),
            "resumen_para_llm": resultado_local.get("texto") or "No se encontró contexto local."
        }
    except Exception as e:
        logger.warning(f"Error al buscar contexto local: {e}")
        contexto_enriquecido["contexto_local"] = {
            "fuentes":         [],
            "resumen_para_llm": "No se encontró contexto local."
        }

    # 2. Contexto web
    try:
        resultado_busqueda = buscar_contexto_web(contexto=contexto, max_results=10)
        fuentes = resultado_busqueda.get("fuentes", [])
        fuentes_priorizadas = priorizar_fuentes(fuentes, max_fuentes=max_fuentes)
        resumen_fuentes = resumir_fuentes_para_llm(fuentes_priorizadas)

        contexto_enriquecido["contexto_web"] = {
            "query":           resultado_busqueda.get("query", ""),
            "fuentes":         fuentes_priorizadas,
            "resumen_para_llm": resumen_fuentes or "No se encontraron fuentes web relevantes."
        }
    except Exception as e:
        logger.warning(f"Error al buscar contexto web: {e}")
        contexto_enriquecido["contexto_web"] = {
            "query":           "",
            "fuentes":         [],
            "resumen_para_llm": "No se encontraron fuentes web relevantes."
        }

    return contexto_enriquecido