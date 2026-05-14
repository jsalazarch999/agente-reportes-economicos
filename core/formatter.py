def formatear(num):
    """
    Formatea número a porcentaje con coma decimal.
    Ej: 1.11 → "1,11"
    """
    try:
        return f"{float(num):.2f}".replace(".", ",")
    except (ValueError, TypeError):
        return "0,00"


def periodo_a_texto(periodo):
    """
    Convierte periodo YYYYMM → (mes_texto, año).
    Ej: 202602 → ("febrero", "2026")
    """
    MESES = {
        "01": "enero",   "02": "febrero",  "03": "marzo",
        "04": "abril",   "05": "mayo",     "06": "junio",
        "07": "julio",   "08": "agosto",   "09": "septiembre",
        "10": "octubre", "11": "noviembre","12": "diciembre",
    }

    periodo = str(periodo).strip()

    if len(periodo) != 6 or not periodo.isdigit():
        raise ValueError(f"Formato de periodo inválido: '{periodo}'. Se esperaba YYYYMM.")

    anio = periodo[:4]
    mes_num = periodo[4:6]
    mes_texto = MESES.get(mes_num, "mes")

    return mes_texto, anio


def lista_productos(df):
    """
    Devuelve string tipo: 'cobre (2,57%), hierro (1,48%)'
    Usa variacion_interanual.
    """
    if df is None or df.empty:
        return ""

    return ", ".join(
        f"{str(row['nombre']).lower()} ({formatear(row['variacion_interanual'])}%)"
        for _, row in df.iterrows()
    )


def lista_nombres(df):
    """
    Devuelve string tipo: 'cobre, hierro, oro'
    """
    if df is None or df.empty:
        return ""

    return ", ".join(str(nombre).lower() for nombre in df["nombre"])


def lista_productos_acumulado(df):
    """
    Devuelve string tipo: 'cobre en 2,57%, hierro en 1,48%'
    Usa variacion_acumulada.
    """
    if df is None or df.empty:
        return ""

    return ", ".join(
        f"{str(row['nombre']).lower()} en {formatear(row['variacion_acumulada'])}%"
        for _, row in df.iterrows()
    )