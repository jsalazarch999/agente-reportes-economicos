import streamlit as st
from rag.context_enricher import enriquecer_contexto_rag
from agent.orchestrator import procesar_excel, generar_reporte_llm
from evaluation.quality_scorer import evaluar_calidad
from llm.generator import generar_comentario_causal

st.set_page_config(
    page_title="Agente de Reportes Económicos",
    layout="wide"
)

st.title("Agente de Reportes Económicos")

MODELOS_DISPONIBLES = ["qwen", "llama3", "openai", "gemini", "anthropic", "deepseek"]

# =========================
# CONFIGURACIÓN DE SECTORES
# =========================

SECTORES_DISPONIBLES = {
    "Minería e Hidrocarburos": {
        "habilitado": True,
        "descripcion": "Generación de reporte para el sector Minería e Hidrocarburos."
    },
    "Pesca": {
        "habilitado": False,
        "descripcion": "Módulo pendiente de implementación."
    },
    "Manufactura": {
        "habilitado": False,
        "descripcion": "Módulo pendiente de implementación."
    },
    "Agropecuario": {
        "habilitado": False,
        "descripcion": "Módulo pendiente de implementación."
    }
}

# =========================
# SIDEBAR
# =========================

st.sidebar.header("Configuración")

sector = st.sidebar.selectbox(
    "Selecciona sector",
    list(SECTORES_DISPONIBLES.keys())
)

modelo = st.sidebar.selectbox(
    "Modelo LLM",
    MODELOS_DISPONIBLES
)

mostrar_debug = st.sidebar.checkbox(
    "Mostrar contexto y datos",
    value=True
)

usar_web_rag = st.sidebar.checkbox(
    "Enriquecer con contexto local y fuentes web",
    value=False
)

# =========================
# VALIDAR SECTOR
# =========================

info_sector = SECTORES_DISPONIBLES[sector]

st.subheader(sector)
st.write(info_sector["descripcion"])

if not info_sector["habilitado"]:
    st.warning("Este sector aún no está implementado.")
    st.stop()

# =========================
# CARGA DE ARCHIVO
# =========================

archivo = st.file_uploader(
    "Sube el Excel de variaciones",
    type=["xlsx"]
)

if archivo:

    try:
        resultado = procesar_excel(
            archivo=archivo,
            sector=sector
        )

        periodos = resultado["periodos"]

        periodo = st.selectbox(
            "Selecciona periodo",
            periodos
        )

        datos_periodo = procesar_excel(
            archivo=archivo,
            periodo=periodo,
            sector=sector
        )

        # =========================
        # TEXTO BASE
        # =========================

        st.subheader("Texto base determinístico")

        tipo_reporte = datos_periodo["contexto"].get("tipo_reporte")
        st.info(f"Tipo de reporte detectado: {tipo_reporte}")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Reportes base determinísticos")

            tab1, tab2, tab3 = st.tabs([
                "Reporte 1",
                "Reporte 2",
                "Reporte 3"
            ])

            with tab1:
                st.text_area(
                    "Reporte base 1",
                    datos_periodo["texto_base"]["reporte_1"],
                    height=500
                )

            with tab2:
                st.text_area(
                    "Reporte base 2",
                    datos_periodo["texto_base"]["reporte_2"],
                    height=500
                )

            with tab3:
                if datos_periodo["texto_base"]["reporte_3"]:
                    st.text_area(
                        "Reporte base 3",
                        datos_periodo["texto_base"]["reporte_3"],
                        height=500
                    )
                else:
                    st.info("No aplica para este periodo")
        
        with col2:
            st.subheader("Texto mejorado con IA")

            if st.button("Generar reporte con LLM"):
                with st.spinner("Generando reporte..."):
                    try:
                        contexto_final = datos_periodo["contexto"].copy()

                        if usar_web_rag:
                            contexto_final = enriquecer_contexto_rag(
                                contexto_final,
                                max_fuentes=3
                            )

                        texto_llm = generar_reporte_llm(
                            contexto=contexto_final,
                            texto_base=datos_periodo["texto_base"],
                            modelo=modelo
                        )

                        st.session_state["texto_llm"] = texto_llm
                        st.session_state["contexto_final"] = contexto_final

                    except Exception as e:
                        st.error(f"Error al usar el LLM: {e}")

            if "texto_llm" in st.session_state:
                st.text_area(
                    "Reporte generado por IA",
                    st.session_state["texto_llm"],
                    height=500
                )

        if "texto_llm" in st.session_state:
            texto_llm = st.session_state["texto_llm"]
            contexto_final = st.session_state["contexto_final"]

            if usar_web_rag:
                st.subheader("Comentario causal con RAG")

                comentario_causal = generar_comentario_causal(
                    contexto_final,
                    modelo=modelo
                )

                st.text_area(
                    "Comentario causal por subsector",
                    comentario_causal,
                    height=350
                )

                with st.expander("Contexto local curado consultado"):
                    contexto_local = contexto_final.get("contexto_local", {})
                    st.write(
                        contexto_local.get(
                            "resumen_para_llm",
                            "No se encontró contexto local."
                        )
                    )

                with st.expander("Fuentes web consultadas"):
                    contexto_web = contexto_final.get("contexto_web", {})
                    st.write("Consulta:", contexto_web.get("query", ""))

                    for fuente in contexto_web.get("fuentes", []):
                        st.markdown(
                            f"- [{fuente.get('titulo')}]({fuente.get('url')})"
                        )

            texto_base_completo = "\n\n".join([
                datos_periodo["texto_base"]["reporte_1"],
                datos_periodo["texto_base"]["reporte_2"],
                datos_periodo["texto_base"]["reporte_3"]
            ])

            contexto_eval = contexto_final.copy()
            contexto_eval["texto_base"] = texto_base_completo

            resultado_eval = evaluar_calidad(
                texto_llm=texto_llm,
                periodo=periodo,
                contexto=contexto_eval
            )

            st.subheader("Evaluación de calidad")
            st.write(f"Score total: {resultado_eval['score_total']}")
            st.write(f"Similitud: {resultado_eval['similitud']}")
            st.write(f"Cobertura productos: {resultado_eval['cobertura_productos']}")
            st.write(f"Válido: {resultado_eval['valido']}")
            st.write(f"Benchmark usado: {resultado_eval['benchmark_usado']}")

            if resultado_eval["benchmark_usado"] != "No disponible":
                with st.expander("Ver benchmark histórico"):
                    benchmark_texto = open(
                        resultado_eval["benchmark_usado"],
                        encoding="utf-8"
                    ).read()

                    st.text_area(
                        "Benchmark histórico",
                        benchmark_texto,
                        height=400
                    )

            if resultado_eval["errores"]:
                st.error(resultado_eval["errores"])

            if resultado_eval["advertencias"]:
                st.warning(resultado_eval["advertencias"])

        # =========================
        # DEBUG
        # =========================

        if mostrar_debug:

            with st.expander("Ver contexto estructurado para LLM"):
                st.json(datos_periodo["contexto"])

            with st.expander("Ver datos del periodo seleccionado"):
                st.dataframe(datos_periodo["df_periodo"])

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

else:
    st.info("Sube un archivo Excel para iniciar.")