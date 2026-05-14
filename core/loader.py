import pandas as pd

COLUMNAS_REQUERIDAS = {"clasificacion", "nombre", "periodo"}
COLUMNAS_TEXTO = ["clasificacion", "nombre", "periodo"]


def cargar_excel(archivo):
    """Carga el Excel y normaliza columnas de texto."""
    df = pd.read_excel(archivo)
    df.columns = [c.strip().lower() for c in df.columns]

    columnas_faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if columnas_faltantes:
        raise ValueError(
            f"El archivo Excel no tiene las columnas requeridas: "
            f"{', '.join(sorted(columnas_faltantes))}"
        )

    for col in COLUMNAS_TEXTO:
        df[col] = df[col].astype(str).str.strip()

    return df


def obtener_periodos(df):
    """Retorna lista ordenada de periodos únicos disponibles."""
    return sorted(df["periodo"].dropna().unique())


def filtrar_periodo(df, periodo):
    """Filtra el DataFrame al periodo indicado."""
    dfp = df[df["periodo"] == str(periodo)].copy()

    if dfp.empty:
        raise ValueError(f"No hay datos para el periodo '{periodo}'.")

    return dfp