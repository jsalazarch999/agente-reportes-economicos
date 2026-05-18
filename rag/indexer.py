import os
import json
import logging
import re
from pathlib import Path
from functools import lru_cache

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# =====================================================
# CONSTANTES
# =====================================================

BASE_DIR     = Path(__file__).resolve().parents[1]
CORPUS_DIR   = BASE_DIR / "data" / "corpus"
INDEX_DIR    = BASE_DIR / "data" / "faiss_index"

MODEL_NAME   = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
INDEX_FILE   = "index.faiss"
DOCS_FILE    = "documentos.json"  # metadata + texto de cada chunk


# =====================================================
# MODELO DE EMBEDDINGS
# =====================================================

@lru_cache(maxsize=1)
def _get_modelo():
    """Carga el modelo de embeddings una sola vez."""
    logger.info(f"Cargando modelo de embeddings: {MODEL_NAME}")
    return SentenceTransformer(MODEL_NAME)


# =====================================================
# PARSEO DE DOCUMENTOS
# =====================================================

def _parsear_metadata(texto_crudo):
    """
    Lee el encabezado YAML entre --- y retorna (metadata_dict, cuerpo).
    Si no hay encabezado, retorna ({}, texto completo).
    """
    patron = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)
    match = patron.match(texto_crudo.strip())

    if not match:
        return {}, texto_crudo.strip()

    bloque_meta = match.group(1)
    cuerpo      = match.group(2).strip()
    metadata    = {}

    for linea in bloque_meta.splitlines():
        if ":" in linea:
            clave, _, valor = linea.partition(":")
            metadata[clave.strip()] = valor.strip()

    return metadata, cuerpo


def _leer_documentos(sector):
    """
    Lee todos los .txt del corpus de un sector.
    Retorna lista de dicts con metadata + texto.
    """
    carpeta = CORPUS_DIR / sector
    if not carpeta.exists():
        logger.warning(f"Carpeta de corpus no encontrada: {carpeta}")
        return []

    documentos = []
    for archivo in sorted(carpeta.glob("*.txt")):
        try:
            texto_crudo = archivo.read_text(encoding="utf-8")
            metadata, cuerpo = _parsear_metadata(texto_crudo)

            if not cuerpo:
                logger.warning(f"Documento vacío ignorado: {archivo.name}")
                continue

            doc = {
                "archivo":  archivo.name,
                "sector":   sector,
                "texto":    cuerpo,
                **metadata,  # sector, subsector, producto, empresa, periodo, tipo, fuente
            }
            documentos.append(doc)

        except Exception as e:
            logger.warning(f"Error al leer '{archivo.name}': {e}")
            continue

    logger.info(f"Sector '{sector}': {len(documentos)} documentos cargados.")
    return documentos


# =====================================================
# CONSTRUCCIÓN DEL ÍNDICE
# =====================================================

def construir_indice(sectores=None):
    """
    Construye el índice FAISS con todos los documentos del corpus.

    Parámetros:
        sectores: lista de sectores a indexar. Si None, indexa todos
                  los que existan en data/corpus/.

    Guarda en data/faiss_index/:
        - index.faiss      → índice vectorial
        - documentos.json  → metadata + texto de cada documento
    """
    if sectores is None:
        sectores = [
            d.name for d in CORPUS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
            and d.name != "benchmark"
        ]

    # Recopilar todos los documentos
    todos_los_docs = []
    for sector in sectores:
        todos_los_docs.extend(_leer_documentos(sector))

    if not todos_los_docs:
        raise ValueError(
            "No se encontraron documentos en el corpus. "
            "Agrega archivos .txt en data/corpus/<sector>/ antes de indexar."
        )

    logger.info(f"Total documentos a indexar: {len(todos_los_docs)}")

    # Generar embeddings
    modelo = _get_modelo()
    textos  = [doc["texto"] for doc in todos_los_docs]
    logger.info("Generando embeddings...")
    embeddings = modelo.encode(textos, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")

    # Construir índice FAISS (Inner Product sobre vectores normalizados = coseno)
    dimension = embeddings.shape[1]
    indice    = faiss.IndexFlatIP(dimension)
    indice.add(embeddings)

    # Guardar índice y documentos
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    faiss.write_index(indice, str(INDEX_DIR / INDEX_FILE))
    logger.info(f"Índice FAISS guardado: {INDEX_DIR / INDEX_FILE}")

    with open(INDEX_DIR / DOCS_FILE, "w", encoding="utf-8") as f:
        json.dump(todos_los_docs, f, ensure_ascii=False, indent=2)
    logger.info(f"Documentos guardados: {INDEX_DIR / DOCS_FILE}")

    return {
        "total_documentos": len(todos_los_docs),
        "dimension":        dimension,
        "sectores":         sectores,
    }


# =====================================================
# CARGA DEL ÍNDICE
# =====================================================

@lru_cache(maxsize=1)
def cargar_indice():
    """
    Carga el índice FAISS y los documentos desde disco.
    Se cachea en memoria — solo se lee una vez por sesión.

    Retorna:
        (indice_faiss, lista_de_documentos)
    """
    ruta_indice = INDEX_DIR / INDEX_FILE
    ruta_docs   = INDEX_DIR / DOCS_FILE

    if not ruta_indice.exists() or not ruta_docs.exists():
        raise FileNotFoundError(
            "No se encontró el índice FAISS. "
            "Ejecuta 'python scripts/build_index.py' para construirlo."
        )

    indice = faiss.read_index(str(ruta_indice))

    with open(ruta_docs, encoding="utf-8") as f:
        documentos = json.load(f)

    logger.info(
        f"Índice cargado: {indice.ntotal} vectores, "
        f"{len(documentos)} documentos."
    )
    return indice, documentos