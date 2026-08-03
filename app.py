from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from werkzeug.security import generate_password_hash

from models import Biblioteca, Libro, Bibliotecario, Usuario, Consulta

app = Flask(__name__)
app.secret_key = "adriyjhulimegaclave"

biblioteca = Biblioteca.cargar()


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario" not in session:
            flash("Debes iniciar sesión para hacer eso.", "error")
            return redirect(url_for("login", next=request.path))
        return vista(*args, **kwargs)

    return envoltura


def admin_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if session.get("rol") != "admin":
            flash("Solo el administrador puede acceder a esta vista.", "error")
            return redirect(url_for("catalogo"))
        return vista(*args, **kwargs)

    return envoltura


def usuario_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if session.get("rol") != "usuario":
            flash("Debes iniciar sesión como usuario para entrar a tu panel.", "error")
            return redirect(url_for("login"))
        return vista(*args, **kwargs)

    return envoltura


@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario" in session:
        return redirect(url_for("catalogo"))

    if request.method == "POST":
        tipo = request.form.get("tipo", "admin")
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        if tipo == "admin":
            bibliotecario = Bibliotecario.autenticar(usuario, password)
            if bibliotecario:
                session["usuario"] = bibliotecario.usuario
                session["nombre"] = bibliotecario.nombre
                session["rol"] = "admin"
                flash(f"Bienvenida, {bibliotecario.nombre}.", "exito")
                siguiente = request.args.get("next") or url_for("catalogo")
                return redirect(siguiente)
            flash("Usuario o contraseña incorrectos para administrador.", "error")
        else:
            usuario_obj = biblioteca.buscar_usuario(usuario)
            if usuario_obj and usuario_obj.verificar_password(password):
                session["usuario"] = usuario_obj.id_usuario
                session["nombre"] = usuario_obj.nombre
                session["rol"] = "usuario"
                session["id_usuario"] = usuario_obj.id_usuario
                flash(f"Bienvenido, {usuario_obj.nombre}.", "exito")
                return redirect(url_for("mi_panel"))
            flash("Usuario o contraseña incorrectos para usuario.", "error")

    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        id_usuario = request.form.get("id_usuario", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not nombre or not id_usuario or not password:
            flash("Completa nombre, matrícula y contraseña.", "error")
            return render_template("registro.html")

        if biblioteca.buscar_usuario(id_usuario) is not None:
            flash("Ese usuario ya está registrado.", "error")
            return render_template("registro.html")

        nuevo_usuario = Usuario(
            nombre=nombre,
            id_usuario=id_usuario,
            email=email,
            password_hash=generate_password_hash(password),
            rol="usuario",
        )
        biblioteca.agregar_usuario(nuevo_usuario)
        biblioteca.guardar()
        flash("Registro exitoso. Ahora puedes iniciar sesión como usuario.", "exito")
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "exito")
    return redirect(url_for("login"))


@app.route("/")
def index():
    return redirect(url_for("catalogo"))


@app.route("/catalogo")
def catalogo():
    return render_template(
        "catalogo.html",
        libros=biblioteca.catalogo,
        usuarios=biblioteca.usuarios,
    )


@app.route("/api/buscar")
def api_buscar():
    termino = request.args.get("q", "").strip().lower()
    resultado = []
    for libro in biblioteca.catalogo:
        if termino in libro.titulo.lower() or termino in libro.autor.lower():
            resultado.append(libro.to_dict())
    return jsonify(resultado)


@app.route("/prestar", methods=["POST"])
@login_requerido
def prestar():
    isbn = request.form.get("isbn")
    id_usuario = request.form.get("id_usuario") or session.get("id_usuario")
    dias = request.form.get("dias", "7")
    exito, mensaje = biblioteca.prestar_libro(isbn, id_usuario, dias=dias)
    if exito:
        biblioteca.guardar()

    if request.headers.get("X-Requested-With") == "fetch":
        libro = biblioteca.buscar_libro(isbn)
        return jsonify(
            exito=exito,
            mensaje=mensaje,
            libro=libro.to_dict() if libro else None,
        )

    flash(mensaje, "exito" if exito else "error")
    return redirect(url_for("catalogo"))


@app.route("/devolver", methods=["POST"])
@login_requerido
def devolver():
    isbn = request.form.get("isbn")
    id_usuario = request.form.get("id_usuario") or session.get("id_usuario")
    exito, mensaje = biblioteca.devolver_libro(isbn, id_usuario)
    if exito:
        biblioteca.guardar()

    if request.headers.get("X-Requested-With") == "fetch":
        libro = biblioteca.buscar_libro(isbn)
        return jsonify(
            exito=exito,
            mensaje=mensaje,
            libro=libro.to_dict() if libro else None,
        )

    flash(mensaje, "exito" if exito else "error")
    return redirect(url_for("catalogo"))


@app.route("/agregar_libro", methods=["POST"])
@admin_requerido
def agregar_libro():
    titulo = request.form.get("titulo")
    autor = request.form.get("autor")
    isbn = request.form.get("isbn")
    imagen = request.form.get("imagen") or None
    if biblioteca.buscar_libro(isbn) is not None:
        flash(f"Ya existe un libro con el ISBN {isbn}.", "error")
    else:
        nuevo_libro = Libro(titulo, autor, isbn, imagen=imagen)
        biblioteca.agregar_libro(nuevo_libro)
        biblioteca.guardar()
        flash(f"Libro '{titulo}' agregado al catálogo.", "exito")
    return redirect(url_for("catalogo"))


@app.route("/usuarios")
@admin_requerido
def usuarios():
    usuarios_con_libros = []
    for usuario in biblioteca.usuarios:
        titulos = []
        for isbn in usuario.libros_prestados:
            libro = biblioteca.buscar_libro(isbn)
            if libro:
                titulos.append(libro.titulo)
        usuarios_con_libros.append((usuario, titulos))
    return render_template(
        "usuarios.html",
        usuarios_con_libros=usuarios_con_libros,
        consultas=biblioteca.consultas,
    )


@app.route("/mi_panel")
@usuario_requerido
def mi_panel():
    usuario_actual = biblioteca.buscar_usuario(session.get("id_usuario"))
    return render_template(
        "mi_panel.html",
        usuario=usuario_actual,
        prestamos=usuario_actual.prestamos if usuario_actual else [],
        consultas=biblioteca.consultas,
    )


@app.route("/consultar", methods=["POST"])
@usuario_requerido
def consultar():
    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip()
    mensaje = request.form.get("mensaje", "").strip()
    tipo = request.form.get("tipo", "consulta")

    if not nombre or not mensaje:
        flash("Escribe tu nombre y tu mensaje.", "error")
        return redirect(url_for("mi_panel"))

    biblioteca.agregar_consulta(
        Consulta(nombre=nombre, email=email, mensaje=mensaje, tipo=tipo)
    )
    biblioteca.guardar()
    etiqueta = "sugerencia" if tipo == "sugerencia" else "consulta"
    flash(f"Tu {etiqueta} fue enviada al administrador.", "exito")
    return redirect(url_for("mi_panel"))


if __name__ == "__main__":
    app.run(debug=True)
