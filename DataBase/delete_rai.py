import psycopg2
import os
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)
load_dotenv()

try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()

    print(f"{Style.BRIGHT}💣 Iniciando eliminación de tablas...")

    # Orden inverso al de creación para evitar errores por FK
    tablas = ["otras_deudas", "registros", "clientes", "propietario", "cuentas"]

    for tabla in tablas:
        print(f"{Fore.YELLOW}→ Eliminando tabla: {tabla}...", end=" ")
        cursor.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE;")
        print(f"{Fore.GREEN}OK")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n{Style.BRIGHT + Fore.RED}🔥 Todas las tablas fueron eliminadas exitosamente.")

except Exception as e:
    print(f"{Fore.RED}❌ Error al eliminar tablas: {e}")
