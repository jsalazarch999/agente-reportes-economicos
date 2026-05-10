COLUMNAS_REQUERIDAS = [
    "periodo",
    "clasificacion",
    "nombre",
    "variacion_interanual",
    "incidencia_interanual",
    "variacion_acumulada",
    "incidencia_acumulada",
]

def validar_columnas(df):
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]

    if faltantes:
        raise ValueError(
            f"Faltan columnas en el Excel: {', '.join(faltantes)}"
        )

    return True

def validar_filas_principales(df):
    requeridas = [
        ("sector", "Minería e Hidrocarburos"),
        ("subsector", "Minería Metálica"),
        ("subsector", "Hidrocarburos"),
    ]

    faltantes = []

    for clasificacion, nombre in requeridas:
        fila = df[
            (df["clasificacion"].str.lower().str.strip() == clasificacion.lower()) &
            (df["nombre"].str.lower().str.strip() == nombre.lower())
        ]

        if fila.empty:
            faltantes.append(f"{clasificacion}: {nombre}")

    if faltantes:
        raise ValueError(
            "Faltan filas principales: " + ", ".join(faltantes)
        )

    return True

def validar_numericos(df):
    columnas_numericas = [
        "variacion_interanual",
        "incidencia_interanual",
        "variacion_acumulada",
        "incidencia_acumulada",
    ]

    faltas = []

    for col in columnas_numericas:
        if df[col].isna().any():
            faltas.append(col)

    if faltas:
        raise ValueError(
            "Existen valores vacíos en columnas numéricas: "
            + ", ".join(faltas)
        )

    return True

def validar_dataframe(df):
    validar_columnas(df)
    validar_numericos(df)
    return True

def validar_periodo(df_periodo):
    validar_filas_principales(df_periodo)
    return True