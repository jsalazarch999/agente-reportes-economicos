# =====================================================
# ROLES — usan el parámetro system del LLM, no el prompt
# =====================================================

SYSTEM_REVISION = "Eres un redactor técnico del INEI (Perú), especializado en estadísticas de producción minera e hidrocarburos."
SYSTEM_CAUSAL   = "Eres un analista económico del INEI especializado en coyuntura minera y de hidrocarburos."


# =====================================================
# PROMPTS
# =====================================================

def construir_prompt_revision(texto_base: str) -> str:
    """
    Prompt para mejorar la redacción del texto base determinístico.
    El LLM no debe cambiar ningún dato, cifra ni estructura.
    """
    return f"""Tu tarea es mejorar la redacción del siguiente texto base determinístico.

REGLAS OBLIGATORIAS:
- No agregues causas externas.
- No uses contexto web.
- No menciones precios, inversión, mercado internacional ni eventos externos.
- No cambies cifras, productos ni incidencias.
- No elimines secciones ni resumas.
- Mantén los títulos originales exactamente como están.
- Devuelve únicamente el texto mejorado, sin explicaciones ni comentarios.

TEXTO BASE:
{texto_base}"""


def construir_prompt_causal(
    contexto_local: str = "",
    contexto_web: str = "",
    periodo_texto: str = ""
) -> str:
    """
    Prompt para generar el comentario coyuntural del mes.
    Solo debe referenciar hechos puntuales del periodo analizado.
    """
    referencia_periodo = (
        f"El periodo analizado es: {periodo_texto}.\n" if periodo_texto else ""
    )

    return f"""{referencia_periodo}Tu tarea es redactar SOLO un comentario coyuntural del mes, separado del reporte estadístico.

OBJETIVO:
Explicar hechos puntuales del mes que pudieron afectar la producción.

PROHIBIDO:
- Mencionar porcentajes o variaciones por producto.
- Repetir cifras del Excel o hacer análisis estadístico.
- Usar "creció", "cayó", "aumentó" o "disminuyó" por producto sin ligarlo a un hecho coyuntural.
- Mencionar rankings de metales, producción acumulada o perspectivas.
- Mencionar precios, inversión o mercado internacional.
- Usar subtítulos con "#".

PRIORIZA SOLO HECHOS COYUNTURALES DEL MES:
mantenimientos, paralizaciones, huelgas, accidentes, lluvias,
emergencias, restricciones operativas, interrupciones de transporte, conflictos sociales.

FORMATO DE RESPUESTA:
Minería metálica
[1 párrafo. Si no hay evidencia coyuntural específica, escribe exactamente: "Las fuentes consultadas no permiten identificar una causa coyuntural específica para la minería metálica en el mes analizado."]

Hidrocarburos
[1 párrafo con el hecho coyuntural y sus implicancias operativas, sin repetir porcentajes. Si no hay evidencia, indica lo mismo que arriba adaptado al subsector.]

CONTEXTO LOCAL:
{contexto_local or "No disponible."}

CONTEXTO WEB:
{contexto_web or "No disponible."}"""