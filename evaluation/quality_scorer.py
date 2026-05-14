from pathlib import Path
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from evaluation.rule_checker import evaluar_texto

BASE_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = BASE_DIR / "data" / "corpus" / "mineria_hidrocarburos" / "benchmark"

PRODUCTOS_DEFAULT = [
    "cobre", "hierro", "oro", "estaño",
    "zinc", "plomo", "plata", "molibdeno",
    "petróleo", "líquidos de gas natural", "gas natural"
]


@lru_cache(maxsize=1)
def _get_modelo():
    """Carga el modelo de embeddings una sola vez."""
    return SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )


def cargar_benchmark(periodo):
    """Carga el texto benchmark histórico para el periodo dado."""
    ruta = BENCHMARK_DIR / f"{periodo}.txt"
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe benchmark para el periodo {periodo}: {ruta}"
        )
    return ruta.read_text(encoding="utf-8")


def similitud(a, b):
    """Calcula similitud coseno entre dos textos usando embeddings multilingües."""
    modelo = _get_modelo()
    emb_a, emb_b = modelo.encode([a, b])
    return float(cosine_similarity([emb_a], [emb_b])[0][0])


def cobertura_productos(texto, productos=None):
    """
    Calcula qué fracción de los productos esperados aparece en el texto.
    Si no se pasan productos, usa la lista por defecto de Minería e Hidrocarburos.
    """
    productos = productos or PRODUCTOS_DEFAULT
    texto = texto.lower()
    encontrados = sum(1 for p in productos if p in texto)
    return encontrados / len(productos)


def _calcular_score(
    errores_reglas, advertencias_reglas,
    errores_pct, advertencias_pct,
    score_similitud, score_cobertura
):
    """
    Calcula el score total sobre 100 con los siguientes pesos:
      - Reglas estructurales:   35 pts
      - Advertencias:           15 pts
      - Exactitud numérica:     25 pts
      - Similitud semántica:    15 pts
      - Cobertura productos:    10 pts
    """
    score = 0

    # 1. Reglas estructurales (35 pts) — binario
    if not errores_reglas:
        score += 35

    # 2. Advertencias estructurales (15 pts) — escalonado
    n_adv = len(advertencias_reglas)
    if n_adv == 0:
        score += 15
    elif n_adv <= 2:
        score += 5

    # 3. Exactitud numérica (25 pts) — el más crítico
    n_err_pct = len(errores_pct)
    n_adv_pct = len(advertencias_pct)
    if n_err_pct == 0 and n_adv_pct == 0:
        score += 25
    elif n_err_pct == 0:
        score += max(0, 25 - n_adv_pct * 5)
    else:
        score += max(0, 10 - n_err_pct * 5)

    # 4. Similitud semántica (15 pts)
    if score_similitud >= 0.75:
        score += 15
    elif score_similitud >= 0.60:
        score += 8

    # 5. Cobertura de productos (10 pts)
    score += int(score_cobertura * 10)

    return max(0, min(score, 100))


def evaluar_calidad(texto_llm, periodo, contexto):
    """
    Evalúa la calidad del texto generado por el LLM.
    Retorna un dict con score total, métricas individuales,
    errores, advertencias y porcentajes comparados.
    """
    # --- Similitud semántica contra benchmark histórico ---
    try:
        texto_benchmark = cargar_benchmark(periodo)
        score_similitud = similitud(texto_llm, texto_benchmark)
        benchmark_usado = str(BENCHMARK_DIR / f"{periodo}.txt")
    except FileNotFoundError:
        score_similitud = 0.0
        benchmark_usado = "No disponible"

    # --- Reglas y porcentajes ---
    eval_reglas = evaluar_texto(texto_llm, contexto)

    # Separar errores/advertencias de porcentajes del resto
    errores_pct    = [e for e in eval_reglas["errores"]     if "%" in e or "porcentaje" in e.lower()]
    errores_reglas = [e for e in eval_reglas["errores"]     if e not in errores_pct]

    advertencias_pct    = [a for a in eval_reglas["advertencias"] if "%" in a or "porcentaje" in a.lower()]
    advertencias_reglas = [a for a in eval_reglas["advertencias"] if a not in advertencias_pct]

    # --- Cobertura de productos ---
    productos_contexto = contexto.get("productos", None)
    score_cobertura = cobertura_productos(texto_llm, productos=productos_contexto)

    # --- Score final ---
    score_total = _calcular_score(
        errores_reglas, advertencias_reglas,
        errores_pct, advertencias_pct,
        score_similitud, score_cobertura
    )

    return {
        "periodo":               periodo,
        "benchmark_usado":       benchmark_usado,
        "score_total":           score_total,
        "similitud":             round(score_similitud, 3),
        "cobertura_productos":   round(score_cobertura, 3),
        "valido":                eval_reglas["valido"],
        "errores":               errores_reglas,
        "advertencias":          advertencias_reglas,
        "errores_porcentajes":   errores_pct,
        "advertencias_porcentajes": advertencias_pct,
        "porcentajes_texto":     eval_reglas["porcentajes_texto"],
        "porcentajes_contexto":  eval_reglas["porcentajes_contexto"],
    }