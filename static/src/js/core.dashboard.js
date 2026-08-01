/**
 * Optimized Dashboard JavaScript
 * Externalized for better performance and maintainability
 */

(function() {
  'use strict';

  // Performance monitoring
  const perfData = {
    startTime: performance.now(),
    domReady: false,
    fullyLoaded: false,
    components: {}
  };

  // DOM ready event
  document.addEventListener('DOMContentLoaded', function() {
    perfData.domReady = true;
    console.log('DOM ready in:', performance.now() - perfData.startTime, 'ms');

    // Initialize all dashboard components
    initDashboard();
  });

  // Window load event
  window.addEventListener('load', function() {
    perfData.fullyLoaded = true;
    console.log('Page fully loaded in:', performance.now() - perfData.startTime, 'ms');

    // Mark lazy images as loaded
    document.querySelectorAll('img.lazy').forEach(img => {
      img.classList.add('loaded');
    });
  });

  /**
   * Initialize all dashboard components
   */
  function initDashboard() {
    const startTime = performance.now();

    // Initialize components
    initTabs();
    initLazyLoading();
    initAnimatedCounters();
    initTooltips();
    initAlerts();
    initEmailSync();

    perfData.components.dashboard = performance.now() - startTime;
    console.log('Dashboard initialized in:', perfData.components.dashboard, 'ms');
  }

  /**
   * Initialize tab functionality with lazy loading
   */
  function initTabs() {
    const tabEls = document.querySelectorAll('button[data-bs-toggle="tab"]');

    tabEls.forEach(tabEl => {
      tabEl.addEventListener('shown.bs.tab', function (event) {
        const targetId = event.target.getAttribute('data-bs-target');

        // Lazy load tab content if needed
        loadTabContent(targetId);

        // Track tab switches for analytics
        if (window.gtag) {
          gtag('event', 'tab_switch', {
            tab_name: targetId.replace('#', '')
          });
        }
      });
    });
  }

  /**
   * Load tab content dynamically (can be extended for AJAX loading)
   */
  function loadTabContent(tabId) {
    console.log('Loading content for tab:', tabId);

    // Add loading state
    const tabContent = document.querySelector(tabId);
    if (tabContent) {
      tabContent.classList.add('loading');

      // Simulate content loading (replace with actual AJAX if needed)
      setTimeout(() => {
        tabContent.classList.remove('loading');
      }, 100);
    }
  }

  /**
   * Initialize lazy loading for images and content
   */
  function initLazyLoading() {
    // Image lazy loading
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            img.classList.add('loaded');
          }
          observer.unobserve(img);
        }
      });
    });

    // Observe all lazy images
    document.querySelectorAll('img[data-src]').forEach(img => {
      imageObserver.observe(img);
    });

    // Content lazy loading for below-the-fold sections
    const contentObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const element = entry.target;
          element.classList.add('visible');
          observer.unobserve(element);
        }
      });
    });

    // Observe sections that should be lazy loaded
    document.querySelectorAll('.lazy-section').forEach(section => {
      contentObserver.observe(section);
    });
  }

  /**
   * Initialize animated counters with optimized performance
   */
  function initAnimatedCounters() {
    const counters = document.querySelectorAll('.counter');
    if (counters.length === 0) return;

    const counterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.5,
      rootMargin: '0px 0px -50px 0px'
    });

    counters.forEach(counter => counterObserver.observe(counter));
  }

  /**
   * Animate counter with smooth easing
   */
  function animateCounter(counter) {
    const target = parseInt(counter.getAttribute('data-target')) || 0;
    const duration = 1000; // 1 second
    const start = performance.now();
    const startValue = 0;

    // Use requestAnimationFrame for smooth animation
    function update(currentTime) {
      const elapsed = currentTime - start;
      const progress = Math.min(elapsed / duration, 1);

      // Easing function for smooth animation
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      const currentValue = Math.floor(startValue + (target - startValue) * easeOutQuart);

      counter.textContent = currentValue.toLocaleString();

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        counter.textContent = target.toLocaleString();
      }
    }

    requestAnimationFrame(update);
  }

  /**
   * Initialize Bootstrap tooltips
   */
  function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }

  /**
   * Initialize alert auto-dismiss
   */
  function initAlerts() {
    const alerts = document.querySelectorAll('.alert[data-auto-dismiss]');
    alerts.forEach(alert => {
      const delay = parseInt(alert.dataset.autoDismiss) || 5000;
      setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
      }, delay);
    });
  }

  /**
   * Initialize CX Email Synchronization functionality
   */
  function initEmailSync() {
    // Bind click handlers for email sync buttons
    const checkEmailsBtn = document.getElementById('checkEmailsBtn');
    const processEmailsBtn = document.getElementById('processEmailsBtn');

    if (checkEmailsBtn) {
      checkEmailsBtn.addEventListener('click', checkNewEmails);
    }

    if (processEmailsBtn) {
      processEmailsBtn.addEventListener('click', processEmailsManually);
    }

    // Initialize configuration toggles
    initEmailConfigToggles();
  }

  /**
   * Initialize email configuration toggles
   */
  function initEmailConfigToggles() {
    const autoSyncToggle = document.getElementById('autoSyncToggle');
    const notifyToggle = document.getElementById('notifyOnNewEmails');

    if (autoSyncToggle) {
      autoSyncToggle.addEventListener('change', function() {
        updateEmailConfig('auto_sync', this.checked);
      });
    }

    if (notifyToggle) {
      notifyToggle.addEventListener('change', function() {
        updateEmailConfig('notifications', this.checked);
      });
    }
  }

  /**
   * Check for new emails
   */
  function checkNewEmails() {
    const btn = document.getElementById('checkEmailsBtn');
    const statusEl = document.getElementById('syncStatus');
    const countEl = document.getElementById('lastSyncCount');

    // Disable button and show loading state
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass"></i> Verificando...';

    if (statusEl) {
      statusEl.innerHTML = '<span class="text-info"><i class="bi bi-arrow-repeat"></i> Verificando correos nuevos...</span>';
    }

    // Make AJAX request
    fetch('/events/api/check-new-emails/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update UI with results
        if (statusEl) {
          statusEl.innerHTML = '<span class="text-success"><i class="bi bi-check-circle"></i> Verificación completada</span>';
        }

        if (countEl && data.processed_count !== undefined) {
          countEl.textContent = data.processed_count;
        }

        // Update pending emails count if available
        const pendingEl = document.getElementById('pendingEmails');
        if (pendingEl && data.pending_count !== undefined) {
          pendingEl.textContent = data.pending_count;
        }

        // Show success message
        showAlert('success', `Se procesaron ${data.processed_count || 0} emails CX exitosamente`);

      } else {
        // Show error
        if (statusEl) {
          statusEl.innerHTML = '<span class="text-danger"><i class="bi bi-exclamation-triangle"></i> Error en verificación</span>';
        }
        showAlert('danger', data.error || 'Error al verificar correos');
      }
    })
    .catch(error => {
      console.error('Error checking emails:', error);
      if (statusEl) {
        statusEl.innerHTML = '<span class="text-danger"><i class="bi bi-exclamation-triangle"></i> Error de conexión</span>';
      }
      showAlert('danger', 'Error de conexión al verificar correos');
    })
    .finally(() => {
      // Re-enable button
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-envelope-arrow-down"></i> Verificar Correos Nuevos';
    });
  }

  /**
   * Process emails manually
   */
  function processEmailsManually() {
    const btn = document.getElementById('processEmailsBtn');
    const statusEl = document.getElementById('syncStatus');
    const countEl = document.getElementById('lastSyncCount');

    // Disable button and show loading state
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-robot"></i> Procesando...';

    if (statusEl) {
      statusEl.innerHTML = '<span class="text-info"><i class="bi bi-robot"></i> Procesando emails CX...</span>';
    }

    // Make AJAX request
    fetch('/events/api/process-cx-emails/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update UI with results
        if (statusEl) {
          statusEl.innerHTML = '<span class="text-success"><i class="bi bi-check-circle"></i> Procesamiento completado</span>';
        }

        if (countEl && data.processed_count !== undefined) {
          countEl.textContent = data.processed_count;
        }

        // Update pending emails count if available
        const pendingEl = document.getElementById('pendingEmails');
        if (pendingEl && data.pending_count !== undefined) {
          pendingEl.textContent = data.pending_count;
        }

        // Show success message
        showAlert('success', `Procesamiento CX completado: ${data.processed_count || 0} emails procesados`);

      } else {
        // Show error
        if (statusEl) {
          statusEl.innerHTML = '<span class="text-danger"><i class="bi bi-exclamation-triangle"></i> Error en procesamiento</span>';
        }
        showAlert('danger', data.error || 'Error al procesar emails');
      }
    })
    .catch(error => {
      console.error('Error processing emails:', error);
      if (statusEl) {
        statusEl.innerHTML = '<span class="text-danger"><i class="bi bi-exclamation-triangle"></i> Error de conexión</span>';
      }
      showAlert('danger', 'Error de conexión al procesar emails');
    })
    .finally(() => {
      // Re-enable button
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-robot"></i> Procesar Emails CX';
    });
  }

  /**
   * Update email configuration
   */
  function updateEmailConfig(setting, value) {
    fetch('/events/api/update-email-config/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({
        setting: setting,
        value: value
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showAlert('success', 'Configuración actualizada');
      } else {
        showAlert('danger', data.error || 'Error al actualizar configuración');
        // Revert toggle on error
        const toggle = document.getElementById(setting === 'auto_sync' ? 'autoSyncToggle' : 'notifyOnNewEmails');
        if (toggle) {
          toggle.checked = !value;
        }
      }
    })
    .catch(error => {
      console.error('Error updating config:', error);
      showAlert('danger', 'Error al actualizar configuración');
      // Revert toggle on error
      const toggle = document.getElementById(setting === 'auto_sync' ? 'autoSyncToggle' : 'notifyOnNewEmails');
      if (toggle) {
        toggle.checked = !value;
      }
    });
  }

  /**
   * Get CSRF token from cookies
   */
  function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  /**
   * Show alert message
   */
  function showAlert(type, message) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Add to page
    document.body.appendChild(alertDiv);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      if (alertDiv.parentNode) {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
      }
    }, 5000);
  }

  /**
   * Utility function for debouncing
   */
  function debounce(func, wait) {
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
   * Utility function for throttling
   */
  function throttle(func, limit) {
    let inThrottle;
    return function() {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    }
  }

  // Expose performance data for debugging
  window.dashboardPerf = perfData;

  // Expose utility functions for global use
  window.DashboardUtils = {
    debounce,
    throttle,
    animateCounter
  };

})();