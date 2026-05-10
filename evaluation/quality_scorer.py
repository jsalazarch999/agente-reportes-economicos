from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from evaluation.rule_checker import evaluar_texto


BASE_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = BASE_DIR / "data" / "corpus" / "mineria_hidrocarburos" / "benchmark"

# cargar modelo una sola vez
modelo_embeddings = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

def cargar_benchmark(periodo):
    ruta = BENCHMARK_DIR / f"{periodo}.txt"

    if not ruta.exists():
        raise FileNotFoundError(f"No existe benchmark para el periodo {periodo}: {ruta}")

    return ruta.read_text(encoding="utf-8")


def similitud(a, b):
    emb_a = modelo_embeddings.encode([a])
    emb_b = modelo_embeddings.encode([b])

    score = cosine_similarity(emb_a, emb_b)[0][0]

    return float(score)


def cobertura_productos(texto):
    productos = [
        "cobre", "hierro", "oro", "estaño",
        "zinc", "plomo", "plata", "molibdeno",
        "petróleo", "líquidos de gas natural", "gas natural"
    ]

    texto = texto.lower()
    encontrados = sum(1 for p in productos if p in texto)

    return encontrados / len(productos)


def evaluar_calidad(texto_llm, periodo, contexto):
    try:
        texto_benchmark = cargar_benchmark(periodo)
        score_similitud = similitud(texto_llm, texto_benchmark)
        benchmark_usado = str(BENCHMARK_DIR / f"{periodo}.txt")
    except FileNotFoundError:
        score_similitud = 0
        benchmark_usado = "No disponible"

    eval_reglas = evaluar_texto(texto_llm, contexto)
    score_cobertura = cobertura_productos(texto_llm)

    score = 0

    if eval_reglas["valido"]:
        score += 40

    if score_similitud >= 0.75:
        score += 20
    elif score_similitud >= 0.60:
        score += 10

    if len(eval_reglas["advertencias"]) == 0:
        score += 25
    elif len(eval_reglas["advertencias"]) <= 2:
        score += 5
    else:
        score -= 10

    score += int(score_cobertura * 15)

    return {
        "periodo": periodo,
        "benchmark_usado": benchmark_usado,
        "score_total": max(0, min(score, 100)),
        "similitud": round(score_similitud, 3),
        "cobertura_productos": round(score_cobertura, 3),
        "valido": eval_reglas["valido"],
        "errores": eval_reglas["errores"],
        "advertencias": eval_reglas["advertencias"],
    }