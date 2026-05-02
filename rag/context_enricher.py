from rag.web_search import buscar_contexto_web
from rag.source_filter import priorizar_fuentes, resumir_fuentes_para_llm


def enriquecer_contexto_con_web(contexto, max_fuentes=3):
    """
    Enriquece el contexto del reporte con fuentes web relevantes.

    No reemplaza los datos del Excel.
    Solo agrega contexto coyuntural externo.
    """

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

    contexto_enriquecido = contexto.copy()

    contexto_enriquecido["contexto_web"] = {
        "query": resultado_busqueda.get("query"),
        "fuentes": fuentes_priorizadas,
        "resumen_para_llm": resumen_fuentes
    }

    return contexto_enriquecido


def tiene_contexto_web(contexto):
    """
    Verifica si el contexto ya contiene fuentes web.
    """

    return (
        "contexto_web" in contexto
        and contexto["contexto_web"].get("fuentes")
    )


if __name__ == "__main__":
    contexto_prueba = {
        "periodo_texto": "febrero de 2026",
        "sector": {
            "nombre": "Minería e Hidrocarburos"
        },
        "subsector_hidrocarburos": {
            "variacion_interanual": -9.73,
            "productos_negativos": [
                {"nombre": "petróleo crudo"},
                {"nombre": "líquidos de gas natural"}
            ]
        },
        "subsector_mineria_metalica": {
            "variacion_interanual": 0.13,
            "productos_negativos": [
                {"nombre": "molibdeno"},
                {"nombre": "plata"}
            ]
        }
    }

    contexto_enriquecido = enriquecer_contexto_con_web(
        contexto_prueba,
        max_fuentes=3
    )

    print("\nQUERY:")
    print(contexto_enriquecido["contexto_web"]["query"])

    print("\nFUENTES PRIORIZADAS:")
    for fuente in contexto_enriquecido["contexto_web"]["fuentes"]:
        print("-", fuente["titulo"])
        print(" ", fuente["url"])

    print("\nRESUMEN PARA LLM:")
    print(contexto_enriquecido["contexto_web"]["resumen_para_llm"])