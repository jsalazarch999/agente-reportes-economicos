import os

from core.loader import cargar_excel, obtener_periodos, filtrar_periodo
from core.validator import validar_dataframe, validar_periodo


# 🔹 Ruta robusta (funciona siempre)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

archivo = os.path.join(BASE_DIR, "data", "sample", "variaciones_202602.xlsx")


# =========================
# 1. CARGA
# =========================
df = cargar_excel(archivo)

print("\n===== DATAFRAME CARGADO =====")
print(df.head())


# =========================
# 2. VALIDACIÓN GENERAL
# =========================
validar_dataframe(df)
print("\n✔ Validación general OK")


# =========================
# 3. PERIODOS
# =========================
periodos = obtener_periodos(df)

print("\n===== PERIODOS DISPONIBLES =====")
print(periodos)


# =========================
# 4. SELECCIÓN
# =========================
periodo = periodos[-1]

print("\n===== PERIODO SELECCIONADO =====")
print(periodo)


# =========================
# 5. FILTRADO
# =========================
dfp = filtrar_periodo(df, periodo)

print("\n===== DATAFRAME DEL PERIODO =====")
print(dfp.head())


# =========================
# 6. VALIDACIÓN DEL PERIODO
# =========================
validar_periodo(dfp)
print("\n✔ Validación del periodo OK")


# =========================
# 7. RESUMEN
# =========================
print("\n===== RESUMEN =====")
print("Filas:", len(dfp))
print("Columnas:", list(dfp.columns))