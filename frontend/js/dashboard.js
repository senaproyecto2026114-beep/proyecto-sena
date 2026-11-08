// Configuración
const API_URL = 'http://localhost:8000';
let adminUsuario = null;
let filtroActual = {
    fecha_inicio: null,
    fecha_fin: null,
};

// Verificar sesión (compartida con otras páginas)
function verificarSesion() {
    const admin = localStorage.getItem('admin');
    if (!admin) {
        window.location.href = 'index.html';
        return null;
    }
    return JSON.parse(admin);
}

// Cerrar sesión
function cerrarSesion() {
    localStorage.removeItem('admin');
    window.location.href = 'index.html';
}

// Inicializar dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Verificar sesión
    adminUsuario = verificarSesion();
    if (!adminUsuario) return;
    document.getElementById('adminName').textContent = adminUsuario.nombre;
    
    // Actualizar fecha y hora
    actualizarFechaHora();
    setInterval(actualizarFechaHora, 1000);
    
    // Configurar fecha por defecto
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('fechaInicio').value = hoy;
    document.getElementById('fechaFin').value = hoy;
    filtroActual.fecha_inicio = hoy;
    filtroActual.fecha_fin = hoy;

    // Cargar datos iniciales
    cargarEstadisticasDashboard();
    cargarRegistrosPorFecha(hoy, hoy);
    
    // Configurar listeners de navegación del menú
    document.getElementById('btnEstudiantes').addEventListener('click', function(e) {
        e.preventDefault();
        window.location.href = 'estudiante.html';
    });
    document.getElementById('btnRegistros').addEventListener('click', function(e) {
        e.preventDefault();
        window.location.href = 'historial.html';
    });
    document.getElementById('btnReportes').addEventListener('click', function(e) {
        e.preventDefault();
        window.location.href = 'reportes.html';
    });
    document.getElementById('btnConfiguracion').addEventListener('click', function(e) {
        e.preventDefault();
        window.location.href = 'configuracion.html';
    });
});

// Actualizar fecha y hora
function actualizarFechaHora() {
    const ahora = new Date();
    const fecha = ahora.toLocaleDateString('es-ES', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    const hora = ahora.toLocaleTimeString('es-ES', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    document.getElementById('currentDate').textContent = fecha;
    document.getElementById('currentTime').textContent = hora;
}

// Cargar estadísticas para el dashboard
async function cargarEstadisticasDashboard() {
    try {
        const response = await fetch(`${API_URL}/api/estadisticas`);
        if (response.ok) {
            const data = await response.json();
            
            document.getElementById('totalEstudiantes').textContent = data.total_estudiantes;
            document.getElementById('puntualesHoy').textContent = data.hoy.puntuales;
            document.getElementById('tardesHoy').textContent = data.hoy.tardes;
            document.getElementById('tardesSemana').textContent = data.semana;
        }
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
    }
}

// Cargar registros de hoy
async function cargarRegistrosHoy() {
    const hoy = new Date().toISOString().split('T')[0];
    await cargarRegistrosPorFecha(hoy, hoy);
}

// Filtrar registros por fecha
async function filtrarRegistros() {
    const fechaInicio = document.getElementById('fechaInicio').value;
    const fechaFin = document.getElementById('fechaFin').value;
    
    if (!fechaInicio || !fechaFin) {
        alert('Por favor seleccione ambas fechas');
        return;
    }
    
    filtroActual.fecha_inicio = fechaInicio;
    filtroActual.fecha_fin = fechaFin;
    await cargarRegistrosPorFecha(fechaInicio, fechaFin);
}

// Cargar registros por fecha
async function cargarRegistrosPorFecha(fechaInicio, fechaFin) {
    try {
        const response = await fetch(`${API_URL}/api/registros/fecha`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                fecha_inicio: fechaInicio,
                fecha_fin: fechaFin
            })
        });
        
        if (response.ok) {
            const registros = await response.json();
            mostrarRegistrosTabla(registros);
        }
    } catch (error) {
        console.error('Error cargando registros:', error);
    }
}

// Mostrar registros en tabla
function mostrarRegistrosTabla(registros) {
    const tbody = document.getElementById('tablaRegistrosBody');
    
    if (!registros || registros.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="no-data">No hay registros para las fechas seleccionadas</td>
            </tr>
        `;
        return;
    }
    
    let html = '';
    registros.forEach(registro => {
        const hora = new Date(`1970-01-01T${registro.hora}`).toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        });
        
        const tipoClass = registro.tipo_ingreso === 'PUNTUAL' ? 'tipo-puntual' : 'tipo-tarde';
        const tipoText = registro.tipo_ingreso === 'PUNTUAL' ? 'Puntual' : 'Tarde';
        
        html += `
            <tr>
                <td>${registro.fecha}</td>
                <td>${hora}</td>
                <td>${registro.nombre_completo}</td>
                <td>${registro.grado}</td>
                <td>${registro.dia_semana}</td>
                <td><span class="tipo-indicator ${tipoClass}">${tipoText}</span></td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
}

// Resetear filtros
function resetFiltros() {
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('fechaInicio').value = hoy;
    document.getElementById('fechaFin').value = hoy;
    filtroActual.fecha_inicio = hoy;
    filtroActual.fecha_fin = hoy;
    cargarRegistrosPorFecha(hoy, hoy);
}

// Simular lectura de sensor (en producción sería WebSocket)
function simularLecturaSensor() {
    setInterval(async () => {
        const ahora = new Date();
        const hora = ahora.toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        document.getElementById('ultimaLectura').textContent = hora;
        
        // Simular detección aleatoria
        if (Math.random() > 0.7) {
            const estudiantes = await obtenerEstudiantes();
            if (estudiantes.length > 0) {
                const randomEst = estudiantes[Math.floor(Math.random() * estudiantes.length)];
                document.getElementById('estudianteDetectado').textContent = randomEst.nombre_completo;
                
                // Simular registro de lectura en panel de estado (sin pisar tabla filtrada)
                setTimeout(() => {
                    document.getElementById('estudianteDetectado').textContent = 'Ninguno';
                    cargarEstadisticasDashboard();
                }, 3000);
            }
        }
    }, 5000);
}

// Obtener lista de estudiantes
async function obtenerEstudiantes() {
    try {
        const response = await fetch(`${API_URL}/api/estudiantes`);
        if (response.ok) {
            return await response.json();
        }
        return [];
    } catch (error) {
        console.error('Error:', error);
        return [];
    }
}

// Iniciar simulación de sensor
simularLecturaSensor();