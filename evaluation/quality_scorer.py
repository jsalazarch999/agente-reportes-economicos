from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from evaluation.rule_checker import evaluar_texto

BASE_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = BASE_DIR / "data" / "corpus" / "mineria_hidrocarburos" / "benchmark"

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
    return float(cosine_similarity(emb_a, emb_b)[0][0])


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

    # --- Similitud semántica (benchmark) ---
    try:
        texto_benchmark = cargar_benchmark(periodo)
        score_similitud = similitud(texto_llm, texto_benchmark)
        benchmark_usado = str(BENCHMARK_DIR / f"{periodo}.txt")
    except FileNotFoundError:
        score_similitud = 0
        benchmark_usado = "No disponible"

    # --- Reglas, advertencias y porcentajes ---
    eval_reglas = evaluar_texto(texto_llm, contexto)
    score_cobertura = cobertura_productos(texto_llm)

    # Separar errores de porcentajes del resto para scoring granular
    errores_pct = [e for e in eval_reglas["errores"] if "%" in e or "porcentaje" in e.lower()]
    errores_reglas = [e for e in eval_reglas["errores"] if e not in errores_pct]

    advertencias_pct = [a for a in eval_reglas["advertencias"] if "%" in a or "porcentaje" in a.lower()]
    advertencias_reglas = [a for a in eval_reglas["advertencias"] if a not in advertencias_pct]

    n_errores_pct = len(errores_pct)
    n_advertencias_pct = len(advertencias_pct)

    # =====================
    # SCORING
    # =====================
    score = 0

    # 1. Reglas estructurales (35 pts)
    #    Binario: sin errores de regla → 35, con errores → 0
    if len(errores_reglas) == 0:
        score += 35

    # 2. Advertencias estructurales (15 pts)
    #    Escala: 0 advertencias = 15, 1-2 = 5, 3+ = 0
    if len(advertencias_reglas) == 0:
        score += 15
    elif len(advertencias_reglas) <= 2:
        score += 5

    # 3. Porcentajes — exactitud numérica (25 pts)
    #    Es el bloque más importante: detecta alucinaciones de cifras
    if n_errores_pct == 0 and n_advertencias_pct == 0:
        score += 25                          # todos los números cuadran
    elif n_errores_pct == 0:
        # solo hay redondeos leves, penaliza proporcionalmente
        score += max(0, 25 - n_advertencias_pct * 5)
    else:
        # hay alucinaciones graves, penaliza fuerte
        score += max(0, 10 - n_errores_pct * 5)

    # 4. Similitud semántica (15 pts)
    if score_similitud >= 0.75:
        score += 15
    elif score_similitud >= 0.60:
        score += 8

    # 5. Cobertura de productos (10 pts)
    score += int(score_cobertura * 10)

    return {
        "periodo": periodo,
        "benchmark_usado": benchmark_usado,
        "score_total": max(0, min(score, 100)),
        "similitud": round(score_similitud, 3),
        "cobertura_productos": round(score_cobertura, 3),
        "valido": eval_reglas["valido"],
        "errores": eval_reglas["errores"],
        "advertencias": eval_reglas["advertencias"],
        # nuevos campos para diagnóstico
        "errores_porcentajes": errores_pct,
        "advertencias_porcentajes": advertencias_pct,
        "porcentajes_texto": eval_reglas["porcentajes_texto"],
        "porcentajes_contexto": eval_reglas["porcentajes_contexto"],
    }