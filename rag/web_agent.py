import os
import logging
from functools import lru_cache
from eventregistry import EventRegistry, QueryArticlesIter, QueryItems

logger = logging.getLogger(__name__)

# =====================================================
# CONSTANTES
# =====================================================

DOMINIOS = {
    1: [
        "minem.gob.pe", "perupetro.com.pe", "bcrp.gob.pe",
        "produce.gob.pe", "minagri.gob.pe", "osinergmin.gob.pe",
        "andina.pe",
    ],
    2: [
        "rumbominero.com", "energiminas.com", "proactivo.com.pe",
        "mineriaenergia.com",
    ],
    3: [
        "gestion.pe", "elcomercio.pe", "larepublica.pe",
    ],
    4: [
        "mining.com", "bnamericas.com", "reuters.com",
        "spglobal.com", "mining-technology.com",
    ],
}

TERMINOS_COYUNTURALES = [
    "paralización", "mantenimiento", "huelga", "accidente",
    "lluvias", "emergencia", "restricción", "conflicto",
    "ducto", "lote", "yacimiento", "operaciones",
    "explosión", "rotura", "interrupción", "racionamiento",
    "shutdown", "maintenance", "strike", "emergency",
    "pipeline", "disruption", "outage", "halt",
]

TERMINOS_SECTOR = {
    "mineria_hidrocarburos": {
        "generales":   "producción coyuntura minería hidrocarburos",
        "especificos": "TGP Camisea Pluspetrol Antamina Southern Cerro Verde",
    },
    "pesca": {
        "generales":   "producción coyuntura pesca anchoveta",
        "especificos": "PRODUCE IMARPE veda flota pesquera",
    },
    "manufactura": {
        "generales":   "producción coyuntura manufactura industria",
        "especificos": "PRODUCE SNI parque industrial",
    },
    "agropecuario": {
        "generales":   "producción coyuntura agropecuaria cosecha",
        "especificos": "MINAGRI Senasa irrigación",
    },
}

MAX_CHARS_CONTENIDO = 1_500


# =====================================================
# CLIENTES
# =====================================================

@lru_cache(maxsize=1)
def _get_cliente_newsapi():
    """Instancia el cliente NewsAPI.ai una sola vez."""
    api_key = os.getenv("NEWSAPI_AI_KEY")
    if not api_key:
        raise ValueError("No se encontró NEWSAPI_AI_KEY en .env")
    return EventRegistry(apiKey=api_key)


@lru_cache(maxsize=1)
def _get_cliente_tavily():
    """Instancia el cliente Tavily una sola vez."""
    from tavily import TavilyClient
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("No se encontró TAVILY_API_KEY en .env")
    return TavilyClient(api_key=api_key)


# =====================================================
# CONSTRUCCIÓN DE QUERIES
# =====================================================

def _construir_query(sector, periodo_texto, subsector=None, producto=None):
    terminos    = TERMINOS_SECTOR.get(sector, {})
    generales   = terminos.get("generales", "producción coyuntura")
    especificos = terminos.get("especificos", "")

    foco = ""
    if subsector:
        foco += f" {subsector.replace('_', ' ')}"
    if producto:
        foco += f" {producto}"

    partes = [
        "Perú",
        f'"{periodo_texto}"' if periodo_texto else "",
        generales,
        especificos,
        foco,
    ]
    return " ".join(p for p in partes if p).strip()


# =====================================================
# BÚSQUEDAS
# =====================================================

def _buscar_newsapi(query, periodo, subsector=None, max_results=10):
    """Busca en NewsAPI.ai filtrado por idioma español y fechas del periodo."""
    try:
        er = _get_cliente_newsapi()

        anio = str(periodo)[:4]
        mes  = str(periodo)[4:6]
        fecha_inicio = f"{anio}-{mes}-01"
        ultimo_dia = "28" if mes == "02" else "30" if mes in ["04","06","09","11"] else "31"
        fecha_fin  = f"{anio}-{mes}-{ultimo_dia}"

        q = QueryArticlesIter(
            keywords=QueryItems.AND([query, "Perú"]),
            lang="spa",
            dateStart=fecha_inicio,
            dateEnd=fecha_fin,
            sortBy="rel",
            sortByAsc=False,
        )

        resultados = []
        for art in q.execQuery(er, maxItems=max_results):
            resultados.append({
                "title":   art.get("title", ""),
                "url":     art.get("url", ""),
                "content": art.get("body", art.get("description", "")),
                "score":   art.get("relevance", 0.5),
                "fuente":  "newsapi",
            })

        logger.info(f"NewsAPI.ai: {len(resultados)} resultados")
        return resultados

    except Exception as e:
        logger.warning(f"Error en NewsAPI.ai: {e}")
        return []


def _buscar_tavily(query, max_results=10):
    """Busca en Tavily como fuente complementaria."""
    try:
        cliente = _get_cliente_tavily()
        response = cliente.search(
            query=query,
            max_results=max_results,
            topic="news",
            include_answer=False,
        )
        resultados = []
        for r in response.get("results", []):
            resultados.append({
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "content": r.get("content", ""),
                "score":   r.get("score", 0.5),
                "fuente":  "tavily",
            })
        logger.info(f"Tavily: {len(resultados)} resultados")
        return resultados

    except Exception as e:
        logger.warning(f"Error en Tavily: {e}")
        return []


def _normalizar_resultado(item, nivel_confianza):
    """Convierte un resultado al formato interno."""
    contenido = item.get("content", "")
    if len(contenido) > MAX_CHARS_CONTENIDO:
        contenido = contenido[:MAX_CHARS_CONTENIDO] + "..."

    return {
        "titulo":          item.get("title", ""),
        "url":             item.get("url", ""),
        "contenido":       contenido,
        "score":           item.get("score", 0.5),
        "fuente":          item.get("fuente", "desconocida"),
        "nivel_confianza": nivel_confianza,
    }


# =====================================================
# FILTROS DE CALIDAD
# =====================================================

def _contiene_terminos_coyunturales(resultado):
    texto = (
        resultado.get("titulo", "") + " " +
        resultado.get("contenido", "")
    ).lower()
    return any(t in texto for t in TERMINOS_COYUNTURALES)


def _es_del_periodo(resultado, periodo):
    if not periodo:
        return True
    anio = str(periodo)[:4]
    texto = (
        resultado.get("titulo", "") + " " +
        resultado.get("contenido", "")
    ).lower()
    return anio in texto


def _es_relevante_para_peru(resultado, nivel):
    """
    Para fuentes no clasificadas (nivel 99),
    verifica que el contenido mencione Perú explícitamente.
    Fuentes conocidas (niveles 1-4) se confían por su dominio.
    """
    if nivel <= 4:
        return True

    texto = (
        resultado.get("titulo", "") + " " +
        resultado.get("contenido", "")
    ).lower()

    return "perú" in texto or "peru" in texto

def _determinar_nivel_confianza(url):
    url_lower = url.lower()
    for nivel, dominios in DOMINIOS.items():
        if any(d in url_lower for d in dominios):
            return nivel
    return 99


# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================

def buscar_web(sector, periodo, periodo_texto,
               subsector=None, producto=None, max_resultados=8):

    tiene_newsapi = bool(os.getenv("NEWSAPI_AI_KEY"))
    tiene_tavily  = bool(os.getenv("TAVILY_API_KEY"))

    if not tiene_newsapi and not tiene_tavily:
        logger.warning("Sin APIs de búsqueda configuradas.")
        return {"query": "", "resultados": [], "advertencias": []}

    query = _construir_query(sector, periodo_texto, subsector, producto)

    # Buscar en ambas fuentes y combinar
    crudos = []

    if tiene_newsapi:
        crudos.extend(_buscar_newsapi(
            query, periodo,
            subsector=subsector,
            max_results=max_resultados
        ))

    if tiene_tavily:
        crudos.extend(_buscar_tavily(query, max_results=max_resultados))

    # Deduplicar por URL
    urls_vistas = set()
    crudos_unicos = []
    for r in crudos:
        url = r.get("url", "")
        if url and url not in urls_vistas:
            urls_vistas.add(url)
            crudos_unicos.append(r)



    # Normalizar
    resultados_acumulados = []
    for item in crudos_unicos:
        nivel = _determinar_nivel_confianza(item.get("url", ""))
        resultados_acumulados.append(_normalizar_resultado(item, nivel))

    advertencias = []

    # Filtro 1: dominio conocido + año + términos + Perú
    filtrados = [
        r for r in resultados_acumulados
        if r["nivel_confianza"] <= 4
        and _es_del_periodo(r, periodo)
        and _contiene_terminos_coyunturales(r)
        and _es_relevante_para_peru(r, r["nivel_confianza"])
    ]

    # Filtro 2: cualquier dominio + año + términos + Perú
    if not filtrados:
        filtrados = [
            r for r in resultados_acumulados
            if _es_del_periodo(r, periodo)
            and _contiene_terminos_coyunturales(r)
            and _es_relevante_para_peru(r, r["nivel_confianza"])
        ]

    # Filtro 3: solo año + Perú (último recurso)
    if not filtrados:
        filtrados = [
            r for r in resultados_acumulados
            if _es_del_periodo(r, periodo)
            and _es_relevante_para_peru(r, r["nivel_confianza"])
        ]

    # Advertencias por nivel
    niveles = [r.get("nivel_confianza", 99) for r in filtrados]
    if any(n == 3 for n in niveles):
        advertencias.append(
            "Parte de la fundamentación usa fuentes de prensa general "
            "(nivel 3). Verificar antes de publicar."
        )
    if any(n == 4 for n in niveles):
        advertencias.append(
            "Parte de la fundamentación usa fuentes internacionales en inglés "
            "(nivel 4). Verificar relevancia antes de publicar."
        )
    if any(n == 99 for n in niveles):
        advertencias.append(
            "Parte de la fundamentación usa fuentes no clasificadas "
            "(nivel 99). Verificar cuidadosamente antes de publicar."
        )

    # Ordenar por nivel y score — usando "score" en vez de "score_tavily"
    filtrados.sort(key=lambda x: (
        x["nivel_confianza"],
        -(x.get("score") or 0)
    ))

    return {
        "query":       query,
        "resultados":  filtrados[:max_resultados],
        "advertencias": advertencias,
    }


def buscar_web_por_contexto(contexto):
    sector        = contexto.get("sector", {}).get("nombre", "")
    periodo       = contexto.get("periodo", "")
    periodo_texto = contexto.get("periodo_texto", "")
    alta_inc      = contexto.get("productos_alta_incidencia", {})

    sector_clave = (
        sector.lower()
        .replace(" e ", "_")
        .replace(" ", "_")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("á", "a")
        .replace("ú", "u")
    )

    resultados   = {}
    advertencias = []

    res_sector = buscar_web(
        sector=sector_clave,
        periodo=periodo,
        periodo_texto=periodo_texto,
        max_resultados=5,
    )
    resultados["sector"] = res_sector["resultados"]
    advertencias.extend(res_sector["advertencias"])

    for subsector, productos in alta_inc.items():
        res_sub = buscar_web(
            sector=sector_clave,
            periodo=periodo,
            periodo_texto=periodo_texto,
            subsector=subsector,
            max_resultados=4,
        )
        resultados[subsector] = res_sub["resultados"]
        advertencias.extend(res_sub["advertencias"])

        for producto in productos:
            clave = f"{subsector}__{producto.lower()}"
            res_prod = buscar_web(
                sector=sector_clave,
                periodo=periodo,
                periodo_texto=periodo_texto,
                subsector=subsector,
                producto=producto,
                max_resultados=3,
            )
            resultados[clave] = res_prod["resultados"]
            advertencias.extend(res_prod["advertencias"])

    advertencias = list(dict.fromkeys(advertencias))

    return {
        "resultados":   resultados,
        "advertencias": advertencias,
    }