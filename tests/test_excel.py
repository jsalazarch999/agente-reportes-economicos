from pathlib import Path

from core.loader import cargar_excel, obtener_periodos, filtrar_periodo
from core.validator import validar_dataframe, validar_periodo


BASE_DIR = Path(__file__).resolve().parents[1]
ARCHIVO = BASE_DIR / "data" / "sample" / "variaciones_202602.xlsx"


def probar_excel(archivo=ARCHIVO):
    if not archivo.exists():
        raise FileNotFoundError(f"No existe el archivo de prueba: {archivo}")

    df = cargar_excel(archivo)

    print("\n===== DATAFRAME CARGADO =====")
    print(df.head())

    validar_dataframe(df)
    print("\n✔ Validación general OK")

    periodos = obtener_periodos(df)

    if not periodos:
        raise ValueError("No se encontraron periodos en el Excel.")

    print("\n===== PERIODOS DISPONIBLES =====")
    print(periodos)

    periodo = periodos[-1]

    print("\n===== PERIODO SELECCIONADO =====")
    print(periodo)

    dfp = filtrar_periodo(df, periodo)

    print("\n===== DATAFRAME DEL PERIODO =====")
    print(dfp.head())

    validar_periodo(dfp)
    print("\n✔ Validación del periodo OK")

    print("\n===== RESUMEN =====")
    print("Archivo:", archivo.name)
    print("Periodo:", periodo)
    print("Filas:", len(dfp))
    print("Columnas:", list(dfp.columns))

    return dfp, periodo


if __name__ == "__main__":
    probar_excel()