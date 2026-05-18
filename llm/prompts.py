# =====================================================
# ROLES
# =====================================================

SYSTEM_ESTADISTICO = (
    "Eres un redactor técnico especializado en estadísticas de producción "
    "sectorial. Tu tarea es generar texto preciso basado exclusivamente en "
    "los datos numéricos proporcionados, sin agregar interpretaciones causales."
)

SYSTEM_FUNDAMENTACION = (
    "Eres un analista económico especializado en coyuntura sectorial. "
    "Tu tarea es redactar fundamentaciones basadas exclusivamente en los "
    "hechos documentados en el contexto provisto, sin inventar causas."
)

# Alias para compatibilidad con generator.py existente
SYSTEM_REVISION = SYSTEM_ESTADISTICO
SYSTEM_CAUSAL   = SYSTEM_FUNDAMENTACION


# =====================================================
# PROMPT 1 — PÁRRAFO ESTADÍSTICO
# =====================================================

def construir_prompt_estadistico(texto_base: str, contexto: dict) -> str:
    """
    Prompt para generar el párrafo estadístico del reporte.
    Implementa el patrón SymGen (MIT 2024): el LLM genera
    libremente pero debe referenciar cada cifra al campo
    del JSON de origen.

    El texto determinístico actúa como árbitro post-generación,
    no como guía — el LLM no lo ve directamente.
    """
    sector        = contexto.get("sector", {}).get("nombre", "el sector")
    periodo_texto = contexto.get("periodo_texto", "")
    tipo_reporte  = contexto.get("tipo_reporte", "mensual")

    # Serializar solo los datos numéricos relevantes para el LLM
    import json
    datos_json = json.dumps({
        "periodo":    periodo_texto,
        "sector":     contexto.get("sector", {}),
        "subsector_mineria_metalica": contexto.get("subsector_mineria_metalica", {}),
        "subsector_hidrocarburos":    contexto.get("subsector_hidrocarburos", {}),
    }, ensure_ascii=False, indent=2)

    seccion_acumulado = ""
    if tipo_reporte in ("mensual_y_acumulado", "anual_y_mensual"):
        seccion_acumulado = """
- ACUMULADO: párrafo con variaciones acumuladas del periodo enero–{mes}.
""".format(mes=periodo_texto.split(" de ")[0] if " de " in periodo_texto else "")

    return f"""Genera el reporte estadístico de producción para {sector} en {periodo_texto}.

DATOS DE ORIGEN (JSON):
{datos_json}

REGLAS OBLIGATORIAS:
- Usa ÚNICAMENTE los valores numéricos del JSON anterior.
- Cada cifra que menciones debe corresponder exactamente a un campo del JSON.
- No inventes ni redondees valores fuera de los provistos.
- No agregues causas, explicaciones externas ni contexto coyuntural.
- No menciones precios internacionales ni eventos externos.
- Mantén terminología técnica precisa: "variación interanual", "incidencia", "puntos porcentuales".
- No uses subtítulos con "#".

ESTRUCTURA DEL REPORTE (respeta este orden exacto):

EVOLUCIÓN SECTORIAL
- Párrafo con variación interanual del sector y comportamiento de subsectores.
- Párrafo con incidencias por subsector en puntos porcentuales.

MINERÍA METÁLICA
- Párrafo con variación y productos con mayor incidencia positiva y negativa.
{seccion_acumulado}
HIDROCARBUROS
- Párrafo con variación e incidencia del subsector.

Devuelve únicamente el texto del reporte, sin explicaciones ni comentarios previos."""


# =====================================================
# PROMPT 2 — FUNDAMENTACIÓN POR SUBSECTOR
# =====================================================

def construir_prompt_fundamentacion_subsector(
    subsector: str,
    periodo_texto: str,
    variacion: float,
    contexto_rag: str,
) -> str:
    """
    Prompt para generar el párrafo de fundamentación coyuntural
    de un subsector específico.

    Un prompt por subsector — más específico que uno global,
    como recomienda la literatura para dominios acotados.
    """
    direccion = "crecimiento" if variacion > 0 else "decrecimiento"
    subsector_texto = subsector.replace("_", " ").title()

    return f"""Redacta un párrafo de fundamentación coyuntural para el subsector {subsector_texto}.

CONTEXTO DEL PERIODO:
- Periodo analizado: {periodo_texto}
- El subsector registró un {direccion} en su producción.

CONTEXTO DOCUMENTADO:
{contexto_rag or "No se encontró contexto coyuntural específico para este subsector."}

REGLAS OBLIGATORIAS:
- Usa ÚNICAMENTE hechos presentes en el contexto documentado anterior.
- No menciones porcentajes ni variaciones numéricas.
- No repitas datos estadísticos del reporte.
- Solo incluye hechos coyunturales: mantenimientos, paralizaciones, huelgas,
  lluvias, emergencias, restricciones operativas, conflictos sociales.
- No menciones precios internacionales ni perspectivas futuras.
- PROHIBIDO inventar frases genéricas como "condiciones operativas normales",
  "sin reportes de incidentes", "contexto favorable" o similares.
- Si el contexto no tiene evidencia suficiente, escribe EXACTAMENTE esto
  sin modificarlo:
  "Las fuentes consultadas no permiten identificar una causa coyuntural
  específica para {subsector_texto} en {periodo_texto}."
- Redacta en tercera persona, tono técnico, un solo párrafo.
- No uses subtítulos ni viñetas.

Devuelve únicamente el párrafo, sin explicaciones previas."""


# =====================================================
# PROMPT 3 — FUNDAMENTACIÓN POR PRODUCTO
# =====================================================

def construir_prompt_fundamentacion_producto(
    producto: str,
    subsector: str,
    periodo_texto: str,
    variacion: float,
    incidencia: float,
    contexto_rag: str,
    empresas: list = None,
) -> str:
    """
    Prompt para generar el párrafo de fundamentación coyuntural
    de un producto específico de alta incidencia.

    Se llama solo para productos que superan UMBRAL_ALTA_INCIDENCIA
    definido en context_builder.py.
    """
    direccion   = "mayor" if variacion > 0 else "menor"
    tipo_inc    = "positiva" if incidencia > 0 else "negativa"
    subsector_t = subsector.replace("_", " ").title()

    # Mencionar empresas si están disponibles
    bloque_empresas = ""
    if empresas:
        lista_emp = ", ".join(empresas)
        bloque_empresas = f"\nEmpresas productoras principales: {lista_emp}."

    return f"""Redacta un párrafo explicando los factores coyunturales detrás del comportamiento
de la producción de {producto} en {periodo_texto}.

CONTEXTO DEL PERIODO:
- Subsector: {subsector_t}
- Producto: {producto}
- El producto registró {direccion} producción con incidencia {tipo_inc}.{bloque_empresas}

CONTEXTO DOCUMENTADO:
{contexto_rag or f"No se encontró contexto coyuntural específico para {producto}."}

REGLAS OBLIGATORIAS:
- Usa ÚNICAMENTE hechos del contexto documentado.
- No menciones porcentajes, variaciones numéricas ni incidencias.
- Solo hechos operativos concretos: qué ocurrió, dónde, cuándo en el mes.
- Si hay empresas listadas, puedes mencionarlas si el contexto las referencia.
- PROHIBIDO mencionar precios internacionales, elecciones, incertidumbre
  política o confianza de inversionistas.
- PROHIBIDO especular sobre causas no documentadas en el contexto.
- PROHIBIDO inventar frases genéricas como "niveles sostenidos", 
  "contexto favorable" o "recuperación operativa" sin respaldo documental.
- Si el contexto no tiene evidencia específica del producto en Perú,
  escribe EXACTAMENTE esto sin modificarlo:
  "Las fuentes consultadas no permiten identificar una causa coyuntural
  específica para la producción de {producto} en {periodo_texto}."
  No intentes buscar causas alternativas bajo ninguna circunstancia.
- Tono técnico, tercera persona, un solo párrafo sin viñetas.

Devuelve únicamente el párrafo, sin explicaciones previas."""


# =====================================================
# PROMPT 4 — UNIFICACIÓN DEL REPORTE
# =====================================================

def construir_prompt_unificacion(
    texto_estadistico: str,
    fundamentaciones: dict,
    periodo_texto: str,
) -> str:
    """
    Prompt para unificar el texto estadístico con los párrafos
    de fundamentación en un reporte cohesivo e intercalado.
    """
    bloques_fund = ""
    for clave, texto in fundamentaciones.items():
        if texto and texto.strip():
            nombre = clave.replace("__", " — ").replace("_", " ").title()
            bloques_fund += f"\n[FUNDAMENTACIÓN {nombre.upper()}]\n{texto}\n"

    if not bloques_fund:
        bloques_fund = "No se generaron fundamentaciones coyunturales."

    return f"""Tienes un reporte estadístico y párrafos de fundamentación coyuntural.
Tu tarea es integrarlos en un reporte unificado y cohesivo.

PERIODO: {periodo_texto}

REPORTE ESTADÍSTICO:
{texto_estadistico}

FUNDAMENTACIONES COYUNTURALES:
{bloques_fund}

REGLAS DE INTEGRACIÓN:
- Intercala cada fundamentación inmediatamente después de la sección
  estadística a la que corresponde.
- Mantén todos los datos numéricos exactamente como están en el
  reporte estadístico — no los modifiques.
- Conecta el texto estadístico con la fundamentación usando frases
  de transición naturales (ej. "Este comportamiento estuvo asociado a...",
  "En el contexto operativo del mes,...").
- Si una fundamentación dice que no hay evidencia coyuntural, omítela
  del reporte final — no incluyas el mensaje de "no se encontró".
- Mantén los títulos de sección originales (EVOLUCIÓN SECTORIAL,
  MINERÍA METÁLICA, HIDROCARBUROS).
- Tono técnico uniforme, sin subtítulos con "#".
- No agregues introducción ni conclusión.

REGLAS ANTI-REPETICIÓN (críticas):
- Si varios productos del mismo subsector comparten la misma causa
  coyuntural (ej. todos mencionan la misma explosión, paralización
  o emergencia), consolídala en UN SOLO párrafo al nivel del subsector.
  No la repitas para cada producto.
- Si una causa ya fue mencionada en la fundamentación del subsector,
  NO la repitas en la fundamentación de productos individuales.
- Usa frases como "que también afectó la producción de X e Y"
  para mencionar productos adicionales sin repetir la causa completa.
- Elimina cualquier frase genérica que no venga del texto estadístico
  ni de las fundamentaciones (ej. "condiciones operativas normales",
  "eventos específicos del mes", "sin reportes de incidentes").

Devuelve únicamente el reporte integrado."""


# =====================================================
# PROMPT 5 — REVISIÓN FINAL (compatibilidad)
# =====================================================

def construir_prompt_revision(texto_base: str) -> str:
    """
    Prompt de revisión de estilo del texto base determinístico.
    Mantenido por compatibilidad con el flujo anterior.
    """
    return f"""Mejora la redacción del siguiente texto estadístico.

REGLAS OBLIGATORIAS:
- No cambies cifras, productos ni incidencias.
- No agregues causas externas ni contexto coyuntural.
- No elimines secciones ni resumas.
- Mantén los títulos originales exactamente como están.
- PROHIBIDO agregar frases genéricas como "condiciones operativas normales",
  "sin reportes de incidentes", "contexto favorable" o similares.
- Devuelve únicamente el texto mejorado, sin comentarios.

TEXTO BASE:
{texto_base}"""


def construir_prompt_causal(
    contexto_local: str = "",
    contexto_web: str = "",
    periodo_texto: str = "",
) -> str:
    """
    Prompt causal del flujo anterior.
    Mantenido por compatibilidad — en el nuevo flujo se usan
    construir_prompt_fundamentacion_subsector y
    construir_prompt_fundamentacion_producto.
    """
    referencia_periodo = (
        f"El periodo analizado es: {periodo_texto}.\n"
        if periodo_texto else ""
    )

    return f"""{referencia_periodo}Redacta un comentario coyuntural del mes basado exclusivamente
en el contexto provisto.

PROHIBIDO:
- Mencionar porcentajes o variaciones numéricas.
- Repetir datos estadísticos.
- Mencionar precios o mercado internacional.
- Usar subtítulos con "#".

PRIORIZA: mantenimientos, paralizaciones, huelgas, accidentes,
lluvias, emergencias, conflictos sociales.

CONTEXTO LOCAL:
{contexto_local or "No disponible."}

CONTEXTO WEB:
{contexto_web or "No disponible."}"""