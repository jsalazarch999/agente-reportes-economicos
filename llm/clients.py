from anthropic import Anthropic
from groq import Groq
import google.generativeai as genai

import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# =====================================================
# REGISTRO DE MODELOS
# =====================================================

def _build_qwen():
    client = InferenceClient(
        provider="auto",
        token=_require_env("HF_TOKEN")
    )
    return {"tipo": "huggingface", "client": client, "model": "Qwen/Qwen3-8B"}


def _build_llama3():
    client = Groq(api_key=_require_env("GROQ_API_KEY"))
    return {"tipo": "groq", "client": client, "model": "llama-3.3-70b-versatile"}


def _build_openai():
    if OpenAI is None:
        raise ImportError("OpenAI no está instalado")
    client = OpenAI(api_key=_require_env("OPENAI_API_KEY"))
    return {"tipo": "openai", "client": client, "model": "gpt-4.1-mini"}


def _build_gemini():
    genai.configure(api_key=_require_env("GEMINI_API_KEY"))
    model_id = "gemini-2.5-flash"
    client = genai.GenerativeModel(model_id)
    return {"tipo": "gemini", "client": client, "model": model_id}


def _build_anthropic():
    client = Anthropic(api_key=_require_env("ANTHROPIC_API_KEY"))
    return {"tipo": "anthropic", "client": client, "model": "claude-sonnet-4-6"}


def _build_deepseek():
    if OpenAI is None:
        raise ImportError("OpenAI SDK no está instalado para usar DeepSeek")
    client = OpenAI(
        api_key=_require_env("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )
    return {"tipo": "deepseek", "client": client, "model": "deepseek-v4-flash"}


_REGISTRY = {
    "qwen":      _build_qwen,
    "llama3":    _build_llama3,
    "openai":    _build_openai,
    "gemini":    _build_gemini,
    "anthropic": _build_anthropic,
    "deepseek":  _build_deepseek,
}

# =====================================================
# HELPERS
# =====================================================

def _require_env(key: str) -> str:
    """Obtiene una variable de entorno o lanza ValueError si no existe."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Falta {key} en .env")
    return value


def modelos_disponibles() -> list[str]:
    """Retorna la lista de modelos registrados."""
    return list(_REGISTRY.keys())


# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================

def get_client(modelo: str = "qwen") -> dict:
    """
    Retorna el cliente y configuración según el modelo seleccionado.

    Retorna un dict con:
        - tipo:   str — identifica el SDK a usar para la invocación
        - client: objeto cliente del SDK correspondiente
        - model:  str — ID del modelo a pasar en la llamada

    Modelos disponibles: qwen, llama3, openai, gemini, anthropic, deepseek
    """
    builder = _REGISTRY.get(modelo)

    if builder is None:
        disponibles = ", ".join(_REGISTRY.keys())
        raise ValueError(
            f"Modelo no soportado: '{modelo}'. "
            f"Disponibles: {disponibles}"
        )

    return builder()