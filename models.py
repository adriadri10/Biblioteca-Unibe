import json
import os
from datetime import date, timedelta
from werkzeug.security import check_password_hash, generate_password_hash

RUTA_DATOS = os.path.join(os.path.dirname(__file__), "data", "biblioteca.json")
RUTA_BIBLIOTECARIOS = os.path.join(
    os.path.dirname(__file__), "data", "bibliotecarios.json"
)

IMAGEN_POR_DEFECTO = "https://via.placeholder.com/200x300.png?text=Sin+portada"


class Libro:
    def __init__(self, titulo, autor, isbn, disponible=True, imagen=None):
        self.titulo = titulo
        self.autor = autor
        self.isbn = isbn
        self.disponible = disponible
        self.imagen = imagen if imagen else IMAGEN_POR_DEFECTO

    def prestar(self):
        if self.disponible:
            self.disponible = False
            return True
        return False

    def devolver(self):
        self.disponible = True

    def __str__(self):
        estado = "Disponible" if self.disponible else "Prestado"
        return f"{self.titulo} - {self.autor} (ISBN: {self.isbn}) - Estado: {estado}"

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
        return Libro(
            d["titulo"],
            d["autor"],
            d["isbn"],
            d["disponible"],
            d.get("imagen"),
        )


class Consulta:
    def __init__(self, nombre, email, mensaje, fecha=None, estado="nuevo", tipo="consulta"):
        self.nombre = nombre
        self.email = email
        self.mensaje = mensaje
        self.fecha = fecha or date.today().isoformat()
        self.estado = estado
        self.tipo = tipo

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "email": self.email,
            "mensaje": self.mensaje,
            "fecha": self.fecha,
            "estado": self.estado,
            "tipo": self.tipo,
        }

    @staticmethod
    def from_dict(d):
        return Consulta(
            d.get("nombre", ""),
            d.get("email", ""),
            d.get("mensaje", ""),
            d.get("fecha"),
            d.get("estado", "nuevo"),
            d.get("tipo", "consulta"),
        )


class Usuario:
    def __init__(
        self,
        nombre,
        id_usuario,
        libros_prestados=None,
        email=None,
        password_hash=None,
        rol="usuario",
        prestamos=None,
    ):
        self.nombre = nombre
        self.id_usuario = id_usuario
        self.email = email or ""
        self.password_hash = password_hash
        self.rol = rol
        self.libros_prestados = libros_prestados if libros_prestados is not None else []
        self.prestamos = prestamos if prestamos is not None else []

    def verificar_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __str__(self):
        return (
            f"Usuario: {self.nombre} - Matrícula: {self.id_usuario} - "
            f"Libros en préstamo: {len(self.libros_prestados)}"
        )

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "id_usuario": self.id_usuario,
            "email": self.email,
            "password_hash": self.password_hash,
            "rol": self.rol,
            "libros_prestados": self.libros_prestados,
            "prestamos": self.prestamos,
        }

    @staticmethod
    def from_dict(d):
        return Usuario(
            d["nombre"],
            d["id_usuario"],
            d.get("libros_prestados", []),
            d.get("email"),
            d.get("password_hash"),
            d.get("rol", "usuario"),
            d.get("prestamos", []),
        )

    @staticmethod
    def autenticar(id_usuario, password):
        for usuario in Biblioteca.cargar().usuarios:
            if usuario.id_usuario == id_usuario:
                return usuario if usuario.verificar_password(password) else None
        return None


class Bibliotecario:
    def __init__(self, usuario, nombre, password_hash):
        self.usuario = usuario
        self.nombre = nombre
        self.password_hash = password_hash

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def cargar_todos():
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
        for b in Bibliotecario.cargar_todos():
            if b.usuario == usuario:
                return b if b.verificar_password(password) else None
        return None


class Biblioteca:
    def __init__(self, nombre):
        self.nombre = nombre
        self.catalogo = []
        self.usuarios = []
        self.consultas = []

    def agregar_libro(self, libro):
        self.catalogo.append(libro)

    def buscar_libro(self, isbn):
        for libro in self.catalogo:
            if libro.isbn == isbn:
                return libro
        return None

    def agregar_usuario(self, usuario):
        self.usuarios.append(usuario)

    def buscar_usuario(self, id_usuario):
        for usuario in self.usuarios:
            if usuario.id_usuario == id_usuario:
                return usuario
        return None

    def validar_dias(self, dias):
        try:
            dias_int = int(dias)
        except (TypeError, ValueError):
            return False, "Los días deben ser un número válido."
        if dias_int < 3 or dias_int > 30:
            return False, "El préstamo debe estar entre 3 y 30 días."
        return True, dias_int

    def prestar_libro(self, isbn, id_usuario, dias=7):
        libro = self.buscar_libro(isbn)
        usuario = self.buscar_usuario(id_usuario)
        if libro is None or usuario is None:
            return False, "Libro o usuario no encontrado."
        if not libro.disponible:
            return False, f"El libro '{libro.titulo}' no está disponible."

        valido, respuesta = self.validar_dias(dias)
        if not valido:
            return False, respuesta

        libro.prestar()
        usuario.libros_prestados.append(isbn)
        fecha_inicio = date.today()
        fecha_fin = fecha_inicio + timedelta(days=int(respuesta))
        usuario.prestamos.append(
            {
                "isbn": isbn,
                "dias": int(respuesta),
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
            }
        )
        return True, f"Libro '{libro.titulo}' prestado a {usuario.nombre} por {respuesta} días."

    def devolver_libro(self, isbn, id_usuario):
        libro = self.buscar_libro(isbn)
        usuario = self.buscar_usuario(id_usuario)
        if libro is None or usuario is None:
            return False, "Libro o usuario no encontrado."
        if isbn not in usuario.libros_prestados:
            return False, "Este usuario no tiene registrado ese libro."
        libro.devolver()
        usuario.libros_prestados.remove(isbn)
        usuario.prestamos = [
            prestamo for prestamo in usuario.prestamos if prestamo.get("isbn") != isbn
        ]
        return True, f"Libro '{libro.titulo}' devuelto correctamente."

    def agregar_consulta(self, consulta):
        self.consultas.append(consulta)

    def guardar(self):
        datos = {
            "nombre": self.nombre,
            "catalogo": [libro.to_dict() for libro in self.catalogo],
            "usuarios": [usuario.to_dict() for usuario in self.usuarios],
            "consultas": [consulta.to_dict() for consulta in self.consultas],
        }
        os.makedirs(os.path.dirname(RUTA_DATOS), exist_ok=True)
        with open(RUTA_DATOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)

    @staticmethod
    def cargar():
        if not os.path.exists(RUTA_DATOS):
            return Biblioteca("Biblioteca UNIBE")
        with open(RUTA_DATOS, "r", encoding="utf-8") as f:
            datos = json.load(f)

        bib = Biblioteca(datos["nombre"])
        bib.catalogo = [Libro.from_dict(d) for d in datos["catalogo"]]
        bib.usuarios = [Usuario.from_dict(d) for d in datos["usuarios"]]
        bib.consultas = [Consulta.from_dict(d) for d in datos.get("consultas", [])]
        return bib
