import pandas as pd

def obtener_fila(df, clasificacion, nombre):
    """
    Busca una fila por clasificación y nombre.
    Ejemplo:
    clasificacion = "sector"
    nombre = "Minería e Hidrocarburos"
    """

    fila = df[
        (df["clasificacion"].str.strip().str.lower() == clasificacion.strip().lower()) &
        (df["nombre"].str.strip().str.lower() == nombre.strip().lower())
    ]

    if fila.empty:
        return None

    return fila.iloc[0]

from core.formatter import (
    formatear,
    periodo_a_texto,
    lista_productos,
    lista_productos_acumulado,
    lista_nombres,
)

def obtener_fila(df, clasificacion, nombre):
    fila = df[
        (df["clasificacion"].str.strip().str.lower() == clasificacion.strip().lower()) &
        (df["nombre"].str.strip().str.lower() == nombre.strip().lower())
    ]

    if fila.empty:
        return None

    return fila.iloc[0]

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

    mm_pos_acum = productos_mm[productos_mm["variacion_acumulada"] > 0].copy()
    mm_neg_acum = productos_mm[productos_mm["variacion_acumulada"] < 0].copy()

    hidro_pos_acum = productos_hidro[productos_hidro["variacion_acumulada"] > 0].copy()
    hidro_neg_acum = productos_hidro[productos_hidro["variacion_acumulada"] < 0].copy()

    # Ordenar por incidencia acumulada
    mm_pos_acum = mm_pos_acum.sort_values("incidencia_acumulada", ascending=False)
    mm_neg_acum = mm_neg_acum.sort_values("incidencia_acumulada", ascending=True)

    hidro_pos_acum = hidro_pos_acum.sort_values("incidencia_acumulada", ascending=False)
    hidro_neg_acum = hidro_neg_acum.sort_values("incidencia_acumulada", ascending=True)

    lista_mm_pos_acum = lista_productos_acumulado(mm_pos_acum) if not mm_pos_acum.empty else ""
    lista_mm_neg_acum = lista_productos_acumulado(mm_neg_acum) if not mm_neg_acum.empty else ""

    lista_hidro_pos_acum = lista_productos_acumulado(hidro_pos_acum) if not hidro_pos_acum.empty else ""
    lista_hidro_neg_acum = lista_productos_acumulado(hidro_neg_acum) if not hidro_neg_acum.empty else ""

    inc_mm_pos_acum = mm_pos_acum["incidencia_acumulada"].sum() if not mm_pos_acum.empty else 0
    inc_mm_neg_acum = mm_neg_acum["incidencia_acumulada"].sum() if not mm_neg_acum.empty else 0

    inc_hidro_pos_acum = hidro_pos_acum["incidencia_acumulada"].sum() if not hidro_pos_acum.empty else 0
    inc_hidro_neg_acum = hidro_neg_acum["incidencia_acumulada"].sum() if not hidro_neg_acum.empty else 0

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
        texto_resumen_hidro = (
            f"determinado por el comportamiento decreciente del subsector hidrocarburos "
            f"en {formatear(var_hidro)}%, con reportes a la baja de {lista_hidro_neg_nombres}"
        )
    else:
        texto_resumen_hidro = (
            f"favorecido por el comportamiento creciente del subsector hidrocarburos "
            f"en {formatear(var_hidro)}%, explicado por la mayor producción de {lista_nombres(hidro_pos)}"
        )

    if var_mm > 0:
        texto_resumen_mm = (
            f"la actividad minera metálica presentó un avance de {formatear(abs(var_mm))}%, "
            f"explicado fundamentalmente por la mayor producción de {lista_nombres(mm_pos)}"
        )
    else:
        texto_resumen_mm = (
            f"la actividad minera metálica presentó una disminución de {formatear(abs(var_mm))}%, "
            f"explicada por la menor producción de {lista_nombres(mm_neg)}"
        )

    if var_hidro < 0:
        texto_detalle_hidro = (
            f"El subsector hidrocarburos se contrajo en {formatear(abs(var_hidro))}%, "
            f"como consecuencia del menor volumen registrado de {lista_hidro_neg}."
        )
    else:
        texto_detalle_hidro = (
            f"El subsector hidrocarburos creció en {formatear(abs(var_hidro))}%, "
            f"como consecuencia del mayor volumen registrado de {lista_hidro_pos}."
        )

    if var_mm > 0:
        texto_detalle_mm = (
            f"El subsector minero metálico registró incremento de {formatear(var_mm)}%, "
            f"ante la mayor producción de {lista_mm_pos}"
        )

        if lista_mm_neg:
            texto_detalle_mm += (
                f"; mientras que, la producción de {lista_mm_neg}."
            )
        else:
            texto_detalle_mm += "."

    else:
        texto_detalle_mm = (
            f"El subsector minero metálico registró disminución de {formatear(abs(var_mm))}%, "
            f"ante la menor producción de {lista_mm_neg}"
        )

        if lista_mm_pos:
            texto_detalle_mm += (
                f"; no obstante, la producción de {lista_mm_pos} atenuó parcialmente el resultado."
            )
        else:
            texto_detalle_mm += "."

    texto1 = (
        f"El sector minería e hidrocarburos registró en {mes_texto} de "
        f"{anio_texto} un {'crecimiento' if var_sector > 0 else 'decrecimiento'} "
        f"de {formatear(abs(var_sector))}% respecto al mismo mes del año anterior. "
        f"Este resultado estuvo asociado al comportamiento del subsector Hidrocarburos "
        f"en {formatear(var_hidro)}% y de la minería metálica en {formatear(var_mm)}%."
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
            "variacion_acumulada": round(float(sector_row["variacion_acumulada"]), 2),
        },
        "subsector_mineria_metalica": {
            "variacion_interanual": round(var_mm, 2),
            "variacion_acumulada": round(float(mm["variacion_acumulada"]), 2),
            "incidencia_interanual": round(float(mm["incidencia_interanual"]), 2),
        },
        "subsector_hidrocarburos": {
            "variacion_interanual": round(var_hidro, 2),
            "variacion_acumulada": round(float(hidro["variacion_acumulada"]), 2),
            "incidencia_interanual": round(float(hidro["incidencia_interanual"]), 2),
        },
    }

    # =========================
    # REPORTE 1: EVOLUCIÓN SECTORIAL
    # =========================
    conector_resumen_mm = "En contraste" if var_hidro * var_mm < 0 else "Asimismo"

    reporte_1 = f"""
    EVOLUCIÓN SECTORIAL

Índice de la Producción Minera y de Hidrocarburos
Año base 2007

- El Índice de la Producción Minera y de Hidrocarburos registró {'aumento' if var_sector > 0 else 'disminución'} de {formatear(abs(var_sector))}% en {mes_texto} {anio_texto}, {texto_resumen_hidro}.

- {conector_resumen_mm}, {texto_resumen_mm}.

Variación interanual del Índice de la Producción Minera y de Hidrocarburos

- En {mes_texto} {anio_texto}, la variación de {formatear(var_sector)}% fue producto del comportamiento del subsector hidrocarburos en {formatear(var_hidro)}% con una incidencia de {formatear(float(hidro['incidencia_interanual']))} puntos porcentuales en el índice sectorial; y de la actividad minera metálica en {formatear(var_mm)}% con una incidencia de {formatear(float(mm['incidencia_interanual']))} puntos porcentuales.

- {texto_detalle_hidro}

- {texto_detalle_mm}
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
    if not mm_pos_acum.empty and not mm_neg_acum.empty:
        texto_mm_acum = (
            f"El sector minería e hidrocarburos, en el periodo enero – {mes_texto} de {anio_texto}, "
            f"registró un {'crecimiento' if float(sector_row['variacion_acumulada']) > 0 else 'decrecimiento'} "
            f"de {formatear(abs(float(sector_row['variacion_acumulada'])))}%, explicado por el desempeño "
            f"{'positivo' if float(mm['variacion_acumulada']) > 0 else 'negativo'} de la actividad minera metálica "
            f"en {formatear(float(mm['variacion_acumulada']))}%, sustentado en los mayores volúmenes de producción de "
            f"{lista_mm_pos_acum}, con una incidencia positiva conjunta de "
            f"{formatear(abs(float(inc_mm_pos_acum)))} puntos porcentuales al resultado global del sector; "
            f"atenuado parcialmente por la variación acumulada negativa en la producción de {lista_mm_neg_acum}, "
            f"con una incidencia negativa de {formatear(abs(float(inc_mm_neg_acum)))} puntos porcentuales."
        )

    elif not mm_pos_acum.empty:
        texto_mm_acum = (
            f"El sector minería e hidrocarburos, en el periodo enero – {mes_texto} de {anio_texto}, "
            f"registró un {'crecimiento' if float(sector_row['variacion_acumulada']) > 0 else 'decrecimiento'} "
            f"de {formatear(abs(float(sector_row['variacion_acumulada'])))}%, explicado por el desempeño positivo "
            f"de la actividad minera metálica en {formatear(float(mm['variacion_acumulada']))}%, sustentado en los "
            f"mayores volúmenes de producción de {lista_mm_pos_acum}, con una incidencia positiva conjunta de "
            f"{formatear(abs(float(inc_mm_pos_acum)))} puntos porcentuales al resultado global del sector."
        )

    elif not mm_neg_acum.empty:
        texto_mm_acum = (
            f"El sector minería e hidrocarburos, en el periodo enero – {mes_texto} de {anio_texto}, "
            f"registró un {'crecimiento' if float(sector_row['variacion_acumulada']) > 0 else 'decrecimiento'} "
            f"de {formatear(abs(float(sector_row['variacion_acumulada'])))}%, influenciado por el desempeño negativo "
            f"de la actividad minera metálica en {formatear(float(mm['variacion_acumulada']))}%, explicado por la "
            f"menor producción acumulada de {lista_mm_neg_acum}, con una incidencia negativa conjunta de "
            f"{formatear(abs(float(inc_mm_neg_acum)))} puntos porcentuales."
        )

    else:
        texto_mm_acum = (
            f"El sector minería e hidrocarburos, en el periodo enero – {mes_texto} de {anio_texto}, "
            f"registró una variación acumulada de {formatear(float(sector_row['variacion_acumulada']))}%."
        )
        
    if not hidro_neg_acum.empty and not hidro_pos_acum.empty:
        texto_hidro_acum = (
            f"Por otro lado, el subsector hidrocarburos presentó "
            f"{'crecimiento' if float(hidro['variacion_acumulada']) > 0 else 'disminución'} "
            f"de {formatear(abs(float(hidro['variacion_acumulada'])))}% en el periodo de referencia, "
            f"determinado por el menor volumen de explotación de {lista_hidro_neg_acum}, "
            f"con una incidencia negativa de {formatear(abs(float(inc_hidro_neg_acum)))} "
            f"puntos porcentuales a la evolución del sector; en contraste, "
            f"la producción de {lista_hidro_pos_acum} registró incrementos "
            f"con una incidencia positiva conjunta de {formatear(abs(float(inc_hidro_pos_acum)))} "
            f"puntos porcentuales."
        )

    elif not hidro_neg_acum.empty:
        texto_hidro_acum = (
            f"Por otro lado, el subsector hidrocarburos presentó disminución de "
            f"{formatear(abs(float(hidro['variacion_acumulada'])))}% en el periodo de referencia, "
            f"determinada por el menor volumen de explotación de {lista_hidro_neg_acum}, "
            f"con una incidencia negativa de {formatear(abs(float(inc_hidro_neg_acum)))} "
            f"puntos porcentuales a la evolución del sector."
        )

    elif not hidro_pos_acum.empty:
        texto_hidro_acum = (
            f"Por otro lado, el subsector hidrocarburos presentó crecimiento de "
            f"{formatear(abs(float(hidro['variacion_acumulada'])))}% en el periodo de referencia, "
            f"explicado por el mayor volumen de explotación de {lista_hidro_pos_acum}, "
            f"con una incidencia positiva conjunta de {formatear(abs(float(inc_hidro_pos_acum)))} "
            f"puntos porcentuales a la evolución del sector."
        )

    else:
        texto_hidro_acum = (
            f"Por otro lado, el subsector hidrocarburos presentó una variación acumulada de "
            f"{formatear(float(hidro['variacion_acumulada']))}%."
        )

    if tipo_reporte == "mensual_y_acumulado":
        reporte_3 = f"""
    Producción Sectorial: Enero-{mes_texto.capitalize()} {anio_texto}

Sector Minería e Hidrocarburos

{texto_mm_acum}

{texto_hidro_acum}
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