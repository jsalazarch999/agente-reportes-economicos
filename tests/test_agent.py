from agent.orchestrator import procesar_excel, generar_reporte_llm


archivo = "data/sample/variaciones_202602.xlsx"

# 1. Leer Excel y obtener periodos
resultado = procesar_excel(archivo)

print("\n===== PERIODOS DISPONIBLES =====")
print(resultado["periodos"])

# 2. Usar último periodo disponible
periodo = resultado["periodos"][-1]

print("\n===== PERIODO SELECCIONADO =====")
print(periodo)

# 3. Procesar periodo
resultado_periodo = procesar_excel(archivo, periodo=periodo)

print("\n===== TEXTO BASE =====")
print("\n1. SECTOR MINERÍA E HIDROCARBUROS")
print(resultado_periodo["texto_base"]["sector"])

print("\n2. MINERÍA METÁLICA")
print(resultado_periodo["texto_base"]["mineria_metalica"])

print("\n3. HIDROCARBUROS")
print(resultado_periodo["texto_base"]["hidrocarburos"])

print("\n===== CONTEXTO =====")
print(resultado_periodo["contexto"])

# 4. Generar reporte con LLM
print("\n===== TEXTO LLM =====")

texto_llm = generar_reporte_llm(
    resultado_periodo["contexto"],
    modelo="qwen"
)

print(texto_llm)