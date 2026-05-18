"""
build_index.py — Construye el índice FAISS desde el corpus local.

Uso:
    python scripts/build_index.py
    python scripts/build_index.py --sectores mineria_hidrocarburos pesca
    python scripts/build_index.py --verbose

Este script se ejecuta manualmente cada vez que se agregan
o modifican documentos en data/corpus/<sector>/.
No forma parte del flujo de Streamlit.
"""

import sys
import logging
import argparse
from pathlib import Path

# Agregar raíz del proyecto al path para importar módulos
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.indexer import construir_indice, CORPUS_DIR


# =====================================================
# LOGGING
# =====================================================

def _configurar_logging(verbose=False):
    nivel = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# =====================================================
# VALIDACIONES PREVIAS
# =====================================================

def _validar_corpus(sectores):
    """
    Verifica que las carpetas del corpus existan y tengan documentos.
    Retorna lista de sectores válidos con al menos un .txt.
    """
    validos    = []
    sin_docs   = []
    no_existen = []

    for sector in sectores:
        carpeta = CORPUS_DIR / sector
        if not carpeta.exists():
            no_existen.append(sector)
            continue

        txts = list(carpeta.glob("*.txt"))
        if not txts:
            sin_docs.append(sector)
            continue

        validos.append((sector, len(txts)))

    return validos, sin_docs, no_existen


def _mostrar_estado_corpus(sectores):
    """Muestra un resumen del estado del corpus antes de indexar."""
    print("\n📁 Estado del corpus:")
    print(f"   Ruta: {CORPUS_DIR}")

    validos, sin_docs, no_existen = _validar_corpus(sectores)

    for sector, n_docs in validos:
        print(f"   ✅ {sector}: {n_docs} documento(s)")

    for sector in sin_docs:
        print(f"   ⚠️  {sector}: carpeta existe pero sin archivos .txt")

    for sector in no_existen:
        print(f"   ❌ {sector}: carpeta no encontrada")

    return [s for s, _ in validos]


# =====================================================
# MAIN
# =====================================================

def main():
    parser = argparse.ArgumentParser(
        description="Construye el índice FAISS desde el corpus local."
    )
    parser.add_argument(
        "--sectores",
        nargs="+",
        help=(
            "Sectores a indexar (nombres de carpetas en data/corpus/). "
            "Si no se especifica, indexa todos los disponibles."
        ),
        default=None,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar logs detallados.",
    )
    args = parser.parse_args()

    _configurar_logging(args.verbose)
    logger = logging.getLogger("build_index")

    print("\n" + "=" * 55)
    print("  Construcción del índice FAISS")
    print("=" * 55)

    # Determinar sectores a indexar
    if args.sectores:
        sectores_solicitados = args.sectores
    else:
        # Detectar automáticamente todos los sectores disponibles
        sectores_solicitados = [
            d.name for d in CORPUS_DIR.iterdir()
            if d.is_dir()
            and not d.name.startswith(".")
            and d.name != "benchmark"
        ]

    if not sectores_solicitados:
        print(f"\n❌ No se encontraron carpetas en {CORPUS_DIR}")
        print("   Crea al menos una carpeta de sector con documentos .txt")
        sys.exit(1)

    # Validar corpus y mostrar estado
    sectores_validos = _mostrar_estado_corpus(sectores_solicitados)

    if not sectores_validos:
        print("\n❌ No hay documentos para indexar.")
        print("   Agrega archivos .txt en data/corpus/<sector>/")
        sys.exit(1)

    # Confirmar antes de indexar
    print(f"\n🔄 Se indexarán {len(sectores_validos)} sector(es): "
          f"{', '.join(sectores_validos)}")

    try:
        respuesta = input("\n¿Continuar? (s/n): ").strip().lower()
    except KeyboardInterrupt:
        print("\n\nCancelado.")
        sys.exit(0)

    if respuesta != "s":
        print("Cancelado.")
        sys.exit(0)

    # Construir índice
    print("\n⏳ Construyendo índice FAISS...")
    try:
        resultado = construir_indice(sectores=sectores_validos)

        print("\n" + "=" * 55)
        print("  ✅ Índice construido exitosamente")
        print("=" * 55)
        print(f"   Total documentos indexados: {resultado['total_documentos']}")
        print(f"   Dimensión de embeddings:    {resultado['dimension']}")
        print(f"   Sectores indexados:         {', '.join(resultado['sectores'])}")
        print(f"\n   Archivos generados:")
        print(f"   → data/faiss_index/index.faiss")
        print(f"   → data/faiss_index/documentos.json")
        print("\n   El sistema RAG está listo para usarse.\n")

    except Exception as e:
        print(f"\n❌ Error construyendo el índice: {e}")
        logger.exception("Error detallado:")
        sys.exit(1)


if __name__ == "__main__":
    main()