from rag.web_search import buscar_contexto_web
from rag.local_search import buscar_contexto_local
from rag.source_filter import priorizar_fuentes, resumir_fuentes_para_llm


def enriquecer_contexto_rag(contexto, max_fuentes=3):
    """
    Enriquece el contexto con fuentes locales y web.

    Prioridad:
    1. Archivos locales curados
    2. Fuentes web complementarias
    """

    contexto_enriquecido = contexto.copy()

    # 1. Contexto local curado
    resultado_local = buscar_contexto_local(contexto)

    contexto_enriquecido["contexto_local"] = {
        "fuentes": resultado_local.get("fuentes", []),
        "resumen_para_llm": resultado_local.get("texto", "")
    }

    # 2. Contexto web
    resultado_busqueda = buscar_contexto_web(
        contexto=contexto,
        max_results=10
    )

    fuentes = resultado_busqueda.get("fuentes", [])

    fuentes_priorizadas = priorizar_fuentes(
        fuentes,
        max_fuentes=max_fuentes
    )

    resumen_fuentes = resumir_fuentes_para_llm(fuentes_priorizadas)

    contexto_enriquecido["contexto_web"] = {
        "query": resultado_busqueda.get("query"),
        "fuentes": fuentes_priorizadas,
        "resumen_para_llm": resumen_fuentes
    }

    return contexto_enriquecido