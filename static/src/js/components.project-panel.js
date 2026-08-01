/**
 * PROJECT PANEL SPECIFIC SCRIPTS
 * Project-specific JavaScript functionality
 */

(function() {
    'use strict';

    // Project Panel Configuration
    const projectPanelConfig = {
        searchInputId: 'searchInput',
        selectedCountId: 'selectedCount',
        selectAllId: 'selectAll',
        checkboxName: 'selected_projects',
        tableSelector: '.datatable tbody tr',
        tabSelector: '#projectTabs .nav-link'
    };

    // Initialize Project Panel
    function initProjectPanel() {
        // Initialize PanelManager with project-specific config
        window.PanelManager.init(projectPanelConfig);

        // Override bulk action URL for projects
        window.PanelManager.getBulkActionUrl = function(action) {
            return '/events/projects/bulk-action/';
        };

        // Bind project-specific events
        bindProjectEvents();
    }

    // Bind project-specific events
    function bindProjectEvents() {
        // Project-specific event bindings can be added here
        console.log('Project panel initialized');
    }

    // Project-specific functions
    window.clearSearch = function() {
        window.PanelManager.clearSearch();
    };

    window.exportProjects = function() {
        window.PanelManager.exportItems('/events/projects/export/');
    };

    window.toggleSelectAll = function() {
        const selectAllCheckbox = document.getElementById('selectAll');
        window.PanelManager.toggleSelectAll(selectAllCheckbox.checked);
    };

    window.bulkAction = function(action) {
        const confirmMessages = {
            'delete': '¿Está seguro de que desea eliminar {count} proyecto(s)? Esta acción no se puede deshacer.',
            'activate': '¿Está seguro de que desea activar {count} proyecto(s)?',
            'complete': '¿Está seguro de que desea marcar como completado(s) {count} proyecto(s)?'
        };

        window.PanelManager.bulkAction(action, confirmMessages[action]);
    };

    window.toggleView = function(viewType) {
        window.PanelManager.toggleView(viewType);
    };

    window.refreshData = function() {
        window.PanelManager.refreshData();
    };

    window.filterByStatus = function(statusId) {
        window.PanelManager.filterByStatus(statusId);
    };

    // Auto-initialize when DOM is ready and we're on project panel
    document.addEventListener('DOMContentLoaded', function() {
        // Check if we're on a project panel page
        if (document.querySelector('.project-panel') || window.location.pathname.includes('/projects/')) {
            initProjectPanel();
        }
    });

})();