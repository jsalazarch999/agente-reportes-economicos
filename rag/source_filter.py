def priorizar_fuentes(fuentes, max_fuentes=3):
    prioridad = {
        "minem": 1,
        "bcrp": 2,
        "perupetro": 3,
        "reuters": 4,
        "gestion": 5,
        "rumbominero": 6,
        "mining.com": 7,
        "larepublica": 8,
        "expreso": 9,
        "mineriaenergia": 10,
    }

    fuentes_rankeadas = []

    for fuente in fuentes:
        url = fuente.get("url", "").lower()
        ranking = 999

        for dominio, score in prioridad.items():
            if dominio in url:
                ranking = score
                break

        fuente_rankeada = fuente.copy()
        fuente_rankeada["ranking"] = ranking
        fuentes_rankeadas.append(fuente_rankeada)

    return sorted(fuentes_rankeadas, key=lambda x: x["ranking"])[:max_fuentes]

def limpiar_contenido(texto):
    if not texto:
        return ""

    basura = [
        "Logo gob.peLogo gob.pe",
        "Logo gob.pe",
        "# Ministerio de Energía y Minas.",
    ]

    for b in basura:
        texto = texto.replace(b, "")

    return texto.strip()

def resumir_fuentes_para_llm(fuentes):
    """
    Convierte fuentes filtradas en texto corto para el LLM
    """

    bloques = []

    for f in fuentes:
        bloque = f"""
Título: {f.get("titulo")}
Resumen: {limpiar_contenido(f.get("contenido", ""))}
Fuente: {f.get("url")}
"""
        bloques.append(bloque.strip())

    return "\n\n".join(bloques)