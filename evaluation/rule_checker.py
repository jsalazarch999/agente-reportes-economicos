import re

TOLERANCIA = 0.5  # diferencia máxima permitida en puntos porcentuales
TOLERANCIA_RELATIVA = 0.15  # 15% del valor esperado para valores pequeños

PALABRAS_PROHIBIDAS_DEFAULT = [
    "sector industrial",
    "subsectora",
    "molybdeno",
    "precios",
    "mercado internacional",
    "tercer trimestre",
]

SECCIONES_OBLIGATORIAS_DEFAULT = [
    "EVOLUCIÓN SECTORIAL",
    "ÍNDICE DE LA PRODUCCIÓN MINERA Y DE HIDROCARBUROS",
    "VARIACIÓN INTERANUAL",
    "PRODUCCIÓN SECTORIAL",
]

# Regex más robusto: captura paréntesis, espacios antes de %, signo negativo
_PATRON_PORCENTAJE = re.compile(r"-?\d+(?:[,.]\d+)?\s*%")


def extraer_porcentajes(texto):
    """Extrae todos los porcentajes del texto como strings."""
    return _PATRON_PORCENTAJE.findall(texto)


def normalizar_porcentaje(valor, mantener_signo=True):
    """
    Convierte un string de porcentaje a float.
    Por defecto mantiene el signo para no confundir crecimientos con decrecimientos.
    """
    valor = str(valor).replace("%", "").replace(",", ".").strip()
    try:
        resultado = round(float(valor), 2)
        return resultado if mantener_signo else abs(resultado)
    except (ValueError, TypeError):
        return None


def obtener_porcentajes_contexto(contexto):
    """
    Recorre recursivamente el contexto y extrae valores de
    claves que contengan 'variacion' o 'incidencia'.
    """
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

    return [n for v in valores if (n := normalizar_porcentaje(v)) is not None]


def _tolerancia_para(valor_esperado, tolerancia_abs=TOLERANCIA, tolerancia_rel=TOLERANCIA_RELATIVA):
    """
    Calcula la tolerancia apropiada según la magnitud del valor.
    Para valores pequeños usa tolerancia relativa; para grandes, la absoluta.
    """
    return max(tolerancia_abs, abs(valor_esperado) * tolerancia_rel)


def validar_porcentajes(porcentajes_texto, porcentajes_contexto):
    """
    Verifica que cada porcentaje del contexto (datos reales del Excel)
    aparezca en el texto dentro de la tolerancia permitida.
    Mantiene el signo para distinguir crecimientos de decrecimientos.
    """
    errores = []
    advertencias = []

    if not porcentajes_contexto:
        return errores, advertencias

    if not porcentajes_texto:
        errores.append(
            f"El texto no contiene porcentajes pero el contexto tiene "
            f"{len(porcentajes_contexto)} valor(es) esperado(s)."
        )
        return errores, advertencias

    for valor_esperado in porcentajes_contexto:
        tolerancia = _tolerancia_para(valor_esperado)
        diferencias = [abs(valor_esperado - v) for v in porcentajes_texto]
        diferencia_minima = min(diferencias)

        if diferencia_minima <= tolerancia:
            continue  # dentro de tolerancia, OK

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


def evaluar_texto(
    texto,
    contexto,
    palabras_prohibidas=None,
    secciones_obligatorias=None,
):
    """
    Evalúa el texto generado por el LLM contra reglas estructurales,
    exactitud numérica y orden de subsectores.

    Acepta listas de palabras_prohibidas y secciones_obligatorias
    como parámetros para soportar múltiples sectores.
    """
    errores = []
    advertencias = []

    palabras_prohibidas = palabras_prohibidas or PALABRAS_PROHIBIDAS_DEFAULT
    secciones_obligatorias = secciones_obligatorias or SECCIONES_OBLIGATORIAS_DEFAULT

    texto_lower = texto.lower()
    tipo = contexto.get("tipo_reporte")

    # 1. Palabras prohibidas
    for palabra in palabras_prohibidas:
        if palabra in texto_lower:
            errores.append(f"Uso no permitido: '{palabra}'")

    # 2. Estructura mínima
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

    # 4. Exactitud numérica
    porcentajes_texto = [
        n for p in extraer_porcentajes(texto)
        if (n := normalizar_porcentaje(p)) is not None
    ]
    porcentajes_contexto = obtener_porcentajes_contexto(contexto)

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
        if idx_1 != -1 and idx_2 != -1 and idx_1 > idx_2:
            advertencias.append(
                f"Orden incorrecto: debería aparecer primero '{nombre_1}'"
            )

    return {
        "valido":               len(errores) == 0,
        "errores":              errores,
        "advertencias":         advertencias,
        "porcentajes_texto":    porcentajes_texto,
        "porcentajes_contexto": porcentajes_contexto,
    }