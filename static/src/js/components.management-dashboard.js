/**
 * MANAGEMENT DASHBOARD SPECIFIC SCRIPTS
 * Dashboard-specific JavaScript functionality
 */

(function() {
    'use strict';

    // Management Dashboard Configuration
    const dashboardConfig = {
        refreshInterval: 30000, // 30 seconds
        chartUpdateInterval: 60000 // 1 minute
    };

    // Initialize Management Dashboard
    function initManagementDashboard() {
        // Initialize dashboard-specific features
        initStatisticsCards();
        initActivityTimeline();
        initQuickActions();

        // Set up auto-refresh for statistics
        setInterval(updateStatistics, dashboardConfig.refreshInterval);

        console.log('Management dashboard initialized');
    }

    // Initialize statistics cards with hover effects
    function initStatisticsCards() {
        const statCards = document.querySelectorAll('.info-card');

        statCards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '';
            });
        });
    }

    // Initialize activity timeline
    function initActivityTimeline() {
        const activityItems = document.querySelectorAll('.activity-item');

        activityItems.forEach(item => {
            item.addEventListener('mouseenter', function() {
                this.style.backgroundColor = 'rgba(0,123,255,0.05)';
            });

            item.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });
        });
    }

    // Initialize quick actions
    function initQuickActions() {
        const actionButtons = document.querySelectorAll('.btn');

        actionButtons.forEach(button => {
            button.addEventListener('mousedown', function() {
                this.style.transform = 'scale(0.98)';
            });

            button.addEventListener('mouseup', function() {
                this.style.transform = 'scale(1)';
            });

            button.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        });
    }

    // Update statistics (mock function - would connect to real API)
    function updateStatistics() {
        // This would typically make an AJAX call to get updated statistics
        console.log('Updating statistics...');

        // Example of updating a counter
        const eventCountElement = document.querySelector('[data-stat="event-count"]');
        if (eventCountElement) {
            // Simulate getting new count from server
            const currentCount = parseInt(eventCountElement.textContent);
            const newCount = currentCount + Math.floor(Math.random() * 3) - 1; // -1, 0, or +1
            if (newCount >= 0) {
                eventCountElement.textContent = newCount;
            }
        }
    }

    // Dashboard-specific utility functions
    window.refreshDashboard = function() {
        updateStatistics();
        showNotification('Dashboard refreshed successfully', 'success');
    };

    window.exportDashboardData = function() {
        // Export dashboard data as JSON
        const dashboardData = {
            timestamp: new Date().toISOString(),
            statistics: {
                events: document.querySelector('[data-stat="event-count"]')?.textContent || '0',
                projects: document.querySelector('[data-stat="project-count"]')?.textContent || '0',
                tasks: document.querySelector('[data-stat="task-count"]')?.textContent || '0'
            }
        };

        const dataStr = JSON.stringify(dashboardData, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});

        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = 'dashboard-data.json';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showNotification('Dashboard data exported successfully', 'success');
    };

    // Simple notification system
    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    // Auto-initialize when DOM is ready and we're on management dashboard
    document.addEventListener('DOMContentLoaded', function() {
        // Check if we're on management dashboard page
        if (document.querySelector('.management-dashboard') ||
            window.location.pathname.includes('/management/') ||
            document.querySelector('[data-page="management"]')) {
            initManagementDashboard();
        }
    });

})();