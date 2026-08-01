// static/events/js/task-panel.js

document.addEventListener('DOMContentLoaded', function() {
    // ============================================================
    // ESTADO GLOBAL DE LA APLICACIÓN
    // ============================================================
    const AppState = {
        tasks: new Map(), // Almacena datos de tareas por ID
        filters: {
            status: '',
            project: '',
            search: ''
        },
        selectedTasks: new Set(),
        views: {
            current: localStorage.getItem('taskViewPreference') || 'table',
            compact: localStorage.getItem('compactView') === 'true'
        },
        stats: {
            total: 0,
            visible: 0,
            completed: 0,
            inProgress: 0,
            blocked: 0,
            pending: 0
        },
        projects: new Map(), // Almacena datos de proyectos
        statusColors: {
            'In Progress': '#007bff',
            'Completed': '#28a745',
            'Blocked': '#dc3545',
            'To Do': '#6c757d'
        }
    };

    // ============================================================
    // INICIALIZACIÓN DE DATOS
    // ============================================================
    function initializeTaskData() {
        // Inicializar desde vista tabla (fuente principal de datos)
        document.querySelectorAll('.task-row').forEach(row => {
            const taskId = row.dataset.taskId;
            const taskData = {
                id: taskId,
                status: row.dataset.status,
                priority: row.dataset.priority,
                project: row.dataset.project,
                projectStatus: row.dataset.projectStatus,
                dueDate: row.dataset.dueDate,
                title: row.querySelector('.task-title')?.textContent.trim() || '',
                assignedTo: row.querySelector('.task-assigned')?.textContent.trim() || '',
                element: row,
                // Guardar referencias a elementos en otras vistas
                kanbanElements: [],
                cardElements: []
            };
            
            AppState.tasks.set(taskId, taskData);
        });
        
        // Sincronizar con vista kanban
        document.querySelectorAll('.kanban-card').forEach(card => {
            const taskId = card.dataset.taskId;
            if (AppState.tasks.has(taskId)) {
                AppState.tasks.get(taskId).kanbanElements.push(card);
            }
        });
        
        // Sincronizar con vista cards
        document.querySelectorAll('#cardsContainer .card').forEach(card => {
            const switch_ = card.querySelector('.task-status-switch');
            if (switch_) {
                const taskId = switch_.dataset.taskId;
                if (AppState.tasks.has(taskId)) {
                    AppState.tasks.get(taskId).cardElements.push(card);
                }
            }
        });
        
        updateStats();
    }

    // ============================================================
    // FUNCIONES DE UTILIDAD
    // ============================================================
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'danger'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        const container = document.querySelector('.toast-container') || createToastContainer();
        container.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    function createToastContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }

    function changeTaskStatusAjax(taskId, newStatusName, action = null) {
        const statusUrl = window.taskPanelConfig.changeStatusUrl;
        const formData = new FormData();
        formData.append('task_id', taskId);
        
        if (action) {
            formData.append('action', action);
        } else {
            formData.append('new_status_name', newStatusName);
        }
        
        return fetch(statusUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                return data;
            } else {
                throw new Error(data.error || 'Error updating task status');
            }
        });
    }

    // ============================================================
    // ACTUALIZACIÓN DE UI (TODAS LAS VISTAS)
    // ============================================================
    function updateTaskStatus(taskId, newStatus) {
        const task = AppState.tasks.get(taskId);
        if (!task) return;
        
        const oldStatus = task.status;
        task.status = newStatus;
        
        // Actualizar vista tabla
        updateTableRow(taskId, newStatus);
        
        // Actualizar vista kanban
        updateKanbanCards(taskId, newStatus, oldStatus);
        
        // Actualizar vista cards
        updateCardsView(taskId, newStatus);
        
        // Actualizar estadísticas
        updateStats();
        
        // Re-aplicar filtros si es necesario
        if (AppState.filters.status || AppState.filters.project || AppState.filters.search) {
            filterTasks();
        }
        
        // Efecto visual de actualización
        highlightUpdatedTask(taskId);
    }

    function updateTableRow(taskId, newStatus) {
        const taskRow = document.querySelector(`tr[data-task-id="${taskId}"]`);
        if (!taskRow) return;
        
        // Actualizar atributo data-status
        taskRow.setAttribute('data-status', newStatus);
        
        // Actualizar badge de estado
        const statusBadge = taskRow.querySelector('.status-badge');
        if (statusBadge) {
            const iconElement = statusBadge.querySelector('.status-icon');
            const iconHTML = iconElement ? iconElement.outerHTML + ' ' : '';
            const statusText = statusBadge.querySelector('.status-text');
            if (statusText) statusText.textContent = newStatus;
            
            statusBadge.style.backgroundColor = AppState.statusColors[newStatus] || '#6c757d';
        }
        
        // Actualizar indicador de estado
        const statusIndicator = taskRow.querySelector('.status-indicator');
        if (statusIndicator) {
            const indicators = {
                'In Progress': '<i class="bi bi-arrow-clockwise"></i> Active',
                'Completed': '<i class="bi bi-check-circle"></i> Done',
                'Blocked': '<i class="bi bi-slash-circle"></i> Blocked',
                'To Do': '<i class="bi bi-circle"></i> Pending'
            };
            statusIndicator.innerHTML = indicators[newStatus] || '';
        }
        
        // Actualizar barra de progreso
        const progressBar = taskRow.querySelector('.task-progress-bar');
        if (progressBar) {
            if (newStatus === 'Completed') {
                progressBar.style.width = '100%';
                progressBar.className = 'progress-bar bg-success task-progress-bar';
            } else if (newStatus === 'In Progress') {
                progressBar.style.width = '50%';
                progressBar.className = 'progress-bar bg-primary task-progress-bar';
            } else {
                progressBar.style.width = '0%';
                progressBar.className = 'progress-bar bg-secondary task-progress-bar';
            }
        }
        
        // Actualizar duración
        const durationCell = taskRow.querySelector('.duration-cell');
        if (durationCell) {
            if (newStatus === 'In Progress') {
                durationCell.innerHTML = `
                    <div class="d-flex flex-column">
                        <small class="text-info d-block duration-time">
                            <i class="bi bi-clock"></i> Just now
                        </small>
                        <small class="text-muted duration-status" style="font-size: 0.7rem;">Active</small>
                    </div>
                `;
            } else if (newStatus === 'Completed') {
                durationCell.innerHTML = `
                    <div class="d-flex flex-column">
                        <small class="text-success d-block duration-time">
                            <i class="bi bi-check-circle"></i> Completed
                        </small>
                        <small class="text-muted duration-status" style="font-size: 0.7rem;">Done</small>
                    </div>
                `;
            } else {
                durationCell.innerHTML = '<small class="text-muted">-</small>';
            }
        }
        
        // Actualizar controles extendidos
        const extendedControls = taskRow.querySelector('.task-extended-controls');
        const switchElement = taskRow.querySelector('.task-status-switch');
        
        if (extendedControls) {
            if (newStatus === 'In Progress') {
                extendedControls.classList.remove('d-none');
            } else {
                extendedControls.classList.add('d-none');
                const completeCheckbox = extendedControls.querySelector('.task-complete-checkbox');
                if (completeCheckbox) completeCheckbox.checked = false;
            }
        }
        
        if (switchElement) {
            switchElement.checked = newStatus === 'In Progress';
            switchElement.disabled = newStatus === 'Completed';
        }
    }

    function updateKanbanCards(taskId, newStatus, oldStatus) {
        const task = AppState.tasks.get(taskId);
        if (!task) return;
        
        task.kanbanElements.forEach(card => {
            if (!card) return;
            
            // Mover tarjeta a la columna correspondiente
            const targetColumn = document.querySelector(`.kanban-column-body[data-status="${getStatusId(newStatus)}"]`);
            const sourceColumn = card.closest('.kanban-column-body');
            
            if (targetColumn && sourceColumn !== targetColumn) {
                // Clonar para mantener eventos
                const newCard = card.cloneNode(true);
                newCard.dataset.taskId = taskId;
                
                // Actualizar contenido de la tarjeta
                const statusBadge = newCard.querySelector('.badge');
                if (statusBadge) {
                    statusBadge.style.backgroundColor = AppState.statusColors[newStatus] || '#6c757d';
                    statusBadge.innerHTML = getStatusIcon(newStatus) + ' ' + newStatus;
                }
                
                const switch_ = newCard.querySelector('.task-status-switch');
                if (switch_) {
                    switch_.checked = newStatus === 'In Progress';
                    switch_.disabled = newStatus === 'Completed';
                }
                
                // Reemplazar en el DOM
                targetColumn.appendChild(newCard);
                card.remove();
                
                // Actualizar referencia
                const index = task.kanbanElements.indexOf(card);
                task.kanbanElements[index] = newCard;
                
                // Re-attach event listeners
                attachKanbanEvents(newCard);
            } else {
                // Solo actualizar contenido si está en la misma columna
                const statusBadge = card.querySelector('.badge');
                if (statusBadge) {
                    statusBadge.style.backgroundColor = AppState.statusColors[newStatus] || '#6c757d';
                    statusBadge.innerHTML = getStatusIcon(newStatus) + ' ' + newStatus;
                }
                
                const switch_ = card.querySelector('.task-status-switch');
                if (switch_) {
                    switch_.checked = newStatus === 'In Progress';
                    switch_.disabled = newStatus === 'Completed';
                }
            }
        });
    }

    function updateCardsView(taskId, newStatus) {
        const task = AppState.tasks.get(taskId);
        if (!task) return;
        
        task.cardElements.forEach(card => {
            if (!card) return;
            
            // Actualizar badge de estado
            const statusBadge = card.querySelector('.badge');
            if (statusBadge) {
                statusBadge.style.backgroundColor = AppState.statusColors[newStatus] || '#6c757d';
                statusBadge.textContent = newStatus;
            }
            
            // Actualizar barra de progreso
            const progressBar = card.querySelector('.progress-bar');
            if (progressBar) {
                if (newStatus === 'Completed') {
                    progressBar.style.width = '100%';
                    progressBar.className = 'progress-bar bg-success';
                } else if (newStatus === 'In Progress') {
                    progressBar.style.width = '50%';
                    progressBar.className = 'progress-bar bg-primary';
                } else {
                    progressBar.style.width = '0%';
                    progressBar.className = 'progress-bar bg-secondary';
                }
            }
            
            // Actualizar switch
            const switch_ = card.querySelector('.task-status-switch');
            if (switch_) {
                switch_.checked = newStatus === 'In Progress';
                switch_.disabled = newStatus === 'Completed';
            }
        });
    }

    function getStatusIcon(status) {
        const icons = {
            'In Progress': '<i class="bi bi-arrow-repeat"></i>',
            'Completed': '<i class="bi bi-check-circle"></i>',
            'Blocked': '<i class="bi bi-exclamation-triangle"></i>',
            'To Do': '<i class="bi bi-circle"></i>'
        };
        return icons[status] || '';
    }

    function getStatusId(statusName) {
        const statusMap = {
            'To Do': 1,
            'In Progress': 2,
            'Completed': 3,
            'Blocked': 4
        };
        return statusMap[statusName] || 1;
    }

    function attachKanbanEvents(card) {
        // Drag and drop events
        card.setAttribute('draggable', 'true');
        
        card.addEventListener('dragstart', function(e) {
            this.classList.add('dragging');
            e.dataTransfer.setData('text/plain', this.dataset.taskId);
        });

        card.addEventListener('dragend', function(e) {
            this.classList.remove('dragging');
        });
        
        // Switch event
        const switch_ = card.querySelector('.task-status-switch');
        if (switch_) {
            switch_.removeEventListener('change', handleSwitchChange);
            switch_.addEventListener('change', handleSwitchChange);
        }
    }

    function handleSwitchChange(e) {
        e.stopPropagation();
        const switch_ = e.target;
        const taskId = switch_.dataset.taskId;
        const isChecked = switch_.checked;
        
        if (switch_.disabled) return;
        switch_.disabled = true;
        
        const action = isChecked ? 'activate' : 'deactivate';
        
        changeTaskStatusAjax(taskId, null, action)
            .then(data => {
                showToast(data.message || 'Estado actualizado', 'success');
                updateTaskStatus(taskId, isChecked ? 'In Progress' : 'To Do');
            })
            .catch(error => {
                console.error('Error:', error);
                switch_.checked = !isChecked;
                showToast(error.message, 'error');
            })
            .finally(() => {
                switch_.disabled = false;
            });
    }

    function highlightUpdatedTask(taskId) {
        // Resaltar la tarea actualizada en todas las vistas
        const selectors = [
            `tr[data-task-id="${taskId}"]`,
            `.kanban-card[data-task-id="${taskId}"]`,
            `#cardsContainer .card:has(.task-status-switch[data-task-id="${taskId}"])`
        ];
        
        selectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                el.classList.add('stat-updated');
                setTimeout(() => el.classList.remove('stat-updated'), 500);
            });
        });
    }

    // ============================================================
    // ACTUALIZACIÓN DE ESTADÍSTICAS
    // ============================================================
    function updateStats() {
        const totalTasks = AppState.tasks.size;
        let completed = 0, inProgress = 0, blocked = 0, pending = 0;
        
        AppState.tasks.forEach(task => {
            if (task.status === 'Completed') completed++;
            else if (task.status === 'In Progress') inProgress++;
            else if (task.status === 'Blocked') blocked++;
            else if (task.status === 'To Do') pending++;
        });
        
        AppState.stats = {
            total: totalTasks,
            visible: document.querySelectorAll('.task-row:not([style*="display: none"])').length,
            completed,
            inProgress,
            blocked,
            pending
        };
        
        updateStatsUI();
        updateProjectProgress();
    }

    function updateStatsUI() {
        const stats = AppState.stats;
        const total = stats.total || 1;
        
        // Actualizar contadores
        const elements = {
            total: document.getElementById('totalTasksCount'),
            inProgress: document.getElementById('inProgressTasksCount'),
            completed: document.getElementById('completedTasksCount'),
            pending: document.getElementById('pendingTasksCount'),
            visible: document.getElementById('visibleTasks')
        };
        
        if (elements.total) elements.total.textContent = stats.total;
        if (elements.inProgress) elements.inProgress.textContent = stats.inProgress;
        if (elements.completed) elements.completed.textContent = stats.completed;
        if (elements.pending) elements.pending.textContent = stats.pending;
        if (elements.visible) elements.visible.textContent = stats.visible;
        
        // Calcular porcentajes
        const percentages = {
            inProgress: Math.round((stats.inProgress / total) * 100) || 0,
            completed: Math.round((stats.completed / total) * 100) || 0,
            pending: Math.round((stats.pending / total) * 100) || 0
        };
        
        // Actualizar badges
        const badges = {
            inProgress: document.getElementById('inProgressPercentBadge'),
            completed: document.getElementById('completedPercentBadge'),
            pending: document.getElementById('pendingPercentBadge')
        };
        
        if (badges.inProgress) {
            badges.inProgress.textContent = percentages.inProgress + '%';
            updateBadgeColor(badges.inProgress, percentages.inProgress);
        }
        if (badges.completed) {
            badges.completed.textContent = percentages.completed + '%';
            updateBadgeColor(badges.completed, percentages.completed);
        }
        if (badges.pending) {
            badges.pending.textContent = percentages.pending + '%';
            updateBadgeColor(badges.pending, percentages.pending);
        }
        
        // Actualizar barras de progreso
        const progressBars = {
            inProgress: document.getElementById('inProgressProgressBar'),
            completed: document.getElementById('completedProgressBar'),
            pending: document.getElementById('pendingProgressBar')
        };
        
        if (progressBars.inProgress) progressBars.inProgress.style.width = percentages.inProgress + '%';
        if (progressBars.completed) progressBars.completed.style.width = percentages.completed + '%';
        if (progressBars.pending) progressBars.pending.style.width = percentages.pending + '%';
    }

    function updateBadgeColor(badge, percentage) {
        badge.classList.remove('bg-success', 'bg-warning', 'bg-danger', 'bg-opacity-10', 'text-success', 'text-warning', 'text-danger');
        
        if (percentage >= 70) {
            badge.classList.add('bg-success', 'bg-opacity-10', 'text-success');
        } else if (percentage >= 30) {
            badge.classList.add('bg-warning', 'bg-opacity-10', 'text-warning');
        } else {
            badge.classList.add('bg-danger', 'bg-opacity-10', 'text-danger');
        }
    }

    function updateProjectProgress() {
        const projectStats = new Map();
        
        AppState.tasks.forEach(task => {
            if (task.project) {
                if (!projectStats.has(task.project)) {
                    projectStats.set(task.project, {
                        total: 0,
                        completed: 0
                    });
                }
                const stats = projectStats.get(task.project);
                stats.total++;
                if (task.status === 'Completed') stats.completed++;
            }
        });
        
        projectStats.forEach((stats, projectId) => {
            const percentage = stats.total > 0 ? (stats.completed / stats.total * 100) : 0;
            document.querySelectorAll(`[data-project-id="${projectId}"] .project-progress`).forEach(el => {
                el.style.width = `${percentage}%`;
            });
        });
    }

    // ============================================================
    // FILTROS Y BÚSQUEDA
    // ============================================================
    function filterTasks() {
        const status = AppState.filters.status;
        const projectId = AppState.filters.project;
        const searchQuery = AppState.filters.search.toLowerCase();
        
        let visibleCount = 0;
        
        AppState.tasks.forEach(task => {
            const row = task.element;
            if (!row) return;
            
            const statusMatch = !status || task.status === status;
            const projectMatch = !projectId || task.project === projectId;
            const searchMatch = !searchQuery || 
                task.title.toLowerCase().includes(searchQuery) ||
                (task.assignedTo && task.assignedTo.toLowerCase().includes(searchQuery));
            
            const isVisible = statusMatch && projectMatch && searchMatch;
            
            // Actualizar visibilidad en tabla
            row.style.display = isVisible ? '' : 'none';
            
            // Actualizar visibilidad en kanban
            task.kanbanElements.forEach(card => {
                if (card) card.style.display = isVisible ? '' : 'none';
            });
            
            // Actualizar visibilidad en cards
            task.cardElements.forEach(card => {
                if (card) {
                    const cardContainer = card.closest('.col-xl-4, .col-lg-6, .col-md-6');
                    if (cardContainer) {
                        cardContainer.style.display = isVisible ? '' : 'none';
                    }
                }
            });
            
            if (isVisible) visibleCount++;
            
            // Deseleccionar si está oculto
            if (!isVisible) {
                const checkbox = row.querySelector('.task-checkbox');
                if (checkbox && checkbox.checked) {
                    checkbox.checked = false;
                    AppState.selectedTasks.delete(task.id);
                }
            }
        });
        
        AppState.stats.visible = visibleCount;
        updateStatsUI();
        updateSelectedCount();
    }

    // ============================================================
    // SELECCIÓN MASIVA
    // ============================================================
    const selectAllCheckbox = document.getElementById('selectAllTasks');
    const deleteSelectedBtn = document.getElementById('deleteSelected');
    const exportSelectedBtn = document.getElementById('exportSelected');

    function updateSelectedCount() {
        if (!deleteSelectedBtn || !exportSelectedBtn || !selectAllCheckbox) return;
        
        AppState.selectedTasks.clear();
        document.querySelectorAll('.task-checkbox:checked:not([style*="display: none"])').forEach(cb => {
            AppState.selectedTasks.add(cb.value);
        });
        
        const count = AppState.selectedTasks.size;
        const visibleCheckboxes = document.querySelectorAll('.task-checkbox:not([style*="display: none"])');
        const totalVisible = visibleCheckboxes.length;
        
        deleteSelectedBtn.disabled = count === 0;
        
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = count > 0 && count === totalVisible;
            selectAllCheckbox.indeterminate = count > 0 && count < totalVisible;
        }
        
        deleteSelectedBtn.innerHTML = `<i class="bi bi-trash"></i> Delete ${count > 0 ? `(${count})` : ''}`;
        exportSelectedBtn.innerHTML = `<i class="bi bi-download"></i> Export ${count > 0 ? `(${count})` : ''}`;
    }

    // ============================================================
    // VISTAS
    // ============================================================
    const viewButtons = document.querySelectorAll('[data-view]');
    const viewContainers = {
        'table': document.getElementById('tableView'),
        'kanban': document.getElementById('kanbanView'),
        'cards': document.getElementById('cardsView')
    };

    function switchView(view) {
        AppState.views.current = view;
        
        viewButtons.forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-view="${view}"]`)?.classList.add('active');
        
        Object.keys(viewContainers).forEach(key => {
            if (viewContainers[key]) {
                viewContainers[key].style.display = key === view ? 'block' : 'none';
            }
        });
        
        localStorage.setItem('taskViewPreference', view);
    }

    // ============================================================
    // COMPACT VIEW
    // ============================================================
    const compactToggle = document.getElementById('compactViewToggle');
    if (compactToggle) {
        const checkIcon = compactToggle.querySelector('.bi-check2');
        
        compactToggle.addEventListener('click', function(e) {
            e.preventDefault();
            const isActive = AppState.views.compact;
            
            if (isActive) {
                checkIcon.style.display = 'none';
                document.body.classList.remove('compact-view');
            } else {
                checkIcon.style.display = 'block';
                document.body.classList.add('compact-view');
            }
            
            AppState.views.compact = !isActive;
            localStorage.setItem('compactView', AppState.views.compact);
        });
        
        if (AppState.views.compact) {
            compactToggle.click();
        }
    }

    // ============================================================
    // MANEJADORES DE EVENTOS
    // ============================================================

    // Búsqueda
    const searchInput = document.getElementById('searchInput');
    let searchTimeout;

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                AppState.filters.search = this.value;
                filterTasks();
            }, 300);
        });
    }

    // Filtros
    const statusFilter = document.getElementById('statusFilter');
    const projectFilter = document.getElementById('projectFilter');
    const clearFiltersBtn = document.getElementById('clearFilters');

    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            AppState.filters.status = this.value;
            filterTasks();
        });
    }

    if (projectFilter) {
        projectFilter.addEventListener('change', function() {
            AppState.filters.project = this.value;
            filterTasks();
        });
    }

    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            if (searchInput) {
                searchInput.value = '';
                AppState.filters.search = '';
            }
            if (statusFilter) {
                statusFilter.value = '';
                AppState.filters.status = '';
            }
            if (projectFilter) {
                projectFilter.value = '';
                AppState.filters.project = '';
            }
            filterTasks();
        });
    }

    // Cambio de vista
    viewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const view = this.getAttribute('data-view');
            switchView(view);
        });
    });

    // Switches de estado (tabla)
    document.querySelectorAll('.task-status-switch').forEach(switchElement => {
        switchElement.addEventListener('change', handleSwitchChange);
    });

    // Checkbox de completado
    document.addEventListener('change', function(e) {
        const target = e.target;
        
        if (target.classList.contains('task-checkbox')) {
            updateSelectedCount();
            return;
        }
        
        if (target.classList.contains('task-complete-checkbox')) {
            e.stopPropagation();
            
            const checkbox = target;
            const taskId = checkbox.dataset.taskId;
            
            if (checkbox.checked && !checkbox.disabled) {
                if (confirm('¿Marcar como completada? Esto actualizará el proyecto asociado.')) {
                    checkbox.disabled = true;
                    
                    changeTaskStatusAjax(taskId, 'Completed')
                        .then(data => {
                            showToast('Tarea completada', 'success');
                            updateTaskStatus(taskId, 'Completed');
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            checkbox.checked = false;
                            showToast(error.message, 'error');
                        })
                        .finally(() => {
                            checkbox.disabled = false;
                        });
                } else {
                    checkbox.checked = false;
                }
            }
        }
    });

    // Opciones de estado
    document.addEventListener('click', function(e) {
        const target = e.target.closest('.task-status-option, .task-block-option');
        if (!target) return;
        
        e.preventDefault();
        e.stopPropagation();
        
        const taskId = target.dataset.taskId;
        
        if (target.classList.contains('task-status-option')) {
            const statusName = target.dataset.statusName;
            if (confirm(`¿Cambiar estado a "${statusName}"?`)) {
                changeTaskStatusAjax(taskId, statusName)
                    .then(data => {
                        showToast(`Estado cambiado a ${statusName}`, 'success');
                        updateTaskStatus(taskId, statusName);
                    })
                    .catch(error => {
                        showToast(error.message, 'error');
                    });
            }
        } else if (target.classList.contains('task-block-option')) {
            if (confirm('¿Marcar como Bloqueada?')) {
                changeTaskStatusAjax(taskId, 'Blocked')
                    .then(data => {
                        showToast('Tarea bloqueada', 'success');
                        updateTaskStatus(taskId, 'Blocked');
                    })
                    .catch(error => {
                        showToast(error.message, 'error');
                    });
            }
        }
    });

    // Seleccionar todos
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function(e) {
            e.stopPropagation();
            
            const isChecked = this.checked;
            document.querySelectorAll('.task-checkbox:not([style*="display: none"])').forEach(checkbox => {
                checkbox.checked = isChecked;
            });
            
            updateSelectedCount();
        });
    }

    // Acciones masivas
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', function() {
            const selectedIds = Array.from(AppState.selectedTasks);
            if (selectedIds.length === 0) return;
            
            if (confirm(`¿Eliminar ${selectedIds.length} tarea(s)?`)) {
                console.log('Bulk delete IDs:', selectedIds);
                showToast(`Eliminando ${selectedIds.length} tareas...`, 'info');
            }
        });
    }

    if (exportSelectedBtn) {
        exportSelectedBtn.addEventListener('click', function() {
            const selectedIds = Array.from(AppState.selectedTasks);
            if (selectedIds.length === 0) return;
            
            console.log('Export selected IDs:', selectedIds);
            showToast(`Exportando ${selectedIds.length} tareas...`, 'info');
        });
    }

    // Drag and drop para kanban
    document.querySelectorAll('.kanban-column-body').forEach(column => {
        column.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });

        column.addEventListener('dragleave', function(e) {
            this.classList.remove('drag-over');
        });

        column.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');

            const taskId = e.dataTransfer.getData('text/plain');
            const draggedCard = document.querySelector(`.kanban-card[data-task-id="${taskId}"]`);
            
            if (draggedCard) {
                const newStatus = getStatusNameFromColumn(this.dataset.status);
                if (newStatus) {
                    this.appendChild(draggedCard);
                    updateTaskStatus(taskId, newStatus);
                }
            }
        });
    });

    function getStatusNameFromColumn(statusId) {
        const statusMap = {
            '1': 'To Do',
            '2': 'In Progress',
            '3': 'Completed',
            '4': 'Blocked'
        };
        return statusMap[statusId];
    }

    // ============================================================
    // ATALOS DE TECLADO
    // ============================================================
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'f' && searchInput) {
            e.preventDefault();
            searchInput.focus();
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '3') {
            e.preventDefault();
            const viewIndex = parseInt(e.key) - 1;
            const views = ['table', 'kanban', 'cards'];
            switchView(views[viewIndex]);
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
            e.preventDefault();
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = !selectAllCheckbox.checked;
                selectAllCheckbox.dispatchEvent(new Event('change'));
            }
        }
    });

    // ============================================================
    // INICIALIZACIÓN
    // ============================================================
    initializeTaskData();
    updateStats();
    switchView(AppState.views.current);
    
    // Sincronización periódica
    setInterval(() => {
        console.log('Checking for updates...');
        // Aquí podrías hacer peticiones ligeras para actualizar datos
    }, 30000);

        // ============================================================
    // MANEJO DE COLUMNAS KANBAN DINÁMICAS (ACTUALIZADO)
    // ============================================================
    
    // Definición de todas las columnas posibles
    const KANBAN_COLUMNS = [
        { id: 1, name: 'To Do', icon: 'bi-list-task', color: 'bg-light', headerColor: 'bg-light' },
        { id: 2, name: 'In Progress', icon: 'bi-arrow-repeat', color: 'bg-warning', headerColor: 'bg-warning' },
        { id: 3, name: 'Completed', icon: 'bi-check-circle', color: 'bg-success', headerColor: 'bg-success' },
        { id: 4, name: 'Blocked', icon: 'bi-exclamation-triangle', color: 'bg-danger', headerColor: 'bg-danger' }
    ];
    
    function ensureKanbanColumn(statusName, statusId) {
        const columnWrapper = document.querySelector(`.kanban-column-wrapper[data-status-name="${statusName}"]`);
        
        if (columnWrapper) {
            return columnWrapper.querySelector('.kanban-column-body');
        }
        
        // Crear nueva columna si no existe
        return createKanbanColumn(statusName, statusId);
    }
    
    function createKanbanColumn(statusName, statusId) {
        const template = document.getElementById('kanban-column-template');
        const kanbanBoard = document.getElementById('kanbanBoard');
        
        if (!template || !kanbanBoard) return null;
        
        // Clonar el template
        const columnWrapper = template.content.cloneNode(true).querySelector('.kanban-column-wrapper');
        
        // Configurar atributos
        columnWrapper.dataset.statusId = statusId;
        columnWrapper.dataset.statusName = statusName;
        
        // Configurar header según el tipo de columna
        const columnConfig = KANBAN_COLUMNS.find(col => col.name === statusName) || KANBAN_COLUMNS[0];
        
        const header = columnWrapper.querySelector('.card-header');
        header.className = `card-header d-flex justify-content-between align-items-center ${columnConfig.headerColor}`;
        if (['In Progress', 'Completed', 'Blocked'].includes(statusName)) {
            header.querySelector('h6').classList.add('text-white');
            header.querySelector('small').classList.add('text-white-50');
        }
        
        // Configurar título e icono
        const titleSpan = columnWrapper.querySelector('.kanban-column-title');
        titleSpan.textContent = statusName;
        
        const icon = columnWrapper.querySelector('h6 i');
        icon.className = `bi ${columnConfig.icon} me-2`;
        
        // Configurar column body
        const columnBody = columnWrapper.querySelector('.kanban-column-body');
        columnBody.dataset.statusId = statusId;
        columnBody.dataset.statusName = statusName;
        
        // Configurar botón de añadir tarea
        const addBtn = columnWrapper.querySelector('.add-task-btn');
        addBtn.href = `/events/tasks/create/?status=${statusId}`;
        
        // Añadir al board
        kanbanBoard.appendChild(columnWrapper);
        
        // Configurar eventos drag & drop
        setupKanbanColumnEvents(columnBody);
        
        return columnBody;
    }
    
    function setupKanbanColumnEvents(columnBody) {
        columnBody.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });
    
        columnBody.addEventListener('dragleave', function(e) {
            this.classList.remove('drag-over');
        });
    
        columnBody.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
    
            const taskId = e.dataTransfer.getData('text/plain');
            const draggedCard = document.querySelector(`.kanban-card[data-task-id="${taskId}"]`);
            
            if (draggedCard) {
                const newStatusName = this.dataset.statusName;
                if (newStatusName) {
                    this.appendChild(draggedCard);
                    updateTaskStatus(taskId, newStatusName);
                    updateKanbanColumnCounts();
                }
            }
        });
    }
    
    // NUEVA FUNCIÓN: Eliminar columnas vacías
    function removeEmptyKanbanColumns() {
        document.querySelectorAll('.kanban-column-wrapper').forEach(wrapper => {
            const columnBody = wrapper.querySelector('.kanban-column-body');
            const cards = columnBody.querySelectorAll('.kanban-card:not([style*="display: none"])');
            
            // Si no hay tarjetas visibles, eliminar la columna
            if (cards.length === 0) {
                wrapper.remove();
            }
        });
    }
    
    // ACTUALIZADA: Actualizar contadores y ocultar columnas vacías
    function updateKanbanColumnCounts() {
        document.querySelectorAll('.kanban-column-wrapper').forEach(wrapper => {
            const columnBody = wrapper.querySelector('.kanban-column-body');
            const cards = columnBody.querySelectorAll('.kanban-card:not([style*="display: none"])');
            const count = cards.length;
            
            const countSpan = wrapper.querySelector('.kanban-column-count');
            const countBadge = wrapper.querySelector('.kanban-count-badge');
            
            if (countSpan) countSpan.textContent = `${count} tasks`;
            if (countBadge) countBadge.textContent = count;
            
            // Mostrar/ocultar empty state
            const emptyState = wrapper.querySelector('.kanban-empty-state');
            if (emptyState) {
                emptyState.style.display = count === 0 ? 'block' : 'none';
            }
        });
        
        // Eliminar columnas completamente vacías
        removeEmptyKanbanColumns();
    }
    
    // Sobrescribir la función updateKanbanCards para usar columnas dinámicas
    function updateKanbanCards(taskId, newStatus, oldStatus) {
        const task = AppState.tasks.get(taskId);
        if (!task) return;
        
        // Asegurar que existe la columna destino
        const targetColumnBody = ensureKanbanColumn(newStatus, getStatusId(newStatus));
        if (!targetColumnBody) return;
        
        task.kanbanElements.forEach(card => {
            if (!card) return;
            
            const sourceColumn = card.closest('.kanban-column-body');
            
            if (targetColumnBody !== sourceColumn) {
                // Clonar para mantener eventos
                const newCard = card.cloneNode(true);
                newCard.dataset.taskId = taskId;
                
                // Actualizar contenido de la tarjeta
                updateKanbanCardContent(newCard, newStatus);
                
                // Añadir a la columna destino
                targetColumnBody.appendChild(newCard);
                
                // Remover de la columna origen
                card.remove();
                
                // Actualizar referencia
                const index = task.kanbanElements.indexOf(card);
                task.kanbanElements[index] = newCard;
                
                // Re-attach event listeners
                attachKanbanEvents(newCard);
            } else {
                // Solo actualizar contenido si está en la misma columna
                updateKanbanCardContent(card, newStatus);
            }
        });
        
        // Actualizar contadores de todas las columnas
        updateKanbanColumnCounts();
    }
    
    function updateKanbanCardContent(card, newStatus) {
        // Actualizar badge de estado
        const statusBadge = card.querySelector('.badge');
        if (statusBadge) {
            statusBadge.style.backgroundColor = AppState.statusColors[newStatus] || '#6c757d';
            statusBadge.innerHTML = getStatusIcon(newStatus) + ' ' + newStatus;
        }
        
        // Actualizar switch
        const switch_ = card.querySelector('.task-status-switch');
        if (switch_) {
            switch_.checked = newStatus === 'In Progress';
            switch_.disabled = newStatus === 'Completed';
        }
    }
    
    // Inicializar eventos de drag & drop en todas las columnas existentes
    function initializeKanbanDragAndDrop() {
        document.querySelectorAll('.kanban-column-body').forEach(columnBody => {
            setupKanbanColumnEvents(columnBody);
        });
    }
    
    // Modificar la función initializeTaskData para incluir la inicialización de kanban
    const originalInitializeTaskData = initializeTaskData;
    initializeTaskData = function() {
        originalInitializeTaskData();
        
        // Asegurar que existen todas las columnas kanban necesarias SOLO si tienen tareas
        // Ya no creamos todas las columnas por defecto
        
        // Inicializar drag & drop
        initializeKanbanDragAndDrop();
        
        // Actualizar contadores
        updateKanbanColumnCounts();
    };
    
    // Reemplazar la función original
    window.initializeTaskData = initializeTaskData;
    
    // ACTUALIZAR también la función filterTasks para manejar columnas vacías
    const originalFilterTasks = filterTasks;
    filterTasks = function() {
        originalFilterTasks();
        
        // Después de filtrar, actualizar columnas kanban
        if (AppState.views.current === 'kanban') {
            updateKanbanColumnCounts();
        }
    };
    
    // Reemplazar la función original
    window.filterTasks = filterTasks;
  
  
  
});