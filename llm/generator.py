import logging
from llm.clients import get_client
from llm.prompts import (
    construir_prompt_estadistico,
    construir_prompt_fundamentacion_subsector,
    construir_prompt_fundamentacion_producto,
    construir_prompt_unificacion,
    construir_prompt_revision,
    construir_prompt_causal,
    SYSTEM_ESTADISTICO,
    SYSTEM_FUNDAMENTACION,
    SYSTEM_REVISION,
    SYSTEM_CAUSAL,
)

logger = logging.getLogger(__name__)

# =====================================================
# CONSTANTES
# =====================================================

MAX_TOKENS            = 1200
MAX_TOKENS_CAUSAL     = 1200
MAX_TOKENS_FUND       = 600
MAX_TOKENS_UNIF       = 3000
TEMPERATURE_ESTADIST  = 0.1
TEMPERATURE_FUND      = 0.3
TEMPERATURE_UNIF      = 0.2

# Tokens por sección — reporte_1 tiene más bullets y puede ser más largo
MAX_TOKENS_POR_SECCION = {
    "reporte_1": 1500,
    "reporte_2": 1200,
    "reporte_3": 1200,
}

_SEPARADOR = "\n\n---\n\n"

# =====================================================
# CAPA DE INVOCACIÓN AL LLM
# =====================================================

def _llamar_openai_compatible(
    client, model_name, prompt, temperature, max_tokens, system, extra_body=None
):
    kwargs = dict(
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if extra_body:
        kwargs["extra_body"] = extra_body

    response  = client.chat.completions.create(**kwargs)
    contenido = response.choices[0].message.content

    if not contenido or not contenido.strip():
        raise ValueError("El modelo devolvió una respuesta vacía.")

    return contenido


def generar_con_prompt(
    prompt,
    modelo="qwen",
    temperature=0.2,
    max_tokens=MAX_TOKENS,
    system=SYSTEM_REVISION,
):
    client_info = get_client(modelo)
    tipo        = client_info["tipo"]
    client      = client_info["client"]
    model_name  = client_info["model"]

    if tipo in {"huggingface", "openai", "groq"}:
        return _llamar_openai_compatible(
            client, model_name, prompt, temperature, max_tokens, system
        )
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
                "temperature":       temperature,
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


# =====================================================
# GENERACIÓN DEL PÁRRAFO ESTADÍSTICO
# Estrategia Deferred: sección por sección
# =====================================================

def generar_parrafo_estadistico(contexto, modelo="qwen"):
    """
    Genera el reporte estadístico usando la estrategia Deferred:
    mejora el estilo de cada sección del texto base por separado
    y las concatena determinísticamente.

    Ventajas sobre generación directa:
    - Nunca se trunca (cada sección < 1200 tokens)
    - Los números no cambian (el LLM solo mejora estilo)
    - Más rápido en modelos pequeños como Qwen

    Si no hay texto base disponible, genera desde el JSON
    del contexto (flujo nuevo, para cuando no haya determinístico).
    """
    texto_base = contexto.get("texto_base", {})

    # --- Flujo nuevo: sin texto base, generar desde JSON ---
    if not texto_base:
        logger.info("Sin texto base — generando desde JSON del contexto.")
        prompt = construir_prompt_estadistico("", contexto)
        return generar_con_prompt(
            prompt=prompt,
            modelo=modelo,
            temperature=TEMPERATURE_ESTADIST,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_ESTADISTICO,
        )

    # --- Flujo Deferred: mejorar cada sección por separado ---
    logger.info("Generando reporte sección por sección (estrategia Deferred).")

    secciones_mejoradas = []

    for clave in ["reporte_1", "reporte_2", "reporte_3"]:
        texto_seccion = texto_base.get(clave)

        if not texto_seccion:
            logger.info(f"{clave} vacío — omitido.")
            continue

        prompt  = construir_prompt_revision(texto_base=texto_seccion)
        max_tok = MAX_TOKENS_POR_SECCION.get(clave, 1200)  

        try:
            seccion_mejorada = generar_con_prompt(
                prompt=prompt,
                modelo=modelo,
                temperature=TEMPERATURE_ESTADIST,
                max_tokens=max_tok,                        
                system=SYSTEM_REVISION,
            )
            secciones_mejoradas.append(seccion_mejorada)
            logger.info(f"{clave} generado correctamente.")

        except Exception as e:
            logger.warning(
                f"Error mejorando {clave} — usando texto base original: {e}"
            )
            secciones_mejoradas.append(texto_seccion)

    if not secciones_mejoradas:
        raise RuntimeError(
            "No se pudo generar ninguna sección del reporte estadístico."
        )

    # Concatenación determinística de las secciones
    return _SEPARADOR.join(secciones_mejoradas)


# =====================================================
# GENERACIÓN DE FUNDAMENTACIONES
# =====================================================

def generar_fundamentacion_subsector(
    subsector, periodo_texto, variacion, contexto_rag, modelo="qwen"
):
    prompt = construir_prompt_fundamentacion_subsector(
        subsector=subsector,
        periodo_texto=periodo_texto,
        variacion=variacion,
        contexto_rag=contexto_rag,
    )
    return generar_con_prompt(
        prompt=prompt,
        modelo=modelo,
        temperature=TEMPERATURE_FUND,
        max_tokens=MAX_TOKENS_FUND,
        system=SYSTEM_FUNDAMENTACION,
    )


def generar_fundamentacion_producto(
    producto, subsector, periodo_texto,
    variacion, incidencia, contexto_rag,
    empresas=None, modelo="qwen"
):
    prompt = construir_prompt_fundamentacion_producto(
        producto=producto,
        subsector=subsector,
        periodo_texto=periodo_texto,
        variacion=variacion,
        incidencia=incidencia,
        contexto_rag=contexto_rag,
        empresas=empresas or [],
    )
    return generar_con_prompt(
        prompt=prompt,
        modelo=modelo,
        temperature=TEMPERATURE_FUND,
        max_tokens=MAX_TOKENS_FUND,
        system=SYSTEM_FUNDAMENTACION,
    )


def generar_todas_las_fundamentaciones(contexto, modelo="qwen"):
    """
    Genera fundamentaciones para todos los subsectores y
    productos de alta incidencia presentes en el contexto.
    """
    fundamentaciones = {}
    periodo_texto    = contexto.get("periodo_texto", "")
    contexto_rag     = contexto.get("contexto_rag", {})
    alta_incidencia  = contexto.get("productos_alta_incidencia", {})

    subsectores = {
        "mineria_metalica": contexto.get("subsector_mineria_metalica", {}),
        "hidrocarburos":    contexto.get("subsector_hidrocarburos", {}),
    }

    # Fundamentación por subsector
    for subsector, datos_sub in subsectores.items():
        variacion   = datos_sub.get("variacion_interanual", 0)
        rag_subsect = contexto_rag.get(subsector, {}).get("resumen", "")

        try:
            texto = generar_fundamentacion_subsector(
                subsector=subsector,
                periodo_texto=periodo_texto,
                variacion=variacion,
                contexto_rag=rag_subsect,
                modelo=modelo,
            )
            if "no permiten identificar" not in texto.lower():
                fundamentaciones[subsector] = texto
            else:
                logger.info(
                    f"Sin evidencia coyuntural para '{subsector}' — omitido."
                )
        except Exception as e:
            logger.warning(
                f"Error en fundamentación de subsector '{subsector}': {e}"
            )

    # Fundamentación por producto de alta incidencia
    for subsector, productos in alta_incidencia.items():
        datos_sub = subsectores.get(subsector, {})

        for producto in productos:
            clave    = f"{subsector}__{producto.lower()}"
            rag_prod = contexto_rag.get(clave, {}).get("resumen", "")

            producto_datos = next(
                (p for p in datos_sub.get("productos", [])
                 if p.get("nombre", "").lower() == producto.lower()),
                {}
            )
            variacion  = producto_datos.get("variacion_interanual", 0)
            incidencia = producto_datos.get("incidencia_interanual", 0)
            empresas   = producto_datos.get("empresas", [])

            try:
                texto = generar_fundamentacion_producto(
                    producto=producto,
                    subsector=subsector,
                    periodo_texto=periodo_texto,
                    variacion=variacion,
                    incidencia=incidencia,
                    contexto_rag=rag_prod,
                    empresas=empresas,
                    modelo=modelo,
                )
                if "no permiten identificar" not in texto.lower():
                    fundamentaciones[clave] = texto
                else:
                    logger.info(
                        f"Sin evidencia coyuntural para producto '{producto}' — omitido."
                    )
            except Exception as e:
                logger.warning(
                    f"Error en fundamentación de producto '{producto}': {e}"
                )

    logger.info(
        f"Fundamentaciones generadas: {len(fundamentaciones)} "
        f"de {len(subsectores) + sum(len(p) for p in alta_incidencia.values())} posibles."
    )
    return fundamentaciones


# =====================================================
# UNIFICACIÓN DEL REPORTE
# =====================================================

def unificar_reporte(
    texto_estadistico, fundamentaciones, periodo_texto, modelo="qwen"
):
    if not fundamentaciones:
        logger.info("Sin fundamentaciones — devolviendo solo texto estadístico.")
        return texto_estadistico

    prompt = construir_prompt_unificacion(
        texto_estadistico=texto_estadistico,
        fundamentaciones=fundamentaciones,
        periodo_texto=periodo_texto,
    )
    return generar_con_prompt(
        prompt=prompt,
        modelo=modelo,
        temperature=TEMPERATURE_UNIF,
        max_tokens=MAX_TOKENS_UNIF,
        system=SYSTEM_ESTADISTICO,
    )


# =====================================================
# PIPELINE COMPLETO
# =====================================================

def generar_reporte_completo(contexto, texto_base, modelo="qwen"):
    """
    Pipeline completo:
        1. Párrafo estadístico (Deferred — sección por sección)
        2. Fundamentaciones por subsector y producto
        3. Unificación intercalada
    """
    periodo_texto = contexto.get("periodo_texto", "")

    # Pasar texto_base al contexto para generar_parrafo_estadistico
    contexto_con_base = {**contexto, "texto_base": texto_base}

    # 1. Estadístico
    logger.info("Generando reporte estadístico (Deferred)...")
    try:
        texto_estadistico = generar_parrafo_estadistico(
            contexto=contexto_con_base,
            modelo=modelo,
        )
    except Exception as e:
        raise RuntimeError(f"Error generando párrafo estadístico: {e}")

    # 2. Fundamentaciones
    fundamentaciones = {}
    if contexto.get("contexto_rag"):
        logger.info("Generando fundamentaciones coyunturales...")
        fundamentaciones = generar_todas_las_fundamentaciones(
            contexto=contexto,
            modelo=modelo,
        )
    else:
        logger.info("Sin contexto RAG — sin fundamentaciones.")

    # 3. Unificación
    logger.info("Unificando reporte...")
    reporte_final = unificar_reporte(
        texto_estadistico=texto_estadistico,
        fundamentaciones=fundamentaciones,
        periodo_texto=periodo_texto,
        modelo=modelo,
    )

    return {
        "reporte_final":     reporte_final,
        "texto_estadistico": texto_estadistico,
        "fundamentaciones":  fundamentaciones,
    }


# =====================================================
# COMPATIBILIDAD
# =====================================================

def generar_texto(contexto, modelo="qwen"):
    if not isinstance(contexto, dict) or "texto_base" not in contexto:
        raise ValueError("Falta 'texto_base' en el contexto.")
    prompt = construir_prompt_revision(texto_base=contexto["texto_base"])
    return generar_con_prompt(
        prompt=prompt,
        modelo=modelo,
        system=SYSTEM_REVISION,
    )


def generar_comentario_causal(contexto, modelo="qwen"):
    contexto_local = contexto.get("contexto_local", {}).get("resumen_para_llm", "")
    contexto_web   = contexto.get("contexto_web",   {}).get("resumen_para_llm", "")

    if not contexto_local and not contexto_web:
        raise ValueError("No hay contexto RAG disponible.")

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
        max_tokens=MAX_TOKENS_CAUSAL,
    )