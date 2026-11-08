const SETTINGS_KEY = 'sistema_config_general';

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

function cargarConfiguracion() {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return;
    try {
        const cfg = JSON.parse(raw);
        if (cfg.nombreProyecto) document.getElementById('nombreProyecto').value = cfg.nombreProyecto;
        if (cfg.apiVersion) document.getElementById('apiVersion').value = cfg.apiVersion;
        if (cfg.entorno) document.getElementById('entorno').value = cfg.entorno;
        if (cfg.idioma) document.getElementById('idioma').value = cfg.idioma;
        if (cfg.zonaHoraria) document.getElementById('zonaHoraria').value = cfg.zonaHoraria;
    } catch (e) {
        console.warn('No se pudo leer configuración guardada', e);
    }
}

function guardarConfiguracion() {
    const cfg = {
        nombreProyecto: document.getElementById('nombreProyecto').value.trim(),
        apiVersion: document.getElementById('apiVersion').value.trim(),
        entorno: document.getElementById('entorno').value,
        idioma: document.getElementById('idioma').value,
        zonaHoraria: document.getElementById('zonaHoraria').value,
    };
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(cfg));
    alert('Configuración guardada correctamente.');
}

document.addEventListener('DOMContentLoaded', () => {
    if (!verificarSesion()) return;
    cargarConfiguracion();
    document.getElementById('btnGuardarConfig').addEventListener('click', guardarConfiguracion);
});
