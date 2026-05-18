"""
add_document.py — Agrega un documento al corpus y reconstruye el índice FAISS.

Uso:
    python scripts/add_document.py
    python scripts/add_document.py --archivo ruta/al/documento.txt
    python scripts/add_document.py --archivo doc.txt --sector mineria_hidrocarburos

El script valida el formato de metadata, copia el archivo a la carpeta
correcta del corpus y reconstruye el índice FAISS automáticamente.
"""

import sys
import shutil
import logging
import argparse
import re
from pathlib import Path
from datetime import datetime

# Agregar raíz del proyecto al path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.indexer import construir_indice, CORPUS_DIR


# =====================================================
# CONSTANTES
# =====================================================

SECTORES_VALIDOS = [
    "mineria_hidrocarburos",
    "pesca",
    "manufactura",
    "agropecuario",
]

TIPOS_VALIDOS = ["coyuntural", "institucional", "precio"]

CAMPOS_REQUERIDOS  = ["sector", "periodo", "tipo", "fuente"]
CAMPOS_OPCIONALES  = ["subsector", "producto", "empresa"]

# Formato esperado de nombre de archivo: YYYYMM_descripcion.txt
_PATRON_NOMBRE = re.compile(r"^\d{6}_.+\.txt$")


# =====================================================
# LOGGING
# =====================================================

def _configurar_logging():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s]: %(message)s",
        datefmt="%H:%M:%S",
    )


# =====================================================
# PARSEO Y VALIDACIÓN DE METADATA
# =====================================================

def _parsear_metadata(texto_crudo):
    """
    Lee el encabezado YAML entre --- y retorna (metadata, cuerpo).
    Igual que en indexer.py para consistencia.
    """
    patron = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)
    match  = patron.match(texto_crudo.strip())

    if not match:
        return None, texto_crudo.strip()

    bloque_meta = match.group(1)
    cuerpo      = match.group(2).strip()
    metadata    = {}

    for linea in bloque_meta.splitlines():
        if ":" in linea:
            clave, _, valor = linea.partition(":")
            metadata[clave.strip()] = valor.strip()

    return metadata, cuerpo


def _validar_metadata(metadata, cuerpo):
    """
    Valida que el documento tenga los campos requeridos
    y valores correctos.

    Retorna lista de errores (vacía si todo está bien).
    """
    errores = []

    if metadata is None:
        errores.append(
            "El archivo no tiene encabezado de metadata. "
            "Debe comenzar con --- y terminar con ---."
        )
        return errores

    # Campos requeridos
    for campo in CAMPOS_REQUERIDOS:
        if campo not in metadata or not metadata[campo].strip():
            errores.append(f"Campo requerido faltante o vacío: '{campo}'")

    # Validar sector
    sector = metadata.get("sector", "")
    if sector and sector not in SECTORES_VALIDOS:
        errores.append(
            f"Sector '{sector}' no válido. "
            f"Valores permitidos: {', '.join(SECTORES_VALIDOS)}"
        )

    # Validar tipo
    tipo = metadata.get("tipo", "")
    if tipo and tipo not in TIPOS_VALIDOS:
        errores.append(
            f"Tipo '{tipo}' no válido. "
            f"Valores permitidos: {', '.join(TIPOS_VALIDOS)}"
        )

    # Validar formato de periodo
    periodo = metadata.get("periodo", "")
    if periodo:
        if not re.match(r"^\d{6}$", periodo):
            errores.append(
                f"Periodo '{periodo}' con formato incorrecto. "
                "Debe ser YYYYMM (ej. 202502)."
            )
        else:
            mes = int(periodo[4:6])
            if not 1 <= mes <= 12:
                errores.append(
                    f"Periodo '{periodo}' tiene mes inválido: {mes}."
                )

    # Validar cuerpo no vacío
    if not cuerpo or len(cuerpo.strip()) < 50:
        errores.append(
            "El cuerpo del documento está vacío o es demasiado corto "
            "(mínimo 50 caracteres)."
        )

    return errores


def _validar_nombre_archivo(nombre):
    """
    Verifica que el nombre del archivo siga la convención
    YYYYMM_descripcion.txt
    """
    if not _PATRON_NOMBRE.match(nombre):
        return (
            f"Nombre '{nombre}' no sigue la convención requerida. "
            "Formato esperado: YYYYMM_descripcion_breve.txt "
            "(ej. 202502_antamina_mantenimiento_cobre.txt)"
        )
    return None


# =====================================================
# FLUJO INTERACTIVO
# =====================================================

def _leer_archivo(ruta_str):
    """Lee el archivo y retorna su contenido."""
    ruta = Path(ruta_str)

    if not ruta.exists():
        print(f"\n❌ El archivo no existe: {ruta}")
        sys.exit(1)

    if ruta.suffix.lower() != ".txt":
        print(f"\n❌ El archivo debe ser .txt: {ruta.name}")
        sys.exit(1)

    try:
        return ruta, ruta.read_text(encoding="utf-8")
    except Exception as e:
        print(f"\n❌ Error al leer el archivo: {e}")
        sys.exit(1)


def _mostrar_metadata(metadata, cuerpo):
    """Muestra un resumen del documento para confirmación."""
    print("\n📄 Resumen del documento:")
    print(f"   sector:    {metadata.get('sector', '—')}")
    print(f"   subsector: {metadata.get('subsector', '—')}")
    print(f"   producto:  {metadata.get('producto', '—')}")
    print(f"   empresa:   {metadata.get('empresa', '—')}")
    print(f"   periodo:   {metadata.get('periodo', '—')}")
    print(f"   tipo:      {metadata.get('tipo', '—')}")
    print(f"   fuente:    {metadata.get('fuente', '—')}")
    print(f"\n   Cuerpo ({len(cuerpo)} chars):")
    preview = cuerpo[:200] + "..." if len(cuerpo) > 200 else cuerpo
    for linea in preview.splitlines():
        print(f"   {linea}")


def _determinar_destino(metadata, nombre_archivo, sector_arg=None):
    """
    Determina la ruta de destino en el corpus.
    Usa el sector del metadata o el argumento --sector.
    """
    sector = sector_arg or metadata.get("sector", "")

    if not sector:
        print("\n❌ No se pudo determinar el sector.")
        print("   Especifica '--sector' o agrega 'sector:' al metadata.")
        sys.exit(1)

    destino = CORPUS_DIR / sector / nombre_archivo
    return destino


def _copiar_documento(origen, destino):
    """Copia el documento al corpus."""
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists():
        print(f"\n⚠️  Ya existe un archivo con ese nombre: {destino.name}")
        try:
            resp = input("   ¿Sobreescribir? (s/n): ").strip().lower()
        except KeyboardInterrupt:
            print("\n\nCancelado.")
            sys.exit(0)

        if resp != "s":
            print("Cancelado.")
            sys.exit(0)

    shutil.copy2(str(origen), str(destino))
    return destino


# =====================================================
# MAIN
# =====================================================

def main():
    parser = argparse.ArgumentParser(
        description="Agrega un documento al corpus y reconstruye el índice FAISS."
    )
    parser.add_argument(
        "--archivo",
        help="Ruta al archivo .txt a agregar.",
        default=None,
    )
    parser.add_argument(
        "--sector",
        help=(
            "Sector destino (sobreescribe el campo 'sector' del metadata). "
            f"Valores válidos: {', '.join(SECTORES_VALIDOS)}"
        ),
        choices=SECTORES_VALIDOS,
        default=None,
    )
    parser.add_argument(
        "--sin-confirmar",
        action="store_true",
        help="Omitir confirmación interactiva (útil para scripts automatizados).",
    )
    args = parser.parse_args()

    _configurar_logging()

    print("\n" + "=" * 55)
    print("  Agregar documento al corpus RAG")
    print("=" * 55)

    # Solicitar archivo si no se pasó por argumento
    if args.archivo:
        ruta_origen = args.archivo
    else:
        print("\nNo se especificó archivo con --archivo.")
        try:
            ruta_origen = input("Ruta al archivo .txt: ").strip()
        except KeyboardInterrupt:
            print("\n\nCancelado.")
            sys.exit(0)

    # Leer archivo
    ruta, contenido = _leer_archivo(ruta_origen)

    # Validar nombre
    error_nombre = _validar_nombre_archivo(ruta.name)
    if error_nombre:
        print(f"\n⚠️  {error_nombre}")
        try:
            resp = input("   ¿Continuar de todas formas? (s/n): ").strip().lower()
        except KeyboardInterrupt:
            print("\n\nCancelado.")
            sys.exit(0)
        if resp != "s":
            print("Cancelado.")
            sys.exit(0)

    # Parsear y validar metadata
    metadata, cuerpo = _parsear_metadata(contenido)
    errores = _validar_metadata(metadata, cuerpo)

    if errores:
        print("\n❌ El documento tiene errores de formato:")
        for err in errores:
            print(f"   • {err}")
        print(
            "\n   Corrige el archivo y vuelve a ejecutar el script."
            "\n   Consulta el formato en README.md → Corpus local.\n"
        )
        sys.exit(1)

    # Mostrar resumen y confirmar
    _mostrar_metadata(metadata, cuerpo)

    destino = _determinar_destino(metadata, ruta.name, sector_arg=args.sector)
    print(f"\n📂 Destino: {destino}")

    if not args.sin_confirmar:
        try:
            resp = input("\n¿Agregar al corpus? (s/n): ").strip().lower()
        except KeyboardInterrupt:
            print("\n\nCancelado.")
            sys.exit(0)

        if resp != "s":
            print("Cancelado.")
            sys.exit(0)

    # Copiar documento
    destino_final = _copiar_documento(ruta, destino)
    print(f"\n✅ Documento copiado: {destino_final}")

    # Reconstruir índice
    print("\n⏳ Reconstruyendo índice FAISS...")
    try:
        sector_a_indexar = args.sector or metadata.get("sector")
        resultado = construir_indice(sectores=[sector_a_indexar])

        print(f"✅ Índice reconstruido: {resultado['total_documentos']} documentos.")
        print(f"   El documento '{ruta.name}' ya está disponible para el RAG.\n")

    except Exception as e:
        print(f"\n⚠️  Documento copiado pero error al reconstruir índice: {e}")
        print("   Ejecuta 'python scripts/build_index.py' manualmente.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()