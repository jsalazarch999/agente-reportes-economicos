import streamlit as st
import pandas as pd

# Configuración inicial
st.set_page_config(page_title="Agente de Reportes Económicos", layout="wide")

st.title("📊 Agente de Reportes Económicos")
st.write("Sube un archivo Excel y genera un reporte automático.")

# Función de reporte
def generar_reporte(sector, periodo, fila):
    texto = f"En el periodo {periodo}, el sector {sector}"

    if "variacion_interanual" in fila and pd.notna(fila["variacion_interanual"]):
        texto += f" registró una variación interanual de {fila['variacion_interanual']}%"

    if "variacion_acumulada" in fila and pd.notna(fila["variacion_acumulada"]):
        texto += f" y una variación acumulada de {fila['variacion_acumulada']}%"

    if "indice" in fila and pd.notna(fila["indice"]):
        texto += f". Además, el índice alcanzó un valor de {fila['indice']}"

    texto += "."
    return texto


# Subida de archivo
archivo = st.file_uploader("📂 Sube tu archivo Excel", type=["xlsx"])

if archivo is not None:
    try:
        df = pd.read_excel(archivo)

        st.subheader("🔍 Vista previa de los datos")
        st.dataframe(df)

        columnas = df.columns.tolist()

        st.subheader("⚙ Configuración")

        col1, col2 = st.columns(2)

        with col1:
            col_sector = st.selectbox("Columna de sector", columnas)

        with col2:
            col_periodo = st.selectbox("Columna de periodo", columnas)

        st.subheader("📊 Mapeo de indicadores (opcional)")

        col3, col4, col5 = st.columns(3)

        with col3:
            col_inter = st.selectbox("Variación interanual", ["(ninguna)"] + columnas)

        with col4:
            col_acum = st.selectbox("Variación acumulada", ["(ninguna)"] + columnas)

        with col5:
            col_indice = st.selectbox("Índice", ["(ninguna)"] + columnas)

        # Renombrar columnas
        df2 = df.copy()
        df2 = df2.rename(columns={
            col_sector: "sector",
            col_periodo: "periodo"
        })

        if col_inter != "(ninguna)":
            df2 = df2.rename(columns={col_inter: "variacion_interanual"})

        if col_acum != "(ninguna)":
            df2 = df2.rename(columns={col_acum: "variacion_acumulada"})

        if col_indice != "(ninguna)":
            df2 = df2.rename(columns={col_indice: "indice"})

        # Selección
        st.subheader("🎯 Selección")

        sectores = df2["sector"].dropna().astype(str).unique()
        periodos = df2["periodo"].dropna().astype(str).unique()

        col6, col7 = st.columns(2)

        with col6:
            sector_sel = st.selectbox("Selecciona sector", sorted(sectores))

        with col7:
            periodo_sel = st.selectbox("Selecciona periodo", sorted(periodos))

        df_filtrado = df2[
            (df2["sector"].astype(str) == sector_sel) &
            (df2["periodo"].astype(str) == periodo_sel)
        ]

        st.subheader("📄 Datos filtrados")
        st.dataframe(df_filtrado)

        # Generar reporte
        if st.button("📝 Generar reporte"):
            if df_filtrado.empty:
                st.error("No hay datos para esa selección.")
            else:
                fila = df_filtrado.iloc[0]
                reporte = generar_reporte(sector_sel, periodo_sel, fila)

                st.subheader("📢 Reporte generado")
                st.success(reporte)

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")