/**
 * TASK PANEL SPECIFIC SCRIPTS
 * Task-specific JavaScript functionality
 */

(function() {
    'use strict';

    // Task Panel Configuration
    const taskPanelConfig = {
        searchInputId: 'taskSearchInput',
        selectedCountId: 'taskSelectedCount',
        selectAllId: 'taskSelectAll',
        checkboxName: 'selected_tasks',
        tableSelector: '.datatable tbody tr',
        tabSelector: '#taskTabs .nav-link'
    };

    // Initialize Task Panel
    function initTaskPanel() {
        // Initialize PanelManager with task-specific config
        window.PanelManager.init(taskPanelConfig);

        // Override bulk action URL for tasks
        window.PanelManager.getBulkActionUrl = function(action) {
            return '/events/tasks/bulk-action/';
        };

        // Bind task-specific events
        bindTaskEvents();
    }

    // Bind task-specific events
    function bindTaskEvents() {
        // Task-specific event bindings can be added here
        console.log('Task panel initialized');
    }

    // Task-specific functions
    window.clearTaskSearch = function() {
        window.PanelManager.clearSearch();
    };

    window.exportTasks = function() {
        window.PanelManager.exportItems('/events/tasks/export/');
    };

    window.toggleTaskSelectAll = function() {
        const selectAllCheckbox = document.getElementById('taskSelectAll');
        window.PanelManager.toggleSelectAll(selectAllCheckbox.checked);
    };

    window.bulkTaskAction = function(action) {
        const confirmMessages = {
            'delete': '¿Está seguro de que desea eliminar {count} tarea(s)? Esta acción no se puede deshacer.',
            'activate': '¿Está seguro de que desea activar {count} tarea(s)?',
            'complete': '¿Está seguro de que desea marcar como completada(s) {count} tarea(s)?'
        };

        window.PanelManager.bulkAction(action, confirmMessages[action]);
    };

    window.toggleTaskView = function(viewType) {
        window.PanelManager.toggleView(viewType);
    };

    window.refreshTaskData = function() {
        window.PanelManager.refreshData();
    };

    window.filterTasksByStatus = function(statusId) {
        window.PanelManager.filterByStatus(statusId);
    };

    // Auto-initialize when DOM is ready and we're on task panel
    document.addEventListener('DOMContentLoaded', function() {
        // Check if we're on a task panel page
        if (document.querySelector('.task-panel') || window.location.pathname.includes('/tasks/')) {
            initTaskPanel();
        }
    });

})();