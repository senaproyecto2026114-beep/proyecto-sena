const API_URL = 'http://localhost:8000';

function verificarSesion() {
    const admin = localStorage.getItem('admin');
    if (!admin) {
        window.location.href = 'index.html';
        return null;
    }
    return JSON.parse(admin);
}

function cerrarSesion() {
    localStorage.removeItem('admin');
    window.location.href = 'index.html';
}

function formatHora(value) {
    return new Date(`1970-01-01T${value}`).toLocaleTimeString('es-ES', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
}

function pintarTabla(registros) {
    const tbody = document.getElementById('tablaHistorialBody');
    if (!registros || !registros.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="no-data">No hay registros para las fechas seleccionadas</td></tr>';
        return;
    }
    tbody.innerHTML = registros.map((r) => {
        const tipoClass = r.tipo_ingreso === 'PUNTUAL' ? 'tipo-puntual' : 'tipo-tarde';
        const tipoText = r.tipo_ingreso === 'PUNTUAL' ? 'Puntual' : 'Tarde';
        return `
            <tr>
                <td>${r.fecha}</td>
                <td>${formatHora(r.hora)}</td>
                <td>${r.nombre_completo}</td>
                <td>${r.grado}</td>
                <td>${r.dia_semana}</td>
                <td><span class="tipo-indicator ${tipoClass}">${tipoText}</span></td>
            </tr>
        `;
    }).join('');
}

async function cargarHistorial() {
    const fecha_inicio = document.getElementById('fechaInicio').value;
    const fecha_fin = document.getElementById('fechaFin').value;
    if (!fecha_inicio || !fecha_fin) {
        alert('Seleccione fecha inicio y fecha fin.');
        return;
    }
    try {
        const response = await fetch(`${API_URL}/api/registros/fecha`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fecha_inicio, fecha_fin }),
        });
        if (!response.ok) throw new Error('No se pudo cargar historial');
        const data = await response.json();
        pintarTabla(data);
    } catch (error) {
        console.error(error);
        document.getElementById('tablaHistorialBody').innerHTML = '<tr><td colspan="6" class="no-data">Error al cargar historial</td></tr>';
    }
}

async function borrarTodoHistorial() {
    const ok = confirm('¿Seguro que desea eliminar TODO el historial de asistencia? Esta acción es solo para pruebas y no se puede deshacer.');
    if (!ok) return;
    try {
        const response = await fetch(`${API_URL}/api/registros`, { method: 'DELETE' });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || 'No se pudo eliminar historial');
        alert(`Historial eliminado. Registros borrados: ${payload.registros_eliminados ?? 0}`);
        await cargarHistorial();
    } catch (error) {
        alert(error.message || 'Error al eliminar historial');
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    if (!verificarSesion()) return;
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('fechaInicio').value = hoy;
    document.getElementById('fechaFin').value = hoy;
    document.getElementById('btnFiltrar').addEventListener('click', cargarHistorial);
    document.getElementById('btnReset').addEventListener('click', async () => {
        document.getElementById('fechaInicio').value = hoy;
        document.getElementById('fechaFin').value = hoy;
        await cargarHistorial();
    });
    document.getElementById('btnBorrarHistorial').addEventListener('click', borrarTodoHistorial);
    await cargarHistorial();
});
