from pathlib import Path

from agent.orchestrator import procesar_excel, generar_reporte_llm
from tests.test_quality import evaluar_calidad


BASE_DIR = Path(__file__).resolve().parents[1]
ARCHIVO = BASE_DIR / "data" / "sample" / "variaciones_202602.xlsx"


def probar_agente(archivo=ARCHIVO, modelo="qwen"):
    resultado = procesar_excel(archivo)

    print("\n===== PERIODOS DISPONIBLES =====")
    print(resultado["periodos"])

    periodo = resultado["periodos"][-1]

    print("\n===== PERIODO SELECCIONADO =====")
    print(periodo)

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

    print("\n===== TEXTO LLM =====")

    texto_llm = generar_reporte_llm(
        resultado_periodo["contexto"],
        modelo=modelo
    )

    print(texto_llm)

    print("\n===== EVALUACIÓN DE CALIDAD =====")

    evaluacion = evaluar_calidad(
        texto_llm=texto_llm,
        periodo=periodo,
        contexto=resultado_periodo["contexto"]
    )

    print("Modelo:", modelo)
    print("Periodo:", periodo)
    print("Score total:", evaluacion["score_total"])
    print("Similitud:", evaluacion["similitud"])
    print("Cobertura productos:", evaluacion["cobertura_productos"])
    print("¿Válido?:", evaluacion["valido"])
    print("Benchmark usado:", evaluacion["benchmark_usado"])

    if evaluacion["errores"]:
        print("\nErrores:")
        for e in evaluacion["errores"]:
            print("-", e)

    if evaluacion["advertencias"]:
        print("\nAdvertencias:")
        for a in evaluacion["advertencias"]:
            print("-", a)

    return {
        "periodo": periodo,
        "texto_llm": texto_llm,
        "evaluacion": evaluacion,
        "contexto": resultado_periodo["contexto"]
    }


if __name__ == "__main__":
    probar_agente()