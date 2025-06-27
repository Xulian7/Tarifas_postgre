import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
import pandas as pd
import psycopg2
from datetime import datetime

# ---------- Configuración base de datos ----------
DB_PARAMS = {
    "dbname": "railway",
    "user": "postgres",
    "password": "cUVmSghVIpRTJkWWtUymoMaadGwzLKUn",
    "host": "shuttle.proxy.rlwy.net",
    "port": "38698"
}

# ---------- Función para obtener datos ----------
def obtener_datos(fecha):
    conn = psycopg2.connect(**DB_PARAMS)
    query = """
        SELECT 
            nombre_cuenta, 
            CASE 
                WHEN motivo = 'N-a' THEN 'Tarifas'
                ELSE motivo 
            END AS motivo,
            valor,
            saldos
        FROM registros
        WHERE fecha_sistema = %s
    """
    df = pd.read_sql(query, conn, params=(fecha,))
    conn.close()
    return df

# ---------- Crear interfaz ----------
def crear_resumen_por_cuenta_y_motivo():
    ventana = tk.Tk()
    ventana.title("Resumen por Cuenta y Motivo")
    ventana.geometry("950x600")

    # ---------- Filtro: Fecha + Botón ----------
    frame_top = tk.Frame(ventana)
    frame_top.pack(pady=10)

    tk.Label(frame_top, text="Seleccione fecha:", font=("Arial", 12)).pack(side="left", padx=10)
    fecha_entry = DateEntry(frame_top, width=12, background='darkblue', foreground='white',
                            borderwidth=2, date_pattern='yyyy-mm-dd')
    fecha_entry.set_date(datetime.now())
    fecha_entry.pack(side="left")

    tree = ttk.Treeview(ventana, columns=["Cuenta", "Motivo", "Total Valor", "Total Saldos"], show="headings")
    tree.heading("Cuenta", text="Cuenta")
    tree.heading("Motivo", text="Motivo")
    tree.heading("Total Valor", text="Total Valor")
    tree.heading("Total Saldos", text="Total Saldos")

    for col in ["Cuenta", "Motivo", "Total Valor", "Total Saldos"]:
        tree.column(col, anchor="center", width=200)

    tree.pack(fill="both", expand=True)

    scrollbar_y = ttk.Scrollbar(ventana, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_y.set)
    scrollbar_y.pack(side="right", fill="y")

    # ---------- Acción de cargar datos ----------
    def cargar_datos():
        tree.delete(*tree.get_children())
        fecha = fecha_entry.get_date()

        try:
            df = obtener_datos(fecha)
        except Exception as e:
            print(f"Error al obtener datos: {e}")
            return

        if df.empty:
            tree.insert("", "end", values=("Sin datos", "", "", ""))
            return

        resumen = (
            df.groupby(["nombre_cuenta", "motivo"])
            .agg({"valor": "sum", "saldos": "sum"})
            .reset_index()
        )

        for cuenta in resumen["nombre_cuenta"].unique():
            df_cuenta = resumen[resumen["nombre_cuenta"] == cuenta]
            total_valor_cuenta = df_cuenta["valor"].sum()
            total_saldos_cuenta = df_cuenta["saldos"].sum()

            tree.insert("", "end", values=(
                cuenta, "", f"{total_valor_cuenta:,.0f}", f"{total_saldos_cuenta:,.0f}"), tags=("bold",))

            for _, row in df_cuenta.iterrows():
                tree.insert("", "end", values=(
                    "", row["motivo"], f"{row['valor']:,.0f}", f"{row['saldos']:,.0f}"))

        tree.tag_configure("bold", font=("Arial", 10, "bold"))

    # ---------- Botón ----------
    btn_cargar = tk.Button(frame_top, text="Cargar Resumen", command=cargar_datos)
    btn_cargar.pack(side="left", padx=10)

    ventana.mainloop()

# ---------- Ejecutar ----------
if __name__ == "__main__":
    crear_resumen_por_cuenta_y_motivo()
