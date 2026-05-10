from llm.clients import get_client
from llm.prompts import construir_prompt_revision, construir_prompt_causal

MAX_TOKENS = 2000
TEMPERATURE = 0.2

SYSTEM_PROMPT = "Eres un economista del INEI experto en redacción técnica."

def generar_con_prompt(prompt, modelo="qwen", temperature=TEMPERATURE, max_tokens=MAX_TOKENS):
    client_info = get_client(modelo)

    tipo = client_info["tipo"]
    client = client_info["client"]
    model_name = client_info["model"]

    if tipo == "huggingface":
        response = client.chat_completion(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content

    elif tipo == "openai":
        extra_body = None

        if "deepseek" in model_name:
            extra_body = {
                "thinking": {
                    "type": "disabled"
                }
            }

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body=extra_body
        )

        contenido = response.choices[0].message.content

        if not contenido or not contenido.strip():
            raise ValueError(f"El modelo {model_name} devolvió una respuesta vacía.")

        return contenido

    elif tipo == "groq":
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content

    elif tipo == "gemini":
        prompt_final = f"""
{SYSTEM_PROMPT}

{prompt}
"""

        response = client.generate_content(
            prompt_final,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
        )

        return response.text

    elif tipo == "anthropic":
        response = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{prompt}"}
            ]
        )

        return response.content[0].text

    else:
        raise ValueError(f"Tipo de modelo no soportado: {tipo}")


def generar_texto(contexto, modelo="qwen"):
    if not isinstance(contexto, dict) or "texto_base" not in contexto:
        raise ValueError(
            "Falta 'texto_base' en el contexto. El LLM debe revisar un texto base determinístico."
        )

    prompt = construir_prompt_revision(
        texto_base=contexto["texto_base"]
    )

    return generar_con_prompt(
        prompt=prompt,
        modelo=modelo,
        temperature=0.2,
        max_tokens=2000
    )


def generar_comentario_causal(contexto, modelo="qwen"):
    contexto_local = contexto.get("contexto_local", {}).get("resumen_para_llm", "")
    contexto_web = contexto.get("contexto_web", {}).get("resumen_para_llm", "")

    prompt = construir_prompt_causal(
        contexto_local=contexto_local,
        contexto_web=contexto_web
    )

    return generar_con_prompt(
        prompt=prompt,
        modelo=modelo,
        temperature=0.0,
        max_tokens=1200
    )