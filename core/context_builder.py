import pandas as pd

from core.formatter import (
    formatear,
    periodo_a_texto,
    lista_productos,
    lista_nombres,
)

from core.processor import obtener_fila


PRODUCTOS_MM = [
    "Cobre", "Hierro", "Oro", "Estaño",
    "Zinc", "Plomo", "Plata", "Molibdeno"
]

PRODUCTOS_HIDRO = [
    "Petróleo crudo",
    "Líquidos de gas natural",
    "Gas natural"
]

ORDEN_MM = [
    "Cobre", "Hierro", "Oro", "Estaño",
    "Molibdeno", "Plata", "Plomo", "Zinc"
]

ORDEN_HIDRO = [
    "Petróleo crudo",
    "Líquidos de gas natural",
    "Gas natural"
]

def obtener_tipo_reporte(periodo):
    periodo = str(periodo)
    mes = periodo[4:6]

    if mes == "01":
        return "mensual"
    elif mes == "12":
        return "anual_y_mensual"
    else:
        return "mensual_y_acumulado"


def ordenar_productos(df, orden):
    df = df.copy()
    df["nombre"] = pd.Categorical(
        df["nombre"],
        categories=orden,
        ordered=True
    )
    return df.sort_values("nombre")


def construir_contexto(df_periodo, periodo):
    """
    Construye:
    - contexto estructurado para LLM
    - texto base determinístico
    """

    mes_texto, anio_texto = periodo_a_texto(periodo)

    tipo_reporte = obtener_tipo_reporte(periodo)

    sector_row = obtener_fila(
        df_periodo,
        "sector",
        "Minería e Hidrocarburos"
    )

    mm = obtener_fila(
        df_periodo,
        "subsector",
        "Minería Metálica"
    )

    hidro = obtener_fila(
        df_periodo,
        "subsector",
        "Hidrocarburos"
    )

    if sector_row is None or mm is None or hidro is None:
        raise ValueError("Faltan filas principales del sector o subsectores.")

    productos_mm = df_periodo[
        (df_periodo["clasificacion"].str.lower() == "producto") &
        (df_periodo["nombre"].isin(PRODUCTOS_MM))
    ].copy()

    productos_hidro = df_periodo[
        (df_periodo["clasificacion"].str.lower() == "producto") &
        (df_periodo["nombre"].isin(PRODUCTOS_HIDRO))
    ].copy()

    productos_mm = ordenar_productos(productos_mm, ORDEN_MM)
    productos_hidro = ordenar_productos(productos_hidro, ORDEN_HIDRO)

    mm_pos = productos_mm[productos_mm["variacion_interanual"] > 0].copy()
    mm_neg = productos_mm[productos_mm["variacion_interanual"] < 0].copy()

    hidro_pos = productos_hidro[
        productos_hidro["variacion_interanual"] > 0
    ].copy()

    hidro_neg = productos_hidro[
        productos_hidro["variacion_interanual"] < 0
    ].copy()

    lista_mm_pos = lista_productos(mm_pos) if not mm_pos.empty else ""
    lista_mm_neg = lista_productos(mm_neg) if not mm_neg.empty else ""

    lista_hidro_neg_nombres = (
        lista_nombres(hidro_neg) if not hidro_neg.empty else ""
    )

    lista_hidro_neg = (
        lista_productos(hidro_neg) if not hidro_neg.empty else ""
    )

    lista_hidro_pos = (
        lista_productos(hidro_pos) if not hidro_pos.empty else ""
    )

    inc_pos = (
        mm_pos["incidencia_interanual"].sum()
        if not mm_pos.empty
        else 0
    )

    inc_neg = (
        abs(mm_neg["incidencia_interanual"].sum())
        if not mm_neg.empty
        else 0
    )

    var_sector = float(sector_row["variacion_interanual"])
    var_mm = float(mm["variacion_interanual"])
    var_hidro = float(hidro["variacion_interanual"])

    # =====================================================
    # TEXTO 1: SECTOR MINERÍA E HIDROCARBUROS
    # =====================================================

    if var_hidro < 0:
        parte_hidro = (
            f"explicado por el desempeño negativo del subsector hidrocarburos en "
            f"{formatear(var_hidro)}%, debido a la menor producción de "
            f"{lista_hidro_neg_nombres}"
            if lista_hidro_neg_nombres
            else (
                f"explicado por el desempeño negativo del subsector "
                f"hidrocarburos en {formatear(var_hidro)}%"
            )
        )
    else:
        parte_hidro = (
            f"favorecido por el crecimiento del subsector hidrocarburos en "
            f"{formatear(var_hidro)}%, asociado a la mayor producción de "
            f"{lista_hidro_pos}"
            if lista_hidro_pos
            else (
                f"favorecido por el crecimiento del subsector "
                f"hidrocarburos en {formatear(var_hidro)}%"
            )
        )

    if var_mm > 0:
        parte_mm = (
            f"resultado que fue atenuado por la expansión del subsector de "
            f"minería metálica en {formatear(var_mm)}%, sustentado en los "
            f"mayores volúmenes de producción de {lista_nombres(mm_pos)}"
            if not mm_pos.empty
            else (
                f"resultado que fue atenuado por la expansión del subsector "
                f"de minería metálica en {formatear(var_mm)}%"
            )
        )
    else:
        parte_mm = (
            f"resultado que fue acentuado por la contracción del subsector de "
            f"minería metálica en {formatear(abs(var_mm))}%, debido a la "
            f"menor producción de {lista_nombres(mm_neg)}"
            if not mm_neg.empty
            else (
                f"resultado que fue acentuado por la contracción del subsector "
                f"de minería metálica en {formatear(abs(var_mm))}%"
            )
        )

    texto1 = (
        f"El sector minería e hidrocarburos registró en {mes_texto} de "
        f"{anio_texto} un {'crecimiento' if var_sector > 0 else 'decrecimiento'} "
        f"de {formatear(abs(var_sector))}% respecto al mismo mes del año anterior, "
        f"{parte_hidro}; {parte_mm}."
    )

    # =====================================================
    # TEXTO 2: MINERÍA METÁLICA
    # =====================================================

    if var_mm > 0:
        texto2 = (
            f"La minería metálica registró una expansión de "
            f"{formatear(abs(var_mm))}% en {mes_texto} de {anio_texto}, "
            f"explicada por los mayores niveles de producción de "
            f"{lista_mm_pos}, con una incidencia positiva de "
            f"{formatear(float(inc_pos))} puntos porcentuales a la variación "
            f"del sector; expansión limitada por la disminución en el volumen "
            f"de producción de {lista_mm_neg}, con una incidencia negativa de "
            f"{formatear(float(inc_neg))} puntos porcentuales."
        )
    else:
        texto2 = (
            f"La minería metálica registró una contracción de "
            f"{formatear(abs(var_mm))}% en {mes_texto} de {anio_texto}, "
            f"explicada por la menor producción de {lista_mm_neg}, con una "
            f"incidencia negativa de {formatear(float(inc_neg))} puntos "
            f"porcentuales; resultado que fue atenuado por el incremento en "
            f"la producción de {lista_mm_pos}, con una incidencia positiva de "
            f"{formatear(float(inc_pos))} puntos porcentuales."
        )

    # =====================================================
    # TEXTO 3: HIDROCARBUROS
    # =====================================================

    if var_hidro < 0:
        texto3 = (
            f"El subsector de hidrocarburos registró una contracción de "
            f"{formatear(abs(var_hidro))}% en {mes_texto} de {anio_texto}, "
            f"explicada por la menor extracción de {lista_hidro_neg}"
        )

        if not hidro_pos.empty:
            texto3 += (
                f"; resultado que fue parcialmente atenuado por el incremento "
                f"en la producción de {lista_hidro_pos}"
            )

        texto3 += (
            f", que en conjunto determinaron una incidencia de "
            f"{formatear(float(hidro['incidencia_interanual']))} puntos "
            f"porcentuales."
        )

    else:
        texto3 = (
            f"El subsector de hidrocarburos registró un crecimiento de "
            f"{formatear(abs(var_hidro))}% en {mes_texto} de {anio_texto}, "
            f"explicado por la mayor extracción de {lista_hidro_pos}"
        )

        if not hidro_neg.empty:
            texto3 += (
                f"; resultado parcialmente limitado por la menor producción de "
                f"{lista_hidro_neg}"
            )

        texto3 += (
            f", que en conjunto determinaron una incidencia de "
            f"{formatear(float(hidro['incidencia_interanual']))} puntos "
            f"porcentuales."
        )

    inc_mm = float(mm["incidencia_interanual"])
    inc_hidro = float(hidro["incidencia_interanual"])

    orden_subsectores = sorted(
        [
            ("mineria_metalica", inc_mm),
            ("hidrocarburos", inc_hidro)
        ],
        key=lambda x: abs(x[1]),
        reverse=True
    )

    orden_nombres = [x[0] for x in orden_subsectores]
    # =====================================================
    # CONTEXTO PARA LLM
    # =====================================================

    contexto = {
        "periodo": str(periodo),
        "periodo_texto": f"{mes_texto} de {anio_texto}",
        "tipo_reporte": tipo_reporte,
        "orden_subsectores": orden_nombres,
        "sector": {
            "nombre": "Minería e Hidrocarburos",
            "variacion_interanual": round(var_sector, 2),
        },
        "subsector_mineria_metalica": {
            "variacion_interanual": round(var_mm, 2),
            "productos_positivos": [
                {
                    "nombre": str(row["nombre"]),
                    "variacion_interanual": round(
                        float(row["variacion_interanual"]), 2
                    ),
                    "incidencia_interanual": round(
                        float(row["incidencia_interanual"]), 2
                    ),
                }
                for _, row in mm_pos.iterrows()
            ],
            "productos_negativos": [
                {
                    "nombre": str(row["nombre"]),
                    "variacion_interanual": round(
                        float(row["variacion_interanual"]), 2
                    ),
                    "incidencia_interanual": round(
                        float(row["incidencia_interanual"]), 2
                    ),
                }
                for _, row in mm_neg.iterrows()
            ],
            "incidencia_positiva": round(float(inc_pos), 2),
            "incidencia_negativa": round(float(inc_neg), 2),
        },
        "subsector_hidrocarburos": {
            "variacion_interanual": round(var_hidro, 2),
            "incidencia_interanual": round(
                float(hidro["incidencia_interanual"]), 2
            ),
            "productos_negativos": [
                {
                    "nombre": str(row["nombre"]),
                    "variacion_interanual": round(
                        float(row["variacion_interanual"]), 2
                    ),
                    "incidencia_interanual": round(
                        float(row["incidencia_interanual"]), 2
                    ),
                }
                for _, row in hidro_neg.iterrows()
            ],
            "productos_positivos": [
                {
                    "nombre": str(row["nombre"]),
                    "variacion_interanual": round(
                        float(row["variacion_interanual"]), 2
                    ),
                    "incidencia_interanual": round(
                        float(row["incidencia_interanual"]), 2
                    ),
                }
                for _, row in hidro_pos.iterrows()
            ],
        },
    }

    # =========================
    # REPORTE 1: EVOLUCIÓN SECTORIAL
    # =========================

    reporte_1 = f"""
    EVOLUCIÓN SECTORIAL

    Índice de la Producción Minera y de Hidrocarburos

    Año base 2007

    • El Índice de la Producción Minera y de Hidrocarburos registró {'aumento' if var_sector > 0 else 'disminución'} de {formatear(abs(var_sector))}% en {mes_texto} {anio_texto}, determinado por el comportamiento {'creciente' if var_hidro > 0 else 'decreciente'} del subsector hidrocarburos en {formatear(var_hidro)}%.

    • {'Asimismo' if var_mm > 0 and var_hidro > 0 else 'En contraste'}, la actividad minera metálica presentó {'un avance' if var_mm > 0 else 'una disminución'} de {formatear(abs(var_mm))}%.

    Variación interanual del Índice de la Producción Minera y de Hidrocarburos

    En {mes_texto} {anio_texto}, la variación de {formatear(var_sector)}% fue producto del comportamiento del subsector hidrocarburos en {formatear(var_hidro)}% con una incidencia de {formatear(float(hidro['incidencia_interanual']))} puntos porcentuales en el índice sectorial; y de la actividad minera metálica en {formatear(var_mm)}%.

    El subsector hidrocarburos registró variación de {formatear(var_hidro)}%, como consecuencia del comportamiento de {lista_hidro_neg if not hidro_neg.empty else lista_hidro_pos}.

    El subsector minero metálico registró variación de {formatear(var_mm)}%, ante el comportamiento positivo de {lista_mm_pos}; mientras que, la producción con resultado negativo correspondió a {lista_mm_neg}.
    """.strip()


    # =========================
    # REPORTE 2: PRODUCCIÓN MENSUAL
    # =========================

    reporte_2 = f"""
    Producción Sectorial: {mes_texto.capitalize()} {anio_texto}

    Sector Minería e Hidrocarburos

    {texto1}

    {texto2}

    {texto3}
    """.strip()


    # =========================
    # REPORTE 3: ACUMULADO / ANUAL
    # =========================

    if tipo_reporte == "mensual_y_acumulado":
        reporte_3 = f"""
    Producción Sectorial: Enero-{mes_texto.capitalize()} {anio_texto}

    Sector Minería e Hidrocarburos

    El sector minería e hidrocarburos, en el periodo enero – {mes_texto} de {anio_texto}, registró una variación acumulada de {formatear(float(sector_row['variacion_acumulada']))}%.

    La actividad minera metálica registró una variación acumulada de {formatear(float(mm['variacion_acumulada']))}%.

    Por otro lado, el subsector hidrocarburos presentó una variación acumulada de {formatear(float(hidro['variacion_acumulada']))}%.
    """.strip()

    elif tipo_reporte == "anual_y_mensual":
        reporte_3 = f"""
    Producción Sectorial: Año {anio_texto}

    Sector Minería e Hidrocarburos

    En el año {anio_texto}, el sector minería e hidrocarburos presentó una variación acumulada de {formatear(float(sector_row['variacion_acumulada']))}%.

    La actividad minera metálica registró una variación acumulada de {formatear(float(mm['variacion_acumulada']))}%.

    El subsector hidrocarburos registró una variación acumulada de {formatear(float(hidro['variacion_acumulada']))}%.
    """.strip()

    else:
        reporte_3 = ""


    texto_base = {
        "reporte_1": reporte_1,
        "reporte_2": reporte_2,
        "reporte_3": reporte_3,
    }

    return contexto, texto_base