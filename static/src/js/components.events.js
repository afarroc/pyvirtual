// ============================================================================
// COMPONENTS.JS - SISTEMA DE COMPONENTES UNIFICADO
// Eventos, Inbox, Tareas, Proyectos - GTD System
// ============================================================================

(function() {
    'use strict';

    // ------------------------------------------------------------------------
    // 1. CONSTANTES Y CONFIGURACIÓN
    // ------------------------------------------------------------------------
    const CONFIG = {
        AUTO_DISMISS_TIME: 5000,          // 5 segundos
        DEBOUNCE_DELAY: 300,              // 300ms para búsqueda
        ANIMATION_ENABLED: true,
        DEBUG: false                      // Cambiar a true para logs
    };

    const SELECTORS = {
        // Formularios
        DELETE_FORM: 'form[id^="delete-form-"], form[id^="delete-"]',
        STATUS_FORM: 'form[id^="form-"], form[data-status-form]',
        FILTER_FORM: '.filter-card form, .filter-section form',
        
        // Componentes Bootstrap
        DROPDOWN_TOGGLE: '[data-bs-toggle="dropdown"]',
        TOOLTIP: '[data-bs-toggle="tooltip"]',
        POPOVER: '[data-bs-toggle="popover"]',
        MODAL: '.modal',
        
        // Tablas y búsqueda
        DATATABLE: '.table.datatable, .table-responsive table',
        SEARCH_INPUT: 'input[type="search"], .table-search',
        
        // Tarjetas y elementos
        ITEM_CARD: '.event-card, .item-card, .processed-card, .task-card, .project-card',
        ACTIVITY_ITEM: '.activity-item',
        STATS_CARD: '.stats-card',
        
        // Alertas
        ALERT: '.alert:not(.alert-persistent)',
        MESSAGES_CONTAINER: '.messages-container',
        
        // CSRF
        CSRF_TOKEN: '[name=csrfmiddlewaretoken]'
    };

    // ------------------------------------------------------------------------
    // 2. UTILIDADES
    // ------------------------------------------------------------------------
    const Utils = {
        /**
         * Obtiene el token CSRF del documento
         */
        getCSRFToken: function() {
            return document.querySelector(SELECTORS.CSRF_TOKEN)?.value || '';
        },

        /**
         * Escapa HTML para prevenir XSS
         */
        escapeHtml: function(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },

        /**
         * Debounce para búsquedas
         */
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        /**
         * Formatea fecha a local
         */
        formatDate: function(date) {
            return new Date(date).toLocaleDateString('es-ES', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        /**
         * Log condicional
         */
        log: function(...args) {
            if (CONFIG.DEBUG) {
                console.log('[Components]', ...args);
            }
        },

        /**
         * Error logging
         */
        error: function(...args) {
            console.error('[Components Error]', ...args);
        }
    };

    // ------------------------------------------------------------------------
    // 3. SISTEMA DE ALERTAS
    // ------------------------------------------------------------------------
    const AlertSystem = {
        /**
         * Muestra una alerta flotante
         */
        show: function(message, type = 'info', title = '') {
            Utils.log('Mostrando alerta:', { message, type, title });

            // Buscar o crear contenedor
            let container = document.querySelector(SELECTORS.MESSAGES_CONTAINER);
            if (!container) {
                container = document.createElement('div');
                container.className = 'messages-container';
                const main = document.querySelector('main, .container-fluid, .container, .content');
                if (main) {
                    main.prepend(container);
                } else {
                    document.body.prepend(container);
                }
            }

            // Iconos por tipo
            const icons = {
                success: 'bi-check-circle-fill',
                danger: 'bi-exclamation-triangle-fill',
                error: 'bi-exclamation-triangle-fill',
                warning: 'bi-exclamation-circle-fill',
                info: 'bi-info-circle-fill'
            };

            // Crear alerta
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
            alertDiv.setAttribute('role', 'alert');
            alertDiv.setAttribute('data-bs-auto-dismiss', 'true');
            
            alertDiv.innerHTML = `
                <div class="alert-content d-flex align-items-start">
                    <div class="alert-icon me-3">
                        <i class="bi ${icons[type] || icons.info}"></i>
                    </div>
                    <div class="alert-text flex-grow-1">
                        ${title ? `<strong class="d-block alert-title">${Utils.escapeHtml(title)}</strong>` : ''}
                        ${Utils.escapeHtml(message)}
                    </div>
                    <button type="button" class="btn-close ms-2" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
                ${['success', 'info'].includes(type) ? `
                    <div class="alert-progress">
                        <div class="progress-bar"></div>
                    </div>
                ` : ''}
            `;

            container.appendChild(alertDiv);

            // Auto-ocultar para success/info
            if (['success', 'info'].includes(type)) {
                setTimeout(() => {
                    try {
                        const bsAlert = bootstrap.Alert.getOrCreateInstance(alertDiv);
                        bsAlert.close();
                    } catch (e) {
                        alertDiv.remove();
                    }
                }, CONFIG.AUTO_DISMISS_TIME);
            }

            // Scroll suave
            alertDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });

            return alertDiv;
        },

        /**
         * Auto-oculta alertas existentes
         */
        initAutoDismiss: function() {
            document.querySelectorAll(SELECTORS.ALERT).forEach(alert => {
                if (alert.classList.contains('alert-success') || 
                    alert.classList.contains('alert-info')) {
                    
                    setTimeout(() => {
                        try {
                            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                            bsAlert.close();
                        } catch (e) {
                            alert.remove();
                        }
                    }, CONFIG.AUTO_DISMISS_TIME);
                }
            });
        }
    };

    // ------------------------------------------------------------------------
    // 4. MANEJADORES DE FORMULARIOS
    // ------------------------------------------------------------------------
    const FormHandlers = {
        /**
         * Confirmación de eliminación
         */
        handleDelete: function(e) {
            if (!confirm('¿Estás seguro de que quieres eliminar este elemento?\nEsta acción no se puede deshacer.')) {
                e.preventDefault();
                return false;
            }
            return true;
        },

        /**
         * Cambio de estado vía AJAX
         */
        handleStatusChange: function(e) {
            e.preventDefault();
            const form = e.target;
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn?.innerHTML || '';

            Utils.log('Cambiando estado:', form.action);

            // Feedback visual
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Actualizando...';
            }

            const formData = new FormData(form);
            
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': Utils.getCSRFToken()
                }
            })
            .then(response => {
                if (!response.ok) throw new Error('Error en la respuesta del servidor');
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    AlertSystem.show('Estado actualizado correctamente', 'success', 'Actualizado');
                    
                    // Actualizar badge en la tarjeta
                    const card = form.closest(SELECTORS.ITEM_CARD);
                    if (card) {
                        const badge = card.querySelector('.badge:not(.bg-secondary)');
                        if (badge && data.new_status) {
                            badge.textContent = data.new_status;
                        }
                    }
                } else {
                    AlertSystem.show(data.error || 'Error al actualizar el estado', 'danger', 'Error');
                }
            })
            .catch(error => {
                Utils.error('Error en cambio de estado:', error);
                AlertSystem.show('Error de conexión al servidor', 'danger', 'Error');
            })
            .finally(() => {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            });
        },

        /**
         * Manejo de filtros
         */
        handleFilter: function(e) {
            const form = e.target;
            const formData = new FormData(form);
            
            // Guardar estado en sessionStorage
            for (let [key, value] of formData.entries()) {
                if (value) {
                    sessionStorage.setItem(`filter_${key}`, value);
                }
            }
            
            Utils.log('Filtro aplicado:', Object.fromEntries(formData));
        },

        /**
         * Inicializa listeners de formularios
         */
        init: function() {
            // Eliminación
            document.querySelectorAll(SELECTORS.DELETE_FORM).forEach(form => {
                form.removeEventListener('submit', FormHandlers.handleDelete);
                form.addEventListener('submit', FormHandlers.handleDelete);
            });

            // Cambio de estado
            document.querySelectorAll(SELECTORS.STATUS_FORM).forEach(form => {
                form.removeEventListener('submit', FormHandlers.handleStatusChange);
                form.addEventListener('submit', FormHandlers.handleStatusChange);
            });

            // Filtros
            document.querySelectorAll(SELECTORS.FILTER_FORM).forEach(form => {
                form.removeEventListener('submit', FormHandlers.handleFilter);
                form.addEventListener('submit', FormHandlers.handleFilter);
            });
        }
    };

    // ------------------------------------------------------------------------
    // 5. BÚSQUEDA EN TABLAS
    // ------------------------------------------------------------------------
    const TableSearch = {
        /**
         * Filtra filas de tabla
         */
        filterTable: function(table, searchTerm) {
            const rows = table.querySelectorAll('tbody tr');
            let visibleCount = 0;

            rows.forEach(row => {
                let found = false;
                row.querySelectorAll('td').forEach(cell => {
                    if (cell.textContent.toLowerCase().includes(searchTerm)) {
                        found = true;
                    }
                });
                row.style.display = found ? '' : 'none';
                if (found) visibleCount++;
            });

            // Mostrar/ocultar mensaje de "sin resultados"
            let emptyMessage = table.querySelector('.empty-search-message');
            if (visibleCount === 0) {
                if (!emptyMessage) {
                    emptyMessage = document.createElement('tr');
                    emptyMessage.className = 'empty-search-message';
                    emptyMessage.innerHTML = '<td colspan="10" class="text-center py-4 text-muted">No se encontraron resultados</td>';
                    table.querySelector('tbody').appendChild(emptyMessage);
                }
            } else if (emptyMessage) {
                emptyMessage.remove();
            }
        },

        /**
         * Inicializa búsqueda en tiempo real
         */
        init: function() {
            const tables = document.querySelectorAll(SELECTORS.DATATABLE);
            
            tables.forEach(table => {
                const card = table.closest('.card');
                const searchInput = card?.querySelector(SELECTORS.SEARCH_INPUT) || 
                                   document.querySelector(SELECTORS.SEARCH_INPUT);
                
                if (searchInput) {
                    const debouncedSearch = Utils.debounce(function() {
                        TableSearch.filterTable(table, this.value.toLowerCase());
                    }, CONFIG.DEBOUNCE_DELAY);

                    searchInput.removeEventListener('input', debouncedSearch);
                    searchInput.addEventListener('input', debouncedSearch);
                }
            });
        }
    };

    // ------------------------------------------------------------------------
    // 6. COMPONENTES DE BOOTSTRAP
    // ------------------------------------------------------------------------
    const BootstrapComponents = {
        /**
         * Inicializa todos los componentes de Bootstrap
         */
        init: function() {
            // Dropdowns
            document.querySelectorAll(SELECTORS.DROPDOWN_TOGGLE).forEach(el => {
                try {
                    if (!bootstrap.Dropdown.getInstance(el)) {
                        new bootstrap.Dropdown(el);
                    }
                } catch (e) {
                    Utils.error('Error inicializando dropdown:', e);
                }
            });

            // Tooltips
            document.querySelectorAll(SELECTORS.TOOLTIP).forEach(el => {
                try {
                    if (!bootstrap.Tooltip.getInstance(el)) {
                        new bootstrap.Tooltip(el);
                    }
                } catch (e) {
                    Utils.error('Error inicializando tooltip:', e);
                }
            });

            // Popovers
            document.querySelectorAll(SELECTORS.POPOVER).forEach(el => {
                try {
                    if (!bootstrap.Popover.getInstance(el)) {
                        new bootstrap.Popover(el);
                    }
                } catch (e) {
                    Utils.error('Error inicializando popover:', e);
                }
            });

            // Modales
            document.querySelectorAll(SELECTORS.MODAL).forEach(el => {
                try {
                    bootstrap.Modal.getOrCreateInstance(el);
                } catch (e) {
                    Utils.error('Error inicializando modal:', e);
                }
            });
        }
    };

    // ------------------------------------------------------------------------
    // 7. TIMELINE DE ACTIVIDAD
    // ------------------------------------------------------------------------
    const ActivityTimeline = {
        /**
         * Inicializa la línea de tiempo
         */
        init: function() {
            document.querySelectorAll(SELECTORS.ACTIVITY_ITEM).forEach(item => {
                // Aplicar color del badge
                const badge = item.querySelector('.activity-badge');
                if (badge) {
                    const color = badge.getAttribute('style') || '';
                    if (color.includes('color')) {
                        badge.style.color = badge.style.color;
                    }
                }

                // Marcar último elemento
                const parent = item.parentElement;
                if (parent && parent.lastElementChild === item) {
                    item.style.borderLeftColor = 'transparent';
                }
            });
        }
    };

    // ------------------------------------------------------------------------
    // 8. OBSERVADOR DE CAMBIOS
    // ------------------------------------------------------------------------
    const MutationObserverHandler = {
        /**
         * Inicializa el observer
         */
        init: function() {
            const observer = new MutationObserver((mutations) => {
                let needsUpdate = false;
                
                mutations.forEach((mutation) => {
                    if (mutation.addedNodes.length) {
                        needsUpdate = true;
                    }
                });

                if (needsUpdate) {
                    Utils.log('Contenido dinámico detectado, actualizando componentes...');
                    BootstrapComponents.init();
                    FormHandlers.init();
                    AlertSystem.initAutoDismiss();
                    TableSearch.init();
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    };

    // ------------------------------------------------------------------------
    // 9. INICIALIZACIÓN PRINCIPAL
    // ------------------------------------------------------------------------
    function init() {
        Utils.log('Inicializando sistema de componentes...');

        try {
            // Componentes Bootstrap
            BootstrapComponents.init();
            
            // Manejadores de formularios
            FormHandlers.init();
            
            // Búsqueda en tablas
            TableSearch.init();
            
            // Timeline de actividad
            ActivityTimeline.init();
            
            // Auto-ocultar alertas
            AlertSystem.initAutoDismiss();
            
            // Observador de cambios dinámicos
            MutationObserverHandler.init();

            Utils.log('✅ Sistema de componentes inicializado correctamente');
        } catch (error) {
            Utils.error('Error durante la inicialización:', error);
        }
    }

    // ------------------------------------------------------------------------
    // 10. EJECUCIÓN
    // ------------------------------------------------------------------------
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ------------------------------------------------------------------------
    // 11. API PÚBLICA
    // ------------------------------------------------------------------------
    window.EventComponents = {
        // Utilidades
        showAlert: AlertSystem.show,
        getCSRFToken: Utils.getCSRFToken,
        formatDate: Utils.formatDate,
        
        // Inicialización manual
        refresh: function() {
            Utils.log('Refrescando componentes...');
            BootstrapComponents.init();
            FormHandlers.init();
            ActivityTimeline.init();
        },
        
        // Configuración
        setDebug: function(enabled) {
            CONFIG.DEBUG = enabled;
        },
        
        setAutoDismissTime: function(ms) {
            CONFIG.AUTO_DISMISS_TIME = ms;
        }
    };

})();