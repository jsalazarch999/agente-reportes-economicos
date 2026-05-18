import logging
from pathlib import Path
from functools import lru_cache

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from evaluation.rule_checker import evaluar_texto
from evaluation.grounding_checker import verificar_grounding_reporte

logger = logging.getLogger(__name__)

# =====================================================
# CONSTANTES
# =====================================================

BASE_DIR      = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = BASE_DIR / "data" / "corpus"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

PRODUCTOS_DEFAULT = [
    "cobre", "hierro", "oro", "estaño",
    "zinc", "plomo", "plata", "molibdeno",
    "petróleo", "líquidos de gas natural", "gas natural"
]

# Pesos del score total (deben sumar 100)
PESOS = {
    "reglas_estructurales": 35,
    "advertencias":         15,
    "exactitud_numerica":   25,
    "grounding_rag":        15,  # nuevo — reemplaza similitud semántica parcialmente
    "similitud_benchmark":  10,  # reducido de 15 a 10
    "cobertura_productos":  10,  # sin cambios
}
# Nota: 35+15+25+15+10+10 = 110 — se normaliza a 100 en _calcular_score


# =====================================================
# MODELO DE EMBEDDINGS
# =====================================================

@lru_cache(maxsize=1)
def _get_modelo():
    """Carga el modelo de embeddings una sola vez."""
    return SentenceTransformer(MODEL_NAME)


# =====================================================
# BENCHMARK
# =====================================================

def _ruta_benchmark(sector, periodo):
    sector_clave = (
        sector.lower()
        .replace(" e ", "_")      # "Minería e Hidrocarburos" → "minería_hidrocarburos"
        .replace(" ", "_")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("á", "a")
        .replace("ú", "u")
    )
    return BASE_DIR / "data" / "corpus" / sector_clave / "benchmark" / f"{periodo}.txt"


def cargar_benchmark(sector, periodo):
    """Carga el texto benchmark histórico para el sector y periodo."""
    ruta = _ruta_benchmark(sector, periodo)
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe benchmark para '{sector}' periodo {periodo}: {ruta}"
        )
    return ruta.read_text(encoding="utf-8")


# =====================================================
# MÉTRICAS INDIVIDUALES
# =====================================================

def _similitud_semantica(texto_a, texto_b):
    """Calcula similitud coseno entre dos textos."""
    modelo    = _get_modelo()
    emb_a, emb_b = modelo.encode([texto_a, texto_b], normalize_embeddings=True)
    return float(cosine_similarity([emb_a], [emb_b])[0][0])


def _cobertura_productos(texto, productos=None):
    """
    Calcula qué fracción de los productos esperados
    aparece en el texto generado.
    """
    productos = productos or PRODUCTOS_DEFAULT
    texto_lower = texto.lower()
    encontrados = sum(1 for p in productos if p in texto_lower)
    return encontrados / len(productos)


# =====================================================
# SCORING
# =====================================================

def _calcular_score(
    errores_reglas,
    advertencias_reglas,
    errores_pct,
    advertencias_pct,
    score_similitud,
    score_cobertura,
    score_grounding,
):
    """
    Calcula el score total sobre 100.

    Distribución de puntos:
      - Reglas estructurales:  35 pts (binario)
      - Advertencias:          15 pts (escalonado)
      - Exactitud numérica:    25 pts (gradual)
      - Grounding RAG:         15 pts (gradual, 0 si RAG no activo)
      - Similitud benchmark:   10 pts (gradual)
      - Cobertura productos:   10 pts (proporcional)
    Total posible: 110 pts → normalizado a 100
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

    # 4. Grounding RAG (15 pts) — nuevo
    # Solo aplica si el RAG estaba activo (score_grounding no es None)
    if score_grounding is not None:
        if score_grounding >= 0.75:
            score += 15
        elif score_grounding >= 0.60:
            score += 10
        elif score_grounding >= 0.40:
            score += 5
        # < 0.40 → posible alucinación → 0 pts
    else:
        # RAG no activo — redistribuir estos 15 pts al resto
        # (simplemente no se restan, el total máximo baja a 95)
        pass

    # 5. Similitud semántica con benchmark (10 pts)
    if score_similitud >= 0.75:
        score += 10
    elif score_similitud >= 0.60:
        score += 6
    elif score_similitud >= 0.45:
        score += 3

    # 6. Cobertura de productos (10 pts)
    score += int(score_cobertura * 10)

    # Normalizar: máximo posible es 110 con RAG, 95 sin RAG
    maximo = 110 if score_grounding is not None else 95
    score_normalizado = round((score / maximo) * 100)

    return max(0, min(score_normalizado, 100))


# =====================================================
# EVALUACIÓN PRINCIPAL
# =====================================================

def evaluar_calidad(
    texto_llm,
    periodo,
    contexto,
    fundamentaciones=None,
    contexto_rag=None,
):
    """
    Evalúa la calidad del reporte generado.

    Parámetros:
        texto_llm:        texto del reporte estadístico generado
        periodo:          YYYYMM del periodo
        contexto:         dict del orquestador (con sector, productos, etc.)
        fundamentaciones: dict {clave: texto} de fundamentaciones (opcional)
        contexto_rag:     dict del contexto RAG enriquecido (opcional)

    Retorna dict con score total, métricas individuales,
    errores, advertencias y diagnóstico de grounding.
    """
    sector = contexto.get("sector", {}).get("nombre", "mineria_hidrocarburos")

    # --- Similitud semántica contra benchmark ---
    try:
        texto_benchmark = cargar_benchmark(sector, periodo)
        score_similitud = _similitud_semantica(texto_llm, texto_benchmark)
        benchmark_usado = str(_ruta_benchmark(sector, periodo))
    except FileNotFoundError:
        score_similitud = 0.0
        benchmark_usado = "No disponible"
        logger.info(f"Sin benchmark para sector='{sector}' periodo={periodo}")

    # --- Reglas estructurales y exactitud numérica ---
    eval_reglas = evaluar_texto(texto_llm, contexto)

    errores_pct    = [
        e for e in eval_reglas["errores"]
        if "%" in e or "porcentaje" in e.lower()
    ]
    errores_reglas = [
        e for e in eval_reglas["errores"]
        if e not in errores_pct
    ]
    advertencias_pct    = [
        a for a in eval_reglas["advertencias"]
        if "%" in a or "porcentaje" in a.lower()
    ]
    advertencias_reglas = [
        a for a in eval_reglas["advertencias"]
        if a not in advertencias_pct
    ]

    # --- Cobertura de productos ---
    productos_contexto = contexto.get("productos")
    score_cobertura    = _cobertura_productos(texto_llm, productos=productos_contexto)

    # --- Grounding RAG (nuevo) ---
    resultado_grounding = None
    score_grounding     = None
    advertencias_grounding = []

    if fundamentaciones and contexto_rag:
        resultado_grounding = verificar_grounding_reporte(
            fundamentaciones=fundamentaciones,
            contexto_rag=contexto_rag,
        )
        score_grounding        = resultado_grounding.get("score_global")
        advertencias_grounding = resultado_grounding.get("advertencias", [])

    # --- Score final ---
    score_total = _calcular_score(
        errores_reglas=errores_reglas,
        advertencias_reglas=advertencias_reglas,
        errores_pct=errores_pct,
        advertencias_pct=advertencias_pct,
        score_similitud=score_similitud,
        score_cobertura=score_cobertura,
        score_grounding=score_grounding,
    )

    return {
        # Identificación
        "periodo":                  periodo,
        "benchmark_usado":          benchmark_usado,

        # Score principal
        "score_total":              score_total,

        # Métricas individuales
        "similitud":                round(score_similitud, 3),
        "cobertura_productos":      round(score_cobertura, 3),
        "score_grounding":          round(score_grounding, 3) if score_grounding else None,

        # Validez estructural
        "valido":                   eval_reglas["valido"],

        # Errores y advertencias separados por tipo
        "errores":                  errores_reglas,
        "advertencias":             advertencias_reglas,
        "errores_porcentajes":      errores_pct,
        "advertencias_porcentajes": advertencias_pct,
        "advertencias_grounding":   advertencias_grounding,

        # Porcentajes para diagnóstico
        "porcentajes_texto":        eval_reglas["porcentajes_texto"],
        "porcentajes_contexto":     eval_reglas["porcentajes_contexto"],

        # Detalle de grounding por fundamentación
        "detalle_grounding":        resultado_grounding,
    }