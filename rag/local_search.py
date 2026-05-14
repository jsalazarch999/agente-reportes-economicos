from pathlib import Path
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]

CONTEXT_DIRS = {
    "Minería e Hidrocarburos": "mineria_hidrocarburos",
    "Pesca":                   "pesca",
    "Manufactura":             "manufactura",
    "Agropecuario":            "agropecuario",
}

MAX_BYTES_POR_ARCHIVO = 100_000  # 100 KB por archivo


def buscar_contexto_local(contexto, max_archivos=5):
    """
    Busca archivos .txt locales curados que coincidan con el periodo y sector.
    Retorna metadatos de fuentes y texto concatenado para el LLM.
    """
    periodo = contexto.get("periodo", "")
    sector  = contexto.get("sector", {}).get("nombre", "")

    nombre_carpeta = CONTEXT_DIRS.get(sector)
    if not nombre_carpeta:
        logger.warning(f"Sector no reconocido para búsqueda local: '{sector}'")
        return {"fuentes": [], "texto": ""}

    carpeta = BASE_DIR / "data" / "corpus" / nombre_carpeta / "contexto"
    if not carpeta.exists():
        logger.warning(f"Carpeta de contexto local no existe: {carpeta}")
        return {"fuentes": [], "texto": ""}

    archivos = sorted(carpeta.glob(f"{periodo}*.txt"))[:max_archivos]

    if not archivos:
        return {"fuentes": [], "texto": ""}

    fuentes = []
    textos  = []

    for archivo in archivos:
        try:
            # Limitar tamaño para evitar cargar archivos enormes
            if archivo.stat().st_size > MAX_BYTES_POR_ARCHIVO:
                logger.warning(f"Archivo ignorado por tamaño excesivo: {archivo.name}")
                continue

            contenido = archivo.read_text(encoding="utf-8")

            # Metadatos en fuentes, sin duplicar el contenido
            fuentes.append({
                "archivo": archivo.name,
                "ruta":    str(archivo),
            })

            textos.append(f"Fuente local: {archivo.name}\n{contenido}")

        except Exception as e:
            logger.warning(f"Error al leer archivo local '{archivo.name}': {e}")
            continue

    return {
        "fuentes": fuentes,
        "texto":   "\n\n".join(textos)
    }