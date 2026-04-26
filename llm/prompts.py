import json


def construir_prompt(contexto):
    """
    Prompt profesional tipo INEI.
    Controla al modelo para evitar alucinaciones.
    """

    return f"""
Eres un redactor técnico del INEI (Perú).

Tu tarea es redactar un análisis económico EXACTO basado únicamente en los datos proporcionados.

INSTRUCCIONES ESTRICTAS:
- NO inventes información.
- NO agregues causas externas (precios, mercado, etc.).
- NO cambies cifras.
- NO traduzcas nombres de productos.
- NO uses "sector industrial".
- NO uses "subsectora".
- Usa "subsector Hidrocarburos".
- Usa coma decimal (ejemplo: 1,25%).
- Mantén coherencia económica.

FORMATO SEGÚN TIPO DE REPORTE:

Siempre inicia con esta estructura:

EVOLUCIÓN SECTORIAL
Índice de la Producción Minera y de Hidrocarburos
Año base 2007

• Redacta un primer resumen del índice sectorial del periodo.
• Redacta un segundo párrafo de contraste entre minería metálica e hidrocarburos.

Variación interanual del Índice de la Producción Minera y de Hidrocarburos

Redacta 3 párrafos:
1. Resultado global del sector, incluyendo variación e incidencias de los subsectores.
2. Detalle del subsector Hidrocarburos.
3. Detalle del subsector minero metálico.

Si tipo_reporte = "mensual":

Producción Sectorial: MES AÑO
Sector Minería e Hidrocarburos

Redacta:
- párrafo del sector total
- párrafo de minería metálica
- párrafo de hidrocarburos

Si tipo_reporte = "mensual_y_acumulado":

Producción Sectorial: MES AÑO
Sector Minería e Hidrocarburos

Redacta:
- párrafo del sector total
- párrafo de minería metálica
- párrafo de hidrocarburos

Producción Sectorial: Enero-MES AÑO
Sector Minería e Hidrocarburos

Redacta el bloque acumulado enero-MES usando las variaciones acumuladas e incidencias acumuladas si están disponibles.

Si tipo_reporte = "anual_y_mensual":

Producción Sectorial: Año AÑO
Sector Minería e Hidrocarburos

Redacta primero el bloque anual.

Producción Sectorial: MES AÑO
Sector Minería e Hidrocarburos

Redacta:
- párrafo del sector total
- párrafo de minería metálica
- párrafo de hidrocarburos

REGLAS DE FORMATO:
- No uses numeración tipo 1., 2., 3.
- Usa viñetas solo en el bloque inicial de EVOLUCIÓN SECTORIAL.
- Respeta exactamente los títulos indicados.
- No agregues títulos no solicitados.

- Respeta el tipo_reporte indicado en el contexto.
- Si tipo_reporte = "mensual", no generes bloque acumulado.
- Si tipo_reporte = "anual_y_mensual", genera primero el bloque anual y luego el bloque mensual.
- Si tipo_reporte = "mensual_y_acumulado", genera bloque mensual y luego bloque acumulado.

Debes generar tres salidas independientes:

REPORTE_1_EVOLUCION_SECTORIAL
REPORTE_2_PRODUCCION_MENSUAL
REPORTE_3_ACUMULADO_O_ANUAL

Si tipo_reporte = "mensual", el tercer reporte debe indicar: NO APLICA.
Si tipo_reporte = "mensual_y_acumulado", el tercer reporte corresponde al acumulado enero-mes.
Si tipo_reporte = "anual_y_mensual", el tercer reporte corresponde al año completo.

- El orden de los subsectores debe seguir "orden_subsectores" del contexto.
- Primero menciona el subsector con mayor incidencia absoluta en el resultado del sector.
- Luego menciona el otro subsector.

DATOS:
{json.dumps(contexto, ensure_ascii=False, indent=2)}
"""