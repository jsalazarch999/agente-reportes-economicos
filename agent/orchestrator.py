import logging
from core.loader import cargar_datos, obtener_periodos, filtrar_periodo
from core.validator import validar_dataframe, validar_periodo
from core.context_builder import construir_contexto
from llm.generator import generar_reporte_completo, generar_texto

logger = logging.getLogger(__name__)


# =====================================================
# CARGA DE DATOS
# =====================================================

def obtener_periodos_datos(origen, tipo="excel"):
    """
    Carga la fuente de datos y retorna los periodos disponibles.
    Agnóstico al origen: Excel hoy, SQL Server en producción.

    Retorna:
        dict con 'df' y 'periodos'
    """
    df          = cargar_datos(origen, tipo=tipo)
    advertencias = validar_dataframe(df)

    if advertencias:
        for adv in advertencias:
            logger.warning(f"Advertencia en datos: {adv}")

    periodos = obtener_periodos(df)
    return {"df": df, "periodos": periodos}


def procesar_periodo(origen, periodo, sector="Minería e Hidrocarburos", tipo="excel"):
    """
    Procesa un periodo específico y retorna contexto y texto base.

    Parámetros:
        origen:  ruta al archivo o conexión SQL Server
        periodo: YYYYMM del periodo a procesar
        sector:  nombre del sector
        tipo:    'excel' | 'csv' | 'sqlserver'

    Retorna:
        dict con periodos, df_periodo, contexto, texto_base, advertencias
    """
    df           = cargar_datos(origen, tipo=tipo)
    advertencias = validar_dataframe(df)
    periodos     = obtener_periodos(df)

    df_periodo = filtrar_periodo(df, periodo)
    validar_periodo(df_periodo, sector=sector)

    contexto, texto_base = construir_contexto(df_periodo, periodo, sector)

    return {
        "periodos":    periodos,
        "df_periodo":  df_periodo,
        "contexto":    contexto,
        "texto_base":  texto_base,
        "advertencias": advertencias,
    }


# =====================================================
# GENERACIÓN DEL REPORTE
# =====================================================

def generar_reporte(
    contexto,
    texto_base,
    modelo="qwen",
    usar_rag=False,
    usar_web=True,
):
    """
    Pipeline completo de generación del reporte.

    Flujo:
        1. Si usar_rag=True, enriquece el contexto con FAISS + web
        2. Genera párrafo estadístico (SymGen)
        3. Genera fundamentaciones por subsector y producto
        4. Unifica en reporte intercalado
        5. Retorna reporte final + componentes para evaluación

    Parámetros:
        contexto:   dict del context_builder
        texto_base: dict con reporte_1, reporte_2, reporte_3
                    (árbitro de verificación post-generación)
        modelo:     nombre del modelo LLM
        usar_rag:   si True, activa recuperación FAISS + web
        usar_web:   si False, solo usa corpus local (datos confidenciales)

    Retorna:
        dict con reporte_final, texto_estadistico,
        fundamentaciones, advertencias_rag
    """
    contexto_final    = contexto.copy()
    advertencias_rag  = []

    # 1. Enriquecimiento RAG (opcional)
    if usar_rag:
        try:
            from rag.context_enricher import enriquecer_contexto_rag
            contexto_final = enriquecer_contexto_rag(
                contexto_final,
                usar_web=usar_web,
            )

            # Recopilar advertencias del contexto web
            advertencias_rag = (
                contexto_final
                .get("contexto_web", {})
                .get("advertencias", [])
            )

            logger.info(
                f"Contexto RAG enriquecido: "
                f"{len(contexto_final.get('contexto_rag', {}))} claves."
            )
        except Exception as e:
            logger.warning(
                f"Error en enriquecimiento RAG: {e}. "
                "Continuando sin contexto RAG."
            )

    # 2. Generación completa
    try:
        resultado = generar_reporte_completo(
            contexto=contexto_final,
            texto_base=texto_base,
            modelo=modelo,
        )
    except Exception as e:
        raise RuntimeError(f"Error en generación del reporte: {e}")

    return {
        "reporte_final":     resultado["reporte_final"],
        "texto_estadistico": resultado["texto_estadistico"],
        "fundamentaciones":  resultado["fundamentaciones"],
        "contexto_final":    contexto_final,
        "advertencias_rag":  advertencias_rag,
    }


# =====================================================
# COMPATIBILIDAD CON APP.PY ANTERIOR
# =====================================================

def obtener_periodos_excel(archivo):
    """
    Alias de compatibilidad con app.py durante la migración.
    Usar obtener_periodos_datos en código nuevo.
    """
    return obtener_periodos_datos(archivo, tipo="excel")


def procesar_periodo_excel(archivo, periodo, sector="Minería e Hidrocarburos"):
    """
    Alias de compatibilidad con app.py durante la migración.
    Usar procesar_periodo en código nuevo.
    """
    return procesar_periodo(archivo, periodo, sector, tipo="excel")


def generar_reporte_llm(contexto, texto_base=None, modelo="qwen"):
    """
    Flujo anterior: genera reporte sin RAG estructurado.
    Mantenido por compatibilidad con app.py durante la migración.
    """
    contexto_final = contexto.copy()

    if texto_base is not None:
        if isinstance(texto_base, dict):
            texto_base_str = "\n\n".join(filter(None, [
                texto_base.get("reporte_1"),
                texto_base.get("reporte_2"),
                texto_base.get("reporte_3"),
            ]))
        else:
            texto_base_str = texto_base
        contexto_final["texto_base"] = texto_base_str

    return generar_texto(contexto=contexto_final, modelo=modelo)