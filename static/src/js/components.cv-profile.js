// Corporate Profile JavaScript

// Export profile function
function exportProfile() {
    // Implementar funcionalidad de exportación
    alert('Funcionalidad de exportación próximamente disponible');
}

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Animate metrics on scroll
    animateMetricsOnScroll();
    
    // Initialize progress bars animation
    animateProgressBars();
});

// Animate metrics when they come into view
function animateMetricsOnScroll() {
    const metrics = document.querySelectorAll('.metric-value');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    
    metrics.forEach(metric => observer.observe(metric));
}

// Animate progress bars
function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0';
        
        setTimeout(() => {
            bar.style.width = width;
        }, 100);
    });
}

// Tab persistence
document.addEventListener('DOMContentLoaded', function() {
    // Get current tab from localStorage
    const activeTab = localStorage.getItem('activeProfileTab');
    
    if (activeTab) {
        const tab = document.querySelector(`[data-bs-target="${activeTab}"]`);
        if (tab) {
            // Trigger tab show
            bootstrap.Tab.getOrCreateInstance(tab).show();
        }
    }
    
    // Save active tab to localStorage when changed
    const tabs = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            localStorage.setItem('activeProfileTab', event.target.dataset.bsTarget);
        });
    });
});

// Refresh metrics (can be called periodically)
function refreshMetrics() {
    fetch('/api/dashboard/stats/')
        .then(response => response.json())
        .then(data => {
            updateMetrics(data);
        })
        .catch(error => console.error('Error refreshing metrics:', error));
}

// Update metrics in UI
function updateMetrics(data) {
    const metricsElements = {
        tasks_completed: document.querySelector('.metric-value[data-metric="tasks"]'),
        projects_active: document.querySelector('.metric-value[data-metric="projects"]'),
        events_attended: document.querySelector('.metric-value[data-metric="events"]')
    };
    
    Object.keys(metricsElements).forEach(key => {
        if (metricsElements[key] && data[key] !== undefined) {
            metricsElements[key].textContent = data[key];
        }
    });
}

// Optional: Auto-refresh every 5 minutes
// setInterval(refreshMetrics, 300000);

// Añadir esta función al archivo existente

// Animate numbers in summary cards
function animateNumbers() {
    const numberElements = document.querySelectorAll('.summary-card .number, .stat-value');
    
    numberElements.forEach(element => {
        const target = parseInt(element.textContent) || 0;
        if (target === 0) return;
        
        let current = 0;
        const increment = target / 30; // 30 steps
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, 20);
    });
}

// Llamar a la función cuando la pestaña esté activa
document.addEventListener('DOMContentLoaded', function() {
    // Observar cuando la pestaña de información corporativa está activa
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.target.classList.contains('active') && 
                mutation.target.id === 'corporate-info') {
                animateNumbers();
            }
        });
    });

    const corporateTab = document.getElementById('corporate-info');
    if (corporateTab) {
        observer.observe(corporateTab, { attributes: true, attributeFilter: ['class'] });
    }
});