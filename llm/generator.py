from llm.clients import get_client
from llm.prompts import (
    construir_prompt_revision,
    construir_prompt_causal,
    SYSTEM_REVISION,
    SYSTEM_CAUSAL,
)

MAX_TOKENS = 2000
MAX_TOKENS_CAUSAL = 1200
TEMPERATURE = 0.2

# Tipos que usan la interfaz estándar OpenAI-compatible
_TIPOS_OPENAI_COMPATIBLE = {"openai", "groq", "deepseek", "huggingface"}


def _llamar_openai_compatible(client, model_name, prompt, temperature, max_tokens, system, extra_body=None):
    """Llamada estándar para proveedores compatibles con la API de OpenAI."""
    kwargs = dict(
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if extra_body:
        kwargs["extra_body"] = extra_body

    response = client.chat.completions.create(**kwargs)
    contenido = response.choices[0].message.content

    if not contenido or not contenido.strip():
        raise ValueError("El modelo devolvió una respuesta vacía.")

    return contenido


def generar_con_prompt(
    prompt,
    modelo="qwen",
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
    system=SYSTEM_REVISION,
):
    """
    Envía un prompt al LLM indicado y retorna el texto generado.
    Soporta: huggingface, openai, groq, deepseek, gemini, anthropic.
    """
    client_info = get_client(modelo)
    tipo       = client_info["tipo"]
    client     = client_info["client"]
    model_name = client_info["model"]

    if tipo == "huggingface" or tipo in {"openai", "groq"}:
        return _llamar_openai_compatible(client, model_name, prompt, temperature, max_tokens, system)

    elif tipo == "deepseek":
        return _llamar_openai_compatible(
            client, model_name, prompt, temperature, max_tokens, system,
            extra_body={"thinking": {"type": "disabled"}}
        )

    elif tipo == "gemini":
        response = client.generate_content(
            f"{system}\n\n{prompt}",
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return response.text

    elif tipo == "anthropic":
        response = client.messages.create(
            model=model_name,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    else:
        raise ValueError(f"Tipo de modelo no soportado: '{tipo}'")


def generar_texto(contexto, modelo="qwen"):
    """
    Mejora el texto base determinístico usando el LLM indicado.
    Requiere que el contexto contenga 'texto_base'.
    """
    if not isinstance(contexto, dict) or "texto_base" not in contexto:
        raise ValueError(
            "Falta 'texto_base' en el contexto. "
            "El LLM debe revisar un texto base determinístico."
        )

    prompt = construir_prompt_revision(texto_base=contexto["texto_base"])
    return generar_con_prompt(prompt=prompt, modelo=modelo, system=SYSTEM_REVISION)


def generar_comentario_causal(contexto, modelo="qwen"):
    """
    Genera el comentario causal con contexto RAG (local + web).
    Si no hay contexto disponible, lanza un error en vez de generar con prompt vacío.
    """
    contexto_local = contexto.get("contexto_local", {}).get("resumen_para_llm", "")
    contexto_web   = contexto.get("contexto_web",   {}).get("resumen_para_llm", "")

    if not contexto_local and not contexto_web:
        raise ValueError(
            "No hay contexto RAG disponible para generar el comentario causal. "
            "Activa 'Enriquecer con contexto local y fuentes web' antes de continuar."
        )

    prompt = construir_prompt_causal(
        contexto_local=contexto_local,
        contexto_web=contexto_web,
        periodo_texto=contexto.get("periodo_texto", "")
    )
    return generar_con_prompt(
        prompt=prompt,
        modelo=modelo,
        system=SYSTEM_CAUSAL,
        temperature=0.0,
        max_tokens=MAX_TOKENS_CAUSAL
    )