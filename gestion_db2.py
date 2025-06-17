import sqlite3

# Conexión a la base de datos
conn = sqlite3.connect("diccionarios/base_dat.db")
cursor = conn.cursor()

# Crear la tabla otras_deudas si no existe
cursor.execute("""
    CREATE TABLE IF NOT EXISTS otras_deudas (
        Cedula TEXT,
        Placa TEXT,
        Fecha_deuda TEXT,
        Descripcion TEXT,
        Valor REAL
    )
""")

# Guardar cambios y cerrar conexión
conn.commit()
conn.close()

print("Tabla 'otras_deudas' verificada o creada sin alterar la base existente.")
