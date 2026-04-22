import streamlit as st
import pandas as pd
import json
import os
from openai import OpenAI

st.set_page_config(page_title="Generador de Reporte - Minería e Hidrocarburos", layout="wide")
st.title("Generador de Reporte - Minería e Hidrocarburos")

archivo = st.file_uploader("Sube el Excel de variaciones", type=["xlsx"])


def formatear(num):
    return f"{num:.2f}".replace(".", ",")


def obtener_fila(df, clasificacion, nombre):
    fila = df[
        (df["clasificacion"].str.strip().str.lower() == clasificacion.strip().lower()) &
        (df["nombre"].str.strip().str.lower() == nombre.strip().lower())
    ]
    if fila.empty:
        return None
    return fila.iloc[0]


def lista_productos(df):
    return ", ".join(
        [
            f"{row['nombre'].lower()} ({formatear(row['variacion_interanual'])}%)"
            for _, row in df.iterrows()
        ]
    )


def lista_nombres(df):
    return ", ".join([row["nombre"].lower() for _, row in df.iterrows()])


def periodo_a_texto(periodo):
    periodo = str(periodo)
    anio = periodo[:4]
    mes_num = periodo[4:6]

    meses = {
        "01": "enero",
        "02": "febrero",
        "03": "marzo",
        "04": "abril",
        "05": "mayo",
        "06": "junio",
        "07": "julio",
        "08": "agosto",
        "09": "septiembre",
        "10": "octubre",
        "11": "noviembre",
        "12": "diciembre",
    }

    return meses.get(mes_num, "mes"), anio


def construir_contexto(periodo, mes_texto, anio_texto, sector_row, mm, hidro, mm_pos, mm_neg, hidro_neg, hidro_pos):
    return {
        "periodo": str(periodo),
        "periodo_texto": f"{mes_texto} de {anio_texto}",
        "sector": {
            "nombre": "Minería e Hidrocarburos",
            "variacion_interanual": round(float(sector_row["variacion_interanual"]), 2),
        },
        "subsector_mineria_metalica": {
            "variacion_interanual": round(float(mm["variacion_interanual"]), 2),
            "productos_positivos": [
                {
                    "nombre": str(row["nombre"]),
                    "variacion_interanual": round(float(row["variacion_interanual"]), 2),
                }
                for _, row in mm_pos.iterrows()
            ],
            "productos_negativos": [
                {
                    "nombre": str(row["nombre"]),
                    "variacion_interanual": round(float(row["variacion_interanual"]), 2),
                }
                for _, row in mm_neg.iterrows()
            ],
            "incidencia_positiva": round(float(mm_pos["incidencia_interanual"].sum()), 2) if not mm_pos.empty else 0.0,
            "incidencia_negativa": round(abs(float(mm_neg["incidencia_interanual"].sum())), 2) if not mm_neg.empty else 0.0,
        },
        "subsector_hidrocarburos": {
            "variacion_interanual": round(float(hidro["variacion_interanual"]), 2),
            "incidencia_interanual": round(float(hidro["incidencia_interanual"]), 2),
            "productos_negativos": [
                {
                    "nombre": str(row["nombre"]),
                    "variacion_interanual": round(float(row["variacion_interanual"]), 2),
                }
                for _, row in hidro_neg.iterrows()
            ],
            "productos_positivos": [
                {
                    "nombre": str(row["nombre"]),
                    "variacion_interanual": round(float(row["variacion_interanual"]), 2),
                }
                for _, row in hidro_pos.iterrows()
            ],
        },
    }


def generar_texto_llm(contexto):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No se encontró la variable de entorno OPENAI_API_KEY.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
Eres un redactor técnico del sector económico peruano.

Tu tarea es redactar exactamente 3 bloques:
1. SECTOR MINERÍA E HIDROCARBUROS
2. Minería Metálica
3. Hidrocarburos

Instrucciones:
- Usa SOLO la información proporcionada.
- No inventes datos, empresas ni causas externas.
- Mantén estilo formal, técnico e institucional.
- Usa porcentajes con dos decimales y coma decimal.
- Si la variación es negativa, escribe "decrecimiento" o "contracción" sin mostrar doble signo.
- En hidrocarburos, menciona tanto productos negativos como positivos si existen, explicando que los positivos atenúan el resultado.
- Entrega solo el texto final, sin explicaciones adicionales.

Datos:
{json.dumps(contexto, ensure_ascii=False, indent=2)}
"""

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt,
    )

    return response.output_text


if archivo:
    df = pd.read_excel(archivo)

    # Normalizar nombres de columnas
    df.columns = [c.strip().lower() for c in df.columns]

    columnas_necesarias = [
        "periodo",
        "clasificacion",
        "nombre",
        "variacion_interanual",
        "incidencia_interanual",
        "variacion_acumulada",
        "incidencia_acumulada",
    ]

    faltantes = [c for c in columnas_necesarias if c not in df.columns]
    if faltantes:
        st.error(f"Faltan estas columnas en el Excel: {', '.join(faltantes)}")
        st.stop()

    df["clasificacion"] = df["clasificacion"].astype(str).str.strip()
    df["nombre"] = df["nombre"].astype(str).str.strip()
    df["periodo"] = df["periodo"].astype(str).str.strip()

    periodos = sorted(df["periodo"].unique())
    periodo = st.selectbox("Selecciona periodo", periodos)

    dfp = df[df["periodo"] == periodo].copy()

    if dfp.empty:
        st.error("No hay datos para el periodo seleccionado.")
        st.stop()

    mes_texto, anio_texto = periodo_a_texto(periodo)

    sector_row = obtener_fila(dfp, "sector", "Minería e Hidrocarburos")
    mm = obtener_fila(dfp, "subsector", "Minería Metálica")
    hidro = obtener_fila(dfp, "subsector", "Hidrocarburos")

    if sector_row is None or mm is None or hidro is None:
        st.error("Faltan filas principales del sector/subsectores.")
        st.stop()

    var_sector = float(sector_row["variacion_interanual"])

    productos_mm = dfp[
        (dfp["clasificacion"].str.lower() == "producto") &
        (dfp["nombre"].isin(["Cobre", "Hierro", "Oro", "Estaño", "Zinc", "Plomo", "Plata", "Molibdeno"]))
    ].copy()

    productos_hidro = dfp[
        (dfp["clasificacion"].str.lower() == "producto") &
        (dfp["nombre"].isin(["Petróleo crudo", "Líquidos de gas natural", "Gas natural"]))
    ].copy()

    orden_mm = ["Cobre", "Hierro", "Oro", "Estaño", "Molibdeno", "Plata", "Plomo", "Zinc"]
    orden_hidro = ["Petróleo crudo", "Líquidos de gas natural", "Gas natural"]

    productos_mm["nombre"] = pd.Categorical(productos_mm["nombre"], categories=orden_mm, ordered=True)
    productos_hidro["nombre"] = pd.Categorical(productos_hidro["nombre"], categories=orden_hidro, ordered=True)

    productos_mm = productos_mm.sort_values("nombre")
    productos_hidro = productos_hidro.sort_values("nombre")

    mm_pos = productos_mm[productos_mm["variacion_interanual"] > 0].copy()
    mm_neg = productos_mm[productos_mm["variacion_interanual"] < 0].copy()
    hidro_neg = productos_hidro[productos_hidro["variacion_interanual"] < 0].copy()
    hidro_pos = productos_hidro[productos_hidro["variacion_interanual"] > 0].copy()

    lista_mm_pos = lista_productos(mm_pos) if not mm_pos.empty else ""
    lista_mm_neg = lista_productos(mm_neg) if not mm_neg.empty else ""
    lista_hidro_neg_nombres = lista_nombres(hidro_neg) if not hidro_neg.empty else ""
    lista_hidro_neg = lista_productos(hidro_neg) if not hidro_neg.empty else ""
    lista_hidro_pos = lista_productos(hidro_pos) if not hidro_pos.empty else ""

    inc_pos = mm_pos["incidencia_interanual"].sum() if not mm_pos.empty else 0
    inc_neg = abs(mm_neg["incidencia_interanual"].sum()) if not mm_neg.empty else 0

    # Texto base determinístico
    if float(hidro["variacion_interanual"]) < 0:
        parte_hidro = (
            f"explicado por el desempeño negativo del subsector hidrocarburos en "
            f"{formatear(float(hidro['variacion_interanual']))}%, debido a la menor producción de {lista_hidro_neg_nombres}"
            if lista_hidro_neg_nombres
            else f"explicado por el desempeño negativo del subsector hidrocarburos en {formatear(float(hidro['variacion_interanual']))}%"
        )
    else:
        parte_hidro = (
            f"favorecido por el crecimiento del subsector hidrocarburos en "
            f"{formatear(float(hidro['variacion_interanual']))}%, asociado a la mayor producción de {lista_hidro_pos}"
            if lista_hidro_pos
            else f"favorecido por el crecimiento del subsector hidrocarburos en {formatear(float(hidro['variacion_interanual']))}%"
        )

    if float(mm["variacion_interanual"]) > 0:
        parte_mm = (
            f"resultado que fue atenuado por la expansión del subsector de minería metálica en "
            f"{formatear(float(mm['variacion_interanual']))}%, sustentado en los mayores volúmenes de producción de {lista_nombres(mm_pos)}"
            if not mm_pos.empty
            else f"resultado que fue atenuado por la expansión del subsector de minería metálica en {formatear(float(mm['variacion_interanual']))}%"
        )
    else:
        parte_mm = (
            f"resultado que fue acentuado por la contracción del subsector de minería metálica en "
            f"{formatear(abs(float(mm['variacion_interanual'])))}%, debido a la menor producción de {lista_nombres(mm_neg)}"
            if not mm_neg.empty
            else f"resultado que fue acentuado por la contracción del subsector de minería metálica en {formatear(abs(float(mm['variacion_interanual'])))}%"
        )

    texto1 = (
        f"El sector minería e hidrocarburos registró en {mes_texto} de {anio_texto} un "
        f"{'crecimiento' if var_sector > 0 else 'decrecimiento'} de {formatear(abs(var_sector))}% "
        f"respecto al mismo mes del año anterior, {parte_hidro}; {parte_mm}."
    )

    if float(mm["variacion_interanual"]) > 0:
        texto2 = (
            f"La minería metálica registró una expansión de {formatear(abs(float(mm['variacion_interanual'])))}% "
            f"en {mes_texto} de {anio_texto}, explicada por los mayores niveles de producción de "
            f"{lista_mm_pos}, con una incidencia positiva de {formatear(float(inc_pos))} puntos porcentuales "
            f"a la variación del sector; expansión limitada por la disminución en el volumen de producción de "
            f"{lista_mm_neg}, con una incidencia negativa de {formatear(float(inc_neg))} puntos porcentuales."
        )
    else:
        texto2 = (
            f"La minería metálica registró una contracción de {formatear(abs(float(mm['variacion_interanual'])))}% "
            f"en {mes_texto} de {anio_texto}, explicada por la menor producción de "
            f"{lista_mm_neg}, con una incidencia negativa de {formatear(float(inc_neg))} puntos porcentuales; "
            f"resultado que fue atenuado por el incremento en la producción de "
            f"{lista_mm_pos}, con una incidencia positiva de {formatear(float(inc_pos))} puntos porcentuales."
        )

    if float(hidro["variacion_interanual"]) < 0:
        texto3 = (
            f"El subsector de hidrocarburos registró una contracción de {formatear(abs(float(hidro['variacion_interanual'])))}% "
            f"en {mes_texto} de {anio_texto}, explicada por la menor extracción de {lista_hidro_neg}"
        )
        if not hidro_pos.empty:
            texto3 += f"; resultado que fue parcialmente atenuado por el incremento en la producción de {lista_hidro_pos}"
        texto3 += (
            f", que en conjunto determinaron una incidencia de "
            f"{formatear(float(hidro['incidencia_interanual']))} puntos porcentuales."
        )
    else:
        texto3 = (
            f"El subsector de hidrocarburos registró un crecimiento de {formatear(abs(float(hidro['variacion_interanual'])))}% "
            f"en {mes_texto} de {anio_texto}, explicado por la mayor extracción de {lista_hidro_pos}"
        )
        if not hidro_neg.empty:
            texto3 += f"; resultado parcialmente limitado por la menor producción de {lista_hidro_neg}"
        texto3 += (
            f", que en conjunto determinaron una incidencia de "
            f"{formatear(float(hidro['incidencia_interanual']))} puntos porcentuales."
        )

    contexto = construir_contexto(
        periodo=periodo,
        mes_texto=mes_texto,
        anio_texto=anio_texto,
        sector_row=sector_row,
        mm=mm,
        hidro=hidro,
        mm_pos=mm_pos,
        mm_neg=mm_neg,
        hidro_neg=hidro_neg,
        hidro_pos=hidro_pos,
    )

    st.subheader("Texto base")
    st.markdown("### SECTOR MINERÍA E HIDROCARBUROS")
    st.write(texto1)
    st.markdown("### Minería Metálica")
    st.write(texto2)
    st.markdown("### Hidrocarburos")
    st.write(texto3)

    if st.button("Mejorar redacción con LLM"):
        try:
            texto_llm = generar_texto_llm(contexto)
            st.subheader("Texto mejorado con LLM")
            st.text_area("Salida del LLM", texto_llm, height=500)
        except Exception as e:
            st.error(f"Error al usar el LLM: {e}")

    with st.expander("Ver contexto estructurado para LLM"):
        st.json(contexto)

    with st.expander("Ver datos del periodo seleccionado"):
        st.dataframe(dfp)