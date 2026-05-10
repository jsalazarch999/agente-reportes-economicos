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


def get_client(modelo="qwen"):
    """
    Retorna el cliente y configuración según el modelo seleccionado.
    """

    # 🔹 QWEN (Hugging Face)
    if modelo == "qwen":
        client = InferenceClient(
            provider="auto",
            token=os.getenv("HF_TOKEN")
        )

        return {
            "tipo": "huggingface",
            "client": client,
            "model": "Qwen/Qwen2.5-7B-Instruct"
        }

    # 🔹 LLAMA 3     
    elif modelo == "llama3":

        client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

        return {
            "tipo": "groq",
            "client": client,
            "model": "llama-3.3-70b-versatile"
        }

    # 🔹 OPENAI (opcional)
    elif modelo == "openai":

        if OpenAI is None:
            raise ImportError("OpenAI no está instalado")

        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

        return {
            "tipo": "openai",
            "client": client,
            "model": "gpt-4.1-mini"
        }
    
    # 🔹 GEMINI
    elif modelo == "gemini":

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("Falta GEMINI_API_KEY en .env")

        genai.configure(api_key=api_key)

        client = genai.GenerativeModel("gemini-2.5-flash")

        return {
            "tipo": "gemini",
            "client": client,
            "model": "gemini-2.5-flash"
        }
    
    elif modelo == "anthropic":

        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError("Falta ANTHROPIC_API_KEY en .env")

        client = Anthropic(
            api_key=api_key
        )

        return {
            "tipo": "anthropic",
            "client": client,
            "model": "claude-sonnet-4-6"
        }
    
    elif modelo == "deepseek":

        if OpenAI is None:
            raise ImportError("OpenAI SDK no está instalado para usar DeepSeek")

        api_key = os.getenv("DEEPSEEK_API_KEY")

        if not api_key:
            raise ValueError("Falta DEEPSEEK_API_KEY en .env")

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        return {
            "tipo": "openai",
            "client": client,
            #"model": "deepseek-v4-flash"
            "model": "deepseek-v4-pro"
        }
    
    else:
        raise ValueError(f"Modelo no soportado: {modelo}")