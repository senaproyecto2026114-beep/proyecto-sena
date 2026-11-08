// Configuración (var para que otros <script> en la misma página, p. ej. index.html, vean API_URL)
var API_URL = 'http://localhost:8000';
if (typeof window !== 'undefined') {
    window.API_URL = API_URL;
}

// Cargar estadísticas al iniciar
document.addEventListener('DOMContentLoaded', function() {
    cargarEstadisticas();
    cargarUltimosRegistros();
    
    // Configurar formulario de login
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
});

// Manejar login
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const rememberMeCheckbox = document.getElementById('rememberMe');
    const rememberMe = rememberMeCheckbox ? rememberMeCheckbox.checked : false;
    
    try {
        const response = await fetch(`${API_URL}/api/login`, {
            method: 'POST',
            mode: 'cors',
            credentials: 'omit',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('admin', JSON.stringify(data.admin));

            // Guardar en localStorage si "Recordarme" está activado
            if (rememberMe) {
                localStorage.setItem('savedUsername', username);
                localStorage.setItem('rememberMe', 'true');
            } else {
                localStorage.removeItem('savedUsername');
                localStorage.removeItem('rememberMe');
            }
            window.location.href = 'dashboard.html';
        } else {
            alert('Usuario o contraseña incorrectos');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al conectar con el servidor');
    }
}

// Cargar estadísticas
async function cargarEstadisticas() {
    try {
        const response = await fetch(`${API_URL}/api/estadisticas`, { mode: 'cors', credentials: 'omit' });
        if (response.ok) {
            const data = await response.json();
            document.getElementById('studentCount').textContent = data.total_estudiantes;
        }
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
    }
}

// Cargar últimos registros
async function cargarUltimosRegistros() {
    try {
        const response = await fetch(`${API_URL}/api/registros/fecha`, {
            method: 'POST',
            mode: 'cors',
            credentials: 'omit',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                fecha_inicio: new Date().toISOString().split('T')[0],
                fecha_fin: new Date().toISOString().split('T')[0]
            })
        });
        
        if (response.ok) {
            const registros = await response.json();
            mostrarUltimosRegistros(registros.slice(0, 5));
        }
    } catch (error) {
        console.error('Error cargando registros:', error);
    }
}

// Mostrar últimos registros
function mostrarUltimosRegistros(registros) {
    const container = document.getElementById('recentEntries');
    
    if (!registros || registros.length === 0) {
        container.innerHTML = '<p>No hay registros hoy</p>';
        return;
    }
    
    let html = '';
    registros.forEach(registro => {
        const hora = new Date(`1970-01-01T${registro.hora}`).toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        const statusClass = registro.tipo_ingreso === 'PUNTUAL' ? 'status-puntual' : 'status-tarde';
        const statusText = registro.tipo_ingreso === 'PUNTUAL' ? 'Puntual' : 'Tarde';
        
        html += `
            <div class="entry-item">
                <span class="entry-time">${hora}</span>
                <span class="entry-name">${registro.nombre_completo}</span>
                <span class="entry-status ${statusClass}">${statusText}</span>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Verificar si hay sesión activa
function verificarSesion() {
    const admin = localStorage.getItem('admin');
    if (!admin) {
        window.location.href = 'index.html';
    }
    return JSON.parse(admin);
}

// Cerrar sesión
function cerrarSesion() {
    localStorage.removeItem('admin');
    window.location.href = 'index.html';
}