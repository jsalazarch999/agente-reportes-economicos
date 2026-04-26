from groq import Groq

import os
from dotenv import load_dotenv

from huggingface_hub import InferenceClient

# Opcional (solo si usas OpenAI)
try:
    from openai import OpenAI
except:
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
    

    else:
        raise ValueError(f"Modelo no soportado: {modelo}")