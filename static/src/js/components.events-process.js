// ============================================================================
// INICIALIZACIÓN DE BOOTSTRAP Y VARIABLES GLOBALES
// ============================================================================

// Almacenar instancias de modales para un mejor control
let modals = {};
// Variable para evitar doble envío
let isSubmitting = false;

// Inicializar cuando el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    console.log('Process Inbox Item JS inicializado');
    
    // Inicializar todos los modales de Bootstrap
    initializeModals();
    
    // Inicializar opciones de proyecto y evento
    toggleProjectOptions();
    toggleEventOptions();
    
    // Configurar event listeners
    setupEventListeners();
    
    // Configurar búsquedas en tiempo real
    setupSearchFilters();
    
    // Actualizar vista previa inicial
    updateCreationPreview();
    
    // Configurar formulario de clasificación
    setupClassificationForm();
});

// ============================================================================
// INICIALIZACIÓN DE MODALES
// ============================================================================

function initializeModals() {
    // Lista de IDs de modales a inicializar
    const modalIds = ['taskSelectorModal', 'projectSelectorModal', 'eventSelectorModal', 'alertModal'];
    
    modalIds.forEach(id => {
        const modalElement = document.getElementById(id);
        if (modalElement) {
            try {
                // Crear instancia del modal de Bootstrap
                modals[id] = new bootstrap.Modal(modalElement);
                console.log(`Modal ${id} inicializado correctamente`);
                
                // Agregar event listeners para depuración
                modalElement.addEventListener('show.bs.modal', () => {
                    console.log(`Mostrando modal: ${id}`);
                });
                
                modalElement.addEventListener('shown.bs.modal', () => {
                    console.log(`Modal ${id} mostrado completamente`);
                    // Cargar datos según el tipo de modal
                    if (id === 'taskSelectorModal') loadAvailableTasks();
                    if (id === 'projectSelectorModal') loadAvailableProjects();
                    if (id === 'eventSelectorModal') loadAvailableEvents();
                });
                
            } catch (error) {
                console.error(`Error inicializando modal ${id}:`, error);
            }
        } else {
            console.warn(`Elemento modal ${id} no encontrado en el DOM`);
        }
    });
}

// ============================================================================
// FUNCIONES DE CONFIGURACIÓN DE CREACIÓN
// ============================================================================

// Mostrar/ocultar opciones de proyecto
function toggleProjectOptions() {
    const projectOption = document.getElementById('projectOption');
    if (!projectOption) return;
    
    const existingProjectSelect = document.getElementById('existingProjectSelect');
    const taskContextPreview = document.getElementById('taskContextPreview');
    const taskProjectPreview = document.getElementById('taskProjectPreview');
    const projectEventPreview = document.getElementById('projectEventPreview');
    
    // Mostrar/ocultar selector de proyecto existente
    if (existingProjectSelect) {
        existingProjectSelect.style.display = projectOption.value === 'existing' ? 'block' : 'none';
    }
    
    // Actualizar vistas previas
    if (projectOption.value === 'new') {
        if (taskContextPreview) taskContextPreview.textContent = 'Tarea en nuevo proyecto';
        if (taskProjectPreview) taskProjectPreview.textContent = 'Nuevo proyecto';
        if (projectEventPreview) projectEventPreview.textContent = 'Nuevo';
    } else if (projectOption.value === 'existing') {
        if (taskContextPreview) taskContextPreview.textContent = 'Tarea en proyecto existente';
        if (taskProjectPreview) taskProjectPreview.textContent = 'Existente (seleccionar)';
        if (projectEventPreview) projectEventPreview.textContent = 'Del proyecto';
    } else {
        if (taskContextPreview) taskContextPreview.textContent = 'Tarea independiente';
        if (taskProjectPreview) taskProjectPreview.textContent = 'Ninguno';
        if (projectEventPreview) projectEventPreview.textContent = 'Nuevo';
    }
    
    updateCreationPreview();
}

// Mostrar/ocultar opciones de evento
function toggleEventOptions() {
    const eventOption = document.getElementById('eventOption');
    if (!eventOption) return;
    
    const existingEventSelect = document.getElementById('existingEventSelect');
    const taskEventPreview = document.getElementById('taskEventPreview');
    const projectEventPreview = document.getElementById('projectEventPreview');
    
    // Mostrar/ocultar selector de evento existente
    if (existingEventSelect) {
        existingEventSelect.style.display = eventOption.value === 'existing' ? 'block' : 'none';
    }
    
    // Actualizar vistas previas
    if (eventOption.value === 'new') {
        if (taskEventPreview) taskEventPreview.textContent = 'Nuevo';
        if (projectEventPreview) projectEventPreview.textContent = 'Nuevo';
    } else if (eventOption.value === 'existing') {
        if (taskEventPreview) taskEventPreview.textContent = 'Existente (seleccionar)';
        if (projectEventPreview) projectEventPreview.textContent = 'Existente (seleccionar)';
    } else {
        if (taskEventPreview) taskEventPreview.textContent = 'Sin evento';
        if (projectEventPreview) projectEventPreview.textContent = 'Sin evento';
    }
    
    updateCreationPreview();
}

// Actualizar vista previa de creación
function updateCreationPreview() {
    const projectOption = document.getElementById('projectOption');
    const eventOption = document.getElementById('eventOption');
    const previewText = document.getElementById('previewText');
    
    if (!projectOption || !eventOption || !previewText) return;
    
    const projectMessages = {
        'new': '📁 <strong>Nuevo proyecto</strong> creado automáticamente',
        'existing': '📁 <strong>Proyecto existente</strong> seleccionado',
        'none': '📁 <strong>Sin proyecto</strong> asociado'
    };
    
    const eventMessages = {
        'new': '📅 <strong>Nuevo evento</strong> creado automáticamente',
        'existing': '📅 <strong>Evento existente</strong> seleccionado',
        'none': '📅 <strong>Sin evento</strong> asociado'
    };
    
    const preview = [
        projectMessages[projectOption.value] || projectMessages.none,
        eventMessages[eventOption.value] || eventMessages.new
    ];
    
    previewText.innerHTML = preview.join('<br>');
}

// ============================================================================
// CONFIGURACIÓN DE EVENT LISTENERS
// ============================================================================

function setupEventListeners() {
    // Configurar cambios en selectores de proyecto y evento
    const projectOption = document.getElementById('projectOption');
    const eventOption = document.getElementById('eventOption');
    
    if (projectOption) {
        projectOption.addEventListener('change', function() {
            console.log('Proyecto cambiado a:', this.value);
            toggleProjectOptions();
        });
    }
    
    if (eventOption) {
        eventOption.addEventListener('change', function() {
            console.log('Evento cambiado a:', this.value);
            toggleEventOptions();
        });
    }
    
    // Configurar botones de confirmación en modales
    const linkEventBtn = document.getElementById('linkEventConfirmBtn');
    if (linkEventBtn) {
        linkEventBtn.addEventListener('click', linkToSelectedEvent);
    }
    
    const linkProjectBtn = document.getElementById('linkProjectConfirmBtn');
    if (linkProjectBtn) {
        linkProjectBtn.addEventListener('click', linkToSelectedProject);
    }
    
    // Capturar el envío del formulario para incluir las opciones seleccionadas
    const processForm = document.getElementById('processForm');
    if (processForm) {
        processForm.addEventListener('submit', function(e) {
            console.log('Formulario enviado con:');
            console.log('- project_option:', document.getElementById('projectOption').value);
            console.log('- event_option:', document.getElementById('eventOption').value);
            console.log('- assigned_to:', document.querySelector('[name="assigned_to"]').value);
        });
    }
}

// ============================================================================
// FUNCIONES DE CARGA DE DATOS (TAREAS, PROYECTOS, EVENTOS)
// ============================================================================

// Función genérica para cargar datos
async function loadData(endpoint, listElementId, sampleData, itemTemplate, fallbackMessage) {
    const listElement = document.getElementById(listElementId);
    if (!listElement) {
        console.warn(`Elemento ${listElementId} no encontrado`);
        return;
    }

    listElement.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Cargando...</div>';

    try {
        const response = await fetch(endpoint, {
            method: 'GET',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });

        let data;
        if (!response.ok) {
            console.log(`API ${endpoint} no disponible (${response.status}), mostrando datos de ejemplo`);
            data = { items: sampleData };
        } else {
            data = await response.json();
        }

        // Procesar diferentes formatos de respuesta
        let items = [];
        if (data && data.items) items = data.items;
        else if (data && data.tasks) items = data.tasks;
        else if (data && data.projects) items = data.projects;
        else if (data && data.events) items = data.events;
        else if (Array.isArray(data)) items = data;

        if (items && items.length > 0) {
            listElement.innerHTML = items.map(itemTemplate).join('');
        } else {
            listElement.innerHTML = `<div class="text-center text-muted py-3">${fallbackMessage}</div>`;
        }
    } catch (error) {
        console.error(`Error cargando ${endpoint}:`, error);
        // Mostrar datos de ejemplo como fallback
        if (sampleData && sampleData.length > 0) {
            listElement.innerHTML = sampleData.map(itemTemplate).join('');
        } else {
            listElement.innerHTML = '<div class="text-center text-danger">Error al cargar datos</div>';
        }
    }
}

// Cargar tareas disponibles
function loadAvailableTasks() {
    const sampleTasks = [
        { id: 1, title: 'Revisar documentación del proyecto', description: 'Actualizar la documentación técnica', priority: 'alta' },
        { id: 2, title: 'Implementar nueva funcionalidad', description: 'Desarrollar el módulo de reportes', priority: 'media' },
        { id: 3, title: 'Corregir bugs menores', description: 'Arreglar issues reportados por usuarios', priority: 'baja' }
    ];

    const taskTemplate = task => `
        <div class="list-group-item task-item" onclick="selectTask(${task.id}, '${task.title.replace(/'/g, "\\'")}')">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${task.title}</h6>
                    <small class="text-muted">${task.description || 'Sin descripción'}</small>
                </div>
                <span class="badge bg-${task.priority === 'alta' ? 'danger' : task.priority === 'media' ? 'warning' : 'secondary'}">
                    ${task.priority}
                </span>
            </div>
        </div>`;

    loadData(
        '/events/inbox/api/tasks/',
        'taskList',
        sampleTasks,
        taskTemplate,
        'No hay tareas disponibles'
    );
}

// Cargar proyectos disponibles
function loadAvailableProjects() {
    const sampleProjects = [
        { id: 1, title: 'Sistema de Gestión de Proyectos', description: 'Desarrollo completo del sistema GTD', status: 'En progreso' },
        { id: 2, title: 'Migración a nueva plataforma', description: 'Actualización tecnológica del sistema', status: 'Planificación' },
        { id: 3, title: 'Implementación de API REST', description: 'Desarrollo de endpoints para integración', status: 'Pendiente' }
    ];

    const projectTemplate = project => `
        <div class="list-group-item project-item" data-project-id="${project.id}">
            <div class="form-check">
                <input class="form-check-input" type="radio" name="selected_project" 
                       id="project${project.id}" value="${project.id}">
                <label class="form-check-label w-100" for="project${project.id}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">${project.title}</h6>
                            <small class="text-muted">${project.description || 'Sin descripción'}</small>
                        </div>
                        <span class="badge bg-primary">${project.status}</span>
                    </div>
                </label>
            </div>
        </div>`;

    loadData(
        '/events/inbox/api/projects/',
        'projectList',
        sampleProjects,
        projectTemplate,
        'No hay proyectos disponibles'
    );
}

// Cargar eventos disponibles
function loadAvailableEvents() {
    const sampleEvents = [
        { id: 1, title: 'Reunión de Proyecto Alpha', description: 'Revisión semanal del proyecto', status: 'En progreso' },
        { id: 2, title: 'Lanzamiento Beta', description: 'Presentación del lanzamiento beta', status: 'Planificado' },
        { id: 3, title: 'Capacitación del Equipo', description: 'Sesión de capacitación técnica', status: 'Completado' }
    ];

    const eventTemplate = event => `
        <div class="list-group-item event-item" data-event-id="${event.id}">
            <div class="form-check">
                <input class="form-check-input" type="radio" name="selected_event" 
                       id="event${event.id}" value="${event.id}">
                <label class="form-check-label w-100" for="event${event.id}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">${event.title}</h6>
                            <small class="text-muted">${event.description || 'Sin descripción'}</small>
                        </div>
                        <span class="badge bg-primary">${event.status}</span>
                    </div>
                </label>
            </div>
        </div>`;

    loadData(
        '/events/inbox/api/events/',
        'eventList',
        sampleEvents,
        eventTemplate,
        'No hay eventos disponibles'
    );
}

// ============================================================================
// CONFIGURACIÓN DE FILTROS DE BÚSQUEDA
// ============================================================================

function setupSearchFilters() {
    const setupSearch = (searchId, itemSelector) => {
        const searchElement = document.getElementById(searchId);
        if (!searchElement) return;
        
        searchElement.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            const items = document.querySelectorAll(itemSelector);
            
            items.forEach(item => {
                const title = item.querySelector('h6')?.textContent.toLowerCase() || '';
                const description = item.querySelector('small')?.textContent.toLowerCase() || '';
                const matches = title.includes(searchTerm) || description.includes(searchTerm);
                item.style.display = matches ? '' : 'none';
            });
        });
    };
    
    setupSearch('taskSearch', '#taskList .task-item');
    setupSearch('projectSearch', '#projectList .project-item');
    setupSearch('eventSearch', '#eventList .event-item');
}

// ============================================================================
// FUNCIONES DE SELECCIÓN Y VINCULACIÓN
// ============================================================================

// Seleccionar tarea
window.selectTask = function(taskId, taskTitle) {
    const selectedTaskInfo = document.getElementById('selectedTaskInfo');
    if (selectedTaskInfo) {
        selectedTaskInfo.innerHTML = `
            <div class="alert alert-success">
                <h6 class="mb-1"><i class="bi bi-check-circle me-2"></i>Tarea Seleccionada</h6>
                <p class="mb-0">${taskTitle}</p>
                <input type="hidden" name="selected_task_id" value="${taskId}">
                <button type="button" class="btn btn-sm btn-primary mt-2" onclick="confirmTaskLink(${taskId}, '${taskTitle.replace(/'/g, "\\'")}')">
                    <i class="bi bi-link me-1"></i>Confirmar Vinculación
                </button>
            </div>`;
    }
    
    // Cerrar modal
    if (modals['taskSelectorModal']) {
        modals['taskSelectorModal'].hide();
    }
};

// Confirmar vinculación de tarea
window.confirmTaskLink = function(taskId, taskTitle) {
    const form = document.createElement('form');
    form.method = 'post';
    form.action = window.location.href;
    form.style.display = 'none';
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
        <input type="hidden" name="action" value="link_to_task">
        <input type="hidden" name="task_id" value="${taskId}">
    `;
    
    document.body.appendChild(form);
    form.submit();
};

// Vincular a proyecto seleccionado
window.linkToSelectedProject = function() {
    const selectedProject = document.querySelector('input[name="selected_project"]:checked');
    if (!selectedProject) {
        showAlertModal('Selección requerida', 'Por favor, selecciona un proyecto para vincular.', 'warning');
        return;
    }
    
    const projectId = selectedProject.value;
    const projectTitle = document.querySelector(`label[for="project${projectId}"] h6`)?.textContent || 'Proyecto seleccionado';
    
    const form = document.createElement('form');
    form.method = 'post';
    form.action = window.location.href;
    form.style.display = 'none';
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
        <input type="hidden" name="action" value="link_to_project">
        <input type="hidden" name="project_id" value="${projectId}">
    `;
    
    document.body.appendChild(form);
    form.submit();
};

// Vincular a evento seleccionado
window.linkToSelectedEvent = function() {
    const selectedEvent = document.querySelector('input[name="selected_event"]:checked');
    if (!selectedEvent) {
        showAlertModal('Selección requerida', 'Por favor, selecciona un evento para vincular.', 'warning');
        return;
    }
    
    const eventId = selectedEvent.value;
    const eventTitle = document.querySelector(`label[for="event${eventId}"] h6`)?.textContent || 'Evento seleccionado';
    
    const form = document.createElement('form');
    form.method = 'post';
    form.action = window.location.href;
    form.style.display = 'none';
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
        <input type="hidden" name="action" value="link_to_event">
        <input type="hidden" name="event_id" value="${eventId}">
    `;
    
    document.body.appendChild(form);
    form.submit();
};

// ============================================================================
// FUNCIONES DE UTILIDAD - MODALES Y MENSAJES
// ============================================================================

// Mostrar modal de alerta
function showAlertModal(title, message, type = 'info') {
    const modalElement = document.getElementById('alertModal');
    if (!modalElement) {
        alert(`${title}: ${message}`);
        return;
    }
    
    const icons = {
        'success': 'bi-check-circle-fill text-success',
        'danger': 'bi-exclamation-triangle-fill text-danger',
        'warning': 'bi-exclamation-triangle-fill text-warning',
        'info': 'bi-info-circle-fill text-info'
    };

    document.getElementById('alertModalLabel').innerHTML = 
        `<i class="bi ${icons[type] || icons['info']} me-2"></i>${title}`;
    document.getElementById('alertModalBody').innerHTML = `<p class="mb-0">${message}</p>`;
    
    // Usar la instancia guardada o crear una nueva
    if (modals['alertModal']) {
        modals['alertModal'].show();
    } else {
        try {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
            modals['alertModal'] = modal;
        } catch (error) {
            console.error('Error mostrando modal de alerta:', error);
            alert(`${title}: ${message}`);
        }
    }
}

// Función de depuración
window.testModals = function() {
    console.log('=== TEST DE CONFIGURACIÓN ===');
    console.log('projectOption:', document.getElementById('projectOption')?.value);
    console.log('eventOption:', document.getElementById('eventOption')?.value);
    console.log('assigned_to:', document.querySelector('[name="assigned_to"]')?.value);
    
    showAlertModal('Test', 'La configuración está funcionando correctamente.', 'success');
};

// ============================================================================
// FUNCIONES DE CLASIFICACIÓN GTD - VERSIÓN DEFINITIVA CORREGIDA
// ============================================================================

// Configurar formulario de clasificación
function setupClassificationForm() {
    const confidenceRange = document.getElementById('confidenceRange');
    const confidenceValue = document.getElementById('confidenceValue');
    
    if (confidenceRange && confidenceValue) {
        confidenceValue.textContent = confidenceRange.value;
        
        confidenceRange.addEventListener('input', function() {
            confidenceValue.textContent = this.value;
        });
    }
    
    // Configurar el formulario de clasificación - ELIMINAR EVENTOS DUPLICADOS
    const classificationForm = document.getElementById('classificationForm');
    if (classificationForm) {
        // Remover cualquier evento submit previo para evitar duplicados
        classificationForm.removeEventListener('submit', handleClassificationSubmit);
        
        // Agregar el nuevo manejador con prevención de envío tradicional
        classificationForm.addEventListener('submit', function(e) {
            e.preventDefault(); // IMPORTANTE: Prevenir envío tradicional
            e.stopPropagation(); // Detener propagación del evento
            
            if (!isSubmitting) {
                handleClassificationSubmit(e);
            }
            return false; // Asegurar que no se propague
        });
    }
    
    // Configurar botón de confirmación de reclasificación
    const confirmReclassifyBtn = document.getElementById('confirmReclassifyBtn');
    if (confirmReclassifyBtn) {
        confirmReclassifyBtn.removeEventListener('click', confirmReclassification);
        confirmReclassifyBtn.addEventListener('click', confirmReclassification);
    }
    
    // Cargar historial cuando se abra el modal
    const reclassifyHistoryModal = document.getElementById('reclassifyHistoryModal');
    if (reclassifyHistoryModal) {
        reclassifyHistoryModal.removeEventListener('show.bs.modal', loadClassificationHistory);
        reclassifyHistoryModal.addEventListener('show.bs.modal', loadClassificationHistory);
    }
}

// Manejar envío del formulario de clasificación - VERSIÓN CORREGIDA
async function handleClassificationSubmit(e) {
    // Asegurar que el evento se previene múltiples veces
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Evitar doble envío
    if (isSubmitting) {
        console.log('Ya se está procesando una solicitud');
        return;
    }
    
    const form = document.getElementById('classificationForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const submitBtn = document.getElementById('saveClassificationBtn');
    if (!submitBtn) return;
    
    const originalText = submitBtn.innerHTML;
    
    // Marcar como enviando
    isSubmitting = true;
    
    // Mostrar estado de carga
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
    
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Mostrar vista previa de cambios para reclasificación
            if (data.changed) {
                showReclassifyPreview(data.old_values, data.new_values);
                // Restaurar el botón (se manejará en la reclasificación)
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            } else {
                showAlertModal('Clasificación guardada', 'Los cambios han sido guardados exitosamente.', 'success');
                // Actualizar la sección de consenso inmediatamente
                await updateConsensusDisplay();
                
                // Actualizar los valores mostrados en el formulario
                updateFormValues(data.new_values);
                
                // Restaurar el botón
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        } else {
            showAlertModal('Error', data.error || 'Error al guardar la clasificación', 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    } catch (error) {
        console.error('Error:', error);
        showAlertModal('Error', 'Error de conexión al guardar la clasificación', 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    } finally {
        // Restaurar estado después de un tiempo
        setTimeout(() => {
            isSubmitting = false;
        }, 1000);
    }
    
    return false; // Asegurar que no se propague
}

// Actualizar los valores del formulario después de guardar
function updateFormValues(newValues) {
    // Actualizar categoría GTD
    const gtdCategorySelect = document.getElementById('gtdCategory');
    if (gtdCategorySelect && newValues.gtd_category) {
        gtdCategorySelect.value = newValues.gtd_category;
    }
    
    // Actualizar tipo de acción
    const actionTypeSelect = document.getElementById('actionType');
    if (actionTypeSelect) {
        if (newValues.action_type) {
            actionTypeSelect.value = newValues.action_type;
        } else {
            actionTypeSelect.value = '';
        }
    }
    
    // Actualizar prioridad
    const prioritySelect = document.getElementById('priority');
    if (prioritySelect && newValues.priority) {
        prioritySelect.value = newValues.priority;
    }
    
    // Actualizar confianza si está presente
    const confidenceRange = document.getElementById('confidenceRange');
    const confidenceValue = document.getElementById('confidenceValue');
    if (confidenceRange && newValues.confidence) {
        confidenceRange.value = newValues.confidence;
        if (confidenceValue) confidenceValue.textContent = newValues.confidence;
    }
}

// Mostrar vista previa de reclasificación - CORREGIDA
function showReclassifyPreview(oldValues, newValues) {
    const oldPreview = document.getElementById('oldClassificationPreview');
    const newPreview = document.getElementById('newClassificationPreview');
    
    if (oldPreview && newPreview) {
        oldPreview.innerHTML = `
            <span class="badge bg-secondary me-1">${oldValues.gtd_category || 'No definida'}</span>
            <span class="badge bg-info me-1">${oldValues.action_type || 'No definida'}</span>
            <span class="badge bg-${oldValues.priority === 'alta' ? 'danger' : oldValues.priority === 'media' ? 'warning' : 'success'}">${oldValues.priority || 'media'}</span>
        `;
        
        newPreview.innerHTML = `
            <span class="badge bg-secondary me-1">${newValues.gtd_category}</span>
            <span class="badge bg-info me-1">${newValues.action_type || 'No definida'}</span>
            <span class="badge bg-${newValues.priority === 'alta' ? 'danger' : newValues.priority === 'media' ? 'warning' : 'success'}">${newValues.priority}</span>
        `;
        
        // Guardar los datos para la confirmación
        window.pendingClassification = {
            old: oldValues,
            new: newValues
        };
        
        // Mostrar modal de confirmación
        const modal = new bootstrap.Modal(document.getElementById('reclassifyConfirmModal'));
        modal.show();
    }
}

// Confirmar reclasificación - CORREGIDA
function confirmReclassification() {
    if (!window.pendingClassification) return;
    
    // Cerrar modal de confirmación
    const confirmModal = bootstrap.Modal.getInstance(document.getElementById('reclassifyConfirmModal'));
    if (confirmModal) {
        confirmModal.hide();
    }
    
    const submitBtn = document.getElementById('saveClassificationBtn');
    if (!submitBtn) return;
    
    const originalText = submitBtn.innerHTML;
    
    // Mostrar estado de carga
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Reclasificando...';
    
    // Enviar el formulario realmente
    const form = document.getElementById('classificationForm');
    const formData = new FormData(form);
    
    // Agregar indicador de reclasificación
    formData.append('reclassification', 'true');
    
    // Enviar el formulario vía fetch
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlertModal('Reclasificación exitosa', 'El item ha sido reclasificado correctamente.', 'success');
            // Actualizar consenso
            updateConsensusDisplay();
            // Actualizar valores del formulario
            updateFormValues(data.new_values);
        } else {
            showAlertModal('Error', data.error || 'Error al reclasificar', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlertModal('Error', 'Error al procesar la reclasificación', 'danger');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
        window.pendingClassification = null;
        isSubmitting = false;
    });
}

// Cargar historial de clasificaciones - MEJORADA
async function loadClassificationHistory() {
    const historyList = document.getElementById('classificationHistoryList');
    if (!historyList) return;
    
    const itemId = document.querySelector('[data-inbox-item-id]')?.dataset.inboxItemId;
    if (!itemId) {
        historyList.innerHTML = '<div class="alert alert-danger text-center">ID de item no encontrado</div>';
        return;
    }
    
    historyList.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-warning" role="status"></div><p class="mt-2">Cargando historial...</p></div>';
    
    try {
        const response = await fetch(`/events/inbox/api/classification-history/${itemId}/`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        if (data.success && data.history && data.history.length > 0) {
            let html = '<div class="timeline">';
            
            data.history.forEach((item, index) => {
                const date = new Date(item.created_at);
                const formattedDate = date.toLocaleDateString('es-ES', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                html += `
                    <div class="timeline-item ${index === 0 ? 'latest' : ''}">
                        <div class="timeline-badge ${item.action === 'reclassified' ? 'bg-warning' : 'bg-info'}">
                            <i class="bi ${item.action === 'reclassified' ? 'bi-arrow-repeat' : 'bi-tag'}"></i>
                        </div>
                        <div class="timeline-content card mb-3">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <h6 class="card-subtitle mb-2 text-muted">
                                        <i class="bi bi-person-circle me-1"></i>${item.user || 'Sistema'}
                                    </h6>
                                    <small class="text-muted">${formattedDate}</small>
                                </div>
                                <div class="row mt-2">
                                    <div class="col-md-6">
                                        <strong>Anterior:</strong><br>
                                        <span class="badge bg-secondary me-1">${item.old_values?.gtd_category || 'N/A'}</span>
                                        <span class="badge bg-info me-1">${item.old_values?.action_type || 'N/A'}</span>
                                        <span class="badge bg-${item.old_values?.priority === 'alta' ? 'danger' : item.old_values?.priority === 'media' ? 'warning' : 'success'}">${item.old_values?.priority || 'N/A'}</span>
                                    </div>
                                    <div class="col-md-6">
                                        <strong>Nueva:</strong><br>
                                        <span class="badge bg-secondary me-1">${item.new_values?.gtd_category || 'N/A'}</span>
                                        <span class="badge bg-info me-1">${item.new_values?.action_type || 'N/A'}</span>
                                        <span class="badge bg-${item.new_values?.priority === 'alta' ? 'danger' : item.new_values?.priority === 'media' ? 'warning' : 'success'}">${item.new_values?.priority || 'N/A'}</span>
                                    </div>
                                </div>
                                ${item.notes ? `<p class="mt-2 mb-0 small"><i class="bi bi-chat-text me-1"></i>${item.notes}</p>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            historyList.innerHTML = html;
        } else {
            historyList.innerHTML = '<div class="alert alert-info text-center">No hay historial de clasificaciones para este item.</div>';
        }
    } catch (error) {
        console.error('Error cargando historial:', error);
        historyList.innerHTML = '<div class="alert alert-danger text-center">Error al cargar el historial de clasificaciones.</div>';
    }
}

// Función para reclasificar rápidamente desde el panel
window.quickReclassify = function(category, action, priority) {
    const form = document.getElementById('classificationForm');
    if (!form) return;
    
    // Actualizar valores del formulario
    if (category) document.querySelector('[name="gtd_category"]').value = category;
    if (action) document.querySelector('[name="action_type"]').value = action;
    if (priority) document.querySelector('[name="priority"]').value = priority;
    
    // Enviar formulario si no está enviando
    if (!isSubmitting) {
        // Disparar el evento submit
        const event = new Event('submit', { cancelable: true });
        form.dispatchEvent(event);
    }
};

// ============================================================================
// FUNCIÓN PARA ACTUALIZAR EL CONSENSO - MEJORADA
// ============================================================================

// Actualizar la sección de consenso después de una clasificación
async function updateConsensusDisplay() {
    const itemId = document.querySelector('[data-inbox-item-id]')?.dataset.inboxItemId;
    if (!itemId) return;
    
    try {
        const response = await fetch(`/events/inbox/api/consensus/${itemId}/`);
        if (!response.ok) return;
        
        const data = await response.json();
        
        if (data.success) {
            // Actualizar categoría de consenso
            const consensusCategoryEl = document.querySelector('.consensus-item:first-child .badge');
            if (consensusCategoryEl) {
                consensusCategoryEl.textContent = data.consensus_category ? 
                    data.consensus_category.charAt(0).toUpperCase() + data.consensus_category.slice(1) : 
                    'Sin consenso';
            }
            
            // Actualizar tipo de acción de consenso
            const consensusActionEl = document.querySelector('.consensus-item:nth-child(2) .badge');
            if (consensusActionEl) {
                consensusActionEl.textContent = data.consensus_action ? 
                    data.consensus_action.charAt(0).toUpperCase() + data.consensus_action.slice(1) : 
                    'Sin consenso';
            }
            
            // Actualizar número de votos
            const votesEl = document.querySelector('.consensus-item:last-child .badge');
            if (votesEl) {
                votesEl.textContent = `${data.votes} usuario(s)`;
            }
            
            console.log('Consenso actualizado:', data);
        }
    } catch (error) {
        console.error('Error actualizando consenso:', error);
    }
}