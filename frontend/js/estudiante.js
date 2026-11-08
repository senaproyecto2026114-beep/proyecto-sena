// Configuración
const API_URL = 'http://localhost:8000';
let adminUsuario = null;
let estudiantesData = [];
let estudianteSeleccionadoId = null;
let currentPage = 1;
const itemsPerPage = 10;

// Inicializar página
document.addEventListener('DOMContentLoaded', function() {
    // Verificar sesión
    adminUsuario = verificarSesion();
    document.getElementById('adminName').textContent = adminUsuario.nombre;
    document.getElementById('adminInfo').textContent = `Conectado como: ${adminUsuario.nombre}`;
    
    // Cargar estudiantes
    cargarEstudiantes();
    
    // Configurar listeners
    document.getElementById('searchNombre').addEventListener('input', filtrarEstudiantes);
    document.getElementById('filterGrado').addEventListener('change', filtrarEstudiantes);
    document.getElementById('filterEstado').addEventListener('change', filtrarEstudiantes);
});

// Verificar sesión
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

// Cargar todos los estudiantes
async function cargarEstudiantes() {
    try {
        const response = await fetch(`${API_URL}/api/estudiantes`);
        if (response.ok) {
            estudiantesData = await response.json();
            mostrarEstudiantes(estudiantesData);
        } else {
            throw new Error('Error al cargar estudiantes');
        }
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('tablaEstudiantesBody').innerHTML = `
            <tr>
                <td colspan="7" class="no-data">Error al cargar los datos</td>
            </tr>
        `;
    }
}

// Mostrar estudiantes en tabla
function mostrarEstudiantes(estudiantes) {
    const tbody = document.getElementById('tablaEstudiantesBody');
    
    if (!estudiantes || estudiantes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="no-data">No hay estudiantes registrados</td>
            </tr>
        `;
        document.getElementById('pagination').innerHTML = '';
        return;
    }
    
    // Calcular paginación
    const totalPages = Math.ceil(estudiantes.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const estudiantesPagina = estudiantes.slice(startIndex, endIndex);
    
    let html = '';
    estudiantesPagina.forEach(estudiante => {
        const estadoClass = estudiante.activo ? 'status-active' : 'status-inactive';
        const estadoText = estudiante.activo ? 'Activo' : 'Inactivo';
        const huellaStatus = estudiante.huella_dactilar ? 'Registrada' : 'No registrada';
        const huellaIcon = estudiante.huella_dactilar ? 'fas fa-check-circle' : 'fas fa-times-circle';
        const huellaColor = estudiante.huella_dactilar ? '#28a745' : '#dc3545';
        
        html += `
            <tr>
                <td>${estudiante.id}</td>
                <td>${estudiante.nombre_completo}</td>
                <td>${estudiante.grado}</td>
                <td>${estudiante.codigo_estudiante || 'N/A'}</td>
                <td><span class="${estadoClass}">${estadoText}</span></td>
                <td>
                    <i class="${huellaIcon}" style="color: ${huellaColor};"></i>
                    ${huellaStatus}
                </td>
                <td>
                    <div class="action-buttons">
                        <button class="btn-action btn-view" onclick="verHistorial(${estudiante.id})" title="Ver Historial">
                            <i class="fas fa-history"></i>
                        </button>
                        <button class="btn-action btn-edit" onclick="editarEstudiante(${estudiante.id})" title="Editar">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-action btn-download" onclick="descargarHistorialPDF(${estudiante.id})" title="Descargar PDF">
                            <i class="fas fa-file-pdf"></i>
                        </button>
                        <button class="btn-action btn-delete" onclick="eliminarEstudiante(${estudiante.id})" title="Eliminar">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
    generarPaginacion(totalPages);
}

// Generar controles de paginación
function generarPaginacion(totalPages) {
    const pagination = document.getElementById('pagination');
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Botón anterior
    html += `
        <button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="cambiarPagina(${currentPage - 1})">
            <i class="fas fa-chevron-left"></i>
        </button>
    `;
    
    // Números de página
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `
                <button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="cambiarPagina(${i})">
                    ${i}
                </button>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += `<span class="page-btn">...</span>`;
        }
    }
    
    // Botón siguiente
    html += `
        <button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="cambiarPagina(${currentPage + 1})">
            <i class="fas fa-chevron-right"></i>
        </button>
    `;
    
    pagination.innerHTML = html;
}

// Cambiar página
function cambiarPagina(pagina) {
    currentPage = pagina;
    filtrarEstudiantes();
}

// Filtrar estudiantes
function filtrarEstudiantes() {
    const searchNombre = document.getElementById('searchNombre').value.toLowerCase();
    const filterGrado = document.getElementById('filterGrado').value;
    const filterEstado = document.getElementById('filterEstado').value;
    
    let filtered = estudiantesData;
    
    // Filtrar por nombre
    if (searchNombre) {
        filtered = filtered.filter(est => 
            est.nombre_completo.toLowerCase().includes(searchNombre)
        );
    }
    
    // Filtrar por grado
    if (filterGrado) {
        filtered = filtered.filter(est => 
            est.grado.includes(filterGrado)
        );
    }
    
    // Filtrar por estado
    if (filterEstado) {
        const estadoBool = filterEstado === 'activo';
        filtered = filtered.filter(est => 
            est.activo === estadoBool
        );
    }
    
    mostrarEstudiantes(filtered);
}

// Abrir modal para nuevo estudiante
function abrirModalNuevo() {
    document.getElementById('modalTitle').textContent = 'Nuevo Estudiante';
    document.getElementById('formEstudiante').reset();
    document.getElementById('estudianteId').value = '';
    document.getElementById('huellaDactilar').value = '';
    setHuellaPreviewNuevo();
    document.getElementById('modalEstudiante').style.display = 'flex';
    actualizarBotonesHuellaUI();
}

function setHuellaPreviewNuevo() {
    document.getElementById('huellaPreview').innerHTML = `
        <i class="fas fa-hand-pointer" style="color: #17a2b8;"></i>
        <p id="huellaPreviewTexto"><strong>Paso 1:</strong> rellene nombre, grado y código.</p>
        <p style="font-size:12px;color:#555;margin-top:6px;"><strong>Paso 2:</strong> pulse <strong>Guardar</strong>. Después verá el ID y podrá usar el Arduino.</p>
    `;
}

// Abrir modal para editar estudiante
function editarEstudiante(id) {
    const estudiante = estudiantesData.find(est => est.id === id);
    if (!estudiante) return;
    
    document.getElementById('modalTitle').textContent = 'Editar Estudiante';
    document.getElementById('estudianteId').value = estudiante.id;
    document.getElementById('nombreCompleto').value = estudiante.nombre_completo;
    document.getElementById('grado').value = estudiante.grado;
    document.getElementById('codigoEstudiante').value = estudiante.codigo_estudiante || '';
    document.getElementById('estado').value = estudiante.activo.toString();
    
    if (estudiante.huella_dactilar) {
        const esRef = String(estudiante.huella_dactilar).startsWith('as608_slot_');
        document.getElementById('huellaPreview').innerHTML = `
            <i class="fas fa-fingerprint" style="color: #28a745;"></i>
            <p>${esRef ? 'Referencia en sistema' : 'Dato guardado en sistema'}</p>
            <p style="font-size:11px;color:#666;word-break:break-all;">${estudiante.huella_dactilar}</p>
        `;
        document.getElementById('huellaDactilar').value = estudiante.huella_dactilar;
    } else {
        document.getElementById('huellaPreview').innerHTML = `
            <i class="fas fa-microchip" style="color: #ffc107;"></i>
            <p><strong>Sin referencia en BD</strong></p>
            <p style="font-size:12px;color:#555;">Pulse «Referencia en base de datos» y luego <strong>Guardar</strong>, o solo use el Arduino con el ID <strong>${estudiante.id}</strong>.</p>
        `;
        document.getElementById('huellaDactilar').value = '';
    }

    document.getElementById('modalEstudiante').style.display = 'flex';
    actualizarBotonesHuellaUI();
}

function actualizarBotonesHuellaUI() {
    const id = document.getElementById('estudianteId').value;
    const btn = document.getElementById('btnReferenciaHuella');
    const guia = document.getElementById('huellaFlujoGuia');
    if (btn) {
        btn.disabled = false;
        btn.title = id
            ? 'Escribe en el campo oculto el código as608_slot_ID y podrá guardarlo (opcional).'
            : 'Si aún no tiene ID: primero pulse Guardar abajo. Si ya pulsó Guardar, se abrió de nuevo el formulario con el ID.';
    }
    if (guia) {
        guia.innerHTML = id
            ? `<strong>ID del estudiante:</strong> ${id}. En el monitor serie de <code>enroll_as608.ino</code> escriba exactamente <strong>${id}</strong> y enrolle el dedo dos veces.`
            : `<strong>Importante:</strong> aquí no se “escanea” el dedo. Complete los datos y pulse <strong>Guardar</strong>; luego use el Arduino con <code>enroll_as608.ino</code> y el <strong>mismo ID</strong> que mostrará el sistema.`;
    }
}

// Guardar estudiante (crear o actualizar)
async function guardarEstudiante() {
    const estudianteId = document.getElementById('estudianteId').value;
    const nombreCompleto = document.getElementById('nombreCompleto').value;
    const grado = document.getElementById('grado').value;
    const codigoEstudiante = document.getElementById('codigoEstudiante').value;
    const estado = document.getElementById('estado').value === 'true';
    const huellaDactilar = document.getElementById('huellaDactilar').value;
    
    // Validaciones básicas
    if (!nombreCompleto || !grado || !codigoEstudiante) {
        alert('Por favor complete todos los campos obligatorios (*)');
        return;
    }
    
    const estudianteData = {
        nombre_completo: nombreCompleto,
        grado: grado,
        codigo_estudiante: codigoEstudiante,
        activo: estado,
        huella_dactilar: huellaDactilar || null
    };
    
    try {
        let response;

        if (estudianteId) {
            response = await fetch(`${API_URL}/api/estudiantes/${estudianteId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(estudianteData)
            });
        } else {
            response = await fetch(`${API_URL}/api/estudiantes`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(estudianteData)
            });
        }

        const payload = await response.json().catch(() => ({}));

        if (response.ok) {
            if (!estudianteId && payload.id) {
                const nuevoId = payload.id;
                await cargarEstudiantes();
                editarEstudiante(nuevoId);
                alert(
                    `Estudiante creado. ID: ${nuevoId}\n\n` +
                        `Referencia de huella en base de datos: ${payload.huella_dactilar || `as608_slot_${nuevoId}`}\n\n` +
                        `Se reabrió el formulario en modo edición.\n` +
                        `En Arduino: sketch enroll_as608.ino → monitor 9600 → escriba ${nuevoId} → Enter → dedo dos veces.`
                );
            } else {
                alert(estudianteId ? 'Estudiante actualizado correctamente' : 'Estudiante creado correctamente');
                cerrarModal();
                cargarEstudiantes();
            }
        } else {
            alert(`Error: ${payload.detail || 'No se pudo guardar el estudiante'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al conectar con el servidor');
    }
}

function instruccionesSensorHuella() {
    const id = document.getElementById('estudianteId').value;
    const extra = id
        ? `\n\nEste estudiante ya tiene ID: ${id}. En enroll_as608.ino debe escribir exactamente: ${id}`
        : '\n\nPrimero guarde el estudiante para conocer su ID. Ese mismo número es el que escribirá en el monitor serie al enrolar.';
    alert(
        'El sensor AS608 no se conecta al navegador web.\n\n' +
            'La plantilla biométrica solo existe dentro del chip del sensor después de usar el sketch enroll_as608.ino.\n\n' +
            'El ID que escribe en el monitor serie al enrolar debe ser el mismo que el campo "id" del estudiante en la base de datos.' +
            extra
    );
}

function aplicarReferenciaInternaHuella() {
    const id = document.getElementById('estudianteId').value;
    if (!id) {
        alert(
            'Aún no hay ID de estudiante.\n\n' +
                'Rellene nombre, grado y código, luego pulse **Guardar** (abajo). ' +
                'Al crear, el formulario se volverá a abrir con el ID para que pueda enlazar el Arduino.'
        );
        return;
    }
    const ref = `as608_slot_${id}`;
    document.getElementById('huellaDactilar').value = ref;
    document.getElementById('huellaPreview').innerHTML = `
        <i class="fas fa-fingerprint" style="color: #28a745;"></i>
        <p>Referencia interna lista</p>
        <p style="font-size:11px;color:#666;">${ref} — pulse Guardar para persistir</p>
    `;
    alert(
        `Se guardará el código interno "${ref}" al pulsar Guardar.\n\n` +
            'Esto NO sustituye enrolar el dedo en el AS608; solo ayuda a marcar en el sistema que el flujo va ligado al slot del sensor.'
    );
}

// Ver historial de un estudiante
async function verHistorial(estudianteId) {
    estudianteSeleccionadoId = estudianteId;
    
    try {
        const response = await fetch(`${API_URL}/api/estudiante/${estudianteId}/historial`);
        if (response.ok) {
            const historial = await response.json();
            mostrarHistorialModal(historial);
        } else {
            throw new Error('Error al cargar historial');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al cargar el historial');
    }
}

// Mostrar historial en modal
function mostrarHistorialModal(historial) {
    const estudiante = estudiantesData.find(est => est.id === estudianteSeleccionadoId);
    
    if (!estudiante) {
        alert('Estudiante no encontrado');
        return;
    }
    
    document.getElementById('historialTitle').textContent = `Historial de ${estudiante.nombre_completo}`;
    document.getElementById('historialInfo').innerHTML = `
        <p><strong>Estudiante:</strong> ${estudiante.nombre_completo}</p>
        <p><strong>Grado:</strong> ${estudiante.grado}</p>
        <p><strong>Código:</strong> ${estudiante.codigo_estudiante || 'N/A'}</p>
        <hr>
    `;
    
    const container = document.getElementById('historialContainer');
    
    if (!historial || historial.length === 0) {
        container.innerHTML = '<p class="no-data">No hay registros de asistencia</p>';
    } else {
        let html = '';
        historial.forEach(registro => {
            const hora = new Date(`1970-01-01T${registro.hora}`).toLocaleTimeString('es-ES', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
            
            const tipoClass = registro.tipo_ingreso === 'PUNTUAL' ? 'tipo-puntual' : 'tipo-tarde';
            const tipoText = registro.tipo_ingreso === 'PUNTUAL' ? 'Puntual' : 'Tarde';
            
            html += `
                <div class="historial-item">
                    <div class="historial-date">${registro.fecha} - ${registro.dia_semana}</div>
                    <div class="historial-info">
                        <span>Hora: ${hora}</span>
                        <span class="historial-tipo ${tipoClass}">${tipoText}</span>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    }
    
    document.getElementById('modalHistorial').style.display = 'flex';
}

// Generar PDF del historial
async function generarPDFHistorial() {
    if (!estudianteSeleccionadoId) return;
    
    try {
        // Descargar el PDF
        const response = await fetch(`${API_URL}/api/estudiante/${estudianteSeleccionadoId}/pdf`);
        
        if (response.ok) {
            // Crear un enlace temporal para descargar el archivo
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            const estudiante = estudiantesData.find(est => est.id === estudianteSeleccionadoId);
            const fileName = `historial_${estudiante.nombre_completo.replace(/\s+/g, '_')}.pdf`;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            throw new Error('Error al generar PDF');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al generar el PDF');
    }
}

// Descargar PDF directamente desde la tabla
function descargarHistorialPDF(estudianteId) {
    estudianteSeleccionadoId = estudianteId;
    generarPDFHistorial();
}

// Eliminar estudiante (borrado real en base de datos; registros_asistencia en cascada)
async function eliminarEstudiante(id) {
    if (!confirm('¿Está seguro de eliminar este estudiante? Se borrará de la base de datos y su historial de asistencia asociado. Esta acción no se puede deshacer.')) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/estudiantes/${id}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (response.ok) {
            alert('Estudiante eliminado correctamente');
            cargarEstudiantes();
        } else {
            const err = await response.json().catch(() => ({}));
            const d = err.detail;
            const msg = Array.isArray(d) ? d.map((e) => e.msg || e).join(' ') : (d || 'No se pudo eliminar el estudiante');
            alert(msg);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al conectar con el servidor');
    }
}

// Exportar a Excel
function exportarExcel() {
    const searchNombre = document.getElementById('searchNombre').value.toLowerCase();
    const filterGrado = document.getElementById('filterGrado').value;
    const filterEstado = document.getElementById('filterEstado').value;

    let filtered = [...estudiantesData];
    if (searchNombre) {
        filtered = filtered.filter((est) => est.nombre_completo.toLowerCase().includes(searchNombre));
    }
    if (filterGrado) {
        filtered = filtered.filter((est) => est.grado.includes(filterGrado));
    }
    if (filterEstado) {
        const estadoBool = filterEstado === 'activo';
        filtered = filtered.filter((est) => est.activo === estadoBool);
    }

    if (!filtered.length) {
        alert('No hay estudiantes para exportar con el filtro actual.');
        return;
    }

    const encabezados = [
        'ID',
        'Nombre Completo',
        'Grado',
        'Código del Estudiante',
        'Estado',
        'Huella',
    ];
    const filas = filtered.map((est) => [
        est.id,
        est.nombre_completo,
        est.grado,
        est.codigo_estudiante || '',
        est.activo ? 'Activo' : 'Inactivo',
        est.huella_dactilar ? 'Registrada' : 'No registrada',
    ]);
    const csvRows = [encabezados, ...filas].map((row) =>
        row.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(',')
    );
    const csv = '\uFEFF' + csvRows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `estudiantes_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Cerrar modal estudiante
function cerrarModal() {
    document.getElementById('modalEstudiante').style.display = 'none';
}

// Cerrar modal historial
function cerrarModalHistorial() {
    document.getElementById('modalHistorial').style.display = 'none';
    estudianteSeleccionadoId = null;
}

// Enviar mensaje WhatsApp al coordinador del grado (plantilla oficial; ver backend)
async function enviarWhatsApp(estudianteId) {
    const estudiante = estudiantesData.find(est => est.id === estudianteId);
    if (!estudiante) return;

    try {
        const response = await fetch(`${API_URL}/api/whatsapp/notificar-tardanza`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ estudiante_id: estudianteId }),
        });
        const data = await response.json().catch(() => ({}));

        if (response.ok) {
            const preview = data.mensaje ? `\n\n${data.mensaje}` : '';
            alert(
                (data.enviado
                    ? 'Notificación al coordinador registrada (simulada en consola del servidor).'
                    : 'No se pudo determinar número de destino.') + preview
            );
        } else {
            throw new Error(data.detail || 'Error al enviar mensaje');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al enviar el mensaje: ' + (error.message || error));
    }
}