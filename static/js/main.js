// Este script se carga en todas las páginas (lo incluye base.html).
// Su trabajo es hacer que los mensajes de éxito/error desaparezcan
// solos después de unos segundos, para que la página se sienta más viva.

function iniciarDesvanecimientoMensajes() {
    const mensajes = document.querySelectorAll("#mensajes-contenedor .mensaje");
    mensajes.forEach((mensaje) => {
        setTimeout(() => {
            mensaje.style.opacity = "0";
            setTimeout(() => mensaje.remove(), 600);
        }, 3500);
    });
}

// Muestra un mensaje nuevo dentro del contenedor (usado por las respuestas AJAX)
function mostrarMensaje(texto, categoria) {
    const contenedor = document.getElementById("mensajes-contenedor");
    if (!contenedor) return;

    const parrafo = document.createElement("p");
    parrafo.className = `mensaje ${categoria}`;
    parrafo.textContent = texto;
    contenedor.appendChild(parrafo);

    setTimeout(() => {
        parrafo.style.opacity = "0";
        setTimeout(() => parrafo.remove(), 600);
    }, 3500);
}

document.addEventListener("DOMContentLoaded", iniciarDesvanecimientoMensajes);
