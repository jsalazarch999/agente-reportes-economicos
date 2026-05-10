import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


def get_tavily_client():
    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        raise ValueError("No se encontró TAVILY_API_KEY en el archivo .env")

    return TavilyClient(api_key=api_key)


def buscar_web(query, max_results=10, topic="news"):
    """
    Busca información web relevante para enriquecer el reporte.

    Parámetros:
    - query: texto de búsqueda
    - max_results: cantidad máxima de resultados
    - topic: "general", "news" o "finance"

    Retorna:
    - lista de fuentes relevantes con título, URL y resumen
    """

    client = get_tavily_client()

    response = client.search(
        query=query,
        max_results=max_results,
        topic=topic,
        include_answer=False
    )

    resultados = []

    for item in response.get("results", []):
        resultados.append({
            "titulo": item.get("title", ""),
            "url": item.get("url", ""),
            "contenido": item.get("content", ""),
            "score": item.get("score", None),
        })

    return resultados


def construir_query_sector(contexto):
    periodo = contexto.get("periodo_texto", "")
    sector = contexto.get("sector", {}).get("nombre", "")

    query = (
        f'Perú "{sector}" "{periodo}" '
        f'coyuntura producción minería hidrocarburos '
        f'mantenimiento paralización huelga lluvias emergencia accidente ducto TGP Camisea '
        f'lote Pluspetrol Repsol Toromocho Minsur San Rafael '
        f'MINEM Perupetro Gestión Rumbo Minero'
    )

    return query

def buscar_contexto_web(contexto, max_results=10):
    """
    Función principal para usar en el agente:
    contexto estructurado → búsqueda web → fuentes relevantes.
    """

    query = construir_query_sector(contexto)

    fuentes = buscar_web(
        query=query,
        max_results=max_results,
        topic="news"
    )

    anio = contexto.get("periodo", "")[:4]
    fuentes = filtrar_fuentes_relevantes(fuentes, anio=anio)

    return {
        "query": query,
        "fuentes": fuentes
    }

def filtrar_fuentes_relevantes(fuentes, anio="2026"):
    filtradas = []

    fuentes_validas = [
        "minem",
        "bcrp",
        "perupetro",
        "reuters",
        "gestion",
        "mining.com",
        "rumbominero.com",
        "larepublica.pe",
        "expreso.com.pe",
        "mineriaenergia.com",
        "energiminas.com",
        "proactivo.com.pe",
        "andina.pe",
    ]

    for f in fuentes:
        texto = (
            f"{f.get('titulo', '')} "
            f"{f.get('contenido', '')} "
            f"{f.get('url', '')}"
        ).lower()

        if anio in texto and any(fuente in texto for fuente in fuentes_validas):
            filtradas.append(f)

    return filtradas