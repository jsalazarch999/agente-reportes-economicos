import json
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("No se encontró OPENAI_API_KEY")

    return OpenAI(api_key=api_key)


def construir_prompt_causal(contexto_enriquecido):
    contexto_json = json.dumps(
        contexto_enriquecido,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
Eres un analista económico especializado en minería e hidrocarburos del Perú.

Tu tarea es analizar las fuentes externas y generar:

1. Tres párrafos sobre minería metálica:
- resultado del subsector
- resumen de fuentes consultadas
- conclusión causal

2. Tres párrafos sobre hidrocarburos:
- resultado del subsector
- resumen de fuentes consultadas
- conclusión causal

REGLAS:
- Usa únicamente información explícita del contexto y de las fuentes web.
- No uses frases especulativas como "es plausible", "podría", "es posible", "probablemente".
- No menciones inversión, logística, infraestructura, demanda internacional, mantenimiento u otros factores si no aparecen explícitamente en las fuentes.
- Diferencia claramente entre:
  a) lo que muestran los datos del Excel
  b) lo que sustentan las fuentes externas
- Usa porcentajes con coma decimal.
- Entrega exactamente 6 párrafos:
  1. Minería metálica: resultado y productos explicativos según Excel.
  2. Minería metálica: resumen de fuentes consultadas, fuente por fuente.
  3. Minería metálica: conclusión causal; si no hay causa directa, indicarlo claramente.
  4. Hidrocarburos: resultado y productos explicativos según Excel.
  5. Hidrocarburos: resumen de fuentes consultadas, fuente por fuente.
  6. Hidrocarburos: conclusión causal; si no hay causa directa, indicarlo claramente.
- En los párrafos de resumen de fuentes, menciona explícitamente qué reporta cada fuente relevante.
- Usa estructuras como:
  "Según el MINEM..."
  "Por su parte, el BCRP..."
  "Asimismo, Perupetro..."
- No repitas información del Excel como si proviniera de las fuentes.
- Si una fuente solo contiene estadísticas generales o series históricas, indícalo como contexto informativo.
- No uses subtítulos.
- Si las fuentes identifican una causa directa, úsala y menciona la fuente.
- Si las fuentes no identifican una causa directa, no inventes causas.
- En ese caso escribe primero:
"Las fuentes consultadas no permiten identificar una causa específica para este resultado."
- Luego agrega una oración describiendo únicamente lo que sí reportan las fuentes, sin añadir interpretación propia.
- No conviertas ese contexto descriptivo en explicación causal.
- No uses "podría estar relacionado", "puede estar relacionado", "estaría asociado", "plantea desafíos" ni frases similares.
- No generalices el contenido de las fuentes. Resume solo lo que aparece explícitamente en el campo "resumen_para_llm".
- Si una fuente no menciona minería metálica, no la uses para explicar minería metálica.
- Si una fuente no menciona hidrocarburos, no la uses para explicar hidrocarburos.

CONTEXTO:
{contexto_json}
"""

    return prompt


def generar_explicacion_causal(contexto_enriquecido):
    client = get_openai_client()

    prompt = construir_prompt_causal(contexto_enriquecido)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.0
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    from rag.context_enricher import enriquecer_contexto_con_web

    contexto_base = {
        "periodo_texto": "febrero de 2026",
        "sector": {
            "nombre": "Minería e Hidrocarburos"
        },
        "subsector_hidrocarburos": {
            "variacion_interanual": -9.73,
            "productos_negativos": [
                {"nombre": "petróleo crudo"},
                {"nombre": "líquidos de gas natural"}
            ]
        },
        "subsector_mineria_metalica": {
            "variacion_interanual": 0.13,
            "productos_negativos": [
                {"nombre": "molibdeno"},
                {"nombre": "plata"}
            ]
        }
    }

    contexto_enriquecido = enriquecer_contexto_con_web(
        contexto_base
    )

    resultado = generar_explicacion_causal(
        contexto_enriquecido
    )

    print(resultado)