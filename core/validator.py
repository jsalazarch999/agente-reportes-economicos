import pandas as pd

# =====================================================
# COLUMNAS REQUERIDAS
# =====================================================

COLUMNAS_NUMERICAS = [
    "variacion_interanual",
    "incidencia_interanual",
    "variacion_acumulada",
    "incidencia_acumulada",
]

COLUMNAS_NUMERICAS_OPCIONALES = [
    "precio_internacional",
]

COLUMNAS_TEXTO = ["periodo", "clasificacion", "nombre"]

COLUMNAS_REQUERIDAS = COLUMNAS_TEXTO + COLUMNAS_NUMERICAS

# =====================================================
# FILAS ESTRUCTURALES POR SECTOR
# =====================================================

FILAS_REQUERIDAS = {
    "Minería e Hidrocarburos": [
        ("sector",    "Minería e Hidrocarburos"),
        ("subsector", "Minería Metálica"),
        ("subsector", "Hidrocarburos"),
    ],
    "Pesca": [
        ("sector", "Pesca"),
    ],
    "Manufactura": [
        ("sector", "Manufactura"),
    ],
    "Agropecuario": [
        ("sector", "Agropecuario"),
    ],
}


# =====================================================
# VALIDACIONES
# =====================================================

def validar_columnas(df):
    """Verifica que todas las columnas requeridas estén presentes."""
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise ValueError(
            f"Faltan columnas requeridas en los datos: {', '.join(faltantes)}"
        )


def validar_numericos(df):
    """
    Verifica columnas numéricas obligatorias y opcionales.
    Las opcionales solo se validan si existen en el DataFrame.
    """
    errores = []

    # Obligatorias — deben existir y ser numéricas
    for col in COLUMNAS_NUMERICAS:
        convertida = pd.to_numeric(df[col], errors="coerce")
        n_invalidos = convertida.isna().sum()
        if n_invalidos > 0:
            errores.append(
                f"'{col}' tiene {n_invalidos} valor(es) no numérico(s) o vacío(s)"
            )

    # Opcionales — solo si existen en el DataFrame
    for col in COLUMNAS_NUMERICAS_OPCIONALES:
        if col in df.columns:
            convertida = pd.to_numeric(df[col], errors="coerce")
            n_invalidos = convertida.isna().sum()
            n_total = len(df)
            # Solo alerta si MÁS del 50% son inválidos — valores parciales son normales
            if n_invalidos > n_total * 0.5:
                errores.append(
                    f"'{col}' tiene {n_invalidos}/{n_total} valores no numéricos "
                    f"— verifica que el formato sea correcto"
                )

    if errores:
        raise ValueError(
            "Problemas en columnas numéricas:\n"
            + "\n".join(f"  - {e}" for e in errores)
        )


def validar_empresa(df):
    """
    Validación opcional: si existe la columna 'empresa',
    verifica que las filas de tipo 'producto' tengan empresa asignada.
    Solo advierte — no lanza error — porque empresa es dato nuevo y puede
    estar incompleto en los primeros periodos.
    """
    if "empresa" not in df.columns:
        return []

    advertencias = []
    productos_sin_empresa = df[
        (df["clasificacion"].str.lower() == "producto") &
        (df["empresa"].isna() | (df["empresa"].str.strip() == ""))
    ]

    if not productos_sin_empresa.empty:
        nombres = productos_sin_empresa["nombre"].tolist()
        advertencias.append(
            f"Productos sin empresa asignada: {', '.join(nombres)}"
        )

    return advertencias


def validar_filas_principales(df_periodo, sector="Minería e Hidrocarburos"):
    """Verifica que las filas estructurales del sector estén presentes."""
    filas = FILAS_REQUERIDAS.get(sector)

    if filas is None:
        raise ValueError(
            f"Sector no reconocido para validación: '{sector}'. "
            f"Sectores disponibles: {', '.join(FILAS_REQUERIDAS.keys())}"
        )

    faltantes = []
    for clasificacion, nombre in filas:
        existe = (
            (df_periodo["clasificacion"].str.lower().str.strip() == clasificacion.lower()) &
            (df_periodo["nombre"].str.lower().str.strip() == nombre.lower())
        ).any()

        if not existe:
            faltantes.append(f"{clasificacion}: {nombre}")

    if faltantes:
        raise ValueError(
            f"Faltan filas estructurales para sector '{sector}': "
            + ", ".join(faltantes)
        )


# =====================================================
# FUNCIONES PÚBLICAS
# =====================================================

def validar_dataframe(df):
    """
    Valida estructura completa del DataFrame cargado.
    Retorna lista de advertencias (puede estar vacía).
    """
    validar_columnas(df)
    validar_numericos(df)
    advertencias = validar_empresa(df)
    return advertencias


def validar_periodo(df_periodo, sector="Minería e Hidrocarburos"):
    """Valida que el periodo filtrado tenga las filas estructurales necesarias."""
    validar_filas_principales(df_periodo, sector)