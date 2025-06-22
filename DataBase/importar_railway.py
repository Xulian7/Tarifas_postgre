import psycopg2
import os
import csv
from dotenv import load_dotenv
from colorama import init, Fore, Style
from datetime import datetime

init(autoreset=True)
load_dotenv()

# Conexión a la base de datos Railway desde .env
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

# Carpeta donde están los archivos CSV
csv_folder = "PORTS"

# Tablas con campo SERIAL que usan secuencias
secuencias = {
    "cuentas": "cuentas_id_seq",
    "propietario": "propietario_id_seq",
    "registros": "registros_id_seq",
    "otras_deudas": "otras_deudas_id_seq"
}

# Orden correcto para evitar fallos de claves foráneas
tablas = ["cuentas", "propietario", "clientes", "registros", "otras_deudas"]
total = len(tablas)

def convertir_fecha(valor):
    """Convierte fechas DD/MM/YYYY → YYYY-MM-DD si aplica."""
    try:
        if "/" in valor and len(valor.strip()) == 10:
            return datetime.strptime(valor.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        pass
    return valor  # Si no se puede convertir, dejar tal cual

def importar_csv(tabla, posicion):
    print(f"{Fore.CYAN}[{posicion}/{total}] Importando tabla: {tabla}...", end=" ")

    file_path = os.path.join(csv_folder, f"{tabla}.csv")
    if not os.path.exists(file_path):
        print(f"{Fore.YELLOW}⚠️  Archivo {tabla}.csv no encontrado.")
        return

    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader, None)

        # Detectar columnas de fechas excepto 'fecha_final'
        fecha_indices = [
            i for i, h in enumerate(headers)
            if "fecha" in h.lower() and h.lower() != "fecha_final"
        ]

        rows = []
        for row in reader:
            if any(cell.strip() for cell in row):
                for idx in fecha_indices:
                    if idx < len(row):
                        row[idx] = convertir_fecha(row[idx])
                rows.append(row)

        if not rows:
            print(f"{Fore.YELLOW}📭 Sin datos.")
            return

        placeholders = ", ".join(["%s"] * len(headers))
        columnas = ", ".join(headers)
        insert_query = f"INSERT INTO {tabla} ({columnas}) VALUES ({placeholders})"

        try:
            cursor.executemany(insert_query, rows)
        except Exception as e:
            conn.rollback()
            print(f"{Fore.RED}❌ Error al insertar en {tabla}: {e}")
            return

        print(f"{Fore.GREEN}✅ {len(rows)} filas insertadas", end="")

        # Actualizar secuencia si hay campo ID
        if tabla in secuencias:
            posibles_id = [col for col in headers if col.lower() == "id"]
            if posibles_id:
                id_col = posibles_id[0]
                id_index = headers.index(id_col)
                try:
                    max_id = max(int(row[id_index]) for row in rows if row[id_index].isdigit())
                    seq_name = secuencias[tabla]
                    cursor.execute(f"SELECT setval('{seq_name}', %s, true);", (max_id,))
                    print(f" {Fore.MAGENTA}(secuencia {seq_name} → {max_id})")
                except Exception as e:
                    print(f"{Fore.RED} ⚠️ Error al ajustar secuencia: {e}")
            else:
                print(f"{Fore.YELLOW} ⚠️ No se encontró columna 'id' en {tabla}.csv, no se actualizó secuencia.")
        else:
            print()

def main():
    print(f"{Style.BRIGHT}🚀 Iniciando migración de datos desde carpeta {csv_folder}/")
    for idx, tabla in enumerate(tablas, start=1):
        importar_csv(tabla, idx)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n{Style.BRIGHT + Fore.GREEN}🎉 Migración completada con éxito.")

if __name__ == "__main__":
    main()
