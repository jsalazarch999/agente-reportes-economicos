import pandas as pd


COLUMNAS_REQUERIDAS = [
    "periodo",
    "clasificacion",
    "nombre",
    "variacion_interanual",
    "incidencia_interanual",
    "variacion_acumulada",
    "incidencia_acumulada",
]


def cargar_excel(archivo):
    """
    Lee el Excel y normaliza columnas.
    """

    df = pd.read_excel(archivo)

    # Normalizar nombres de columnas
    df.columns = [c.strip().lower() for c in df.columns]

    # Validar columnas necesarias
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en el Excel: {', '.join(faltantes)}")

    # Normalizar tipos
    df["clasificacion"] = df["clasificacion"].astype(str).str.strip()
    df["nombre"] = df["nombre"].astype(str).str.strip()
    df["periodo"] = df["periodo"].astype(str).str.strip()

    return df


def obtener_periodos(df):
    """
    Retorna lista ordenada de periodos disponibles.
    """
    return sorted(df["periodo"].dropna().unique())


def filtrar_periodo(df, periodo):
    """
    Retorna dataframe filtrado por periodo.
    """
    dfp = df[df["periodo"] == str(periodo)].copy()

    if dfp.empty:
        raise ValueError(f"No hay datos para el periodo {periodo}")

    return dfp