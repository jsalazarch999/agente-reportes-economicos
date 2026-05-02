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

    productos_negativos = []

    hidro_neg = contexto.get("subsector_hidrocarburos", {}).get("productos_negativos", [])
    mineria_neg = contexto.get("subsector_mineria_metalica", {}).get("productos_negativos", [])

    for p in hidro_neg[:2]:
        productos_negativos.append(p["nombre"])

    for p in mineria_neg[:2]:
        productos_negativos.append(p["nombre"])

    productos_texto = " ".join(productos_negativos)

    query = (
        f'Perú "{sector}" "{periodo}" '
        f'{productos_texto} causas producción '
        f'MINEM BCRP Perupetro Reuters Gestión Rumbo Minero'
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
        topic="general"
    )

    fuentes = filtrar_fuentes_relevantes(fuentes, anio="2026")

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
        "mineriaenergia.com"
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

    resultado = buscar_contexto_web(contexto_prueba)

    print("QUERY:")
    print(resultado["query"])

    print("\nFUENTES:")
    for fuente in resultado["fuentes"]:
        print("-", fuente["titulo"])
        print(" ", fuente["url"])