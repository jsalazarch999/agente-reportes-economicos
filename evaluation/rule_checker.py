import re

PALABRAS_PROHIBIDAS = [
    "sector industrial",
    "subsectora",
    "molybdeno",
    "precios",
    "mercado internacional",
    "tercer trimestre",
]

TOLERANCIA = 0.5  # diferencia máxima permitida en puntos porcentuales

def extraer_porcentajes(texto):
    patron = r"-?\d+(?:[,.]\d+)?\s*%"
    return re.findall(patron, texto)

def normalizar_porcentaje(valor):
    valor = str(valor).replace("%", "").replace(",", ".").strip()
    try:
        return abs(round(float(valor), 2))
    except (ValueError, TypeError):
        return None

def obtener_porcentajes_contexto(contexto):
    valores = []

    def recorrer(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if "variacion" in k.lower() or "incidencia" in k.lower():
                    valores.append(v)
                recorrer(v)
        elif isinstance(obj, list):
            for item in obj:
                recorrer(item)

    recorrer(contexto)

    porcentajes = []
    for v in valores:
        n = normalizar_porcentaje(v)
        if n is not None:
            porcentajes.append(n)

    return porcentajes


# ← NUEVO: el puente que faltaba
def validar_porcentajes(porcentajes_texto, porcentajes_contexto, tolerancia=TOLERANCIA):
    """
    Verifica que cada porcentaje del contexto (datos reales del Excel)
    aparezca en el texto con una diferencia menor a `tolerancia`.
    """
    advertencias = []
    errores = []

    if not porcentajes_contexto:
        return errores, advertencias

    if not porcentajes_texto:
        errores.append(
            "El texto no contiene porcentajes pero el contexto tiene "
            f"{len(porcentajes_contexto)} valor(es) esperado(s)."
        )
        return errores, advertencias

    for valor_esperado in porcentajes_contexto:
        # busca si algún porcentaje del texto está dentro de la tolerancia
        encontrado = any(
            abs(valor_esperado - valor_texto) <= tolerancia
            for valor_texto in porcentajes_texto
        )
        if not encontrado:
            # distingue entre error grave (diferencia grande) y advertencia (leve)
            diferencia_minima = min(
                abs(valor_esperado - v) for v in porcentajes_texto
            )
            if diferencia_minima > 2.0:
                errores.append(
                    f"Porcentaje {valor_esperado}% del contexto no aparece en el texto "
                    f"(diferencia mínima encontrada: {diferencia_minima:.1f}pp)."
                )
            else:
                advertencias.append(
                    f"Porcentaje {valor_esperado}% podría estar redondeado en el texto "
                    f"(diferencia mínima: {diferencia_minima:.1f}pp)."
                )

    return errores, advertencias


def evaluar_texto(texto, contexto):
    errores = []
    advertencias = []

    texto_lower = texto.lower()
    tipo = contexto.get("tipo_reporte")

    # 1. Palabras prohibidas
    for palabra in PALABRAS_PROHIBIDAS:
        if palabra in texto_lower:
            errores.append(f"Uso no permitido: '{palabra}'")

    # 2. Estructura mínima
    secciones_obligatorias = [
        "EVOLUCIÓN SECTORIAL",
        "ÍNDICE DE LA PRODUCCIÓN MINERA Y DE HIDROCARBUROS",
        "VARIACIÓN INTERANUAL",
        "PRODUCCIÓN SECTORIAL",
    ]
    for seccion in secciones_obligatorias:
        if seccion.lower() not in texto_lower:
            advertencias.append(f"No se encontró la sección: {seccion}")

    # 3. Tipo de reporte
    if tipo == "mensual" and "enero-" in texto_lower:
        errores.append("No debe generar acumulado para enero.")
    if tipo == "anual_y_mensual" and "año" not in texto_lower:
        advertencias.append("El reporte de diciembre debería incluir bloque anual.")
    if tipo == "mensual_y_acumulado" and "enero" not in texto_lower:
        advertencias.append("El reporte debería incluir bloque acumulado enero-periodo.")

    # 4. Extraer porcentajes
    porcentajes_texto = [
        normalizar_porcentaje(p) for p in extraer_porcentajes(texto)
    ]
    porcentajes_texto = [p for p in porcentajes_texto if p is not None]
    porcentajes_contexto = obtener_porcentajes_contexto(contexto)

    # ← NUEVO: ahora sí se usan
    errores_pct, advertencias_pct = validar_porcentajes(
        porcentajes_texto, porcentajes_contexto
    )
    errores.extend(errores_pct)
    advertencias.extend(advertencias_pct)

    # 5. Orden de subsectores
    orden = contexto.get("orden_subsectores", [])
    if len(orden) == 2:
        nombre_1 = orden[0].replace("_", " ")
        nombre_2 = orden[1].replace("_", " ")
        idx_1 = texto_lower.find(nombre_1)
        idx_2 = texto_lower.find(nombre_2)
        if idx_1 != -1 and idx_2 != -1:
            if idx_1 > idx_2:
                advertencias.append(
                    f"Orden incorrecto: debería aparecer primero '{nombre_1}'"
                )

    return {
        "valido": len(errores) == 0,
        "errores": errores,
        "advertencias": advertencias,
        "porcentajes_texto": porcentajes_texto,
        "porcentajes_contexto": porcentajes_contexto,
    }