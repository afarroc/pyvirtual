/**
 * EVENT PANEL SPECIFIC SCRIPTS
 * Event-specific JavaScript functionality
 */

(function() {
    'use strict';

    // Event Panel Configuration
    const eventPanelConfig = {
        searchInputId: 'eventSearchInput',
        selectedCountId: 'eventSelectedCount',
        selectAllId: 'eventSelectAll',
        checkboxName: 'selected_events',
        tableSelector: '.datatable tbody tr',
        tabSelector: '#eventTabs .nav-link'
    };

    // Initialize Event Panel
    function initEventPanel() {
        // Initialize PanelManager with event-specific config
        window.PanelManager.init(eventPanelConfig);

        // Override bulk action URL for events
        window.PanelManager.getBulkActionUrl = function(action) {
            return '/events/events/bulk-action/';
        };

        // Bind event-specific events
        bindEventEvents();
    }

    // Bind event-specific events
    function bindEventEvents() {
        // Event-specific event bindings can be added here
        console.log('Event panel initialized');
    }

    // Event-specific functions
    window.clearEventSearch = function() {
        window.PanelManager.clearSearch();
    };

    window.exportEvents = function() {
        window.PanelManager.exportItems('/events/events/export/');
    };

    window.toggleEventSelectAll = function() {
        const selectAllCheckbox = document.getElementById('eventSelectAll');
        window.PanelManager.toggleSelectAll(selectAllCheckbox.checked);
    };

    window.bulkEventAction = function(action) {
        const confirmMessages = {
            'delete': '¿Está seguro de que desea eliminar {count} evento(s)? Esta acción no se puede deshacer.',
            'activate': '¿Está seguro de que desea activar {count} evento(s)?',
            'complete': '¿Está seguro de que desea marcar como completado(s) {count} evento(s)?'
        };

        window.PanelManager.bulkAction(action, confirmMessages[action]);
    };

    window.toggleEventView = function(viewType) {
        window.PanelManager.toggleView(viewType);
    };

    window.refreshEventData = function() {
        window.PanelManager.refreshData();
    };

    window.filterEventsByStatus = function(statusId) {
        window.PanelManager.filterByStatus(statusId);
    };

    // Auto-initialize when DOM is ready and we're on event panel
    document.addEventListener('DOMContentLoaded', function() {
        // Check if we're on an event panel page
        if (document.querySelector('.event-panel') || window.location.pathname.includes('/events/')) {
            initEventPanel();
        }
    });

})();