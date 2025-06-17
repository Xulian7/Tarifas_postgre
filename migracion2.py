import psycopg2
import csv
import os
import sys
from tqdm import tqdm

# Conexión
conn = None
cur = None

try:
    conn = psycopg2.connect(
        dbname='railway',
        user='postgres',
        password='kOqrfNfhwfoUJQLCjYaRENZsGAJjdTue',
        host='yamanote.proxy.rlwy.net',
        port='43719'
    )
    cur = conn.cursor()

    ruta_csv = './container'
    log_path = 'errores_importacion.log'
    orden_tablas = ['propietario', 'clientes', 'cuentas', 'registros', 'otras_deudas']

    if os.path.exists(log_path):
        os.remove(log_path)

    def registrar_error(tabla, fila, error):
        with open(log_path, 'a', encoding='utf-8') as log:
            log.write(f"Error en tabla {tabla}:\n")
            log.write(f"  Fila: {fila}\n")
            log.write(f"  Error: {error}\n\n")

    def limpiar_campo(campo, nombre_columna):
        campo = campo.strip()
        if campo == '':
            if nombre_columna.lower() == 'tipo':
                return 'Efectivo'
            return None
        return campo

    for tabla in orden_tablas:
        archivo_csv = os.path.join(ruta_csv, f"{tabla}.csv")
        print(f"📥 Importando: {archivo_csv} → {tabla}")

        if not os.path.exists(archivo_csv):
            print(f"⚠️ Archivo no encontrado: {archivo_csv}")
            continue

        with open(archivo_csv, newline='', encoding='utf-8') as f:
            lector = list(csv.reader(f))
            if not lector:
                print(f"⚠️ Archivo vacío: {archivo_csv}")
                continue

            columnas = lector[0]
            filas = lector[1:]
            placeholders = ', '.join(['%s'] * len(columnas))
            columnas_str = ', '.join(columnas)

            errores_en_tabla = False

            for fila in tqdm(filas, desc=f"Importando {tabla}", unit="registro"):
                fila_limpia = [
                    limpiar_campo(fila[i], columnas[i])
                    for i in range(len(fila))
                ]
                try:
                    cur.execute(
                        f"INSERT INTO {tabla} ({columnas_str}) VALUES ({placeholders})",
                        fila_limpia
                    )
                except Exception as e:
                    registrar_error(tabla, fila_limpia, str(e))
                    print(f"\n⚠️ Error al insertar en {tabla} (fila):\n    {fila_limpia}\n    {e}")
                    errores_en_tabla = True

            conn.commit()
            print(f"✅ {tabla}: importación finalizada {'con errores' if errores_en_tabla else 'sin errores'}.")

except KeyboardInterrupt:
    print("\n⛔ Importación interrumpida por el usuario (Ctrl+C). Se guardaron los errores hasta ese punto.")

except Exception as e:
    print(f"❌ Error inesperado: {e}")

finally:
    if cur and not cur.closed:
        cur.close()
    if conn and not conn.closed:
        conn.close()
    print("🔚 Conexión cerrada.")
