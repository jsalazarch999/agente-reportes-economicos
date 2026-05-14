import re

# =====================================================
# CONSTANTES
# =====================================================

RANKING_DEFAULT = 999  # fuentes sin dominio reconocido van al final

PRIORIDAD_DOMINIOS = {
    "minem":          1,
    "bcrp":           2,
    "perupetro":      3,
    "reuters":        4,
    "gestion":        5,
    "rumbominero":    6,
    "mining.com":     7,
    "larepublica":    8,
    "expreso":        9,
    "mineriaenergia": 10,
}

# Patrones de ruido comunes en scraping de sitios .gob.pe y otros
_PATRONES_BASURA = [
    r"Logo\s+gob\.pe\s*",
    r"#\s*Ministerio de Energía y Minas\.?\s*",
    r"Compartir en\s+\w+\s*",
    r"Síguenos en\s+\w+\s*",
    r"\s{3,}",  # espacios en blanco excesivos
]
_REGEX_BASURA = re.compile("|".join(_PATRONES_BASURA), re.IGNORECASE)

MAX_CHARS_POR_FUENTE = 1_500  # límite de caracteres por fuente al armar el prompt


# =====================================================
# FUNCIONES
# =====================================================

def priorizar_fuentes(fuentes, max_fuentes=3):
    """
    Ordena fuentes por confiabilidad según el dominio
    y retorna las mejores `max_fuentes`.
    """
    def _ranking(fuente):
        url = fuente.get("url", "").lower()
        for dominio, score in PRIORIDAD_DOMINIOS.items():
            if dominio in url:
                return score
        return RANKING_DEFAULT

    rankeadas = sorted(fuentes, key=_ranking)[:max_fuentes]

    # Agrega el ranking como metadato sin mutar el original
    return [
        {**f, "ranking": _ranking(f)}
        for f in rankeadas
    ]


def limpiar_contenido(texto):
    """
    Elimina ruido común de scraping (logos, headers, espacios excesivos).
    """
    if not texto:
        return ""

    texto = _REGEX_BASURA.sub(" ", texto)
    return " ".join(texto.split())  # normaliza espacios


def resumir_fuentes_para_llm(fuentes, max_chars=MAX_CHARS_POR_FUENTE):
    """
    Convierte fuentes filtradas en texto corto para el LLM.
    Limita el contenido de cada fuente a `max_chars` caracteres.
    """
    if not fuentes:
        return ""

    bloques = []

    for f in fuentes:
        contenido = limpiar_contenido(f.get("contenido", ""))

        # Truncar si excede el límite
        if len(contenido) > max_chars:
            contenido = contenido[:max_chars] + "..."

        bloque = (
            f"Título: {f.get('titulo', 'Sin título')}\n"
            f"Fuente: {f.get('url', 'Sin URL')}\n"
            f"Resumen: {contenido}"
        )
        bloques.append(bloque)

    return "\n\n".join(bloques)