from difflib import SequenceMatcher
from llm.evaluator import evaluar_texto


def similitud(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def cobertura_productos(texto):
    productos = [
        "cobre", "hierro", "oro", "estaño",
        "zinc", "plomo", "plata", "molibdeno",
        "petróleo", "líquidos de gas natural", "gas natural"
    ]
    texto = texto.lower()
    encontrados = sum(1 for p in productos if p in texto)
    return encontrados / len(productos)


def evaluar_calidad(texto_llm, texto_benchmark, contexto):
    eval_reglas = evaluar_texto(texto_llm, contexto)

    score_similitud = similitud(texto_llm, texto_benchmark)
    score_cobertura = cobertura_productos(texto_llm)

    score = 0

    # 1. Reglas duras
    if eval_reglas["valido"]:
        score += 40

    # 2. Similitud textual
    if score_similitud >= 0.30:
        score += 20
    elif score_similitud >= 0.15:
        score += 10

    # 3. Advertencias
    if len(eval_reglas["advertencias"]) == 0:
        score += 25
    elif len(eval_reglas["advertencias"]) <= 2:
        score += 15
    else:
        score -= 10

    # 4. Cobertura de productos
    score += int(score_cobertura * 15)

    return {
        "score_total": max(0, min(score, 100)),
        "similitud": round(score_similitud, 3),
        "cobertura_productos": round(score_cobertura, 3),
        "valido": eval_reglas["valido"],
        "errores": eval_reglas["errores"],
        "advertencias": eval_reglas["advertencias"],
    }