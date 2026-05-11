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

load_dotenv()


def _require_env(key: str) -> str:
    """Obtiene una variable de entorno o lanza ValueError si no existe."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Falta {key} en .env")
    return value


def get_client(modelo="qwen") -> dict:
    """
    Retorna el cliente y configuración según el modelo seleccionado.

    Retorna un dict con:
        - tipo: str — identifica el SDK a usar para la invocación
        - client: objeto cliente del SDK correspondiente
        - model: str — ID del modelo a pasar en la llamada
    """

    # 🔹 QWEN (Hugging Face) — actualizado a Qwen3
    if modelo == "qwen":
        client = InferenceClient(
            provider="auto",
            token=_require_env("HF_TOKEN")
        )
        return {
            "tipo": "huggingface",
            "client": client,
            "model": "Qwen/Qwen3-8B"
        }

    # 🔹 LLAMA 3.3 (Groq)
    elif modelo == "llama3":
        client = Groq(api_key=_require_env("GROQ_API_KEY"))
        return {
            "tipo": "groq",
            "client": client,
            "model": "llama-3.3-70b-versatile"
        }

    # 🔹 OPENAI
    elif modelo == "openai":
        if OpenAI is None:
            raise ImportError("OpenAI no está instalado")
        client = OpenAI(api_key=_require_env("OPENAI_API_KEY"))
        return {
            "tipo": "openai",
            "client": client,
            "model": "gpt-4.1-mini"  # o "gpt-5.4-mini" para la versión más reciente
        }

    # 🔹 GEMINI
    elif modelo == "gemini":
        genai.configure(api_key=_require_env("GEMINI_API_KEY"))
        model_id = "gemini-2.5-flash"
        client = genai.GenerativeModel(model_id)
        return {
            "tipo": "gemini",
            "client": client,
            "model": model_id
        }

    # 🔹 ANTHROPIC
    elif modelo == "anthropic":
        client = Anthropic(api_key=_require_env("ANTHROPIC_API_KEY"))
        return {
            "tipo": "anthropic",
            "client": client,
            "model": "claude-sonnet-4-6"
        }

    # 🔹 DEEPSEEK (compatible con SDK de OpenAI)
    elif modelo == "deepseek":
        if OpenAI is None:
            raise ImportError("OpenAI SDK no está instalado para usar DeepSeek")
        client = OpenAI(
            api_key=_require_env("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        return {
            "tipo": "deepseek",  # distinto de "openai" para evitar ambigüedad
            "client": client,
            "model": "deepseek-v4-pro"  # alternativa económica: deepseek-v4-flash
        }

    else:
        raise ValueError(f"Modelo no soportado: {modelo}")