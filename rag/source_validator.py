import re
import logging
from urllib.parse import urlparse

# Importar desde web_agent — fuente única de verdad
from rag.web_agent import DOMINIOS as TODOS_LOS_DOMINIOS

logger = logging.getLogger(__name__)

# =====================================================
# CONSTANTES PROPIAS
# =====================================================

MIN_CHARS_CONTENIDO = 80

PATRONES_BASURA = [
    r"404\s*not\s*found",
    r"page\s*not\s*found",
    r"access\s*denied",
    r"error\s*403",
    r"suscr[ií]base\s*para\s*ver",
    r"contenido\s*exclusivo\s*para\s*suscriptores",
    r"inicie\s*sesi[oó]n",
    r"javascript\s*is\s*required",
]
_REGEX_BASURA = re.compile(
    "|".join(PATRONES_BASURA),
    re.IGNORECASE
)

TERMINOS_MINIMOS = [
    "producción", "minería", "hidrocarburos", "sector",
    "extracción", "petróleo", "gas", "cobre", "oro",
    "pesca", "manufactura", "agropecuario",
    # inglés
    "mining", "production", "petroleum", "copper",
]


# =====================================================
# VALIDACIONES
# =====================================================

def validar_dominio(url):
    """
    Verifica la URL y retorna su nivel de confianza.
    Dominios desconocidos se aceptan con nivel 99 — no se rechazan.
    """
    if not url:
        return False, 99, ""

    try:
        dominio = urlparse(url).netloc.lower()
        dominio = re.sub(r"^www\.", "", dominio)
    except Exception:
        return False, 99, ""

    for nivel, lista in TODOS_LOS_DOMINIOS.items():
        if any(d in dominio for d in lista):
            return True, nivel, dominio

    # Dominio desconocido — aceptar con nivel 99, no rechazar
    return True, 99, dominio


def validar_contenido(contenido):
    if not contenido or not contenido.strip():
        return False, "contenido vacío"
    if len(contenido.strip()) < MIN_CHARS_CONTENIDO:
        return False, f"contenido muy corto ({len(contenido.strip())} chars)"
    if _REGEX_BASURA.search(contenido):
        return False, "contenido de error o paywall detectado"
    return True, "ok"


def validar_relevancia_tematica(titulo, contenido):
    texto = f"{titulo} {contenido}".lower()
    encontrados = [t for t in TERMINOS_MINIMOS if t in texto]
    return len(encontrados) > 0, encontrados


def validar_periodo(titulo, contenido, periodo):
    if not periodo:
        return True, ""
    anio = str(periodo)[:4]
    texto = f"{titulo} {contenido}".lower()
    if anio in texto:
        return True, anio
    return False, anio


# =====================================================
# VALIDACIÓN COMPLETA
# =====================================================

def validar_resultado(resultado, periodo=None):
    url       = resultado.get("url", "")
    titulo    = resultado.get("titulo", "")
    contenido = resultado.get("contenido", "")

    advertencias  = []
    razon_rechazo = ""

    # Filtro 1: dominio
    dominio_valido, nivel, dominio = validar_dominio(url)
    if not dominio_valido:
        return {
            "valido":          False,
            "nivel_confianza": 99,
            "advertencias":    [],
            "razon_rechazo":   f"URL inválida: '{url}'",
        }

    # Advertencias por nivel
    if nivel == 3:
        advertencias.append(
            f"Fuente de prensa general (nivel 3): {dominio}."
        )
    elif nivel == 4:
        advertencias.append(
            f"Fuente internacional en inglés (nivel 4): {dominio}."
        )
    elif nivel == 99:
        advertencias.append(
            f"Fuente no clasificada (nivel 99): {dominio}. Verificar cuidadosamente."
        )

    # Filtro 2: contenido
    contenido_valido, razon_contenido = validar_contenido(contenido)
    if not contenido_valido:
        return {
            "valido":          False,
            "nivel_confianza": nivel,
            "advertencias":    advertencias,
            "razon_rechazo":   f"contenido inválido: {razon_contenido}",
        }

    # Filtro 3: relevancia temática
    es_relevante, terminos = validar_relevancia_tematica(titulo, contenido)
    if not es_relevante:
        return {
            "valido":          False,
            "nivel_confianza": nivel,
            "advertencias":    advertencias,
            "razon_rechazo":   "sin términos temáticos relevantes",
        }

    # Filtro 4: periodo (solo advertencia)
    if periodo:
        periodo_valido, anio = validar_periodo(titulo, contenido, periodo)
        if not periodo_valido:
            advertencias.append(
                f"El resultado no menciona el año {anio}. "
                "Podría ser información desactualizada."
            )

    return {
        "valido":          True,
        "nivel_confianza": nivel,
        "advertencias":    advertencias,
        "razon_rechazo":   "",
    }


def validar_resultados(resultados, periodo=None):
    validos               = []
    advertencias_globales = []
    rechazados            = 0

    for resultado in resultados:
        evaluacion = validar_resultado(resultado, periodo)

        if evaluacion["valido"]:
            resultado_enriquecido = {
                **resultado,
                "nivel_confianza": evaluacion["nivel_confianza"],
                "advertencias":    evaluacion["advertencias"],
            }
            validos.append(resultado_enriquecido)
            advertencias_globales.extend(evaluacion["advertencias"])
        else:
            rechazados += 1
            logger.debug(
                f"Rechazado: {resultado.get('url', '')} "
                f"— {evaluacion['razon_rechazo']}"
            )

    advertencias_globales = list(dict.fromkeys(advertencias_globales))

    logger.info(
        f"Validación: {len(validos)} válidos, "
        f"{rechazados} rechazados de {len(resultados)} totales."
    )

    return validos, advertencias_globales