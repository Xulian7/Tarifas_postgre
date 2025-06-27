import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
from PIL import ImageGrab
import io
import win32clipboard

# ---------- Función para crear el engine ----------
def get_engine():
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "cUVmSghVIpRTJkWWtUymoMaadGwzLKUn")
    host = os.getenv("DB_HOST", "shuttle.proxy.rlwy.net")
    port = os.getenv("DB_PORT", "38698")
    dbname = os.getenv("DB_NAME", "railway")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)

# ---------- Función para obtener datos ----------
def obtener_datos(fecha_inicio, fecha_fin):
    engine = get_engine()
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
        WHERE fecha_sistema BETWEEN %s AND %s
    """
    return pd.read_sql(query, engine, params=(fecha_inicio, fecha_fin))

# ---------- Crear interfaz ----------
def crear_resumen_por_cuenta_y_motivo():
    ventana = tk.Tk()
    ventana.title("Resumen por Cuenta y Motivo")
    ventana.geometry("1000x650")

    # ---------- TÍTULO ----------
    lbl_titulo = tk.Label(ventana, text="", font=("Arial", 16, "bold"))
    lbl_titulo.pack(pady=10)

    # ---------- Filtro: Fecha Inicio y Fin + Botones ----------
    frame_top = tk.Frame(ventana)
    frame_top.pack()

    tk.Label(frame_top, text="Desde:", font=("Arial", 12)).pack(side="left", padx=5)
    fecha_inicio = DateEntry(frame_top, width=12, background='darkblue', foreground='white',
                             borderwidth=2, date_pattern='yyyy-mm-dd')
    fecha_inicio.set_date(datetime.now())
    fecha_inicio.pack(side="left")

    tk.Label(frame_top, text="Hasta:", font=("Arial", 12)).pack(side="left", padx=5)
    fecha_fin = DateEntry(frame_top, width=12, background='darkblue', foreground='white',
                          borderwidth=2, date_pattern='yyyy-mm-dd')
    fecha_fin.set_date(datetime.now())
    fecha_fin.pack(side="left")

    btn_cargar = tk.Button(frame_top, text="Cargar Resumen")
    btn_cargar.pack(side="left", padx=10)

    btn_captura = tk.Button(frame_top, text="📸 Capturar")
    btn_captura.pack(side="left", padx=10)

    # ---------- TREEVIEW ----------
    tree = ttk.Treeview(ventana, columns=["Cuenta", "Motivo", "Total Valor", "Total Saldos"], show="headings")
    for col in ["Cuenta", "Motivo", "Total Valor", "Total Saldos"]:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=200)
    tree.pack(fill="both", expand=True)

    scrollbar_y = ttk.Scrollbar(ventana, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_y.set)
    scrollbar_y.pack(side="right", fill="y")

    # ---------- Estilos ----------
    style = ttk.Style()
    style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
    style.configure("Treeview", font=("Arial", 10), rowheight=25)
    tree.tag_configure("bold", font=("Arial", 10, "bold"))
    tree.tag_configure("total_general", background="#d1ffd1", font=("Arial", 11, "bold"))

    # ---------- Acción del botón ----------
    def cargar_datos():
        tree.delete(*tree.get_children())
        inicio = fecha_inicio.get_date()
        fin = fecha_fin.get_date()

        if inicio > fin:
            messagebox.showwarning("Fechas inválidas", "La fecha de inicio no puede ser posterior a la fecha final.")
            return

        lbl_titulo.config(text=f"📋 Reporte de valores del {inicio.strftime('%d-%m-%Y')} al {fin.strftime('%d-%m-%Y')}")

        try:
            df = obtener_datos(inicio, fin)
        except Exception as e:
            print(f"Error al obtener datos: {e}")
            tree.insert("", "end", values=("Error al obtener datos", "", "", ""))
            return

        if df.empty:
            tree.insert("", "end", values=("Sin datos", "", "", ""))
            return

        resumen = (
            df.groupby(["nombre_cuenta", "motivo"])
            .agg({"valor": "sum", "saldos": "sum"})
            .reset_index()
        )

        total_general_valor = 0
        total_general_saldos = 0

        for cuenta in resumen["nombre_cuenta"].unique():
            df_cuenta = resumen[resumen["nombre_cuenta"] == cuenta]
            total_valor_cuenta = df_cuenta["valor"].sum()
            total_saldos_cuenta = df_cuenta["saldos"].sum()

            for _, row in df_cuenta.iterrows():
                tree.insert("", "end", values=(
                    cuenta, row["motivo"], f"{row['valor']:,.0f}", f"{row['saldos']:,.0f}"))

            tree.insert("", "end", values=(
                cuenta, "TOTAL", f"{total_valor_cuenta:,.0f}", f"{total_saldos_cuenta:,.0f}"), tags=("bold",))
            tree.insert("", "end", values=("", "", "", ""))

            total_general_valor += total_valor_cuenta
            total_general_saldos += total_saldos_cuenta

        tree.insert("", "end", values=(
            "TOTAL GENERAL", "", f"{total_general_valor:,.0f}", f"{total_general_saldos:,.0f}"), tags=("total_general",))

    btn_cargar.config(command=cargar_datos)

    # ---------- Acción del botón de captura al portapapeles ----------
    def capturar_ventana():
        ventana.update()
        x = ventana.winfo_rootx()
        y = ventana.winfo_rooty()
        w = ventana.winfo_width()
        h = ventana.winfo_height()
        imagen = ImageGrab.grab(bbox=(x, y, x + w, y + h)).convert("RGB")
        output = io.BytesIO()
        imagen.save(output, format="BMP")
        data = output.getvalue()[14:]  # quitar cabecera BMP

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

        messagebox.showinfo("Captura", "📸 Captura copiada al portapapeles.")

    btn_captura.config(command=capturar_ventana)

    ventana.mainloop()

# ---------- Ejecutar ----------
if __name__ == "__main__":
    crear_resumen_por_cuenta_y_motivo()
