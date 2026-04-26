def obtener_fila(df, clasificacion, nombre):
    """
    Busca una fila por clasificación y nombre.
    Ejemplo:
    clasificacion = "sector"
    nombre = "Minería e Hidrocarburos"
    """

    fila = df[
        (df["clasificacion"].str.strip().str.lower() == clasificacion.strip().lower()) &
        (df["nombre"].str.strip().str.lower() == nombre.strip().lower())
    ]

    if fila.empty:
        return None

    return fila.iloc[0]