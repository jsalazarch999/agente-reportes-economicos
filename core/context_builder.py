import pandas as pd

from core.formatter import (
    formatear,
    periodo_a_texto,
    lista_productos,
    lista_productos_acumulado,
    lista_nombres,
)

# =====================================================
# CONSTANTES
# =====================================================

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

# Umbral de incidencia para considerar un producto como "de alta incidencia"
# El RAG recuperará documentos específicos para estos productos
UMBRAL_ALTA_INCIDENCIA = 0.3


# =====================================================
# HELPERS EXISTENTES (sin cambios)
# =====================================================

def obtener_fila(df, clasificacion, nombre):
    """Busca una fila por clasificación y nombre (case-insensitive)."""
    fila = df[
        (df["clasificacion"].str.strip().str.lower() == clasificacion.strip().lower()) &
        (df["nombre"].str.strip().str.lower() == nombre.strip().lower())
    ]
    return None if fila.empty else fila.iloc[0]


def obtener_tipo_reporte(periodo):
    mes = str(periodo)[4:6]
    if mes == "01":
        return "mensual"
    elif mes == "12":
        return "anual_y_mensual"
    return "mensual_y_acumulado"


def ordenar_productos(df, orden):
    df = df.copy()
    df["nombre"] = pd.Categorical(df["nombre"], categories=orden, ordered=True)
    return df.sort_values("nombre")


def _suma_incidencia(df, col):
    return df[col].sum() if not df.empty else 0


def _lista_acum(df):
    return lista_productos_acumulado(df) if not df.empty else ""


def _lista_prod(df):
    return lista_productos(df) if not df.empty else ""


# =====================================================
# HELPERS NUEVOS
# =====================================================

def _obtener_empresas_por_producto(df_periodo, nombre_producto):
    """
    Retorna lista de empresas asociadas a un producto si existe
    la columna 'empresa' en el DataFrame. Retorna lista vacía si no.
    """
    if "empresa" not in df_periodo.columns:
        return []

    filas = df_periodo[
        (df_periodo["clasificacion"].str.lower() == "producto") &
        (df_periodo["nombre"].str.lower() == nombre_producto.lower()) &
        (df_periodo["empresa"].notna()) &
        (df_periodo["empresa"].str.strip() != "")
    ]

    return filas["empresa"].str.strip().unique().tolist()


def _obtener_precio_producto(df_periodo, nombre_producto):
    """
    Retorna el precio internacional de un producto si existe
    la columna 'precio_internacional'. Retorna None si no.
    """
    if "precio_internacional" not in df_periodo.columns:
        return None

    filas = df_periodo[
        (df_periodo["clasificacion"].str.lower() == "producto") &
        (df_periodo["nombre"].str.lower() == nombre_producto.lower()) &
        (df_periodo["precio_internacional"].notna())
    ]

    if filas.empty:
        return None

    return round(float(filas.iloc[0]["precio_internacional"]), 2)


def _productos_alta_incidencia(productos_df, col_incidencia, umbral=UMBRAL_ALTA_INCIDENCIA):
    """
    Retorna lista de nombres de productos cuya incidencia absoluta
    supera el umbral definido. Usada por el RAG para recuperación focalizada.
    """
    if productos_df.empty:
        return []

    return productos_df[
        productos_df[col_incidencia].abs() >= umbral
    ]["nombre"].tolist()


def _construir_contexto_productos(df_periodo, productos_df, subsector):
    """
    Construye el bloque de contexto de productos para el JSON del LLM.
    Incluye empresa y precio si están disponibles en los datos.
    """
    productos_contexto = []

    for _, row in productos_df.iterrows():
        nombre = row["nombre"]
        entry = {
            "nombre": nombre,
            "subsector": subsector,
            "variacion_interanual": round(float(row["variacion_interanual"]), 2),
            "incidencia_interanual": round(float(row["incidencia_interanual"]), 2),
            "variacion_acumulada":   round(float(row["variacion_acumulada"]), 2),
        }

        # Empresa: solo si existe en los datos
        empresas = _obtener_empresas_por_producto(df_periodo, nombre)
        if empresas:
            entry["empresas"] = empresas

        # Precio: solo si existe en los datos
        precio = _obtener_precio_producto(df_periodo, nombre)
        if precio is not None:
            entry["precio_internacional"] = precio

        productos_contexto.append(entry)

    return productos_contexto


# =====================================================
# TEXTOS ACUMULADOS (sin cambios)
# =====================================================

def _texto_mm_acumulado(sector_row, mm, mes_texto, anio_texto,
                         mm_pos_acum, mm_neg_acum,
                         lista_mm_pos_acum, lista_mm_neg_acum,
                         inc_mm_pos_acum, inc_mm_neg_acum):
    var_sector_acum = float(sector_row["variacion_acumulada"])
    var_mm_acum = float(mm["variacion_acumulada"])
    crec_sector = "crecimiento" if var_sector_acum > 0 else "decrecimiento"
    signo_mm = "positivo" if var_mm_acum > 0 else "negativo"
    periodo_ref = f"en el periodo enero – {mes_texto} de {anio_texto}"

    base = (
        f"El sector minería e hidrocarburos, {periodo_ref}, "
        f"registró un {crec_sector} de {formatear(abs(var_sector_acum))}%, "
        f"explicado por el desempeño {signo_mm} de la actividad minera metálica "
        f"en {formatear(abs(var_mm_acum))}%"
    )

    if not mm_pos_acum.empty and not mm_neg_acum.empty:
        return (
            f"{base}, sustentado en los mayores volúmenes de producción de "
            f"{lista_mm_pos_acum}, con una incidencia positiva conjunta de "
            f"{formatear(abs(inc_mm_pos_acum))} puntos porcentuales al resultado global del sector; "
            f"atenuado parcialmente por la variación acumulada negativa en la producción de "
            f"{lista_mm_neg_acum}, con una incidencia negativa de "
            f"{formatear(abs(inc_mm_neg_acum))} puntos porcentuales."
        )
    elif not mm_pos_acum.empty:
        return (
            f"{base}, sustentado en los mayores volúmenes de producción de "
            f"{lista_mm_pos_acum}, con una incidencia positiva conjunta de "
            f"{formatear(abs(inc_mm_pos_acum))} puntos porcentuales al resultado global del sector."
        )
    elif not mm_neg_acum.empty:
        return (
            f"{base}, explicado por la menor producción acumulada de "
            f"{lista_mm_neg_acum}, con una incidencia negativa conjunta de "
            f"{formatear(abs(inc_mm_neg_acum))} puntos porcentuales."
        )
    return f"{base}, registrando una variación acumulada de {formatear(var_mm_acum)}%."


def _texto_hidro_acumulado(hidro, mes_texto, anio_texto,
                            hidro_pos_acum, hidro_neg_acum,
                            lista_hidro_pos_acum, lista_hidro_neg_acum,
                            inc_hidro_pos_acum, inc_hidro_neg_acum):
    var_hidro_acum = float(hidro["variacion_acumulada"])
    crec = "crecimiento" if var_hidro_acum > 0 else "disminución"

    base = (
        f"Por otro lado, el subsector hidrocarburos presentó {crec} de "
        f"{formatear(abs(var_hidro_acum))}% en el periodo de referencia"
    )

    if not hidro_neg_acum.empty and not hidro_pos_acum.empty:
        return (
            f"{base}, determinado por el menor volumen de explotación de "
            f"{lista_hidro_neg_acum}, con una incidencia negativa de "
            f"{formatear(abs(inc_hidro_neg_acum))} puntos porcentuales al resultado del sector; "
            f"en contraste, la producción de {lista_hidro_pos_acum} registró incrementos "
            f"con una incidencia positiva conjunta de "
            f"{formatear(abs(inc_hidro_pos_acum))} puntos porcentuales."
        )
    elif not hidro_neg_acum.empty:
        return (
            f"{base}, determinada por el menor volumen de explotación de "
            f"{lista_hidro_neg_acum}, con una incidencia negativa de "
            f"{formatear(abs(inc_hidro_neg_acum))} puntos porcentuales al resultado del sector."
        )
    elif not hidro_pos_acum.empty:
        return (
            f"{base}, explicado por el mayor volumen de explotación de "
            f"{lista_hidro_pos_acum}, con una incidencia positiva conjunta de "
            f"{formatear(abs(inc_hidro_pos_acum))} puntos porcentuales al resultado del sector."
        )
    return f"{base}, registrando una variación acumulada de {formatear(var_hidro_acum)}%."


# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================

def construir_contexto(df_periodo, periodo, sector="Minería e Hidrocarburos"):
    """
    Construye el contexto estructurado para el LLM
    y los textos base determinísticos.

    El contexto ahora incluye:
    - empresas por producto (si disponibles en los datos)
    - precios internacionales (si disponibles en los datos)
    - productos_alta_incidencia (para focalizar la recuperación RAG)
    """
    mes_texto, anio_texto = periodo_a_texto(periodo)
    tipo_reporte = obtener_tipo_reporte(periodo)

    # --- Filas principales ---
    sector_row = obtener_fila(df_periodo, "sector", sector)
    mm         = obtener_fila(df_periodo, "subsector", "Minería Metálica")
    hidro      = obtener_fila(df_periodo, "subsector", "Hidrocarburos")

    if sector_row is None or mm is None or hidro is None:
        raise ValueError("Faltan filas principales del sector o subsectores.")

    # --- Productos ---
    def filtrar_productos(nombres_validos):
        return df_periodo[
            (df_periodo["clasificacion"].str.lower() == "producto") &
            (df_periodo["nombre"].isin(nombres_validos))
        ].copy()

    productos_mm    = ordenar_productos(filtrar_productos(PRODUCTOS_MM),    ORDEN_MM)
    productos_hidro = ordenar_productos(filtrar_productos(PRODUCTOS_HIDRO), ORDEN_HIDRO)

    # --- Variaciones ---
    var_sector     = float(sector_row["variacion_interanual"])
    var_mm         = float(mm["variacion_interanual"])
    var_hidro      = float(hidro["variacion_interanual"])
    var_sector_acum = float(sector_row["variacion_acumulada"])
    var_mm_acum    = float(mm["variacion_acumulada"])
    var_hidro_acum = float(hidro["variacion_acumulada"])
    inc_mm         = float(mm["incidencia_interanual"])
    inc_hidro      = float(hidro["incidencia_interanual"])

    # --- Splits interanuales ---
    mm_pos    = productos_mm[productos_mm["variacion_interanual"] > 0].copy()
    mm_neg    = productos_mm[productos_mm["variacion_interanual"] < 0].copy()
    hidro_pos = productos_hidro[productos_hidro["variacion_interanual"] > 0].copy()
    hidro_neg = productos_hidro[productos_hidro["variacion_interanual"] < 0].copy()

    lista_mm_pos           = _lista_prod(mm_pos)
    lista_mm_neg           = _lista_prod(mm_neg)
    lista_hidro_pos        = _lista_prod(hidro_pos)
    lista_hidro_neg        = _lista_prod(hidro_neg)
    lista_hidro_neg_nombres = lista_nombres(hidro_neg) if not hidro_neg.empty else ""

    inc_pos = mm_pos["incidencia_interanual"].sum() if not mm_pos.empty else 0
    inc_neg = abs(mm_neg["incidencia_interanual"].sum()) if not mm_neg.empty else 0

    # --- Splits acumulados ---
    mm_pos_acum    = productos_mm[productos_mm["variacion_acumulada"] > 0].copy()
    mm_neg_acum    = productos_mm[productos_mm["variacion_acumulada"] < 0].copy()
    hidro_pos_acum = productos_hidro[productos_hidro["variacion_acumulada"] > 0].copy()
    hidro_neg_acum = productos_hidro[productos_hidro["variacion_acumulada"] < 0].copy()

    mm_pos_acum    = mm_pos_acum.sort_values("incidencia_acumulada", ascending=False)
    mm_neg_acum    = mm_neg_acum.sort_values("incidencia_acumulada", ascending=True)
    hidro_pos_acum = hidro_pos_acum.sort_values("incidencia_acumulada", ascending=False)
    hidro_neg_acum = hidro_neg_acum.sort_values("incidencia_acumulada", ascending=True)

    lista_mm_pos_acum    = _lista_acum(mm_pos_acum)
    lista_mm_neg_acum    = _lista_acum(mm_neg_acum)
    lista_hidro_pos_acum = _lista_acum(hidro_pos_acum)
    lista_hidro_neg_acum = _lista_acum(hidro_neg_acum)

    inc_mm_pos_acum    = _suma_incidencia(mm_pos_acum,    "incidencia_acumulada")
    inc_mm_neg_acum    = _suma_incidencia(mm_neg_acum,    "incidencia_acumulada")
    inc_hidro_pos_acum = _suma_incidencia(hidro_pos_acum, "incidencia_acumulada")
    inc_hidro_neg_acum = _suma_incidencia(hidro_neg_acum, "incidencia_acumulada")

    # =====================================================
    # TEXTOS INTERANUALES (sin cambios)
    # =====================================================

    texto_resumen_hidro = (
        f"determinado por el comportamiento decreciente del subsector hidrocarburos "
        f"en {formatear(abs(var_hidro))}%, con reportes a la baja de {lista_hidro_neg_nombres}"
        if var_hidro < 0 else
        f"favorecido por el comportamiento creciente del subsector hidrocarburos "
        f"en {formatear(abs(var_hidro))}%, explicado por la mayor producción de {lista_nombres(hidro_pos)}"
    )

    texto_resumen_mm = (
        f"la actividad minera metálica presentó un avance de {formatear(abs(var_mm))}%, "
        f"explicado fundamentalmente por la mayor producción de {lista_nombres(mm_pos)}"
        if var_mm > 0 else
        f"la actividad minera metálica presentó una disminución de {formatear(abs(var_mm))}%, "
        f"explicada por la menor producción de {lista_nombres(mm_neg)}"
    )

    texto_detalle_hidro = (
        f"El subsector hidrocarburos se contrajo en {formatear(abs(var_hidro))}%, "
        f"como consecuencia del menor volumen registrado de {lista_hidro_neg}."
        if var_hidro < 0 else
        f"El subsector hidrocarburos creció en {formatear(abs(var_hidro))}%, "
        f"como consecuencia del mayor volumen registrado de {lista_hidro_pos}."
    )

    if var_mm > 0:
        texto_detalle_mm = (
            f"El subsector minero metálico registró incremento de {formatear(abs(var_mm))}%, "
            f"ante la mayor producción de {lista_mm_pos}"
        )
        texto_detalle_mm += (
            f"; mientras que, la producción de {lista_mm_neg}." if lista_mm_neg else "."
        )
    else:
        texto_detalle_mm = (
            f"El subsector minero metálico registró disminución de {formatear(abs(var_mm))}%, "
            f"ante la menor producción de {lista_mm_neg}"
        )
        texto_detalle_mm += (
            f"; no obstante, la producción de {lista_mm_pos} atenuó parcialmente el resultado."
            if lista_mm_pos else "."
        )

    texto1 = (
        f"El sector minería e hidrocarburos registró en {mes_texto} de {anio_texto} "
        f"un {'crecimiento' if var_sector > 0 else 'decrecimiento'} de "
        f"{formatear(abs(var_sector))}% respecto al mismo mes del año anterior. "
        f"Este resultado estuvo asociado al comportamiento del subsector Hidrocarburos "
        f"en {formatear(var_hidro)}% y de la minería metálica en {formatear(var_mm)}%."
    )

    texto2 = (
        f"La minería metálica registró una {'expansión' if var_mm > 0 else 'contracción'} de "
        f"{formatear(abs(var_mm))}% en {mes_texto} de {anio_texto}, "
        f"explicada por los {'mayores' if var_mm > 0 else 'menores'} niveles de producción de "
        f"{lista_mm_pos if var_mm > 0 else lista_mm_neg}, con una incidencia "
        f"{'positiva' if var_mm > 0 else 'negativa'} de "
        f"{formatear(abs(inc_pos if var_mm > 0 else inc_neg))} puntos porcentuales; "
        f"{'expansión limitada' if var_mm > 0 else 'resultado atenuado'} por la "
        f"{'disminución' if var_mm > 0 else 'mayor producción'} de "
        f"{lista_mm_neg if var_mm > 0 else lista_mm_pos}, con una incidencia "
        f"{'negativa' if var_mm > 0 else 'positiva'} de "
        f"{formatear(abs(inc_neg if var_mm > 0 else inc_pos))} puntos porcentuales."
    )

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
        f"{formatear(inc_hidro)} puntos porcentuales."
    )

    # =====================================================
    # CONTEXTO PARA LLM — ENRIQUECIDO
    # =====================================================

    orden_subsectores = [
        x[0] for x in sorted(
            [("mineria_metalica", inc_mm), ("hidrocarburos", inc_hidro)],
            key=lambda x: abs(x[1]),
            reverse=True
        )
    ]

    # Productos de alta incidencia — usados por el RAG para recuperación focalizada
    alta_inc_mm    = _productos_alta_incidencia(productos_mm,    "incidencia_interanual")
    alta_inc_hidro = _productos_alta_incidencia(productos_hidro, "incidencia_interanual")

    contexto = {
        "periodo":           str(periodo),
        "periodo_texto":     f"{mes_texto} de {anio_texto}",
        "tipo_reporte":      tipo_reporte,
        "orden_subsectores": orden_subsectores,

        # Nuevo: lista de productos con alta incidencia para el RAG
        "productos_alta_incidencia": {
            "mineria_metalica": alta_inc_mm,
            "hidrocarburos":    alta_inc_hidro,
        },

        "sector": {
            "nombre":               sector,
            "variacion_interanual": round(var_sector, 2),
            "variacion_acumulada":  round(var_sector_acum, 2),
        },
        "subsector_mineria_metalica": {
            "variacion_interanual": round(var_mm, 2),
            "variacion_acumulada":  round(var_mm_acum, 2),
            "incidencia_interanual": round(inc_mm, 2),
            # Nuevo: detalle de productos con empresa y precio si disponibles
            "productos": _construir_contexto_productos(
                df_periodo, productos_mm, "mineria_metalica"
            ),
        },
        "subsector_hidrocarburos": {
            "variacion_interanual": round(var_hidro, 2),
            "variacion_acumulada":  round(var_hidro_acum, 2),
            "incidencia_interanual": round(inc_hidro, 2),
            # Nuevo: detalle de productos con empresa y precio si disponibles
            "productos": _construir_contexto_productos(
                df_periodo, productos_hidro, "hidrocarburos"
            ),
        },
    }

    # =====================================================
    # REPORTES BASE (sin cambios)
    # =====================================================

    conector_resumen_mm = "En contraste" if var_hidro * var_mm < 0 else "Asimismo"

    reporte_1 = f"""EVOLUCIÓN SECTORIAL

Índice de la Producción Minera y de Hidrocarburos
Año base 2007

- El Índice de la Producción Minera y de Hidrocarburos registró {'aumento' if var_sector > 0 else 'disminución'} de {formatear(abs(var_sector))}% en {mes_texto} {anio_texto}, {texto_resumen_hidro}.

- {conector_resumen_mm}, {texto_resumen_mm}.

Variación interanual del Índice de la Producción Minera y de Hidrocarburos

- En {mes_texto} {anio_texto}, la variación de {formatear(var_sector)}% fue producto del comportamiento del subsector hidrocarburos en {formatear(var_hidro)}% con una incidencia de {formatear(inc_hidro)} puntos porcentuales en el índice sectorial; y de la actividad minera metálica en {formatear(var_mm)}% con una incidencia de {formatear(inc_mm)} puntos porcentuales.

- {texto_detalle_hidro}

- {texto_detalle_mm}""".strip()

    reporte_2 = f"""Producción Sectorial: {mes_texto.capitalize()} {anio_texto}

Sector Minería e Hidrocarburos

{texto1}

{texto2}

{texto3}""".strip()

    if tipo_reporte == "mensual_y_acumulado":
        texto_mm_acum = _texto_mm_acumulado(
            sector_row, mm, mes_texto, anio_texto,
            mm_pos_acum, mm_neg_acum,
            lista_mm_pos_acum, lista_mm_neg_acum,
            inc_mm_pos_acum, inc_mm_neg_acum
        )
        texto_hidro_acum = _texto_hidro_acumulado(
            hidro, mes_texto, anio_texto,
            hidro_pos_acum, hidro_neg_acum,
            lista_hidro_pos_acum, lista_hidro_neg_acum,
            inc_hidro_pos_acum, inc_hidro_neg_acum
        )
        reporte_3 = f"""Producción Sectorial: Enero-{mes_texto.capitalize()} {anio_texto}

Sector Minería e Hidrocarburos

{texto_mm_acum}

{texto_hidro_acum}""".strip()

    elif tipo_reporte == "anual_y_mensual":
        reporte_3 = f"""Producción Sectorial: Año {anio_texto}

Sector Minería e Hidrocarburos

En el año {anio_texto}, el sector minería e hidrocarburos presentó una variación acumulada de {formatear(var_sector_acum)}%.

La actividad minera metálica registró una variación acumulada de {formatear(var_mm_acum)}%.

El subsector hidrocarburos registró una variación acumulada de {formatear(var_hidro_acum)}%.""".strip()

    else:
        reporte_3 = None

    return contexto, {"reporte_1": reporte_1, "reporte_2": reporte_2, "reporte_3": reporte_3}