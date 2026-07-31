from flask import Flask, render_template, request, redirect, url_for, flash
from models import Biblioteca, Libro

app = Flask(__name__)
app.secret_key = "adriyjhulimegaclave"  # necesaria para poder usar flash()

# Cargamos la biblioteca UNA vez cuando arranca el servidor.
# a partir de aquí, cada vez que algo cambie, llamamos a biblioteca.guardar() para
# que el cambio quede escrito en el archivo JSON.
biblioteca = Biblioteca.cargar()


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


@app.route("/prestar", methods=["POST"])
def prestar():
    # request.form nos da acceso a los datos que el usuario llenó en el formulario HTML
    isbn = request.form.get("isbn")
    id_usuario = request.form.get("id_usuario")
    exito, mensaje = biblioteca.prestar_libro(isbn, id_usuario)
    if exito:
        biblioteca.guardar()  # solo guardamos en disco si el cambio fue exitoso
        flash(mensaje, "exito")
    else:
        flash(mensaje, "error")
    return redirect(url_for("catalogo"))


@app.route("/devolver", methods=["POST"])
def devolver():
    isbn = request.form.get("isbn")
    id_usuario = request.form.get("id_usuario")
    exito, mensaje = biblioteca.devolver_libro(isbn, id_usuario)
    if exito:
        biblioteca.guardar()
        flash(mensaje, "exito")
    else:
        flash(mensaje, "error")
    return redirect(url_for("catalogo"))


@app.route("/agregar_libro", methods=["POST"])
def agregar_libro():
    titulo = request.form.get("titulo")
    autor = request.form.get("autor")
    isbn = request.form.get("isbn")
    if biblioteca.buscar_libro(isbn) is not None:
        flash(f"Ya existe un libro con el ISBN {isbn}.", "error")
    else:
        nuevo_libro = Libro(titulo, autor, isbn)
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
