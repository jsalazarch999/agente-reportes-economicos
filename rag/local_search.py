from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

CONTEXT_DIRS = {
    "Minería e Hidrocarburos": "mineria_hidrocarburos",
    "Pesca": "pesca",
    "Manufactura": "manufactura",
    "Agropecuario": "agropecuario"
}

def buscar_contexto_local(contexto, max_archivos=5):
    periodo = contexto.get("periodo", "")
    sector = contexto.get("sector", {}).get("nombre", "")

    nombre_carpeta = CONTEXT_DIRS.get(sector)

    if not nombre_carpeta:
        return {
            "fuentes": [],
            "texto": ""
        }

    carpeta = BASE_DIR / "data" / "corpus" / nombre_carpeta / "contexto"

    if not carpeta.exists():
        return {
            "fuentes": [],
            "texto": ""
        }

    archivos = sorted(
        carpeta.glob(f"{periodo}*.txt")
    )[:max_archivos]

    fuentes = []
    textos = []

    for archivo in archivos:
        contenido = archivo.read_text(encoding="utf-8")

        fuentes.append({
            "archivo": archivo.name,
            "ruta": str(archivo),
            "contenido": contenido
        })

        textos.append(
            f"Fuente local: {archivo.name}\n{contenido}"
        )

    return {
        "fuentes": fuentes,
        "texto": "\n\n".join(textos)
    }