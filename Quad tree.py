import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageTk
import tkinter as tk
from tkinter import filedialog
import pickle

MAX_DEPTH = 8
DETAIL_THRESHOLD = 13
SIZE_MULT = 1

# Función para obtener el color promedio de una imagen
def color_promedio(imagen):
    imagen_arr = np.asarray(imagen)
    avg_color_per_row = np.average(imagen_arr, axis=0)
    avg_color = np.average(avg_color_per_row, axis=0)
    return (int(avg_color[0]), int(avg_color[1]), int(avg_color[2]))

# Función para calcular el promedio ponderado de un histograma
def promedio_ponderado(hist):
    total = sum(hist)
    error = value = 0
    if total > 0:
        value = sum(i * x for i, x in enumerate(hist)) / total
        error = sum(x * (value - i) ** 2 for i, x in enumerate(hist)) / total
        error = error ** 0.5
    return error

# Función para calcular el nivel de detalle de una imagen
def obtener_detalle(hist):
    red_detail = promedio_ponderado(hist[:256])
    green_detail = promedio_ponderado(hist[256:512])
    blue_detail = promedio_ponderado(hist[512:768])
    detail_intensity = red_detail * 0.2989 + green_detail * 0.5870 + blue_detail * 0.1140
    return detail_intensity

# Clase para representar un cuadrante
class Cuadrante():
    def __init__(self, imagen, bbox, profundidad):
        self.bbox = bbox
        self.profundidad = profundidad
        self.children = None
        self.leaf = False
        imagen = imagen.crop(bbox)
        hist = imagen.histogram()
        self.detalle = obtener_detalle(hist)
        self.color = color_promedio(imagen)

    def dividir_cuadrante(self, imagen):
        left, top, width, height = self.bbox
        middle_x = left + (width - left) / 2
        middle_y = top + (height - top) / 2
        upper_left = Cuadrante(imagen, (left, top, middle_x, middle_y), self.profundidad+1)
        upper_right = Cuadrante(imagen, (middle_x, top, width, middle_y), self.profundidad+1)
        bottom_left = Cuadrante(imagen, (left, middle_y, middle_x, height), self.profundidad+1)
        bottom_right = Cuadrante(imagen, (middle_x, middle_y, width, height), self.profundidad+1)
        self.children = [upper_left, upper_right, bottom_left, bottom_right]

# Clase para representar el QuadTree
class QuadTree():
    def __init__(self, imagen):
        self.width, self.height = imagen.size
        self.max_depth = 0
        self.imagen_original = imagen
        self.iniciar(imagen)

    def iniciar(self, imagen):
        self.root = Cuadrante(imagen, imagen.getbbox(), 0)
        self.construir(self.root, imagen)

    def construir(self, root, imagen):
        if root.profundidad >= MAX_DEPTH or root.detalle <= DETAIL_THRESHOLD:
            if root.profundidad > self.max_depth:
                self.max_depth = root.profundidad
            root.leaf = True
            return
        root.dividir_cuadrante(imagen)
        for children in root.children:
            self.construir(children, imagen)

    def crear_imagen(self, profundidad_personalizada, mostrar_lineas=False):
        imagen = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(imagen)
        draw.rectangle((0, 0, self.width, self.height), (0, 0, 0))
        cuadrantes_hoja = self.obtener_cuadrantes_hoja(profundidad_personalizada)
        for cuadrante in cuadrantes_hoja:
            if mostrar_lineas:
                draw.rectangle(cuadrante.bbox, cuadrante.color, outline=(0, 0, 0))
            else:
                draw.rectangle(cuadrante.bbox, cuadrante.color)
        return imagen

    def obtener_cuadrantes_hoja(self, profundidad):
        if profundidad > self.max_depth:
            raise ValueError('Se dio una profundidad mayor que la profundidad máxima del árbol')
        cuadrantes = []
        self.busqueda_recursiva(self, self.root, profundidad, cuadrantes.append)
        return cuadrantes

    def busqueda_recursiva(self, arbol, cuadrante, profundidad_maxima, agregar_hoja):
        if cuadrante.leaf == True or cuadrante.profundidad == profundidad_maxima:
            agregar_hoja(cuadrante)
        elif cuadrante.children != None:
            for child in cuadrante.children:
                self.busqueda_recursiva(arbol, child, profundidad_maxima, agregar_hoja)

    def crear_gif(self, nombre_archivo, duracion=1000, loop=0, mostrar_lineas=False):
        gif = []
        imagen_final = self.crear_imagen(self.max_depth, mostrar_lineas=mostrar_lineas)
        for i in range(self.max_depth):
            imagen = self.crear_imagen(i, mostrar_lineas=mostrar_lineas)
            gif.append(imagen)
        for _ in range(4):
            gif.append(imagen_final)
        gif[0].save(
            nombre_archivo,
            save_all=True,
            append_images=gif[1:],
            duration=duracion, loop=loop)
        return gif

    def guardar_compresion(self, filename):
        with open(filename, 'wb') as file:
            pickle.dump(self, file)

    @staticmethod
    def cargar_compresion(filename):
        with open(filename, 'rb') as file:
            return pickle.load(file)

# Clase para la aplicación de la GUI
class QuadTreeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Compresión de Imagen con QuadTree")
        
        self.boton_cargar = tk.Button(root, text="Cargar Imagen", command=self.cargar_imagen)
        self.boton_cargar.pack()
        
        self.boton_cargar_comprimida = tk.Button(root, text="Cargar Imagen Comprimida", command=self.cargar_imagen_comprimida)
        self.boton_cargar_comprimida.pack()

        self.label_profundidad = tk.Label(root, text="Profundidad:")
        self.label_profundidad.pack()
        
        self.scale_profundidad = tk.Scale(root, from_=0, to=MAX_DEPTH, orient=tk.HORIZONTAL)
        self.scale_profundidad.pack()
        
        self.var_mostrar_lineas = tk.IntVar()
        self.check_mostrar_lineas = tk.Checkbutton(root, text="Mostrar Líneas", variable=self.var_mostrar_lineas)
        self.check_mostrar_lineas.pack()
        
        self.boton_comprimir = tk.Button(root, text="Comprimir Imagen", command=self.comprimir_imagen)
        self.boton_comprimir.pack()
        
        self.boton_guardar_comprimida = tk.Button(root, text="Guardar Imagen Comprimida", command=self.guardar_imagen_comprimida)
        self.boton_guardar_comprimida.pack()

        self.boton_descomprimir = tk.Button(root, text="Descomprimir Imagen", command=self.descomprimir_imagen)
        self.boton_descomprimir.pack()

        self.label_imagen_original = tk.Label(root)
        self.label_imagen_original.pack(side=tk.LEFT)
        
        self.label_imagen_comprimida = tk.Label(root)
        self.label_imagen_comprimida.pack(side=tk.RIGHT)
        
        self.boton_guardar_gif = tk.Button(root, text="Guardar GIF", command=self.guardar_gif)
        self.boton_guardar_gif.pack()

        self.label_gif = tk.Label(root)
        self.label_gif.pack(side=tk.BOTTOM)

    def cargar_imagen(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.imagen = Image.open(file_path)
            self.imagen = self.imagen.resize((self.imagen.size[0] * SIZE_MULT, self.imagen.size[1] * SIZE_MULT))
            self.quadtree = QuadTree(self.imagen)
            self.mostrar_imagen_original(self.imagen)

    def cargar_imagen_comprimida(self):
        file_path = filedialog.askopenfilename(filetypes=[("QuadTree files", "*.qt")])
        if file_path:
            self.quadtree = QuadTree.cargar_compresion(file_path)
            imagen_comprimida = self.quadtree.crear_imagen(self.scale_profundidad.get(), mostrar_lineas=self.var_mostrar_lineas.get() == 1)
            self.mostrar_imagen_comprimida(imagen_comprimida)
            self.mostrar_imagen_original(self.quadtree.imagen_original)

    def comprimir_imagen(self):
        if hasattr(self, 'quadtree'):
            profundidad = self.scale_profundidad.get()
            mostrar_lineas = self.var_mostrar_lineas.get() == 1
            imagen_comprimida = self.quadtree.crear_imagen(profundidad, mostrar_lineas=mostrar_lineas)
            self.mostrar_imagen_comprimida(imagen_comprimida)
    
    def guardar_imagen_comprimida(self):
        if hasattr(self, 'quadtree'):
            file_path = filedialog.asksaveasfilename(defaultextension=".qt", filetypes=[("QuadTree files", "*.qt")])
            if file_path:
                self.quadtree.guardar_compresion(file_path)

    def descomprimir_imagen(self):
        if hasattr(self, 'quadtree'):
            imagen_descomprimida = self.quadtree.crear_imagen(MAX_DEPTH, mostrar_lineas=self.var_mostrar_lineas.get() == 1)
            self.mostrar_imagen_comprimida(imagen_descomprimida)

    def guardar_gif(self):
        if hasattr(self, 'quadtree'):
            file_path = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF files", "*.gif")])
            if file_path:
                gif = self.quadtree.crear_gif(file_path, mostrar_lineas=self.var_mostrar_lineas.get() == 1)
                self.mostrar_gif(gif)

    def mostrar_imagen_original(self, imagen):
        imagen_tk = ImageTk.PhotoImage(imagen)
        self.label_imagen_original.configure(image=imagen_tk)
        self.label_imagen_original.image = imagen_tk

    def mostrar_imagen_comprimida(self, imagen):
        imagen_tk = ImageTk.PhotoImage(imagen)
        self.label_imagen_comprimida.configure(image=imagen_tk)
        self.label_imagen_comprimida.image = imagen_tk

    def mostrar_gif(self, gif):
        gif_frames = [ImageTk.PhotoImage(img) for img in gif]
        def animar(counter):
            self.label_gif.configure(image=gif_frames[counter])
            self.root.after(100, animar, (counter + 1) % len(gif_frames))
        animar(0)

if __name__ == '__main__':
    root = tk.Tk()
    app = QuadTreeApp(root)
    root.mainloop()
