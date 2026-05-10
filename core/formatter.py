def formatear(num):
    """
    Formatea número a porcentaje con coma decimal.
    Ej: 1.11 → 1,11
    """
    try:
        return f"{float(num):.2f}".replace(".", ",")
    except (ValueError, TypeError):
        return "0,00"


def periodo_a_texto(periodo):
    """
    Convierte periodo YYYYMM → (mes_texto, año)
    Ej: 202602 → ("febrero", "2026")
    """
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

    mes_texto = meses.get(mes_num, "mes")

    return mes_texto, anio


def lista_productos(df):
    """
    Devuelve string tipo:
    'cobre (2,57%), hierro (1,48%)'
    """
    if df is None or df.empty:
        return ""

    lista = []

    for _, row in df.iterrows():
        nombre = str(row["nombre"]).lower()
        variacion = formatear(row["variacion_interanual"])

        lista.append(f"{nombre} ({variacion}%)")

    return ", ".join(lista)


def lista_nombres(df):
    """
    Devuelve string tipo:
    'cobre, hierro, oro'
    """
    if df is None or df.empty:
        return ""

    return ", ".join([str(row["nombre"]).lower() for _, row in df.iterrows()])

def lista_productos_acumulado(df):
    partes = []

    for _, row in df.iterrows():
        nombre = row["nombre"]
        variacion = formatear(float(row["variacion_acumulada"]))
        partes.append(f"{nombre.lower()} en {variacion}%")

    return ", ".join(partes)