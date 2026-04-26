from llm.clients import get_client
from llm.prompts import construir_prompt


def generar_texto(contexto, modelo="qwen"):
    """
    Genera el texto final usando el modelo seleccionado.

    modelo puede ser:
    - qwen
    - llama3
    - openai
    """

    prompt = construir_prompt(contexto)

    client_info = get_client(modelo)

    tipo = client_info["tipo"]
    client = client_info["client"]
    model_name = client_info["model"]

    if tipo == "huggingface":
        response = client.chat_completion(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un economista del INEI experto en redacción técnica."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=700,
            temperature=0.2
        )

        return response.choices[0].message.content

    elif tipo == "openai":
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un economista del INEI experto en redacción técnica."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=700,
            temperature=0.2
        )

        return response.choices[0].message.content
    
    elif tipo == "groq":

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Eres un economista del INEI experto en redacción técnica."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=700
        )

        return response.choices[0].message.content

    else:
        raise ValueError(f"Tipo de modelo no soportado: {tipo}")