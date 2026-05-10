import re

PALABRAS_PROHIBIDAS = [
    "sector industrial",
    "subsectora",
    "molybdeno",
    "precios",
    "mercado internacional",
    "tercer trimestre",
]

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

def evaluar_texto(texto, contexto):
    errores = []
    advertencias = []

    texto_lower = texto.lower()
    tipo = contexto.get("tipo_reporte")

    # 1. Palabras prohibidas
    for palabra in PALABRAS_PROHIBIDAS:
        if palabra in texto_lower:
            errores.append(f"Uso no permitido: '{palabra}'")

    # 2. Validar estructura mínima
    secciones_obligatorias = [
        "EVOLUCIÓN SECTORIAL",
        "ÍNDICE DE LA PRODUCCIÓN MINERA Y DE HIDROCARBUROS",
        "VARIACIÓN INTERANUAL",
        "PRODUCCIÓN SECTORIAL",
    ]

    for seccion in secciones_obligatorias:
        if seccion.lower() not in texto_lower:
            advertencias.append(f"No se encontró la sección: {seccion}")

    # 3. Validar estructura según tipo de reporte
    if tipo == "mensual" and "enero-" in texto_lower:
        errores.append("No debe generar acumulado para enero.")

    if tipo == "anual_y_mensual" and "año" not in texto_lower:
        advertencias.append("El reporte de diciembre debería incluir bloque anual.")

    if tipo == "mensual_y_acumulado" and "enero" not in texto_lower:
        advertencias.append("El reporte debería incluir bloque acumulado enero-periodo.")

    # 4. Extraer porcentajes solo para diagnóstico
    porcentajes_texto = [
        normalizar_porcentaje(p) for p in extraer_porcentajes(texto)
    ]
    porcentajes_texto = [p for p in porcentajes_texto if p is not None]

    porcentajes_contexto = obtener_porcentajes_contexto(contexto)

    # 5. Validar orden de subsectores según incidencia
    orden = contexto.get("orden_subsectores", [])

    if len(orden) == 2:
        nombre_1 = orden[0].replace("_", " ")
        nombre_2 = orden[1].replace("_", " ")

        idx_1 = texto_lower.find(nombre_1)
        idx_2 = texto_lower.find(nombre_2)

        # Solo validar si ambos aparecen en el texto
        if idx_1 != -1 and idx_2 != -1:
            if idx_1 > idx_2:
                advertencias.append(
                    f"Orden incorrecto de subsectores: debería aparecer primero '{nombre_1}'"
                )
                
    return {
        "valido": len(errores) == 0,
        "errores": errores,
        "advertencias": advertencias,
        "porcentajes_texto": porcentajes_texto,
        "porcentajes_contexto": porcentajes_contexto,
    }