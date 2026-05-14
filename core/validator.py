import pandas as pd

# Columnas que deben existir y ser numéricas
COLUMNAS_NUMERICAS = [
    "variacion_interanual",
    "incidencia_interanual",
    "variacion_acumulada",
    "incidencia_acumulada",
]

# Columnas de texto requeridas (ya validadas en loader, pero se mantienen aquí como referencia)
COLUMNAS_TEXTO = ["periodo", "clasificacion", "nombre"]

COLUMNAS_REQUERIDAS = COLUMNAS_TEXTO + COLUMNAS_NUMERICAS

# Filas estructurales requeridas por sector
FILAS_REQUERIDAS = {
    "Minería e Hidrocarburos": [
        ("sector",    "Minería e Hidrocarburos"),
        ("subsector", "Minería Metálica"),
        ("subsector", "Hidrocarburos"),
    ]
}


def validar_columnas(df):
    """Verifica que todas las columnas requeridas estén presentes."""
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en el Excel: {', '.join(faltantes)}")


def validar_numericos(df):
    """
    Verifica que las columnas numéricas sean convertibles y no tengan NaN.
    Intenta coerción para detectar strings no numéricos.
    """
    errores = []

    for col in COLUMNAS_NUMERICAS:
        convertida = pd.to_numeric(df[col], errors="coerce")
        n_invalidos = convertida.isna().sum()

        if n_invalidos > 0:
            errores.append(f"'{col}' tiene {n_invalidos} valor(es) no numérico(s) o vacío(s)")

    if errores:
        raise ValueError(
            "Problemas en columnas numéricas:\n" + "\n".join(f"  - {e}" for e in errores)
        )


def validar_filas_principales(df_periodo, sector="Minería e Hidrocarburos"):
    """Verifica que las filas estructurales del sector estén presentes."""
    filas = FILAS_REQUERIDAS.get(sector)

    if filas is None:
        raise ValueError(f"Sector no reconocido para validación: '{sector}'")

    faltantes = []

    for clasificacion, nombre in filas:
        existe = (
            (df_periodo["clasificacion"].str.lower().str.strip() == clasificacion.lower()) &
            (df_periodo["nombre"].str.lower().str.strip() == nombre.lower())
        ).any()

        if not existe:
            faltantes.append(f"{clasificacion}: {nombre}")

    if faltantes:
        raise ValueError(
            f"Faltan filas principales para sector '{sector}': "
            + ", ".join(faltantes)
        )


def validar_dataframe(df):
    """Valida estructura completa del DataFrame cargado."""
    validar_columnas(df)
    validar_numericos(df)


def validar_periodo(df_periodo, sector="Minería e Hidrocarburos"):
    """Valida que el periodo filtrado tenga las filas estructurales necesarias."""
    validar_filas_principales(df_periodo, sector)