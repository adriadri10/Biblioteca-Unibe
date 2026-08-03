// Interactividad del catálogo:
// 1) Buscador en vivo (filtra las tarjetas mientras escribes, sin recargar).
// 2) Prestar/Devolver con fetch() para no recargar toda la página.

document.addEventListener("DOMContentLoaded", () => {
    const campoBusqueda = document.getElementById("campo-busqueda");
    const grid = document.getElementById("grid-libros");
    const sinResultados = document.getElementById("sin-resultados");

    // --- 1) Buscador en vivo ---------------------------------------------
    if (campoBusqueda) {
        campoBusqueda.addEventListener("input", () => {
            const termino = campoBusqueda.value.trim().toLowerCase();
            let visibles = 0;

            document.querySelectorAll(".tarjeta-libro").forEach((tarjeta) => {
                const titulo = tarjeta.querySelector("h3").textContent.toLowerCase();
                const autor = tarjeta.querySelector(".autor-libro").textContent.toLowerCase();
                const coincide = titulo.includes(termino) || autor.includes(termino);
                tarjeta.style.display = coincide ? "" : "none";
                if (coincide) visibles++;
            });

            sinResultados.style.display = visibles === 0 ? "block" : "none";
        });
    }

    // --- 2) Prestar / Devolver con fetch (delegación de eventos) ---------
    if (grid) {
        grid.addEventListener("click", async (evento) => {
            const boton = evento.target.closest(".btn-prestar, .btn-devolver");
            if (!boton) return;

            const tarjeta = boton.closest(".tarjeta-libro");
            const isbn = tarjeta.dataset.isbn;
            const select = tarjeta.querySelector(".selector-usuario");
            const idUsuario = select ? select.value : "";

            if (!idUsuario) {
                mostrarMensaje("Debes elegir un usuario primero.", "error");
                return;
            }

            const esPrestamo = boton.classList.contains("btn-prestar");
            const ruta = esPrestamo ? "/prestar" : "/devolver";

            const datos = new FormData();
            datos.append("isbn", isbn);
            datos.append("id_usuario", idUsuario);

            boton.disabled = true;
            try {
                const respuesta = await fetch(ruta, {
                    method: "POST",
                    headers: { "X-Requested-With": "fetch" },
                    body: datos,
                });
                const resultado = await respuesta.json();

                mostrarMensaje(resultado.mensaje, resultado.exito ? "exito" : "error");

                if (resultado.exito && resultado.libro) {
                    actualizarTarjeta(tarjeta, resultado.libro);
                }
            } catch (error) {
                mostrarMensaje("Ocurrió un error de conexión. Intenta de nuevo.", "error");
            } finally {
                boton.disabled = false;
            }
        });
    }

    // Actualiza el estado visual de una tarjeta (Disponible/Prestado y el botón)
    function actualizarTarjeta(tarjeta, libro) {
        const estado = tarjeta.querySelector(".estado-libro");
        estado.innerHTML = libro.disponible
            ? '<span class="disponible">Disponible</span>'
            : '<span class="prestado">Prestado</span>';

        const accion = tarjeta.querySelector(".accion-libro");
        const boton = accion.querySelector(".btn-prestar, .btn-devolver");
        if (boton) {
            boton.textContent = libro.disponible ? "Prestar" : "Devolver";
            boton.classList.toggle("btn-prestar", libro.disponible);
            boton.classList.toggle("btn-devolver", !libro.disponible);
        }

        const select = accion.querySelector(".selector-usuario");
        if (select) select.selectedIndex = 0;
    }
});
