import pandas as pd

# Columnas mínimas que siempre deben existir
COLUMNAS_REQUERIDAS = {"clasificacion", "nombre", "periodo"}

# Columnas de texto que se normalizan siempre
COLUMNAS_TEXTO = ["clasificacion", "nombre", "periodo"]

# Columnas opcionales que se normalizan si existen
COLUMNAS_TEXTO_OPCIONALES = ["empresa", "unidad"]

# Columnas numéricas opcionales que se castean si existen
COLUMNAS_NUMERICAS_OPCIONALES = ["precio_internacional"]


def cargar_datos(origen, tipo="excel"):
    """
    Carga data estructurada y normaliza columnas.

    Parámetros:
        origen: ruta al archivo (Excel/CSV) o conexión SQL Server (futuro)
        tipo:   'excel' | 'csv' | 'sqlserver' (futuro)

    Retorna:
        DataFrame normalizado listo para validar.
    """
    if tipo == "excel":
        df = _cargar_excel(origen)
    elif tipo == "csv":
        df = _cargar_csv(origen)
    elif tipo == "sqlserver":
        df = _cargar_sqlserver(origen)
    else:
        raise ValueError(f"Tipo de origen no soportado: '{tipo}'")

    return _normalizar(df)


# =====================================================
# ORÍGENES
# =====================================================

def _cargar_excel(archivo):
    """Lee un archivo .xlsx o .xls."""
    try:
        return pd.read_excel(archivo)
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo Excel: {e}")


def _cargar_csv(archivo):
    """Lee un archivo .csv con encoding UTF-8."""
    try:
        return pd.read_csv(archivo, encoding="utf-8")
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo CSV: {e}")


def _cargar_sqlserver(conexion):
    """
    Placeholder para conexión SQL Server (fase de producción).
    conexion: dict con keys 'server', 'database', 'query'
    """
    raise NotImplementedError(
        "La conexión SQL Server se habilitará en la fase de producción. "
        "Por ahora usa tipo='excel' o tipo='csv'."
    )


# =====================================================
# NORMALIZACIÓN
# =====================================================

def _normalizar(df):
    """
    Normaliza columnas del DataFrame:
    - nombres en minúsculas y sin espacios
    - columnas de texto: strip
    - columnas numéricas opcionales: coerción a float
    """
    df.columns = [c.strip().lower() for c in df.columns]

    # Validar columnas mínimas obligatorias
    faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        raise ValueError(
            f"Faltan columnas requeridas en los datos: "
            f"{', '.join(sorted(faltantes))}"
        )

    # Normalizar columnas de texto obligatorias
    for col in COLUMNAS_TEXTO:
        df[col] = df[col].astype(str).str.strip()

    # Normalizar columnas de texto opcionales si existen
    for col in COLUMNAS_TEXTO_OPCIONALES:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Castear columnas numéricas opcionales si existen
    for col in COLUMNAS_NUMERICAS_OPCIONALES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# =====================================================
# FUNCIONES PÚBLICAS
# =====================================================

def obtener_periodos(df):
    """Retorna lista ordenada de periodos únicos disponibles."""
    return sorted(df["periodo"].dropna().unique())


def filtrar_periodo(df, periodo):
    """Filtra el DataFrame al periodo indicado."""
    dfp = df[df["periodo"] == str(periodo)].copy()

    if dfp.empty:
        raise ValueError(f"No hay datos para el periodo '{periodo}'.")

    return dfp