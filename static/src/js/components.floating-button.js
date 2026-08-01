/**
 * ============================================================================
 * INBOX GTD FLOATING BUTTON - GLOBAL ACCESS COMPONENT
 * ============================================================================
 * This JavaScript file contains all the functionality for the global inbox GTD
 * floating button that provides quick access to inbox functionality from any page.
 *
 * Features:
 * - Floating button with pulse animation
 * - Expandable panel with quick capture form
 * - Real-time statistics display
 * - Toast notifications system
 * - Keyboard shortcuts (Ctrl+I)
 * - Auto-save functionality
 * - Responsive design
 * - Accessibility features
 *
 * Dependencies:
 * - Main application JavaScript
 *
 * API Endpoints:
 * - /events/inbox/api/stats/ - Get inbox statistics
 * - /events/inbox/ - Create new inbox item
 * - /events/inbox/api/tasks/ - Get available tasks
 * - /events/inbox/api/projects/ - Get available projects
 *
 * ============================================================================
 */

class InboxGTDManager {
    constructor() {
        this.isPanelOpen = false;
        this.pendingCount = 0;
        this.todayCount = 0;
        this.processedCount = 0;
        this.notificationQueue = [];
        this.isLoading = false;
        this.statsInterval = null;
        this.csrfToken = this.getCSRFToken();

        // Configuration
        this.config = {
            statsUpdateInterval: 30000, // 30 seconds
            toastDuration: 5000, // 5 seconds
            maxRetries: 3,
            retryDelay: 1000
        };

        this.init();
    }

    /**
     * Initialize the inbox GTD manager
     */
    init() {
        this.bindEvents();
        this.setupKeyboardShortcuts();
        this.setupAccessibility();
        this.startStatsPolling();
        this.showWelcomeMessage();
    }

    /**
     * Bind all event listeners
     */
    bindEvents() {
        // Floating button click
        const floatingButton = document.getElementById('inboxFloatingButton');
        if (floatingButton) {
            floatingButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.togglePanel();
            });
        }

        // Panel close button
        const closeButton = document.getElementById('inboxPanelClose');
        if (closeButton) {
            closeButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.closePanel();
            });
        }

        // Quick capture form
        const quickForm = document.getElementById('inboxQuickForm');
        if (quickForm) {
            quickForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleQuickCapture();
            });
        }

        // Auto-save on input change
        const titleInput = document.getElementById('inboxQuickTitle');
        const descInput = document.getElementById('inboxQuickDescription');

        if (titleInput) {
            titleInput.addEventListener('input', this.debounce(() => {
                this.autoSaveDraft();
            }, 1000));
        }

        if (descInput) {
            descInput.addEventListener('input', this.debounce(() => {
                this.autoSaveDraft();
            }, 1000));
        }

        // Click outside to close
        document.addEventListener('click', (e) => {
            if (!this.isPanelOpen) return;

            const container = document.getElementById('inboxFloatingContainer');
            if (container && container.contains(e.target)) return;

            const panel = document.getElementById('inboxPanel');
            if (panel && panel.contains(e.target)) return;

            this.closePanel();
        });

        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isPanelOpen) {
                this.closePanel();
            }
        });

        // Prevent panel close when clicking inside
        const panel = document.getElementById('inboxPanel');
        if (panel) {
            panel.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+I or Cmd+I to toggle inbox
            if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
                e.preventDefault();
                this.togglePanel();
            }
        });
    }

    /**
     * Setup accessibility features
     */
    setupAccessibility() {
        const floatingButton = document.getElementById('inboxFloatingButton');
        if (floatingButton) {
            // Add ARIA labels
            floatingButton.setAttribute('aria-label', 'Abrir Inbox GTD (Ctrl+I)');
            floatingButton.setAttribute('role', 'button');
            floatingButton.setAttribute('tabindex', '0');

            // Keyboard navigation
            floatingButton.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.togglePanel();
                }
            });
        }
    }

    /**
     * Toggle the inbox panel
     */
    togglePanel() {
        if (this.isLoading) return;

        if (this.isPanelOpen) {
            this.closePanel();
        } else {
            this.openPanel();
        }
    }

    /**
     * Open the inbox panel
     */
    async openPanel() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoadingState();

        try {
            // Load fresh statistics
            await this.updateStatistics();

            // Show panel
            const panel = document.getElementById('inboxPanel');
            const floatingButton = document.getElementById('inboxFloatingButton');

            if (panel && floatingButton) {
                panel.classList.add('is-open');
                floatingButton.classList.add('is-open');
                this.isPanelOpen = true;

                // Focus on title input
                setTimeout(() => {
                    const titleInput = document.getElementById('inboxQuickTitle');
                    if (titleInput) {
                        titleInput.focus();
                    }
                }, 300);

                // Load draft if exists
                this.loadDraft();

                // Announce to screen readers
                this.announceToScreenReader('Panel de Inbox GTD abierto');
            }
        } catch (error) {
            console.error('Error opening inbox panel:', error);
            this.showToast('Error al abrir el panel del inbox', 'error');
        } finally {
            this.isLoading = false;
            this.hideLoadingState();
        }
    }

    /**
     * Close the inbox panel
     */
    closePanel() {
        const panel = document.getElementById('inboxPanel');
        const floatingButton = document.getElementById('inboxFloatingButton');

        if (panel && floatingButton) {
            panel.classList.remove('is-open');
            floatingButton.classList.remove('is-open');
            this.isPanelOpen = false;

            // Save draft
            this.saveDraft();

            // Announce to screen readers
            this.announceToScreenReader('Panel de Inbox GTD cerrado');
        }
    }

    /**
     * Handle quick capture form submission
     */
    async handleQuickCapture() {
        if (this.isLoading) return;

        const titleInput = document.getElementById('inboxQuickTitle');
        const descInput = document.getElementById('inboxQuickDescription');

        const title = titleInput?.value.trim();
        const description = descInput?.value.trim();

        if (!title) {
            this.showToast('El título es obligatorio', 'error');
            titleInput?.focus();
            return;
        }

        this.isLoading = true;
        this.showLoadingState();

        try {
            const response = await this.createInboxItem(title, description);

            if (response.success) {
                // Clear form
                if (titleInput) titleInput.value = '';
                if (descInput) descInput.value = '';

                // Clear draft
                this.clearDraft();

                // Update statistics
                await this.updateStatistics();

                // Show success message
                this.showToast('Item agregado al inbox correctamente', 'success');

                // Close panel after short delay
                setTimeout(() => {
                    this.closePanel();
                }, 1500);
            } else {
                this.showToast(response.error || 'Error al crear el item', 'error');
            }
        } catch (error) {
            console.error('Error creating inbox item:', error);
            this.showToast('Error al crear el item del inbox', 'error');
        } finally {
            this.isLoading = false;
            this.hideLoadingState();
        }
    }

    /**
     * Create a new inbox item via AJAX
     */
    async createInboxItem(title, description) {
        const formData = new FormData();
        formData.append('title', title);
        formData.append('description', description);
        formData.append('csrfmiddlewaretoken', this.csrfToken);

        const response = await fetch('/events/inbox/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (response.headers.get('X-Requested-With') === 'XMLHttpRequest') {
            return await response.json();
        } else {
            // Handle regular form submission
            window.location.reload();
            return { success: true };
        }
    }

    /**
     * Update statistics from API
     */
    async updateStatistics() {
        try {
            const response = await fetch('/events/inbox/api/stats/', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const data = await response.json();

                if (data.success) {
                    this.updateStatisticsDisplay(data.stats);
                }
            }
        } catch (error) {
            console.error('Error updating statistics:', error);
        }
    }

    /**
     * Update the statistics display
     */
    updateStatisticsDisplay(stats) {
        // Update badge
        const badge = document.getElementById('inboxBadge');
        if (badge) {
            const unprocessedCount = stats.unprocessed || 0;
            badge.textContent = unprocessedCount;
            badge.style.display = unprocessedCount > 0 ? 'flex' : 'none';
        }

        // Update stats in panel
        const statsElements = {
            'inboxStatTotal': stats.total || 0,
            'inboxStatUnprocessed': stats.unprocessed || 0,
            'inboxStatProcessed': stats.processed || 0,
            'inboxStatToday': stats.today || 0,
            'inboxStatRecent': stats.recent || 0
        };

        Object.entries(statsElements).forEach(([elementId, value]) => {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = value;
            }
        });

        // Store counts for reference
        this.pendingCount = stats.unprocessed || 0;
        this.todayCount = stats.today || 0;
        this.processedCount = stats.processed || 0;
    }

    /**
     * Start polling for statistics updates
     */
    startStatsPolling() {
        // Update immediately
        this.updateStatistics();

        // Set up interval
        this.statsInterval = setInterval(() => {
            if (!this.isPanelOpen) { // Only poll when panel is closed
                this.updateStatistics();
            }
        }, this.config.statsUpdateInterval);
    }

    /**
     * Stop polling for statistics updates
     */
    stopStatsPolling() {
        if (this.statsInterval) {
            clearInterval(this.statsInterval);
            this.statsInterval = null;
        }
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `m360-inbox-toast ${type}`;
        toast.innerHTML = `
            <div class="m360-inbox-toast-content">
                <i class="m360-inbox-toast-icon bi ${this.getToastIcon(type)}"></i>
                <div class="m360-inbox-toast-text">
                    <div class="m360-inbox-toast-title">${type === 'success' ? '¡Éxito!' : type === 'error' ? 'Error' : 'Información'}</div>
                    <div class="m360-inbox-toast-message">${message}</div>
                </div>
                <button class="m360-inbox-toast-close" aria-label="Cerrar">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;

        document.body.appendChild(toast);

        // Animate in
        setTimeout(() => toast.classList.add('is-visible'), 100);

        // Auto remove
        setTimeout(() => {
            toast.classList.remove('is-visible');
            setTimeout(() => toast.remove(), 300);
        }, this.config.toastDuration);

        // Bind close button
        const closeBtn = toast.querySelector('.m360-inbox-toast-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                toast.classList.remove('is-visible');
                setTimeout(() => toast.remove(), 300);
            });
        }
    }

    /**
     * Get appropriate icon for toast type
     */
    getToastIcon(type) {
        const icons = {
            success: 'bi-check-circle-fill',
            error: 'bi-exclamation-triangle-fill',
            warning: 'bi-exclamation-circle-fill',
            info: 'bi-info-circle-fill'
        };
        return icons[type] || icons.info;
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        const submitButton = document.getElementById('inboxQuickSubmit');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="bi bi-arrow-clockwise m360-inbox-spinning"></i> Creando...';
        }
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        const submitButton = document.getElementById('inboxQuickSubmit');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="bi bi-lightning-charge-fill"></i> Capturar';
        }
    }

    /**
     * Auto-save draft functionality
     */
    autoSaveDraft() {
        const title = document.getElementById('inboxQuickTitle')?.value || '';
        const description = document.getElementById('inboxQuickDescription')?.value || '';

        if (title || description) {
            const draft = {
                title,
                description,
                timestamp: Date.now()
            };
            localStorage.setItem('inboxGTD_draft', JSON.stringify(draft));
        }
    }

    /**
     * Save draft to localStorage
     */
    saveDraft() {
        this.autoSaveDraft();
    }

    /**
     * Load draft from localStorage
     */
    loadDraft() {
        try {
            const draftData = localStorage.getItem('inboxGTD_draft');
            if (draftData) {
                const draft = JSON.parse(draftData);

                // Check if draft is less than 24 hours old
                if (Date.now() - draft.timestamp < 24 * 60 * 60 * 1000) {
                    const titleInput = document.getElementById('inboxQuickTitle');
                    const descInput = document.getElementById('inboxQuickDescription');

                    if (titleInput && draft.title) {
                        titleInput.value = draft.title;
                    }
                    if (descInput && draft.description) {
                        descInput.value = draft.description;
                    }
                } else {
                    this.clearDraft();
                }
            }
        } catch (error) {
            console.error('Error loading draft:', error);
        }
    }

    /**
     * Clear draft from localStorage
     */
    clearDraft() {
        localStorage.removeItem('inboxGTD_draft');
    }

    /**
     * Show welcome message for first-time users
     */
    showWelcomeMessage() {
        const hasVisited = localStorage.getItem('inboxGTD_welcome_shown');
        if (!hasVisited) {
            setTimeout(() => {
                this.showToast('¡Bienvenido al Inbox GTD! Usa Ctrl+I para acceso rápido desde cualquier página.', 'info');
                localStorage.setItem('inboxGTD_welcome_shown', 'true');
            }, 2000);
        }
    }

    /**
     * Announce message to screen readers
     */
    announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;

        document.body.appendChild(announcement);

        setTimeout(() => {
            announcement.remove();
        }, 1000);
    }

    /**
     * Get CSRF token from form
     */
    getCSRFToken() {
        const csrfForm = document.getElementById('csrf-form');
        if (csrfForm) {
            const csrfToken = csrfForm.querySelector('[name=csrfmiddlewaretoken]');
            return csrfToken ? csrfToken.value : '';
        }
        return '';
    }

    /**
     * Debounce utility function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Cleanup method
     */
    destroy() {
        this.stopStatsPolling();
        this.clearDraft();
    }
}

// ============================================================================
// GLOBAL FUNCTIONS
// ============================================================================

/**
 * Initialize the inbox GTD manager when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page where the inbox should be available
    if (typeof window.inboxGTDManager === 'undefined') {
        window.inboxGTDManager = new InboxGTDManager();
    }
});

/**
 * Global function to show inbox toast (for external use)
 */
function showInboxToast(message, type = 'info') {
    if (window.inboxGTDManager) {
        window.inboxGTDManager.showToast(message, type);
    }
}

/**
 * Global function to update inbox statistics (for external use)
 */
async function updateInboxStats() {
    if (window.inboxGTDManager) {
        await window.inboxGTDManager.updateStatistics();
    }
}

/**
 * Global hook for external components (chat widget) to refresh inbox counts
 */
window.updateNotificationFromWidget = function() {
    if (window.inboxGTDManager) {
        window.inboxGTDManager.updateStatistics();
    }
};


// ============================================================================
// CSS ANIMATIONS
// ============================================================================

// Add spinning animation for loading states
const style = document.createElement('style');
style.textContent = `
    @keyframes spinning {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .spinning {
        animation: spinning 1s linear infinite;
    }

    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
`;
document.head.appendChild(style);
