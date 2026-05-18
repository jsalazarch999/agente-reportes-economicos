import streamlit as st
from dotenv import load_dotenv
from llm.clients import modelos_disponibles
from agent.orchestrator import (
    obtener_periodos_excel,
    procesar_periodo_excel,
    generar_reporte,
)
from evaluation.quality_scorer import evaluar_calidad
from evaluation.grounding_checker import resumen_grounding

load_dotenv()

# =====================================================
# CONFIGURACIÓN DE PÁGINA
# =====================================================

st.set_page_config(
    page_title="Agente de Reportes Económicos",
    layout="wide"
)

st.title("Agente de Reportes Económicos")

MODELOS_DISPONIBLES = modelos_disponibles()

SECTORES_DISPONIBLES = {
    "Minería e Hidrocarburos": {
        "habilitado":  True,
        "descripcion": "Generación de reporte para el sector Minería e Hidrocarburos."
    },
    "Pesca": {
        "habilitado":  False,
        "descripcion": "Módulo pendiente de implementación."
    },
    "Manufactura": {
        "habilitado":  False,
        "descripcion": "Módulo pendiente de implementación."
    },
    "Agropecuario": {
        "habilitado":  False,
        "descripcion": "Módulo pendiente de implementación."
    },
}

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Configuración")

sector = st.sidebar.selectbox(
    "Selecciona sector",
    list(SECTORES_DISPONIBLES.keys())
)

modelo = st.sidebar.selectbox(
    "Modelo LLM",
    MODELOS_DISPONIBLES
)

st.sidebar.divider()
st.sidebar.subheader("RAG y fundamentación")

usar_rag = st.sidebar.checkbox(
    "Activar fundamentación coyuntural",
    value=False,
    help=(
        "Recupera documentos del corpus local (FAISS) y genera "
        "párrafos de fundamentación intercalados en el reporte."
    )
)

usar_web = st.sidebar.checkbox(
    "Incluir búsqueda web",
    value=False,
    disabled=not usar_rag,
    help=(
        "Complementa el corpus local con fuentes web verificadas. "
        "Desactivar si los datos son confidenciales o pre-publicación."
    )
)

if usar_rag and usar_web:
    modelos_externos = {"openai", "anthropic", "gemini", "deepseek", "llama3"}
    if modelo in modelos_externos:
        st.sidebar.warning(
            f"⚠️ El modelo '{modelo}' envía contexto a una API externa. "
            "Asegúrate de que los datos ya son públicos antes de continuar."
        )

st.sidebar.divider()

mostrar_debug = st.sidebar.checkbox(
    "Mostrar contexto y datos",
    value=False
)

# =====================================================
# VALIDAR SECTOR
# =====================================================

info_sector = SECTORES_DISPONIBLES[sector]
st.subheader(sector)
st.write(info_sector["descripcion"])

if not info_sector["habilitado"]:
    st.warning("Este sector aún no está implementado.")
    st.stop()

# =====================================================
# CARGA DE ARCHIVO
# =====================================================

archivo = st.file_uploader(
    "Sube el archivo de data estructurada",
    type=["xlsx", "csv"],
)

if not archivo:
    st.info("Sube un archivo Excel o CSV para iniciar.")
    st.stop()

try:
    resultado     = obtener_periodos_excel(archivo)
    periodos      = resultado["periodos"]
    advertencias_carga = resultado.get("advertencias", [])

    if advertencias_carga:
        for adv in advertencias_carga:
            st.warning(f"⚠️ {adv}")

    periodo = st.selectbox("Selecciona periodo", periodos)

    datos_periodo = procesar_periodo_excel(
        archivo=archivo,
        periodo=periodo,
        sector=sector,
    )

    if datos_periodo.get("advertencias"):
        for adv in datos_periodo["advertencias"]:
            st.warning(f"⚠️ {adv}")

    # =====================================================
    # TEXTO BASE DETERMINÍSTICO
    # =====================================================

    tipo_reporte = datos_periodo["contexto"].get("tipo_reporte")
    st.info(f"Tipo de reporte detectado: **{tipo_reporte}**")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Texto base determinístico")
        tab1, tab2, tab3 = st.tabs(["Reporte 1", "Reporte 2", "Reporte 3"])

        with tab1:
            st.text_area(
                "Reporte base 1",
                datos_periodo["texto_base"]["reporte_1"],
                height=500,
            )
        with tab2:
            st.text_area(
                "Reporte base 2",
                datos_periodo["texto_base"]["reporte_2"],
                height=500,
            )
        with tab3:
            reporte_3 = datos_periodo["texto_base"]["reporte_3"]
            if reporte_3:
                st.text_area("Reporte base 3", reporte_3, height=500)
            else:
                st.info("No aplica para este periodo.")

    # =====================================================
    # GENERACIÓN CON LLM
    # =====================================================

    with col2:
        st.subheader("Reporte generado con IA")

        label_boton = (
            "Generar reporte con fundamentación"
            if usar_rag else
            "Generar reporte estadístico"
        )

        if st.button(label_boton, type="primary"):
            with st.spinner("Generando reporte..."):
                try:
                    resultado_gen = generar_reporte(
                        contexto=datos_periodo["contexto"],
                        texto_base=datos_periodo["texto_base"],
                        modelo=modelo,
                        usar_rag=usar_rag,
                        usar_web=usar_web,
                    )

                    st.session_state["reporte_final"]     = resultado_gen["reporte_final"]
                    st.session_state["texto_estadistico"] = resultado_gen["texto_estadistico"]
                    st.session_state["fundamentaciones"]  = resultado_gen["fundamentaciones"]
                    st.session_state["contexto_final"]    = resultado_gen["contexto_final"]
                    st.session_state["advertencias_rag"]  = resultado_gen["advertencias_rag"]

                except Exception as e:
                    st.error(f"Error al generar el reporte: {e}")

        if "reporte_final" in st.session_state:
            st.text_area(
                "Reporte final",
                st.session_state["reporte_final"],
                height=600,
            )

    # =====================================================
    # SECCIÓN POST-GENERACIÓN
    # =====================================================

    if "reporte_final" not in st.session_state:
        st.stop()

    reporte_final     = st.session_state["reporte_final"]
    texto_estadistico = st.session_state["texto_estadistico"]
    fundamentaciones  = st.session_state["fundamentaciones"]
    contexto_final    = st.session_state["contexto_final"]
    advertencias_rag  = st.session_state["advertencias_rag"]

    # Advertencias del RAG
    if advertencias_rag:
        st.warning("Advertencias de fuentes web:")
        for adv in advertencias_rag:
            st.write(f"• {adv}")

    # Fundamentaciones generadas (si las hay)
    if fundamentaciones:
        with st.expander("Ver fundamentaciones coyunturales generadas"):
            for clave, texto in fundamentaciones.items():
                nombre = clave.replace("__", " → ").replace("_", " ").title()
                st.markdown(f"**{nombre}**")
                st.write(texto)
                st.divider()

    # Fuentes consultadas
    if usar_rag:
        contexto_rag = contexto_final.get("contexto_rag", {})

        if contexto_rag:
            with st.expander("Fuentes locales consultadas (corpus FAISS)"):
                for clave, bloque in contexto_rag.items():
                    docs_locales = bloque.get("local", [])
                    if docs_locales:
                        nombre = clave.replace("__", " → ").replace("_", " ").title()
                        st.markdown(f"**{nombre}**")
                        for doc in docs_locales:
                            st.write(
                                f"• {doc.get('archivo', '—')} "
                                f"(score: {doc.get('_score_semantico', '—')})"
                            )

        if usar_web:
            with st.expander("Fuentes web consultadas"):
                for clave, bloque in contexto_rag.items():
                    docs_web = bloque.get("web", [])
                    if docs_web:
                        nombre = clave.replace("__", " → ").replace("_", " ").title()
                        st.markdown(f"**{nombre}**")
                        for doc in docs_web:
                            nivel = doc.get("nivel_confianza", "?")
                            emoji = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔵"}.get(nivel, "⚪")
                            st.markdown(
                                f"• {emoji} [{doc.get('titulo', '—')}]"
                                f"({doc.get('url', '#')})"
                            )

    # =====================================================
    # EVALUACIÓN DE CALIDAD
    # =====================================================

    st.subheader("Evaluación de calidad")

    contexto_rag_eval = contexto_final.get("contexto_rag") if usar_rag else None

    resultado_eval = evaluar_calidad(
        texto_llm=texto_estadistico,
        periodo=periodo,
        contexto=contexto_final,
        fundamentaciones=fundamentaciones if usar_rag else None,
        contexto_rag=contexto_rag_eval,
    )

    # Métricas principales
    n_cols = 5 if usar_rag else 4
    cols = st.columns(n_cols)
    cols[0].metric("Score total",        resultado_eval["score_total"])
    cols[1].metric("Similitud",          resultado_eval["similitud"])
    cols[2].metric("Cobertura",          resultado_eval["cobertura_productos"])
    cols[3].metric("Válido",             "Sí" if resultado_eval["valido"] else "No")
    if usar_rag and n_cols == 5:
        score_g = resultado_eval.get("score_grounding")
        cols[4].metric(
            "Grounding RAG",
            f"{score_g:.2f}" if score_g is not None else "N/A"
        )

    # Benchmark histórico
    if resultado_eval["benchmark_usado"] != "No disponible":
        with st.expander("Ver benchmark histórico"):
            with open(resultado_eval["benchmark_usado"], encoding="utf-8") as f:
                st.text_area("Benchmark histórico", f.read(), height=400)

    # Errores y advertencias de porcentajes
    if resultado_eval.get("errores_porcentajes"):
        st.error("Alucinaciones numéricas detectadas:")
        for e in resultado_eval["errores_porcentajes"]:
            st.write(f"• {e}")

    if resultado_eval.get("advertencias_porcentajes"):
        st.warning("Posibles redondeos:")
        for a in resultado_eval["advertencias_porcentajes"]:
            st.write(f"• {a}")

    if resultado_eval.get("errores"):
        for e in resultado_eval["errores"]:
            st.error(e)

    if resultado_eval.get("advertencias"):
        for a in resultado_eval["advertencias"]:
            st.warning(a)

    # Grounding por fundamentación
    if usar_rag and resultado_eval.get("detalle_grounding"):
        with st.expander("Diagnóstico de grounding por fundamentación"):
            lineas = resumen_grounding(resultado_eval["detalle_grounding"])
            for linea in lineas:
                st.write(linea)

            if resultado_eval.get("advertencias_grounding"):
                st.divider()
                for adv in resultado_eval["advertencias_grounding"]:
                    st.warning(adv)

    # Porcentajes comparados
    with st.expander("Ver porcentajes comparados"):
        c1, c2 = st.columns(2)
        c1.write("Del contexto (datos):")
        c1.write(resultado_eval["porcentajes_contexto"])
        c2.write("Del texto generado:")
        c2.write(resultado_eval["porcentajes_texto"])

    # =====================================================
    # DEBUG
    # =====================================================

    if mostrar_debug:
        with st.expander("Ver contexto estructurado para LLM"):
            st.json(datos_periodo["contexto"])

        with st.expander("Ver datos del periodo seleccionado"):
            st.dataframe(datos_periodo["df_periodo"])

        if usar_rag and contexto_final.get("contexto_rag"):
            with st.expander("Ver contexto RAG ensamblado"):
                for clave, bloque in contexto_final["contexto_rag"].items():
                    st.markdown(f"**{clave}**")
                    st.write(bloque.get("resumen", "")[:300] + "...")

except Exception as e:
    st.error(f"Error al procesar los datos: {e}")
    if mostrar_debug:
        st.exception(e)