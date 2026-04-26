import pandas as pd

from core.context_builder import construir_contexto
from llm.generator import generar_texto


def procesar_excel(archivo, periodo=None, sector="Minería e Hidrocarburos"):
    """
    Lee el Excel, selecciona un periodo y construye:
    - dataframe del periodo
    - contexto estructurado
    - texto base
    """

    df = pd.read_excel(archivo)

    # Normalizar nombres de columnas
    df.columns = [c.strip().lower() for c in df.columns]

    # Normalizar columnas clave
    if "periodo" in df.columns:
        df["periodo"] = df["periodo"].astype(str).str.strip()

    if "clasificacion" in df.columns:
        df["clasificacion"] = df["clasificacion"].astype(str).str.strip()

    if "nombre" in df.columns:
        df["nombre"] = df["nombre"].astype(str).str.strip()

    # Periodos disponibles
    periodos = sorted(df["periodo"].dropna().unique())

    if periodo is None:
        return {
            "df": df,
            "periodos": periodos
        }

    # Filtrar periodo seleccionado
    df_periodo = df[df["periodo"] == str(periodo)].copy()

    if df_periodo.empty:
        raise ValueError(f"No hay datos para el periodo {periodo}")

    # Construir contexto y texto base
    contexto, texto_base = construir_contexto(df_periodo, periodo)

    return {
        "df": df,
        "periodos": periodos,
        "df_periodo": df_periodo,
        "contexto": contexto,
        "texto_base": texto_base
    }


def generar_reporte_llm(contexto, modelo="qwen"):
    """
    Genera el reporte usando el modelo configurado.
    """

    texto = generar_texto(
        contexto=contexto,
        modelo=modelo
    )

    return texto