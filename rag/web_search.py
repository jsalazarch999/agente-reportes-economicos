import os
import logging
from functools import lru_cache
from tavily import TavilyClient

logger = logging.getLogger(__name__)

# =====================================================
# TÉRMINOS DE BÚSQUEDA POR SECTOR
# =====================================================

TERMINOS_SECTOR = {
    "Minería e Hidrocarburos": {
        "generales": "coyuntura producción minería hidrocarburos mantenimiento paralización huelga lluvias emergencia accidente",
        "especificos": "ducto TGP Camisea lote Pluspetrol Repsol Toromocho Minsur San Rafael MINEM Perupetro",
    },
    "Pesca": {
        "generales": "coyuntura producción pesca anchoveta vedas temporada",
        "especificos": "PRODUCE IMARPE flota pesquera Chimbote Ilo Paita",
    },
    "Manufactura": {
        "generales": "coyuntura producción manufactura industria paralización",
        "especificos": "PRODUCE SNI parque industrial Lima",
    },
    "Agropecuario": {
        "generales": "coyuntura producción agropecuaria cosecha sequía helada",
        "especificos": "MINAGRI Senasa irrigación sierra selva",
    },
}

# Dominios válidos — fuente única compartida con source_filter.py
DOMINIOS_VALIDOS = [
    "minem", "bcrp", "perupetro", "reuters", "gestion",
    "mining.com", "rumbominero.com", "larepublica.pe",
    "expreso.com.pe", "mineriaenergia.com", "energiminas.com",
    "proactivo.com.pe", "andina.pe",
]


# =====================================================
# CLIENTE
# =====================================================

@lru_cache(maxsize=1)
def _get_tavily_client():
    """Instancia el cliente Tavily una sola vez."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("No se encontró TAVILY_API_KEY en el archivo .env")
    return TavilyClient(api_key=api_key)


# =====================================================
# FUNCIONES
# =====================================================

def construir_query_sector(contexto):
    """Construye la query de búsqueda según el sector y periodo del contexto."""
    periodo  = contexto.get("periodo_texto", "")
    sector   = contexto.get("sector", {}).get("nombre", "")
    terminos = TERMINOS_SECTOR.get(sector, {})

    generales  = terminos.get("generales", "producción coyuntura")
    especificos = terminos.get("especificos", "")

    return (
        f'Perú "{sector}" "{periodo}" '
        f'{generales} {especificos} '
        f'Gestión Rumbo Minero'
    ).strip()


def buscar_web(query, max_results=10, topic="news"):
    """
    Envía la query a Tavily y retorna lista de fuentes con
    título, URL, contenido y score.
    """
    client = _get_tavily_client()

    try:
        response = client.search(
            query=query,
            max_results=max_results,
            topic=topic,
            include_answer=False
        )
    except Exception as e:
        logger.error(f"Error en búsqueda Tavily: {e}")
        return []

    return [
        {
            "titulo":   item.get("title", ""),
            "url":      item.get("url", ""),
            "contenido": item.get("content", ""),
            "score":    item.get("score"),
        }
        for item in response.get("results", [])
    ]


def filtrar_fuentes_relevantes(fuentes, anio=""):
    """
    Filtra fuentes para quedarse solo con dominios confiables.
    El filtro por año es opcional para no descartar fuentes con titulares cortos.
    """
    filtradas = []

    for f in fuentes:
        url  = f.get("url", "").lower()
        texto = f"{f.get('titulo', '')} {f.get('contenido', '')}".lower()

        es_dominio_valido = any(d in url for d in DOMINIOS_VALIDOS)
        contiene_anio     = not anio or anio in texto  # si no hay año, no filtra

        if es_dominio_valido and contiene_anio:
            filtradas.append(f)

    return filtradas


def buscar_contexto_web(contexto, max_results=10):
    """
    Función principal: contexto estructurado → búsqueda web → fuentes relevantes.
    """
    query  = construir_query_sector(contexto)
    anio   = str(contexto.get("periodo", ""))[:4]
    fuentes = buscar_web(query=query, max_results=max_results, topic="news")
    fuentes = filtrar_fuentes_relevantes(fuentes, anio=anio)

    return {"query": query, "fuentes": fuentes}