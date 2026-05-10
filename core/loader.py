import pandas as pd


def cargar_excel(archivo):
    df = pd.read_excel(archivo)
    df.columns = [c.strip().lower() for c in df.columns]

    if "clasificacion" in df.columns:
        df["clasificacion"] = df["clasificacion"].astype(str).str.strip()

    if "nombre" in df.columns:
        df["nombre"] = df["nombre"].astype(str).str.strip()

    if "periodo" in df.columns:
        df["periodo"] = df["periodo"].astype(str).str.strip()

    return df


def obtener_periodos(df):
    return sorted(df["periodo"].dropna().unique())


def filtrar_periodo(df, periodo):
    dfp = df[df["periodo"] == str(periodo)].copy()

    if dfp.empty:
        raise ValueError(f"No hay datos para el periodo {periodo}")

    return dfp