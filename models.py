import json
import os
from werkzeug.security import check_password_hash

# Con lo del os construimos la ruta hasta los archivos JSON sin importar en qué
# computadora se ejecute el programa
RUTA_DATOS = os.path.join(os.path.dirname(__file__), "data", "biblioteca.json")
RUTA_BIBLIOTECARIOS = os.path.join(
    os.path.dirname(__file__), "data", "bibliotecarios.json"
)

# Imagen que se usa cuando un libro no tiene portada asignada
IMAGEN_POR_DEFECTO = "https://via.placeholder.com/200x300.png?text=Sin+portada"


# Clase que representa un libro de la biblioteca
class Libro:
    def __init__(self, titulo, autor, isbn, disponible=True, imagen=None):
        self.titulo = titulo
        self.autor = autor
        self.isbn = isbn
        self.disponible = disponible
        # Si no nos pasan una imagen, usamos una portada genérica
        self.imagen = imagen if imagen else IMAGEN_POR_DEFECTO

    def prestar(self):
        # Solo prestamos el libro si está disponible
        if self.disponible:
            self.disponible = False
            return True
        return False

    def devolver(self):
        # Al devolverlo, vuelve a estar disponible yey
        self.disponible = True

    def __str__(self):
        estado = "Disponible" if self.disponible else "Prestado"
        return f"{self.titulo} - {self.autor} (ISBN: {self.isbn}) - Estado: {estado}"

    # métodos que convierten el objeto en un formato que JSON puede guardar y recuperar
    # después.
    def to_dict(self):
        return {
            "titulo": self.titulo,
            "autor": self.autor,
            "isbn": self.isbn,
            "disponible": self.disponible,
            "imagen": self.imagen,
        }

    @staticmethod
    def from_dict(d):
        # va a reconstruir un objeto Libro desde el JSON
        return Libro(
            d["titulo"],
            d["autor"],
            d["isbn"],
            d["disponible"],
            d.get("imagen"),
        )


# Clase que representa un usuario registrado (los que piden prestados los libros)
class Usuario:
    def __init__(self, nombre, id_usuario, libros_prestados=None):
        self.nombre = nombre
        self.id_usuario = id_usuario
        # Guardamos únicamente los ISBN de los libros prestados, no los objetos
        # completos
        self.libros_prestados = (
            libros_prestados if libros_prestados is not None else []
        )

    def __str__(self):
        return (
            f"Usuario: {self.nombre} - Matrícula: {self.id_usuario} - "
            f"Libros en préstamo: {len(self.libros_prestados)}"
        )

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "id_usuario": self.id_usuario,
            "libros_prestados": self.libros_prestados,
        }

    @staticmethod
    def from_dict(d):
        # Reconstruye un usuario desde el JSON
        return Usuario(d["nombre"], d["id_usuario"], d["libros_prestados"])


# Clase que representa a un bibliotecario (personal que puede iniciar sesión
# para administrar el catálogo)
class Bibliotecario:
    def __init__(self, usuario, nombre, password_hash):
        self.usuario = usuario
        self.nombre = nombre
        self.password_hash = password_hash

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def cargar_todos():
        """Lee data/bibliotecarios.json y devuelve una lista de Bibliotecario."""
        if not os.path.exists(RUTA_BIBLIOTECARIOS):
            return []
        with open(RUTA_BIBLIOTECARIOS, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return [
            Bibliotecario(b["usuario"], b["nombre"], b["password_hash"])
            for b in datos.get("bibliotecarios", [])
        ]

    @staticmethod
    def autenticar(usuario, password):
        """Busca al bibliotecario por su usuario y valida la contraseña."""
        for b in Bibliotecario.cargar_todos():
            if b.usuario == usuario:
                return b if b.verificar_password(password) else None
        return None


# Lógica principal de la biblioteca. También se encarga de guardar y cargar los datos
class Biblioteca:
    def __init__(self, nombre):
        self.nombre = nombre
        self.catalogo = []  # Lista de objetos Libro
        self.usuarios = []  # Lista de objetos Usuario

    # Métodos principales
    def agregar_libro(self, libro):
        self.catalogo.append(libro)

    # busca un libro usando su ISBN
    def buscar_libro(self, isbn):
        for libro in self.catalogo:
            if libro.isbn == isbn:
                return libro
        return None

    def agregar_usuario(self, usuario):
        self.usuarios.append(usuario)

    # busca un usuario por su matrícula o ID
    def buscar_usuario(self, id_usuario):
        for usuario in self.usuarios:
            if usuario.id_usuario == id_usuario:
                return usuario
        return None

    # intenta prestar un libro a un usuario
    def prestar_libro(self, isbn, id_usuario):
        libro = self.buscar_libro(isbn)
        usuario = self.buscar_usuario(id_usuario)
        if libro is None or usuario is None:
            return False, "Libro o usuario no encontrado."
        if not libro.disponible:
            return False, f"El libro '{libro.titulo}' no está disponible."
        libro.prestar()
        usuario.libros_prestados.append(isbn)
        return True, f"Libro '{libro.titulo}' prestado a {usuario.nombre}."

    # Devuelve un libro que estaba prestado
    def devolver_libro(self, isbn, id_usuario):
        libro = self.buscar_libro(isbn)
        usuario = self.buscar_usuario(id_usuario)
        if libro is None or usuario is None:
            return False, "Libro o usuario no encontrado."
        if isbn not in usuario.libros_prestados:
            return False, "Este usuario no tiene registrado ese libro."
        libro.devolver()
        usuario.libros_prestados.remove(isbn)
        return True, f"Libro '{libro.titulo}' devuelto correctamente."

    # Métodos para guardar y cargar datos
    def guardar(self):
        """Convierte los objetos en diccionarios y los guarda en el archivo JSON."""
        datos = {
            "nombre": self.nombre,
            "catalogo": [libro.to_dict() for libro in self.catalogo],
            "usuarios": [usuario.to_dict() for usuario in self.usuarios],
        }
        # Si la carpeta data no existe, la va a crear automáticamente
        os.makedirs(os.path.dirname(RUTA_DATOS), exist_ok=True)
        with open(RUTA_DATOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)

    @staticmethod
    def cargar():
        """Lee el archivo JSON y reconstruye la biblioteca."""
        # si todavía no existe el archivo, empezamos con una biblioteca vacía
        if not os.path.exists(RUTA_DATOS):
            return Biblioteca("Biblioteca UNIBE")
        with open(RUTA_DATOS, "r", encoding="utf-8") as f:
            datos = json.load(f)

        # aquí Flask/Python vuelve a crear los objetos usando la información guardada
        # en el JSON
        bib = Biblioteca(datos["nombre"])
        bib.catalogo = [Libro.from_dict(d) for d in datos["catalogo"]]
        bib.usuarios = [Usuario.from_dict(d) for d in datos["usuarios"]]
        return bib
