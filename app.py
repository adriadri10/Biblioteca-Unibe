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

from models import Biblioteca, Libro, Bibliotecario

app = Flask(__name__)
app.secret_key = "adriyjhulimegaclave"  # necesaria para poder usar flash() y session

# Cargamos la biblioteca UNA vez cuando arranca el servidor.
# a partir de aquí, cada vez que algo cambie, llamamos a biblioteca.guardar() para
# que el cambio quede escrito en el archivo JSON.
biblioteca = Biblioteca.cargar()


# ---------------------------------------------------------------------------
# LOGIN: decorador que protege las rutas que solo puede usar el bibliotecario
# ---------------------------------------------------------------------------
def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario" not in session:
            flash("Debes iniciar sesión para hacer eso.", "error")
            return redirect(url_for("login", next=request.path))
        return vista(*args, **kwargs)

    return envoltura


@app.route("/login", methods=["GET", "POST"])
def login():
    # si ya inició sesión, lo mandamos directo al catálogo
    if "usuario" in session:
        return redirect(url_for("catalogo"))

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        bibliotecario = Bibliotecario.autenticar(usuario, password)
        if bibliotecario:
            # guardamos el usuario en la sesión (cookie firmada del lado del cliente)
            session["usuario"] = bibliotecario.usuario
            session["nombre"] = bibliotecario.nombre
            flash(f"Bienvenida, {bibliotecario.nombre}.", "exito")
            siguiente = request.args.get("next") or url_for("catalogo")
            return redirect(siguiente)
        flash("Usuario o contraseña incorrectos.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "exito")
    return redirect(url_for("login"))


@app.route("/")
def index():
    # Redirige la página raíz directo al catálogo
    return redirect(url_for("catalogo"))


@app.route("/catalogo")
def catalogo():
    # render_template busca el archivo dentro de la carpeta templates/
    # y le metemos la lista de libros y usuarios para poder usarla en el HTML
    return render_template(
        "catalogo.html",
        libros=biblioteca.catalogo,
        usuarios=biblioteca.usuarios,
    )


# ---------------------------------------------------------------------------
# Endpoint AJAX: filtra el catálogo por título/autor sin recargar la página.
# Devuelve JSON que el JavaScript del catálogo usa para redibujar la tabla.
# ---------------------------------------------------------------------------
@app.route("/api/buscar")
def api_buscar():
    termino = request.args.get("q", "").strip().lower()
    resultado = []
    for libro in biblioteca.catalogo:
        if termino in libro.titulo.lower() or termino in libro.autor.lower():
            resultado.append(libro.to_dict())
    return jsonify(resultado)


# ---------------------------------------------------------------------------
# Préstamo y devolución ahora responden en JSON para poder actualizarse con
# fetch() desde el catálogo (más interactivo, sin recargar toda la página).
# Requieren sesión iniciada.
# ---------------------------------------------------------------------------
@app.route("/prestar", methods=["POST"])
@login_requerido
def prestar():
    isbn = request.form.get("isbn")
    id_usuario = request.form.get("id_usuario")
    exito, mensaje = biblioteca.prestar_libro(isbn, id_usuario)
    if exito:
        biblioteca.guardar()  # solo guardamos en disco si el cambio fue exitoso

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
    id_usuario = request.form.get("id_usuario")
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
@login_requerido
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
def usuarios():
    # Para cada usuario, buscamos los títulos de sus libros prestados (no solo el
    # ISBN) para que se vea más claro en el HTML
    usuarios_con_libros = []
    for usuario in biblioteca.usuarios:
        titulos = []
        for isbn in usuario.libros_prestados:
            libro = biblioteca.buscar_libro(isbn)
            if libro:
                titulos.append(libro.titulo)
        usuarios_con_libros.append((usuario, titulos))
    return render_template("usuarios.html", usuarios_con_libros=usuarios_con_libros)


if __name__ == "__main__":
    app.run(debug=True)
