from llm.generator import generar_texto
from tests.test_quality import evaluar_calidad

# 🔹 Contexto mínimo de prueba (puedes ajustar)
contexto = {
    "periodo": "202602",
    "periodo_texto": "febrero de 2026",
    "sector": {
        "nombre": "Minería e Hidrocarburos",
        "variacion_interanual": -1.11
    },
    "subsector_mineria_metalica": {
        "variacion_interanual": 0.13,
        "productos_positivos": [
            {"nombre": "Cobre", "variacion_interanual": 2.57, "incidencia_interanual": 1.26},
            {"nombre": "Hierro", "variacion_interanual": 1.48, "incidencia_interanual": 0.05}
        ],
        "productos_negativos": [
            {"nombre": "Zinc", "variacion_interanual": -1.06, "incidencia_interanual": -0.10}
        ],
        "incidencia_positiva": 1.31,
        "incidencia_negativa": 0.10
    },
    "subsector_hidrocarburos": {
        "variacion_interanual": -9.73,
        "incidencia_interanual": -1.22,
        "productos_negativos": [
            {"nombre": "Petróleo crudo", "variacion_interanual": -24.32, "incidencia_interanual": -0.87}
        ],
        "productos_positivos": []
    }
}


# 🔹 Modelos a probar
modelos = ["qwen"]  # puedes agregar: "llama3", "openai"


for modelo in modelos:
    print("\n" + "=" * 50)
    print(f"MODELO: {modelo}")
    print("=" * 50)

    try:
        texto = generar_texto(contexto, modelo=modelo)

        print("\n--- TEXTO GENERADO ---\n")
        print(texto)

        evaluacion = evaluar_calidad(
            texto_llm=texto,
            periodo=contexto["periodo"],
            contexto=contexto
        )

        print("\n--- EVALUACIÓN DE CALIDAD ---\n")
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

    except Exception as e:
        print(f"\n❌ Error con modelo {modelo}: {e}")