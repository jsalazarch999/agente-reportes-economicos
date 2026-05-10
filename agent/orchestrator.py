from core.loader import cargar_excel, obtener_periodos, filtrar_periodo
from core.validator import validar_dataframe, validar_periodo
from core.context_builder import construir_contexto
from llm.generator import generar_texto


def procesar_excel(archivo, periodo=None, sector="Minería e Hidrocarburos"):
    df = cargar_excel(archivo)

    validar_dataframe(df)

    periodos = obtener_periodos(df)

    if periodo is None:
        return {
            "df": df,
            "periodos": periodos
        }

    df_periodo = filtrar_periodo(df, periodo)

    validar_periodo(df_periodo)

    contexto, texto_base = construir_contexto(df_periodo, periodo)

    return {
        "df": df,
        "periodos": periodos,
        "df_periodo": df_periodo,
        "contexto": contexto,
        "texto_base": texto_base
    }


def generar_reporte_llm(contexto, texto_base=None, modelo="qwen"):
    contexto_final = contexto.copy()

    if texto_base is not None:
        if isinstance(texto_base, dict):
            texto_base = "\n\n".join([
                texto_base.get("reporte_1", ""),
                texto_base.get("reporte_2", ""),
                texto_base.get("reporte_3", "")
            ])

        contexto_final["texto_base"] = texto_base

    texto = generar_texto(
        contexto=contexto_final,
        modelo=modelo
    )

    return texto