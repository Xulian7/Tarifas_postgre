import tkinter as tk
from tkinter import Text
from PIL import Image, ImageTk, ImageGrab
import pytesseract

# Si usas Windows y no tienes tesseract en PATH, descomenta esta línea:
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class OCRApp:
    def __init__(self, root):
        self.root = root
        root.title("OCR desde Ctrl+V")
        root.geometry("800x600")

        self.label = tk.Label(root, text="Presiona Ctrl+V para pegar una imagen desde el portapapeles", font=("Arial", 14))
        self.label.pack(pady=10)

        self.canvas = tk.Label(root)
        self.canvas.pack()

        self.text_output = Text(root, wrap=tk.WORD, height=15)
        self.text_output.pack(fill=tk.BOTH, expand=True)

        # Ctrl+V para pegar imagen
        root.bind("<Control-v>", self.pegar_desde_portapapeles)
        root.bind("<Button-1>", lambda e: root.focus_set())

    def mostrar_imagen(self, pil_image):
        resized = pil_image.resize((400, 300))
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.configure(image=self.tk_image)

    def extraer_texto(self, pil_image):
        texto = pytesseract.image_to_string(pil_image)
        self.text_output.delete(1.0, tk.END)
        self.text_output.insert(tk.END, texto)
        self.text_output.focus_set()
        self.text_output.tag_add("sel", "1.0", "end")  # Selecciona todo el texto automáticamente

    def pegar_desde_portapapeles(self, event=None):
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                self.mostrar_imagen(img)
                self.extraer_texto(img)
            else:
                self.text_output.insert(tk.END, "\n⚠️ No hay imagen válida en el portapapeles.\n")
        except Exception as e:
            self.text_output.insert(tk.END, f"\n❌ Error al pegar: {e}\n")

# Ejecutar
if __name__ == "__main__":
    root = tk.Tk()
    app = OCRApp(root)
    root.mainloop()
