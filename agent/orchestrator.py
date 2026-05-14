from core.loader import cargar_excel, obtener_periodos, filtrar_periodo
from core.validator import validar_dataframe, validar_periodo
from core.context_builder import construir_contexto
from llm.generator import generar_texto


def obtener_periodos_excel(archivo):
    """Carga el Excel y retorna los periodos disponibles."""
    df = cargar_excel(archivo)
    validar_dataframe(df)
    periodos = obtener_periodos(df)
    return {"df": df, "periodos": periodos}


def procesar_periodo_excel(archivo, periodo, sector="Minería e Hidrocarburos"):
    """Procesa un periodo específico del Excel y retorna contexto y texto base."""
    df = cargar_excel(archivo)
    validar_dataframe(df)
    periodos = obtener_periodos(df)

    df_periodo = filtrar_periodo(df, periodo)
    validar_periodo(df_periodo)

    contexto, texto_base = construir_contexto(df_periodo, periodo, sector)

    return {
        "periodos": periodos,
        "df_periodo": df_periodo,
        "contexto": contexto,
        "texto_base": texto_base
    }


def generar_reporte_llm(contexto, texto_base=None, modelo="qwen"):
    """Genera el reporte final usando el LLM indicado."""
    contexto_final = contexto.copy()

    if texto_base is not None:
        if isinstance(texto_base, dict):
            texto_base = "\n\n".join(filter(None, [
                texto_base.get("reporte_1"),
                texto_base.get("reporte_2"),
                texto_base.get("reporte_3"),
            ]))
        contexto_final["texto_base"] = texto_base

    return generar_texto(contexto=contexto_final, modelo=modelo)