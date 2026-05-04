import os
from dotenv import load_dotenv

load_dotenv()

# =========================
# MODELO ACTIVO
# =========================

ACTIVE_MODEL = "gemini"
# opciones: qwen | llama3 | openai | gemini


# =========================
# CONFIGURACIÓN DE MODELOS
# =========================

MODELS = {
    "qwen": {
        "provider": "huggingface",
        "model_name": "Qwen/Qwen2.5-7B-Instruct",
    },

    "llama3": {
        "provider": "huggingface",
        "model_name": "meta-llama/Meta-Llama-3-8B-Instruct",
    },

    "openai": {
        "provider": "openai",
        "model_name": "gpt-4.1-mini",
    },

    "gemini": {
        "provider": "google",
        "model_name": "gemini-1.5-flash",
    }
}


# =========================
# TOKENS
# =========================

HF_TOKEN = os.getenv("HF_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# =========================
# PARÁMETROS LLM
# =========================

MAX_TOKENS = 700
TEMPERATURE = 0.2


# =========================
# RUTAS
# =========================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")


# =========================
# VALIDACIÓN
# =========================

STRICT_MODE = True