// process_inbox_item.js
// Funciones JavaScript para la vista de procesamiento de inbox items

// ============================================================================
// CONSTANTES Y CONFIGURACIÓN
// ============================================================================

const API_ENDPOINTS = {
    TASKS: '/events/inbox/api/tasks/',
    PROJECTS: '/events/inbox/api/projects/',
    BULK_ACTION: '/events/inbox/admin/bulk-action/'
};

const EVENT_LISTENERS = {
    TASK_SEARCH: 'taskSearch',
    PROJECT_SEARCH: 'projectSearch',
    TASK_ITEMS: 'taskList',
    PROJECT_ITEMS: 'projectList'
};

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

/**
 * Muestra un modal de alerta
 */
function showAlertModal(title, message, type = 'info') {
    const modal = new bootstrap.Modal(document.getElementById('alertModal'));
    const modalTitle = document.getElementById('alertModalLabel');
    const modalBody = document.getElementById('alertModalBody');

    const icons = {
        'success': 'bi-check-circle-fill text-success',
        'danger': 'bi-exclamation-triangle-fill text-danger',
        'warning': 'bi-exclamation-triangle-fill text-warning',
        'info': 'bi-info-circle-fill text-info'
    };

    modalTitle.innerHTML = `<i class="bi ${icons[type] || icons['info']} me-2"></i>${title}`;
    modalBody.innerHTML = `<p class="mb-0">${message}</p>`;

    modal.show();
}

/**
 * Muestra un modal de confirmación
 */
function showConfirmModal(title, message, type = 'warning', onConfirm, onCancel) {
    const modalHtml = `
        <div class="modal fade" id="confirmModal" tabindex="-1" aria-labelledby="confirmModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="confirmModalLabel">
                            <i class="bi bi-question-circle-fill text-${type} me-2"></i>${title}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p class="mb-0">${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="confirmCancelBtn">Cancelar</button>
                        <button type="button" class="btn btn-${type}" id="confirmOkBtn">Confirmar</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    const confirmBtn = document.getElementById('confirmOkBtn');
    const cancelBtn = document.getElementById('confirmCancelBtn');

    confirmBtn.addEventListener('click', () => {
        modal.hide();
        if (onConfirm) onConfirm();
        setTimeout(() => {
            document.getElementById('confirmModal').remove();
        }, 300);
    });

    cancelBtn.addEventListener('click', () => {
        modal.hide();
        if (onCancel) onCancel();
        setTimeout(() => {
            document.getElementById('confirmModal').remove();
        }, 300);
    });

    document.getElementById('confirmModal').addEventListener('hidden.bs.modal', () => {
        if (onCancel) onCancel();
        document.getElementById('confirmModal').remove();
    });

    modal.show();
}

/**
 * Obtiene el token CSRF del documento
 */
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

/**
 * Maneja errores de API de manera consistente
 */
function handleApiError(error, context = 'operación') {
    console.error(`[ERROR] ${context}:`, error);
    
    let errorMessage = 'Error en la operación';
    if (error instanceof Error) {
        errorMessage = error.message;
    } else if (typeof error === 'string') {
        errorMessage = error;
    }
    
    showAlertModal('Error', errorMessage, 'danger');
}

// ============================================================================
// FUNCIONES DE SELECTORES (TAREAS/PROYECTOS)
// ============================================================================

/**
 * Muestra el selector de tareas
 */
function showTaskSelector() {
    console.log('[SHOW_TASK_SELECTOR] Iniciando apertura del modal de tareas');
    const modal = new bootstrap.Modal(document.getElementById('taskSelectorModal'));
    modal.show();
    loadAvailableTasks();
}

/**
 * Carga tareas disponibles desde la API
 */
function loadAvailableTasks() {
    console.log('[LOAD_TASKS] Iniciando carga de tareas disponibles');
    const taskList = document.getElementById('taskList');
    if (!taskList) return;

    taskList.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Cargando tareas...</div>';

    fetch(API_ENDPOINTS.TASKS, {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (response.status === 404) {
            return loadSampleTasks();
        }
        return response.json();
    })
    .then(data => {
        if (data?.tasks?.length > 0) {
            console.log('[LOAD_TASKS] Datos recibidos:', data.tasks.length, 'tareas');
            renderTaskList(data.tasks);
        } else if (!data) {
            // Ya manejado por loadSampleTasks()
        } else {
            renderEmptyTaskList();
        }
    })
    .catch(error => {
        console.error('[LOAD_TASKS] Error:', error);
        renderTaskError();
    });
}

/**
 * Carga datos de ejemplo cuando la API no está disponible
 */
function loadSampleTasks() {
    const taskList = document.getElementById('taskList');
    const sampleTasks = [
        { 
            id: 1, 
            title: 'Revisar documentación del proyecto', 
            description: 'Actualizar la documentación técnica', 
            priority: 'alta',
            status: 'Pendiente'
        },
        { 
            id: 2, 
            title: 'Implementar nueva funcionalidad', 
            description: 'Desarrollar el módulo de reportes', 
            priority: 'media',
            status: 'En progreso'
        },
        { 
            id: 3, 
            title: 'Corregir bugs menores', 
            description: 'Arreglar issues reportados por usuarios', 
            priority: 'baja',
            status: 'Completado'
        }
    ];

    renderTaskList(sampleTasks);
}

/**
 * Renderiza la lista de tareas
 */
function renderTaskList(tasks) {
    const taskList = document.getElementById('taskList');
    
    taskList.innerHTML = tasks.map(task => `
        <div class="list-group-item task-item" onclick="selectTask(${task.id}, '${escapeHtml(task.title)}')">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${escapeHtml(task.title)}</h6>
                    <small class="text-muted">${escapeHtml(task.description || 'Sin descripción')}</small>
                </div>
                <div class="d-flex flex-column align-items-end gap-1">
                    <span class="badge bg-${getPriorityBadgeClass(task.priority)}">${task.priority || 'media'}</span>
                    <span class="badge bg-secondary">${task.status || 'Sin estado'}</span>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Renderiza lista vacía de tareas
 */
function renderEmptyTaskList() {
    const taskList = document.getElementById('taskList');
    taskList.innerHTML = '<div class="text-center text-muted py-3">No hay tareas disponibles</div>';
}

/**
 * Renderiza error en carga de tareas
 */
function renderTaskError() {
    const taskList = document.getElementById('taskList');
    taskList.innerHTML = '<div class="text-center text-danger py-3">Error al cargar tareas</div>';
    showAlertModal('Error', 'No se pudieron cargar las tareas disponibles', 'danger');
}

/**
 * Selecciona una tarea
 */
function selectTask(taskId, taskTitle) {
    console.log('[SELECT_TASK] Tarea seleccionada:', taskId, taskTitle);
    
    const selectedTaskInfo = document.getElementById('selectedTaskInfo');
    if (selectedTaskInfo) {
        selectedTaskInfo.innerHTML = `
            <div class="selected-info-panel">
                <h6 class="mb-1"><i class="bi bi-check-circle me-2"></i>Tarea Seleccionada</h6>
                <p class="mb-0">${taskTitle}</p>
                <input type="hidden" name="task_id" value="${taskId}">
                <div class="mt-2">
                    <button type="submit" name="action" value="link_to_task" class="btn btn-success btn-sm">
                        <i class="bi bi-link me-1"></i>Vincular a esta tarea
                    </button>
                </div>
            </div>
        `;
    }
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('taskSelectorModal'));
    if (modal) modal.hide();
    
    scrollToElement('selectedTaskInfo');
}

// ============================================================================
// FUNCIONES DE PROYECTOS
// ============================================================================

/**
 * Muestra el selector de proyectos
 */
function showProjectSelector() {
    console.log('[SHOW_PROJECT_SELECTOR] Iniciando apertura del modal de proyectos');
    const modal = new bootstrap.Modal(document.getElementById('projectSelectorModal'));
    modal.show();
    loadAvailableProjects();
}

/**
 * Carga proyectos disponibles desde la API
 */
function loadAvailableProjects() {
    console.log('[LOAD_PROJECTS] Iniciando carga de proyectos disponibles');
    const projectList = document.getElementById('projectList');
    if (!projectList) return;

    projectList.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Cargando proyectos...</div>';

    fetch(API_ENDPOINTS.PROJECTS, {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (response.status === 404) {
            return loadSampleProjects();
        }
        return response.json();
    })
    .then(data => {
        if (data?.projects?.length > 0) {
            console.log('[LOAD_PROJECTS] Datos recibidos:', data.projects.length, 'proyectos');
            renderProjectList(data.projects);
        } else if (!data) {
            // Ya manejado por loadSampleProjects()
        } else {
            renderEmptyProjectList();
        }
    })
    .catch(error => {
        console.error('[LOAD_PROJECTS] Error:', error);
        renderProjectError();
    });
}

/**
 * Carga datos de ejemplo para proyectos
 */
function loadSampleProjects() {
    const projectList = document.getElementById('projectList');
    const sampleProjects = [
        { 
            id: 1, 
            title: 'Sistema de Gestión de Proyectos', 
            description: 'Desarrollo completo del sistema GTD', 
            status: 'En progreso',
            task_count: 15
        },
        { 
            id: 2, 
            title: 'Migración a nueva plataforma', 
            description: 'Actualización tecnológica del sistema', 
            status: 'Planificación',
            task_count: 8
        },
        { 
            id: 3, 
            title: 'Implementación de API REST', 
            description: 'Desarrollo de endpoints para integración', 
            status: 'Pendiente',
            task_count: 5
        }
    ];

    renderProjectList(sampleProjects);
}

/**
 * Renderiza la lista de proyectos
 */
function renderProjectList(projects) {
    const projectList = document.getElementById('projectList');
    
    projectList.innerHTML = projects.map(project => `
        <div class="list-group-item project-item" onclick="selectProject(${project.id}, '${escapeHtml(project.title)}')">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${escapeHtml(project.title)}</h6>
                    <small class="text-muted">${escapeHtml(project.description || 'Sin descripción')}</small>
                    ${project.task_count ? `<small class="d-block text-info mt-1"><i class="bi bi-list-task me-1"></i>${project.task_count} tareas</small>` : ''}
                </div>
                <span class="badge ${getStatusBadgeClass(project.status)}">${project.status || 'Sin estado'}</span>
            </div>
        </div>
    `).join('');
}

/**
 * Renderiza lista vacía de proyectos
 */
function renderEmptyProjectList() {
    const projectList = document.getElementById('projectList');
    projectList.innerHTML = '<div class="text-center text-muted py-3">No hay proyectos disponibles</div>';
}

/**
 * Renderiza error en carga de proyectos
 */
function renderProjectError() {
    const projectList = document.getElementById('projectList');
    projectList.innerHTML = '<div class="text-center text-danger py-3">Error al cargar proyectos</div>';
    showAlertModal('Error', 'No se pudieron cargar los proyectos disponibles', 'danger');
}

/**
 * Selecciona un proyecto
 */
function selectProject(projectId, projectTitle) {
    console.log('[SELECT_PROJECT] Proyecto seleccionado:', projectId, projectTitle);
    
    const selectedProjectInfo = document.getElementById('selectedProjectInfo');
    if (selectedProjectInfo) {
        selectedProjectInfo.innerHTML = `
            <div class="selected-info-panel">
                <h6 class="mb-1"><i class="bi bi-check-circle me-2"></i>Proyecto Seleccionado</h6>
                <p class="mb-0">${projectTitle}</p>
                <input type="hidden" name="project_id" value="${projectId}">
                <div class="mt-2">
                    <button type="submit" name="action" value="link_to_project" class="btn btn-success btn-sm">
                        <i class="bi bi-link me-1"></i>Vincular a este proyecto
                    </button>
                </div>
            </div>
        `;
    }
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('projectSelectorModal'));
    if (modal) modal.hide();
    
    scrollToElement('selectedProjectInfo');
}

// ============================================================================
// FUNCIONES DE BÚSQUEDA Y FILTRADO
// ============================================================================

/**
 * Inicializa la búsqueda en tiempo real para tareas
 */
function initTaskSearch() {
    const taskSearch = document.getElementById('taskSearch');
    if (taskSearch) {
        taskSearch.addEventListener('input', function() {
            filterListItems('taskList', this.value.toLowerCase());
        });
    }
}

/**
 * Inicializa la búsqueda en tiempo real para proyectos
 */
function initProjectSearch() {
    const projectSearch = document.getElementById('projectSearch');
    if (projectSearch) {
        projectSearch.addEventListener('input', function() {
            filterListItems('projectList', this.value.toLowerCase());
        });
    }
}

/**
 * Filtra elementos de lista por término de búsqueda
 */
function filterListItems(listId, searchTerm) {
    const items = document.querySelectorAll(`#${listId} .list-group-item`);
    
    items.forEach(item => {
        const title = item.querySelector('h6')?.textContent?.toLowerCase() || '';
        const description = item.querySelector('small')?.textContent?.toLowerCase() || '';
        
        if (title.includes(searchTerm) || description.includes(searchTerm)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

// ============================================================================
// FUNCIONES DE GESTIÓN DE INBOX ITEMS
// ============================================================================

/**
 * Elimina un item del inbox
 */
function deleteInboxItem(itemId, title) {
    console.log('[DELETE_INBOX_ITEM] Iniciando eliminación:', itemId, title);
    
    showConfirmModal(
        `¿Eliminar item?`,
        `¿Estás seguro de que quieres eliminar "${title}"? Esta acción no se puede deshacer.`,
        'danger',
        () => {
            console.log('[DELETE_INBOX_ITEM] Usuario confirmó eliminación');
            performDeleteInboxItem(itemId);
        },
        () => {
            console.log('[DELETE_INBOX_ITEM] Usuario canceló eliminación');
        }
    );
}

/**
 * Realiza la eliminación del item
 */
function performDeleteInboxItem(itemId) {
    const csrfToken = getCSRFToken();
    
    fetch(API_ENDPOINTS.BULK_ACTION, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `action=delete&selected_items=${itemId}`
    })
    .then(response => response.text())
    .then(text => {
        try {
            const data = JSON.parse(text);
            handleDeleteResponse(data);
        } catch (error) {
            console.error('[DELETE_INBOX_ITEM] Error parseando respuesta:', error);
            showAlertModal('Error', 'Respuesta inválida del servidor', 'danger');
        }
    })
    .catch(error => {
        console.error('[DELETE_INBOX_ITEM] Error en la solicitud:', error);
        showAlertModal('Error', 'Error de conexión con el servidor', 'danger');
    });
}

/**
 * Maneja la respuesta de eliminación
 */
function handleDeleteResponse(data) {
    if (data.success) {
        showAlertModal('Item eliminado', 'El item ha sido eliminado exitosamente.', 'success');
        setTimeout(() => {
            window.location.href = '/events/inbox/';
        }, 1500);
    } else {
        showAlertModal('Error al eliminar', data.error || 'Error desconocido', 'danger');
    }
}

// ============================================================================
// FUNCIONES AUXILIARES
// ============================================================================

/**
 * Obtiene la clase CSS para badges de prioridad
 */
function getPriorityBadgeClass(priority) {
    const classes = {
        'alta': 'danger',
        'media': 'warning',
        'baja': 'secondary',
        'high': 'danger',
        'medium': 'warning',
        'low': 'secondary'
    };
    return classes[priority?.toLowerCase()] || 'secondary';
}

/**
 * Obtiene la clase CSS para badges de estado
 */
function getStatusBadgeClass(status) {
    const classes = {
        'en progreso': 'bg-primary',
        'planificación': 'bg-info',
        'pendiente': 'bg-warning',
        'completado': 'bg-success',
        'cancelado': 'bg-danger'
    };
    return classes[status?.toLowerCase()] || 'bg-secondary';
}

/**
 * Escapa HTML para prevenir XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Desplaza la vista a un elemento específico
 */
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Alterna entre vista de cuadrícula y lista
 */
function toggleActionView(viewType) {
    const actionCards = document.querySelectorAll('.action-card');
    
    actionCards.forEach(card => {
        if (viewType === 'list') {
            card.classList.add('list-view');
            card.classList.remove('grid-view');
        } else {
            card.classList.add('grid-view');
            card.classList.remove('list-view');
        }
    });
    
    // Actualizar estado del botón
    const buttons = document.querySelectorAll('.btn-group-sm .btn');
    buttons.forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
}

// ============================================================================
// FUNCIONES DE INICIALIZACIÓN
// ============================================================================

/**
 * Inicializa todas las funcionalidades cuando el DOM está listo
 */
function initializeInboxProcessing() {
    console.log('[INIT] Inicializando procesamiento de inbox');
    
    // Inicializar búsquedas
    initTaskSearch();
    initProjectSearch();
    
    // Configurar event listeners para formularios
    setupFormListeners();
    
    // Configurar animaciones y efectos
    setupAnimations();
    
    console.log('[INIT] Procesamiento de inbox inicializado');
}

/**
 * Configura listeners para formularios
 */
function setupFormListeners() {
    const processForm = document.getElementById('processForm');
    if (processForm) {
        processForm.addEventListener('submit', function(event) {
            // Validación adicional antes de enviar
            const action = event.submitter?.value;
            if (action === 'link_to_task' && !this.querySelector('[name="task_id"]')) {
                event.preventDefault();
                showAlertModal('Selección requerida', 'Por favor selecciona una tarea primero', 'warning');
                return;
            }
            if (action === 'link_to_project' && !this.querySelector('[name="project_id"]')) {
                event.preventDefault();
                showAlertModal('Selección requerida', 'Por favor selecciona un proyecto primero', 'warning');
                return;
            }
            
            // Mostrar indicador de procesamiento
            const submitButton = event.submitter;
            if (submitButton) {
                const originalText = submitButton.innerHTML;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';
                submitButton.disabled = true;
                
                // Restaurar después de 5 segundos por si algo falla
                setTimeout(() => {
                    submitButton.innerHTML = originalText;
                    submitButton.disabled = false;
                }, 5000);
            }
        });
    }
}

/**
 * Configura animaciones y efectos visuales
 */
function setupAnimations() {
    // Efecto hover en tarjetas de acción
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.zIndex = '10';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.zIndex = '1';
        });
    });
    
    // Efecto click en items de lista
    const listItems = document.querySelectorAll('.task-item, .project-item');
    listItems.forEach(item => {
        item.addEventListener('click', function() {
            // Remover selección anterior
            this.parentNode.querySelectorAll('.selected').forEach(selected => {
                selected.classList.remove('selected');
            });
            // Agregar selección actual
            this.classList.add('selected');
        });
    });
}

// ============================================================================
// EVENTOS GLOBALES
// ============================================================================

/**
 * Maneja errores no capturados
 */
window.addEventListener('error', function(event) {
    console.error('[GLOBAL_ERROR]', event.error);
    showAlertModal('Error inesperado', 'Ocurrió un error inesperado. Por favor recarga la página.', 'danger');
});

/**
 * Maneja promesas rechazadas no capturadas
 */
window.addEventListener('unhandledrejection', function(event) {
    console.error('[UNHANDLED_REJECTION]', event.reason);
    showAlertModal('Error en promesa', 'Ocurrió un error en una operación asíncrona.', 'warning');
});

// ============================================================================
// INICIALIZACIÓN CUANDO EL DOM ESTÁ LISTO
// ============================================================================

document.addEventListener('DOMContentLoaded', initializeInboxProcessing);

// ============================================================================
// EXPORTACIONES (para módulos)
// ============================================================================

// Exportar funciones principales para uso en otros módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showAlertModal,
        showConfirmModal,
        showTaskSelector,
        showProjectSelector,
        deleteInboxItem,
        initializeInboxProcessing
    };
}