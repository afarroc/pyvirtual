/**
 * =======================================================
 * INBOX GTD - SOLUCIÓN DEFINITIVA PARA TECLADO MÓVIL
 * =======================================================
 * Este archivo maneja el problema del desplazamiento con
 * técnicas agresivas pero efectivas.
 */

class InboxGTDManager {
    constructor() {
        this.isPanelOpen = false;
        this.isKeyboardVisible = false;
        this.originalBodyStyles = {};
        this.originalScrollPosition = 0;
        this.keyboardHeight = 0;
        this.viewportHeight = window.innerHeight;
        
        this.init();
    }

    /**
     * Inicializar con enfoque en móvil
     */
    init() {
        this.createOverlay();
        this.bindEvents();
        this.setupKeyboardDetection();
        this.loadInitialData();
        this.injectCriticalStyles();
    }

    /**
     * Crear overlay para bloquear el fondo
     */
    createOverlay() {
        const overlay = document.createElement('div');
        overlay.className = 'inbox-overlay';
        overlay.id = 'inboxOverlay';
        document.body.appendChild(overlay);
    }

    /**
     * Vincular eventos de manera segura
     */
    bindEvents() {
        // Botón flotante
        const floatingButton = document.getElementById('inboxFloatingButton');
        if (floatingButton) {
            floatingButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.togglePanel();
            });
        }

        // Cerrar panel
        const panelClose = document.getElementById('inboxPanelClose');
        if (panelClose) {
            panelClose.addEventListener('click', (e) => {
                e.preventDefault();
                this.closePanel();
            });
        }

        // Cerrar con overlay
        const overlay = document.getElementById('inboxOverlay');
        if (overlay) {
            overlay.addEventListener('click', (e) => {
                e.preventDefault();
                this.closePanel();
            });
        }

        // Formulario
        const quickForm = document.getElementById('inboxQuickForm');
        if (quickForm) {
            quickForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleQuickCapture();
            });
        }

        // Input focus/blur
        const inputs = document.querySelectorAll('#inboxPanel input, #inboxPanel textarea');
        inputs.forEach(input => {
            input.addEventListener('focus', (e) => {
                this.handleInputFocus(e.target);
            });
            
            input.addEventListener('blur', () => {
                this.handleInputBlur();
            });
        });

        // Teclas globales
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
                e.preventDefault();
                this.togglePanel();
            }
            if (e.key === 'Escape' && this.isPanelOpen) {
                e.preventDefault();
                this.closePanel();
            }
        });

        // Prevenir scroll en inputs
        document.addEventListener('touchmove', (e) => {
            if (this.isPanelOpen && 
                (e.target.matches('input') || e.target.matches('textarea'))) {
                e.preventDefault();
            }
        }, { passive: false });

        // Tap fuera del panel
        document.addEventListener('click', (e) => {
            if (this.isPanelOpen) {
                const panel = document.getElementById('inboxPanel');
                const button = document.getElementById('inboxFloatingButton');
                if (panel && !panel.contains(e.target) && 
                    button && !button.contains(e.target)) {
                    this.closePanel();
                }
            }
        });
    }

    /**
     * Configurar detección de teclado AGGRESIVA
     */
    setupKeyboardDetection() {
        // Método 1: Observar cambios en la altura de la ventana
        let lastHeight = window.innerHeight;
        
        const checkHeight = () => {
            const currentHeight = window.innerHeight;
            const diff = lastHeight - currentHeight;
            
            // Si la altura cambió significativamente, es el teclado
            if (diff > 100 && currentHeight < lastHeight * 0.7) {
                this.keyboardHeight = diff;
                this.showKeyboard();
            } else if (diff < -100 || currentHeight > lastHeight * 0.9) {
                this.hideKeyboard();
            }
            
            lastHeight = currentHeight;
        };

        // Verificar frecuentemente
        setInterval(checkHeight, 100);

        // Método 2: Eventos de focus
        document.addEventListener('focusin', (e) => {
            if (e.target.matches('input, textarea') && 
                e.target.closest('#inboxPanel')) {
                setTimeout(() => {
                    this.showKeyboard();
                    this.scrollToInput(e.target);
                }, 300);
            }
        });

        document.addEventListener('focusout', () => {
            setTimeout(() => {
                // Solo ocultar si ningún input tiene focus
                const activeElement = document.activeElement;
                if (!activeElement || !activeElement.matches('input, textarea')) {
                    this.hideKeyboard();
                }
            }, 100);
        });

        // Método 3: ResizeObserver como backup
        if ('ResizeObserver' in window && window.visualViewport) {
            this.resizeObserver = new ResizeObserver(() => {
                checkHeight();
            });
            this.resizeObserver.observe(window.visualViewport);
        }
    }

    /**
     * Mostrar teclado (ajustar posiciones)
     */
    showKeyboard() {
        if (this.isKeyboardVisible || !this.isPanelOpen) return;
        
        this.isKeyboardVisible = true;
        const panel = document.getElementById('inboxPanel');
        const button = document.getElementById('inboxFloatingButton');
        const overlay = document.getElementById('inboxOverlay');
        
        if (panel) {
            panel.classList.add('keyboard-visible');
        }
        
        if (button) {
            button.classList.add('keyboard-visible');
        }
        
        // Bloquear scroll del body completamente
        this.lockBodyScroll();
        
        console.log('Keyboard shown');
    }

    /**
     * Ocultar teclado
     */
    hideKeyboard() {
        if (!this.isKeyboardVisible) return;
        
        this.isKeyboardVisible = false;
        const panel = document.getElementById('inboxPanel');
        const button = document.getElementById('inboxFloatingButton');
        
        if (panel) {
            panel.classList.remove('keyboard-visible');
        }
        
        if (button) {
            button.classList.remove('keyboard-visible');
        }
        
        // Restaurar scroll del body
        this.unlockBodyScroll();
        
        console.log('Keyboard hidden');
    }

    /**
     * Bloquear scroll del body AGGRESIVAMENTE
     */
    lockBodyScroll() {
        this.originalScrollPosition = window.pageYOffset;
        this.originalBodyStyles = {
            position: document.body.style.position,
            top: document.body.style.top,
            width: document.body.style.width,
            height: document.body.style.height,
            overflow: document.body.style.overflow
        };
        
        // Aplicar estilos que bloquean el scroll
        document.body.style.position = 'fixed';
        document.body.style.top = `-${this.originalScrollPosition}px`;
        document.body.style.width = '100%';
        document.body.style.height = '100%';
        document.body.style.overflow = 'hidden';
        
        // Agregar clase para CSS
        document.body.classList.add('inbox-panel-open');
    }

    /**
     * Restaurar scroll del body
     */
    unlockBodyScroll() {
        // Restaurar estilos originales
        Object.keys(this.originalBodyStyles).forEach(key => {
            document.body.style[key] = this.originalBodyStyles[key];
        });
        
        // Restaurar posición de scroll
        window.scrollTo(0, this.originalScrollPosition);
        
        // Remover clase
        document.body.classList.remove('inbox-panel-open');
    }

    /**
     * Scroll al input activo
     */
    scrollToInput(input) {
        if (!input || !this.isPanelOpen) return;
        
        const panel = document.getElementById('inboxPanel');
        if (!panel) return;
        
        const inputRect = input.getBoundingClientRect();
        const panelRect = panel.getBoundingClientRect();
        const panelScroll = panel.scrollTop;
        
        // Calcular si el input está visible
        const inputTopRelative = inputRect.top - panelRect.top + panelScroll;
        const inputBottomRelative = inputRect.bottom - panelRect.top + panelScroll;
        
        // Ajustar scroll si es necesario
        if (inputTopRelative < panelScroll) {
            panel.scrollTop = inputTopRelative - 10;
        } else if (inputBottomRelative > panelScroll + panel.clientHeight) {
            panel.scrollTop = inputBottomRelative - panel.clientHeight + 10;
        }
    }

    /**
     * Manejar focus en input
     */
    handleInputFocus(input) {
        if (!input) return;
        
        // Agregar clase de focus
        input.parentElement.classList.add('input-focused');
        
        // En móvil, mostrar teclado y ajustar
        if (window.innerWidth <= 768) {
            this.showKeyboard();
            setTimeout(() => {
                this.scrollToInput(input);
            }, 350); // Delay para que el teclado aparezca primero
        }
    }

    /**
     * Manejar blur en input
     */
    handleInputBlur() {
        // Remover clases de focus
        document.querySelectorAll('.input-focused').forEach(el => {
            el.classList.remove('input-focused');
        });
    }

    /**
     * Alternar panel
     */
    togglePanel() {
        if (this.isPanelOpen) {
            this.closePanel();
        } else {
            this.openPanel();
        }
    }

    /**
     * Abrir panel
     */
    openPanel() {
        if (this.isPanelOpen) return;
        
        this.isPanelOpen = true;
        const panel = document.getElementById('inboxPanel');
        const button = document.getElementById('inboxFloatingButton');
        const overlay = document.getElementById('inboxOverlay');
        
        if (panel) {
            panel.classList.add('show');
            panel.setAttribute('aria-hidden', 'false');
        }
        
        if (button) {
            button.classList.add('active');
        }
        
        if (overlay) {
            overlay.classList.add('active');
        }
        
        // Bloquear scroll inicialmente
        this.lockBodyScroll();
        
        // Enfocar primer input después de animación
        setTimeout(() => {
            const firstInput = panel.querySelector('input');
            if (firstInput) {
                firstInput.focus();
            }
        }, 400);
        
        console.log('Panel opened');
    }

    /**
     * Cerrar panel
     */
    closePanel() {
        if (!this.isPanelOpen) return;
        
        this.isPanelOpen = false;
        this.isKeyboardVisible = false;
        
        const panel = document.getElementById('inboxPanel');
        const button = document.getElementById('inboxFloatingButton');
        const overlay = document.getElementById('inboxOverlay');
        
        if (panel) {
            panel.classList.remove('show');
            panel.classList.remove('keyboard-visible');
            panel.setAttribute('aria-hidden', 'true');
        }
        
        if (button) {
            button.classList.remove('active');
            button.classList.remove('keyboard-visible');
        }
        
        if (overlay) {
            overlay.classList.remove('active');
        }
        
        // Restaurar scroll
        this.unlockBodyScroll();
        
        // Asegurar que los inputs pierdan focus
        const inputs = panel.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            input.blur();
        });
        
        console.log('Panel closed');
    }

    /**
     * Inyectar estilos críticos
     */
    injectCriticalStyles() {
        const criticalStyles = `
        /* ESTILOS CRÍTICOS INYECTADOS */
        html.inbox-no-scroll {
            overflow: hidden !important;
            position: fixed !important;
            width: 100% !important;
            height: 100% !important;
        }
        
        body.inbox-panel-open {
            position: fixed !important;
            width: 100% !important;
            height: 100% !important;
            overflow: hidden !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
        }
        
        /* Prevenir cualquier scroll durante el focus */
        input:focus, textarea:focus {
            transform: translateZ(0) !important;
            -webkit-transform: translateZ(0) !important;
        }
        
        /* iOS specific: prevenir zoom y otros comportamientos */
        @supports (-webkit-touch-callout: none) {
            .inbox-panel {
                -webkit-overflow-scrolling: touch !important;
            }
            
            body.inbox-panel-open {
                -webkit-overflow-scrolling: touch !important;
            }
            
            /* Deshabilitar pull-to-refresh */
            body {
                overscroll-behavior-y: none !important;
            }
        }
        
        /* Asegurar que el panel esté siempre visible */
        .inbox-panel.keyboard-visible {
            animation: none !important;
            transition: none !important;
        }
        `;
        
        const style = document.createElement('style');
        style.id = 'inbox-critical-styles';
        style.textContent = criticalStyles;
        document.head.appendChild(style);
    }

    /**
     * Manejar captura rápida
     */
    async handleQuickCapture() {
        // ... (mismo código que antes)
    }

    /**
     * Cargar datos iniciales
     */
    async loadInitialData() {
        // ... (mismo código que antes)
    }

    /**
     * Actualizar datos
     */
    async refreshData() {
        // ... (mismo código que antes)
    }

    /**
     * Mostrar notificación
     */
    showNotification(message, type = 'info') {
        // ... (mismo código que antes)
    }

    /**
     * Cleanup
     */
    destroy() {
        this.closePanel();
        
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        
        const overlay = document.getElementById('inboxOverlay');
        if (overlay) {
            overlay.remove();
        }
        
        const styles = document.getElementById('inbox-critical-styles');
        if (styles) {
            styles.remove();
        }
        
        this.unlockBodyScroll();
    }
}

// =======================================================
// INICIALIZACIÓN SIMPLE Y DIRECTA
// =======================================================

// Inicializar inmediatamente
(function() {
    // Esperar a que el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initInboxGTD);
    } else {
        initInboxGTD();
    }
    
    function initInboxGTD() {
        // Verificar si el usuario está autenticado
        const isAuthenticated = document.body.hasAttribute('data-user-authenticated') ||
                              document.querySelector('[data-user-authenticated="true"]');
        
        if (isAuthenticated) {
            try {
                window.inboxGTD = new InboxGTDManager();
                console.log('✅ Inbox GTD initialized with mobile keyboard fixes');
            } catch (error) {
                console.error('❌ Failed to initialize Inbox GTD:', error);
            }
        }
    }
})();

// Limpiar al salir
window.addEventListener('beforeunload', function() {
    if (window.inboxGTD && window.inboxGTD.destroy) {
        window.inboxGTD.destroy();
    }
});