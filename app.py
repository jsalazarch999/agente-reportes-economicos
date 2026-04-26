import streamlit as st

from agent.orchestrator import procesar_excel, generar_reporte_llm
from tests.test_quality import evaluar_calidad

st.set_page_config(
    page_title="Agente de Reportes Económicos",
    layout="wide"
)

st.title("Agente de Reportes Económicos")

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
    ["qwen", "llama3", "openai"]
)

mostrar_debug = st.sidebar.checkbox(
    "Mostrar contexto y datos",
    value=True
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

        st.subheader("Reportes base determinísticos")

        tab1, tab2, tab3 = st.tabs([
            "Reporte 1: Evolución sectorial",
            "Reporte 2: Producción mensual",
            "Reporte 3: Acumulado / anual"
        ])

        with tab1:
            st.text_area(
                "Reporte 1",
                datos_periodo["texto_base"]["reporte_1"],
                height=400
            )

        with tab2:
            st.text_area(
                "Reporte 2",
                datos_periodo["texto_base"]["reporte_2"],
                height=400
            )

        with tab3:
            if datos_periodo["texto_base"]["reporte_3"]:
                st.text_area(
                    "Reporte 3",
                    datos_periodo["texto_base"]["reporte_3"],
                    height=400
                )
            else:
                st.info("Este periodo no requiere reporte acumulado o anual.")


        # =========================
        # LLM
        # =========================

        st.divider()

        st.subheader("Texto mejorado con IA")

        if st.button("Generar reporte con LLM"):

            with st.spinner("Generando reporte..."):

                try:
                    texto_llm = generar_reporte_llm(
                        contexto=datos_periodo["contexto"],
                        modelo=modelo
                    )

                    # =========================
                    # BENCHMARK
                    # =========================

                    reportes = [
                        datos_periodo["texto_base"]["reporte_1"],
                        datos_periodo["texto_base"]["reporte_2"],
                    ]

                    if datos_periodo["texto_base"]["reporte_3"]:
                        reportes.append(datos_periodo["texto_base"]["reporte_3"])

                    benchmark = "\n\n".join(reportes)

                    # =========================
                    # EVALUACIÓN
                    # =========================

                    resultado_eval = evaluar_calidad(
                        texto_llm=texto_llm,
                        texto_benchmark=benchmark,
                        contexto=datos_periodo["contexto"]
                    )

                    # =========================
                    # MOSTRAR RESULTADOS
                    # =========================

                    st.text_area("Reporte generado", texto_llm, height=500)

                    st.subheader("Evaluación de calidad")

                    st.write(f"Score total: {resultado_eval['score_total']}")
                    st.write(f"Similitud: {resultado_eval['similitud']}")
                    st.write(f"Válido: {resultado_eval['valido']}")

                    if resultado_eval["errores"]:
                        st.error(resultado_eval["errores"])

                    if resultado_eval["advertencias"]:
                        st.warning(resultado_eval["advertencias"])


                except Exception as e:
                    st.error(f"Error al usar el LLM: {e}")

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