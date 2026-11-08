const API_URL = 'http://localhost:8000';
let estudiantes = [];

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

function getFiltros() {
    return {
        fecha_inicio: document.getElementById('fechaInicio').value,
        fecha_fin: document.getElementById('fechaFin').value,
        estudiante_id: document.getElementById('estudianteSelect').value,
    };
}

function actualizarEstadoBotonPdf() {
    const { estudiante_id } = getFiltros();
    const btn = document.getElementById('btnGenerarReporte');
    const titulo = document.getElementById('tituloSeleccion');
    if (!estudiante_id) {
        btn.disabled = true;
        titulo.textContent = 'Selecciona un estudiante para generar reporte PDF';
        return;
    }
    const est = estudiantes.find((e) => String(e.id) === String(estudiante_id));
    btn.disabled = false;
    titulo.textContent = `Estudiante seleccionado: ${est ? est.nombre_completo : estudiante_id}`;
}

async function cargarEstudiantes() {
    const response = await fetch(`${API_URL}/api/estudiantes`);
    if (!response.ok) throw new Error('No se pudo cargar estudiantes');
    estudiantes = await response.json();
    const select = document.getElementById('estudianteSelect');
    const opts = ['<option value="">Todos los estudiantes</option>']
        .concat(
            estudiantes.map((e) => `<option value="${e.id}">${e.nombre_completo} (${e.grado})</option>`)
        );
    select.innerHTML = opts.join('');
    actualizarEstadoBotonPdf();
}

async function cargarReporte() {
    const tbody = document.getElementById('tablaReportesBody');
    const { fecha_inicio, fecha_fin, estudiante_id } = getFiltros();
    if (!fecha_inicio || !fecha_fin) {
        alert('Debes seleccionar fecha inicio y fecha fin.');
        return;
    }
    try {
        const response = await fetch(`${API_URL}/api/registros/fecha`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fecha_inicio, fecha_fin }),
        });
        if (!response.ok) throw new Error('No se pudo cargar registros');
        const registros = await response.json();
        const tardanzas = registros.filter((r) => {
            const byTipo = r.tipo_ingreso === 'TARDE';
            const byEst = !estudiante_id || String(r.estudiante_id) === String(estudiante_id);
            return byTipo && byEst;
        });
        if (!tardanzas.length) {
            tbody.innerHTML = '<tr><td colspan="6">No hay llegadas tarde para el filtro seleccionado.</td></tr>';
            return;
        }
        tbody.innerHTML = tardanzas.map((r) => `
            <tr>
                <td>${r.fecha}</td>
                <td>${formatHora(r.hora)}</td>
                <td>${r.nombre_completo}</td>
                <td>${r.grado}</td>
                <td>${r.dia_semana}</td>
                <td><span class="chip-tarde">Tarde</span></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error(error);
        tbody.innerHTML = '<tr><td colspan="6">Error al cargar reportes.</td></tr>';
    }
}

async function generarReportePdf() {
    const { fecha_inicio, fecha_fin, estudiante_id } = getFiltros();
    if (!estudiante_id) {
        alert('Selecciona un estudiante para generar su reporte.');
        return;
    }
    const params = new URLSearchParams({
        fecha_inicio,
        fecha_fin,
    });
    const url = `${API_URL}/api/estudiante/${estudiante_id}/pdf-tardanzas?${params.toString()}`;
    const response = await fetch(url);
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'No se pudo generar el PDF');
    }
    const blob = await response.blob();
    const link = document.createElement('a');
    const tmp = window.URL.createObjectURL(blob);
    link.href = tmp;
    link.download = `reporte_tardanzas_${estudiante_id}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(tmp);
}

document.addEventListener('DOMContentLoaded', async () => {
    if (!verificarSesion()) return;
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('fechaInicio').value = hoy;
    document.getElementById('fechaFin').value = hoy;
    await cargarEstudiantes();
    await cargarReporte();
    document.getElementById('btnFiltrar').addEventListener('click', cargarReporte);
    document.getElementById('estudianteSelect').addEventListener('change', async () => {
        actualizarEstadoBotonPdf();
        await cargarReporte();
    });
    document.getElementById('btnGenerarReporte').addEventListener('click', async () => {
        try {
            await generarReportePdf();
        } catch (error) {
            alert(error.message || 'Error al generar reporte');
        }
    });
});
