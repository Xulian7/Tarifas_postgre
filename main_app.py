import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from dotenv import load_dotenv
import os
from datetime import datetime
import pandas as pd
import tkinter.font as tkFont
from PIL import Image, ImageTk
from tkinter import PhotoImage
from logica import *  # Importar todas las funciones de logica.py
import psycopg2

# Cargar las variables del archivo .env
load_dotenv()
# Acceder a las variables
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DATABASE_URL = os.getenv("DATABASE_URL")


datos_cargados = []  # Variable global para guardar los datos de tree
# Función para cargar las opciones de cuentas disponibles en la DB
nequi_opciones = cargar_nequi_opciones()
# Variable global para saber qué Entry se actualizó por último
ultimo_entry = None

# Crear ventana principal
ventana = tk.Tk()
ventana.title("Registro de Tarifas")
ventana.geometry("800x500")
icono_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img', 'inicio.ico')
if os.path.exists(icono_path):
    ventana.iconbitmap(icono_path)
else:
    print("No se encontró el icono en la ruta especificada")

# Frame para el formulario y los botones
frame_superior = tk.Frame(ventana, bd=2, relief="groove", bg="#f0f0f0")
frame_superior.grid(row=0, column=0, sticky="nsew", padx=1, pady=1) 

# Frame izquierdo que contendrá formulario y botones
frame_izquierdo = tk.Frame(frame_superior, bd=0, relief="flat", bg="#f0f0f0")
frame_izquierdo.grid(row=0, column=0, sticky="nsew", padx=5, pady=5) 
# Definir el ancho común para todos los widgets
ancho_widget = 30 # ajustar este valor según necesidades
# Crear Frame para el formulario
frame_formulario = tk.Frame(frame_izquierdo, bd=2, relief="solid")
frame_formulario.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

# Campos del formulario organizados en filas
tk.Label(frame_formulario, text="Cédula:").grid(row=0, column=0, padx=5, pady=3, sticky="e")
entry_cedula = tk.Entry(frame_formulario, width=ancho_widget, justify="center")
entry_cedula.grid(row=0, column=1, padx=5, pady=3, sticky="w")

tk.Label(frame_formulario, text="Nombre:").grid(row=1, column=0, padx=5, pady=3, sticky="e")
entry_nombre = tk.Entry(frame_formulario, width=ancho_widget, justify="center")
entry_nombre.grid(row=1, column=1, padx=5, pady=3, sticky="w")

def actualizar_sugerencias(event):
    texto = entry_nombre.get()
    listbox_sugerencias.delete(0, tk.END)

    if not texto:
        listbox_sugerencias.grid_forget()
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nombre 
            FROM clientes 
            WHERE nombre ILIKE %s
            ORDER BY LENGTH(nombre)
            LIMIT 5
        """, (f"%{texto}%",))
        resultados = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        return

    if resultados:
        for nombre in resultados:
            listbox_sugerencias.insert(tk.END, nombre[0])
        listbox_sugerencias.grid(row=0, column=0, sticky="nsew")
        frame_sugerencias.grid_rowconfigure(0, weight=1)
        frame_sugerencias.grid_columnconfigure(0, weight=1)
        frame_sugerencias.grid()
    else:
        listbox_sugerencias.grid_forget()

entry_nombre.bind("<KeyRelease>", actualizar_sugerencias)

tk.Label(frame_formulario, text="Placa:").grid(row=2, column=0, padx=5, pady=3, sticky="e")
entry_placa = tk.Entry(frame_formulario, width=ancho_widget, justify="center")
entry_placa.grid(row=2, column=1, padx=5, pady=3, sticky="w")

def actualizar_sugerencias_por_placa(event):
    texto = entry_placa.get().strip().upper()
    listbox_sugerencias.delete(0, tk.END)

    if len(texto) < 3:
        listbox_sugerencias.grid_forget()
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nombre 
            FROM clientes
            WHERE UPPER(placa) LIKE %s
            ORDER BY LENGTH(placa) 
            LIMIT 5
        """, (texto + '%',))
        resultados = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"💥 Error al conectar con PostgreSQL: {e}")
        return

    if resultados:
        for nombre in resultados:
            listbox_sugerencias.insert(tk.END, nombre[0])
        listbox_sugerencias.grid(row=1, column=0, sticky="nsew")
        frame_sugerencias.grid_rowconfigure(1, weight=1)
        frame_sugerencias.grid_columnconfigure(0, weight=1)
        frame_sugerencias.grid()
    else:
        listbox_sugerencias.grid_forget()

entry_placa.bind("<KeyRelease>", actualizar_sugerencias_por_placa)

# Crear la función para seleccionar la sugerencia y actualizar los otros campos
def seleccionar_sugerencia(event):
    seleccion = listbox_sugerencias.curselection()
    
    if seleccion:
        nombre_seleccionado = listbox_sugerencias.get(seleccion)
        
        entry_nombre.delete(0, tk.END)
        entry_nombre.insert(0, nombre_seleccionado)

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Buscar cédula y placa
            cursor.execute("""
                SELECT cedula, placa 
                FROM clientes 
                WHERE nombre = %s
            """, (nombre_seleccionado,))
            resultado = cursor.fetchone()

            if resultado:
                cedula, placa = resultado

                entry_cedula.delete(0, tk.END)
                entry_cedula.insert(0, cedula)
                entry_placa.delete(0, tk.END)
                entry_placa.insert(0, placa)


        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Error de base de datos:\n{e}")
        finally:
            if conn:
                cursor.close()
                conn.close()

        listbox_sugerencias.place_forget()

tk.Label(frame_formulario, text="Tarifa:").grid(row=3, column=0, padx=5, pady=3, sticky="e")
entry_monto = tk.Entry(frame_formulario, width=ancho_widget, justify="center")
entry_monto.grid(row=3, column=1, padx=5, pady=3, sticky="w")

tk.Label(frame_formulario, text="Otros:").grid(row=4, column=0, padx=5, pady=3, sticky="e")
entry_saldos = tk.Entry(frame_formulario, width=ancho_widget, justify="center")
entry_saldos.grid(row=4, column=1, padx=5, pady=3, sticky="w")

tk.Label(frame_formulario, text="Motivo:").grid(row=5, column=0, padx=5, pady=3, sticky="e")
tipos_opciones = ["N-a", "otras deudas", "multa"]
combo_motivo = ttk.Combobox(frame_formulario, values=tipos_opciones, state="readonly", width=27)
combo_motivo.grid(row=5, column=1, padx=5, pady=3, sticky="w")
combo_motivo.set("N-a")


# Crea el frame para las sugerencias
frame_sugerencias = tk.Frame(frame_formulario, width=150, height=100)  # Ajusta según necesidad
frame_sugerencias.grid(row=0, column=2, rowspan=5, padx=5, pady=3, sticky="nsew")
# Crea el Listbox dentro del frame_sugerencias
listbox_sugerencias = tk.Listbox(frame_sugerencias, height=10, width=30, justify="center")  # Ajusta el width
listbox_sugerencias.grid(row=0, column=0, sticky="nsew") 
# Hacer que el frame_sugerencias pueda expandirse
frame_sugerencias.grid_rowconfigure(0, weight=1)  # Hace que el Listbox se expanda
frame_sugerencias.grid_columnconfigure(0, weight=1)  # Hace que el Listbox se expanda
# Vínculo para detectar selección
listbox_sugerencias.bind("<<ListboxSelect>>", seleccionar_sugerencia)
# Actualizar las sugerencias

fecha_actual = datetime.now().strftime('%d-%m-%Y')
tk.Label(frame_formulario, text="Fecha_sistema:").grid(row=0, column=3, padx=5, pady=3, sticky="e")
entry_hoy = tk.Entry(frame_formulario, width=28, justify="center", font=("Helvetica", 10, "bold"))
entry_hoy.insert(0, fecha_actual) 
entry_hoy.config(state="disabled")
entry_hoy.grid(row=0, column=4, padx=5, pady=3, sticky="e")

tk.Label(frame_formulario, text="Fecha_registro:").grid(row=1, column=3, padx=5, pady=3, sticky="e")
entry_fecha = DateEntry(
    frame_formulario,
    width=ancho_widget,
    background='darkblue',
    foreground='white',
    borderwidth=2,
    date_pattern='dd-MM-yyyy',  # Establecer el formato Día-Mes-Año
    locale='es_ES',  # Establecer la localidad a español para garantizar formato correcto
    textvariable=tk.StringVar()  # Para inicializar vacío
)
entry_fecha.configure(justify="center")
entry_fecha.grid(row=1, column=4, padx=5, pady=3, sticky="w")

tk.Label(frame_formulario, text="Tipo:").grid(row=2, column=3, padx=5, pady=3, sticky="e")
tipos_opciones = ["Consignación", "Transfer Nequi", "Bancolombia", "Transfiya", "PTM", "Efectivo", "Ajuste P/P"]
combo_tipo = ttk.Combobox(frame_formulario, values=tipos_opciones, state="readonly", width=ancho_widget)
combo_tipo.grid(row=2, column=4, padx=5, pady=3, sticky="w")

tk.Label(frame_formulario, text="Referencia:").grid(row=3, column=3, padx=5, pady=3, sticky="e")
var_referencia = tk.StringVar()
def to_uppercase(*args):
    var_referencia.set(var_referencia.get().upper())
var_referencia.trace_add("write", to_uppercase)
entry_referencia = tk.Entry(frame_formulario, width=33, justify="center", textvariable=var_referencia)
entry_referencia.grid(row=3, column=4, padx=5, pady=3, sticky="w")

# Combobox cargando las opciones de nequis.json
tk.Label(frame_formulario, text="Cuenta:").grid(row=4, column=3, padx=5, pady=3, sticky="e")
combo_nequi = ttk.Combobox(frame_formulario, values=nequi_opciones, state="disabled", width=ancho_widget)
combo_nequi.grid(row=4, column=4, padx=5, pady=3, sticky="w")

def llenar_nequi_por_placa():
    placa = entry_placa.get().strip()
    if not placa:
        combo_nequi.set("")  # Limpia si no hay placa
        return
    try:
        df = pd.read_excel("diccionarios/cuentas.xlsx")
        # Validar columnas
        if "Placa" not in df.columns or "Cuenta" not in df.columns or df.empty:
            combo_nequi.set("")
            return
        fila = df.loc[df["Placa"] == placa]
        if not fila.empty:
            cuenta = fila["Cuenta"].values[0]
            combo_nequi.set(cuenta)
        else:
            combo_nequi.set("")  # No encontró placa
    except Exception as e:
        print(f"Error leyendo cuentas.xlsx: {e}")
        combo_nequi.set("")  # Limpia combo ante error

def actualizar_nequi(*args):
    """Habilita o deshabilita combo_nequi según la opción en combo_tipo."""
    tipo = combo_tipo.get().strip()

    if tipo == "Efectivo":
        combo_nequi.set("Efectivo")
        combo_nequi.config(state="disabled")
    elif tipo in ("", "Ajuste P/P"):
        combo_nequi.set("")
        combo_nequi.config(state="disabled")
    else:
        combo_nequi.config(state="normal")
        llenar_nequi_por_placa()

def actualizar_referencia(*args):
    # Obtener el valor del combo "Tipo"
    tipo_seleccionado = ["Efectivo", "Ajuste P/P"]
    # Actualizar el texto del Entry de referencia según el tipo seleccionado
    if combo_tipo.get() in tipo_seleccionado:
        entry_referencia.delete(0, tk.END)
        entry_referencia.config(state="readonly")  # Desactiva edición
    else:
        entry_referencia.config(state="normal")  # Activa edición
        
def actualizar_todo(*args):
    actualizar_nequi()
    actualizar_referencia()

# Asociar el cambio en el combo "Tipo" a la función
combo_tipo.bind("<<ComboboxSelected>>", actualizar_todo)

tk.Label(frame_formulario, text="Verificada:").grid(row=5, column=3, padx=5, pady=3, sticky="e")
verificada_opciones = ["", "Si", "No"]
combo_verificada = ttk.Combobox(frame_formulario, values=verificada_opciones, state="readonly", width=ancho_widget)
combo_verificada.grid(row=5, column=4, padx=5, pady=3, sticky="w")
combo_verificada.set("No")  # Establecer "No" como valor por defecto




# Función para cargar imágenes con tamaño uniforme
imagenes = {}
def cargar_imagen(nombre):
    img = Image.open(f"img/{nombre}.png")
    img = img.resize((20, 20), Image.Resampling.LANCZOS)
    img_tk = ImageTk.PhotoImage(img)
    imagenes[nombre] = img_tk
    return img_tk

# Variable global para guardar los datos originales del Tree
datos_tree_original = []

def tomar_foto_tree(tree):
    global datos_tree_original
    datos_tree_original = []
    for child in tree.get_children():
        datos_tree_original.append(tree.item(child)["values"])

# Frame de los botones
frame_botones = tk.Frame(frame_izquierdo, bd=2, relief="solid")
frame_botones.grid(row=1, column=0, padx=5, pady=5, sticky="ew")  # Se expande en X
frame_botones.grid_columnconfigure(0, weight=1)
frame_botones.grid_columnconfigure(1, weight=1)
frame_botones.grid_columnconfigure(2, weight=1)

btn_agregar = tk.Button(frame_botones, text=" Registrar",image=cargar_imagen("Grabar"), compound="left", width=ancho_widget, command=lambda: agregar_registro(tree,entry_hoy, entry_cedula, entry_nombre, entry_placa, entry_monto, entry_saldos, entry_referencia, entry_fecha, combo_tipo, combo_nequi, combo_verificada, listbox_sugerencias))
btn_agregar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

btn_consultar = tk.Button(frame_botones, text=" Consultar", image=cargar_imagen("Buscar"), compound="left", width=ancho_widget, command=lambda: (cargar_db(tree, entry_cedula, entry_nombre, entry_placa, entry_referencia, entry_fecha, combo_tipo, combo_nequi, combo_verificada), tomar_foto_tree(tree)))
btn_consultar.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

btn_limpiar = tk.Button(frame_botones, text=" Limpiar", image=cargar_imagen("Borrar"), compound="left", width=ancho_widget, command=lambda: limpiar_formulario(entry_cedula, entry_nombre, entry_placa, entry_monto, entry_saldos, combo_motivo, entry_referencia, entry_fecha, combo_tipo, combo_nequi, combo_verificada, listbox_sugerencias, tree))
btn_limpiar.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

btn_cuentas = tk.Button(frame_botones, text=" Cuentas", image=cargar_imagen("Cuenta"), compound="left", width=ancho_widget, command=abrir_ventana_cuentas)
btn_cuentas.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

btn_clientes = tk.Button(frame_botones, text=" Conductores", image=cargar_imagen("Cliente"), compound="left", width=ancho_widget, command=abrir_ventana_clientes)
btn_clientes.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

btn_extracto = tk.Button(frame_botones, text=" Extracto", image=cargar_imagen("Extracto"), compound="left", width=ancho_widget, command=lambda: mostrar_registros(entry_cedula))
btn_extracto.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

btn_export = tk.Button(frame_botones, text=" Exportar", image=cargar_imagen("Exportar"), compound="left" , width=ancho_widget, command=join_and_export)
btn_export.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

btn_propietario = tk.Button(frame_botones, text=" Aliados", image=cargar_imagen("llave"), compound="left" , width=ancho_widget,  command=ventana_propietario)
btn_propietario.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

btn_balance = tk.Button(frame_botones, text=" Reportes Medios", image=cargar_imagen("Balance"), compound="left" , width=ancho_widget, command=mostrar_consulta_registros)
btn_balance.grid(row=2, column=2, padx=5, pady=5, sticky="ew")

btn_mora = tk.Button(frame_botones, text=" Reporte Deudas", image=cargar_imagen("Checklist"), compound="left", width=ancho_widget, command=calcular_atraso_simple)
btn_mora.grid(row=3, column=0, padx=5, pady=5, sticky="ew")

btn_blacklist = tk.Button(frame_botones, text=" Lista negra", image=cargar_imagen("blacklist"), compound="left", width=ancho_widget, command=gestionar_blacklist)
btn_blacklist.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

btn_garage = tk.Button(frame_botones, text=" Taller", image=cargar_imagen("garage"), compound="left", width=ancho_widget,command=iniciar_interfaz)
btn_garage.grid(row=3, column=2, padx=5, pady=5, sticky="ew")

btn_deudas = tk.Button(frame_botones, text=" Deudas", image=cargar_imagen("debts"), compound="left", width=ancho_widget,command=abrir_gestion_deudas)
btn_deudas.grid(row=4, column=0, padx=5, pady=5, sticky="ew")

# Frame de información (derecha)
frame_derecho = tk.Frame(frame_superior, bd=0, relief="flat", bg="#f0f0f0")
frame_derecho.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
# Expandir proporcionalmente
frame_superior.columnconfigure(1, weight=1)
frame_superior.rowconfigure(0, weight=1)
# Configurar el grid interno de frame_derecho
frame_derecho.columnconfigure(0, weight=1)  # única columna
frame_derecho.rowconfigure(0, weight=0)     # imagen (fijo)
frame_derecho.rowconfigure(1, weight=1)     # sub-frame puede expandirse si se necesita
# === Imagen ===
try:
    img = Image.open("img/Empresa.png")
    img = ImageTk.PhotoImage(img)
except Exception as e:
    print(f"Error al cargar la imagen: {e}")
    img = None

if img:
    label_imagen = tk.Label(frame_derecho, image=img, bg="#f0f0f0")
    label_imagen.grid(row=0, column=0, pady=(0, 10))
    label_imagen.image = img  # Referencia viva
# === Sub-frame debajo de la imagen ===
subframe_datos = tk.Frame(frame_derecho, bg="#f0f0f0")
subframe_datos.grid(row=1, column=0, sticky="n")
# Configurar columnas en sub-frame
subframe_datos.columnconfigure(0, weight=0)  # Label
subframe_datos.columnconfigure(1, weight=1)  # Entry (para que se estire si hay espacio)
# Elementos nuevos dentro del sub-frame


def verificar_conexion():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        return True
    except Exception:
        return False

def actualizar_estado():
    if verificar_conexion():
        estado_label.config(text="🟢 En línea", fg="green")
    else:
        estado_label.config(text="🔴 Sin conexión", fg="red")
    # Se ejecuta de nuevo en 10 segundos
    ventana.after(10000, actualizar_estado)


def filtrar_por_referencia(event):
    global datos_tree_original

    # Capturar el texto del entry y pasarlo a minúsculas
    filtro = entry_codigo.get().lower()

    # Si todavía no se ha guardado la "foto" original del Treeview, captúrala
    #if not datos_tree_original:
    #    for child in tree.get_children():
    #        datos_tree_original.append(tree.item(child)["values"])

    # Limpiar el Treeview
    for item in tree.get_children():
        tree.delete(item)

    # Si no hay filtro, restaurar todos los datos originales
    if filtro == "":
        for row in datos_tree_original:
            tree.insert("", "end", values=row)
    else:
        # Insertar solo las filas donde la columna Referencia (columna 10) coincida
        for row in datos_tree_original:
            if filtro in str(row[11]).lower():
                tree.insert("", "end", values=row)

label_codigo = tk.Label(subframe_datos, text="Filtrar Ref:", bg="#f0f0f0", font=("Arial", 10))
label_codigo.grid(row=0, column=0, sticky="e", padx=(0, 5))
entry_codigo = tk.Entry(subframe_datos, width=30)
entry_codigo.grid(row=0, column=1, sticky="we")
# Puedes ubicar esto donde quieras en tu layout
estado_label = tk.Label(subframe_datos, text="Verificando conexión...", font=("Segoe UI", 10, "bold"))
estado_label.grid(row=0, column=2 ,pady=10)
entry_codigo.bind("<Return>", filtrar_por_referencia)

def sort_treeview(column, reverse):
    """Ordena el Treeview por la columna seleccionada."""
    data = [(tree.set(item, column), item) for item in tree.get_children()]
    data.sort(reverse=reverse, key=lambda x: x[0].isdigit() and int(x[0]) or x[0])  # Convierte números antes de ordenar

    for index, (_, item) in enumerate(data):
        tree.move(item, '', index)  # Reorganiza los elementos en el Treeview

    # Alterna la dirección de ordenación
    tree.heading(column, command=lambda: sort_treeview(column, not reverse))

# Frame para el Treeview
tree_frame = tk.Frame(ventana, bd=2, relief="ridge")
tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
# Scrollbars
scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal")

# Treeview con sus columnas
tree = ttk.Treeview(tree_frame, 
                    columns=("id", "Fecha_sistema", "Fecha_registro", "Cedula", "Nombre", 
                            "Placa", "Valor", "Otros abonos", "Motivo abono", "Tipo", "Nombre_cuenta", "Referencia", "Verificada"), 
                    show="headings", 
                    yscrollcommand=scroll_y.set,
                    xscrollcommand=scroll_x.set)

# Configurar las scrollbars
scroll_y.config(command=tree.yview)
scroll_x.config(command=tree.xview)
# Posicionar los elementos en el grid
tree.grid(row=0, column=0, sticky="nsew")
scroll_y.grid(row=0, column=1, sticky="ns")
scroll_x.grid(row=1, column=0, sticky="ew")
# Permitir que el Treeview se expanda en su contenedor
tree_frame.grid_rowconfigure(0, weight=1)
tree_frame.grid_columnconfigure(0, weight=1)
# Configurar encabezados y alineación de columnas
for col in tree["columns"]:
    tree.heading(col, text=col, command=lambda c=col: sort_treeview(c, False))
    tree.column(col, anchor="center")
# Ubicar elementos en la grilla
tree.grid(row=0, column=0, sticky="nsew")
scroll_y.grid(row=0, column=1, sticky="ns")
# Configurar expansión para que se adapte correctamente
ventana.grid_rowconfigure(1, weight=1)
ventana.grid_columnconfigure(0, weight=1)
tree_frame.grid_rowconfigure(0, weight=1)
tree_frame.grid_columnconfigure(0, weight=1)

def on_double_click(event, tree):
    # Obtener el item seleccionado
    selected_item = tree.selection()
    if not selected_item:
        return

    # Obtener los valores del item
    item_values = tree.item(selected_item, "values")
    if not item_values:
        return

    # Extraer los valores
    id_registro = item_values[0]  # ID está en la primera columna
    verificada = item_values[12]  # 'Verificada' está en la última columna

    # Verificar si el estado es "NO"
    if verificada.upper() == "NO":
        confirmar = messagebox.askyesno("Confirmación", "¿Desea marcar este registro como verificado?")
        if confirmar:
            try:
                # Conectar a la base de datos y actualizar el estado
                conn = sqlite3.connect("diccionarios/base_dat.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE registros SET Verificada = 'Si' WHERE id = ?", (id_registro,))
                conn.commit()
                conn.close()

                # Actualizar el Treeview
                new_values = list(item_values)
                new_values[11] = "Si"  # Cambiar el estado en la visualización
                tree.item(selected_item, values=new_values)

                messagebox.showinfo("Éxito", "Registro actualizado correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el registro: {e}")

# Asociar el evento al Treeview
tree.bind("<Double-1>", lambda event: on_double_click(event, tree))
# Lanza verificación inicial
actualizar_estado()
ventana.mainloop()


