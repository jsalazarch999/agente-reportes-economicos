import streamlit as st
import pandas as pd


st.set_page_config(page_title="Agente de Reportes Económicos", layout="wide")

st.title("Agente con herramientas para generación de reportes económicos")
st.write("Primera versión: carga de Excel, selección de datos y generación de reporte básico.")


def generar_reporte_basico(sector: str, periodo: str, fila: pd.Series) -> str:
    """
    Genera un reporte simple a partir de una fila seleccionada.
    Ajusta los nombres de columnas según tu Excel real.
    """
    partes = [f"En el periodo {periodo}, el sector {sector}"]

    if "variacion_interanual" in fila.index and pd.notna(fila["variacion_interanual"]):
        partes.append(f"registró una variación interanual de {fila['variacion_interanual']}%")

    if "variacion_acumulada" in fila.index and pd.notna(fila["variacion_acumulada"]):
        partes.append(f"y una variación acumulada de {fila['variacion_acumulada']}%")

    if "indice" in fila.index and pd.notna(fila["indice"]):
        partes.append(f". Asimismo, el índice reportado fue {fila['indice']}")

    texto = " ".join(partes).replace(" .", ".")
    if not texto.endswith("."):
        texto += "."

    return texto


uploaded_file = st.file_uploader("Sube un archivo Excel", type=["xlsx"])

if uploaded_file is not None:
    try:
        xls = pd.ExcelFile(uploaded_file)
        hojas = xls.sheet_names

        st.success("Archivo cargado correctamente.")
        hoja_seleccionada = st.selectbox("Selecciona una hoja", hojas)

        df = pd.read_excel(uploaded_file, sheet_name=hoja_seleccionada)

        st.subheader("Vista previa de los datos")
        st.dataframe(df.head(10), use_container_width=True)

        st.subheader("Columnas detectadas")
        st.write(list(df.columns))

        # Selección flexible de columnas clave
        st.subheader("Configuración de columnas")

        col1, col2, col3 = st.columns(3)

        with col1:
            columna_sector = st.selectbox("Columna de sector", df.columns)

        with col2:
            columna_periodo = st.selectbox("Columna de periodo", df.columns)

        with col3:
            columnas_numericas = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            st.write("Columnas numéricas detectadas:", columnas_numericas)

        # Renombrado interno opcional
        st.subheader("Mapeo opcional de indicadores")

        col4, col5, col6 = st.columns(3)

        with col4:
            col_var_inter = st.selectbox(
                "Variación interanual",
                ["(ninguna)"] + list(df.columns),
                index=0
            )

        with col5:
            col_var_acum = st.selectbox(
                "Variación acumulada",
                ["(ninguna)"] + list(df.columns),
                index=0
            )

        with col6:
            col_indice = st.selectbox(
                "Índice",
                ["(ninguna)"] + list(df.columns),
                index=0
            )

        df_trabajo = df.copy()
        df_trabajo = df_trabajo.rename(columns={
            columna_sector: "sector",
            columna_periodo: "periodo"
        })

        if col_var_inter != "(ninguna)":
            df_trabajo = df_trabajo.rename(columns={col_var_inter: "variacion_interanual"})

        if col_var_acum != "(ninguna)":
            df_trabajo = df_trabajo.rename(columns={col_var_acum: "variacion_acumulada"})

        if col_indice != "(ninguna)":
            df_trabajo = df_trabajo.rename(columns={col_indice: "indice"})

        # Filtros
        st.subheader("Selección de reporte")

        sectores = sorted(df_trabajo["sector"].dropna().astype(str).unique().tolist())
        periodos = sorted(df_trabajo["periodo"].dropna().astype(str).unique().tolist())

        col7, col8 = st.columns(2)

        with col7:
            sector_sel = st.selectbox("Selecciona sector", sectores)

        with col8:
            periodo_sel = st.selectbox("Selecciona periodo", periodos)

        df_filtrado = df_trabajo[
            (df_trabajo["sector"].astype(str) == sector_sel) &
            (df_trabajo["periodo"].astype(str) == periodo_sel)
        ]

        st.subheader("Registro filtrado")
        st.dataframe(df_filtrado, use_container_width=True)

        if st.button("Generar reporte básico"):
            if df_filtrado.empty:
                st.error("No se encontraron datos para esa combinación de sector y periodo.")
            else:
                fila = df_filtrado.iloc[0]
                reporte = generar_reporte_basico(sector_sel, periodo_sel, fila)

                st.subheader("Reporte generado")
                st.text_area("Salida", reporte, height=180)

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")