// Chat Widget Integration System
// This file provides integration between the chat widget and the main notification system

class ChatWidgetIntegration {
    constructor() {
        this.widgetFrame = null;
        this.notificationBadge = null;
        this.isInitialized = false;
        this.eventListeners = {};
    }

    // Initialize the integration system
    init() {
        if (this.isInitialized) return;

        console.log('ChatWidgetIntegration: Initializing...');

        // Find the chat widget iframe or container
        this.findWidget();

        // Setup event listeners
        this.setupEventListeners();

        // Setup message handling
        this.setupMessageHandling();

        this.isInitialized = true;
        console.log('ChatWidgetIntegration: Initialized successfully');
    }

    // Find the chat widget in the DOM
    findWidget() {
        // Try different selectors for the chat widget
        const selectors = [
            '#chat-panel',
            '.chat-widget',
            '[data-chat-widget]',
            'iframe[src*="chat"]'
        ];

        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element) {
                this.widgetFrame = element;
                console.log('ChatWidgetIntegration: Found widget element:', selector);
                break;
            }
        }

        // Find notification badge
        const badgeSelectors = [
            '#header-notification-badge',
            '.notification-badge',
            '.badge-number',
            '[data-notification-badge]'
        ];

        for (const selector of badgeSelectors) {
            const badge = document.querySelector(selector);
            if (badge) {
                this.notificationBadge = badge;
                console.log('ChatWidgetIntegration: Found notification badge:', selector);
                break;
            }
        }
    }

    // Setup event listeners for widget events
    setupEventListeners() {
        // Listen for custom events from the widget
        document.addEventListener('chatWidget:unreadCountReset', (event) => {
            console.log('ChatWidgetIntegration: Unread count reset event received:', event.detail);
            this.handleUnreadCountReset(event.detail);
        });

        document.addEventListener('chatWidget:newMessage', (event) => {
            console.log('ChatWidgetIntegration: New message event received:', event.detail);
            this.handleNewMessage(event.detail);
        });

        document.addEventListener('chatWidget:roomChanged', (event) => {
            console.log('ChatWidgetIntegration: Room changed event received:', event.detail);
            this.handleRoomChange(event.detail);
        });

        document.addEventListener('chatWidget:requestUpdate', (event) => {
            console.log('ChatWidgetIntegration: Update request received');
            this.handleUpdateRequest();
        });
    }

    // Setup message handling for iframe communication
    setupMessageHandling() {
        window.addEventListener('message', (event) => {
            // Verify origin for security (you should replace this with your actual domain)
            // if (event.origin !== 'https://yourdomain.com') return;

            if (event.data && event.data.type && event.data.type.startsWith('chatWidget:')) {
                console.log('ChatWidgetIntegration: Message received from widget:', event.data);

                // Convert postMessage to custom event
                const eventType = event.data.type.replace('chatWidget:', '');
                document.dispatchEvent(new CustomEvent(`chatWidget:${eventType}`, {
                    detail: event.data.data
                }));
            }
        });
    }

    // Handle unread count reset
    handleUnreadCountReset(data) {
        console.log('ChatWidgetIntegration: Handling unread count reset:', data);

        // Update notification badge
        this.updateNotificationBadge();

        // Dispatch event to other parts of the application
        document.dispatchEvent(new CustomEvent('notificationSystem:unreadCountReset', {
            detail: data
        }));

        // If you have a notification manager, update it
        if (window.NotificationManager && typeof window.NotificationManager.forceRefresh === 'function') {
            window.NotificationManager.forceRefresh();
        }
    }

    // Handle new message
    handleNewMessage(data) {
        console.log('ChatWidgetIntegration: Handling new message:', data);

        // Update notification badge
        this.updateNotificationBadge();

        // Dispatch event to other parts of the application
        document.dispatchEvent(new CustomEvent('notificationSystem:newMessage', {
            detail: data
        }));

        // You could also show a browser notification here
        this.showBrowserNotification(data);
    }

    // Handle room change
    handleRoomChange(data) {
        console.log('ChatWidgetIntegration: Handling room change:', data);

        // Update any room-specific UI elements
        document.dispatchEvent(new CustomEvent('notificationSystem:roomChanged', {
            detail: data
        }));
    }

    // Handle update request
    handleUpdateRequest() {
        console.log('ChatWidgetIntegration: Handling update request');

        // Update notification badge
        this.updateNotificationBadge();

        // Send current notification state to widget
        this.sendNotificationStateToWidget();
    }

    // Update notification badge
    updateNotificationBadge() {
        if (!this.notificationBadge) {
            console.warn('ChatWidgetIntegration: No notification badge found');
            return;
        }

        // Fetch current notification count
        fetch('/chat/api/notifications/unread/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data && typeof data.total_unread === 'number') {
                if (data.total_unread > 0) {
                    this.notificationBadge.textContent = data.total_unread > 99 ? '99+' : data.total_unread;
                    this.notificationBadge.style.display = 'block';
                } else {
                    this.notificationBadge.style.display = 'none';
                }
                console.log('ChatWidgetIntegration: Updated notification badge to:', data.total_unread);
            }
        })
        .catch(err => {
            console.warn('ChatWidgetIntegration: Could not update notification badge:', err);
        });
    }

    // Send notification state to widget
    sendNotificationStateToWidget() {
        // Send current notification state to the widget
        if (this.widgetFrame && this.widgetFrame.contentWindow) {
            this.widgetFrame.contentWindow.postMessage({
                type: 'notificationSystem:state',
                data: {
                    timestamp: Date.now()
                }
            }, '*');
        }
    }

    // Show browser notification
    showBrowserNotification(data) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const notification = new Notification(`New message in ${data.roomId || 'Chat'}`, {
                body: data.message || 'You have a new message',
                icon: '/static/assets/img/chat-icon.png' // Replace with your icon path
            });

            // Auto-close after 5 seconds
            setTimeout(() => {
                notification.close();
            }, 5000);
        }
    }

    // Request notification permission
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                console.log('ChatWidgetIntegration: Notification permission:', permission);
            });
        }
    }

    // Send message to widget
    sendMessageToWidget(type, data) {
        const message = {
            type: `notificationSystem:${type}`,
            data: data,
            timestamp: Date.now()
        };

        // Send via postMessage if widget is in iframe
        if (this.widgetFrame && this.widgetFrame.contentWindow) {
            this.widgetFrame.contentWindow.postMessage(message, '*');
        }

        // Also dispatch as custom event
        document.dispatchEvent(new CustomEvent(`notificationSystem:${type}`, {
            detail: data
        }));

        console.log('ChatWidgetIntegration: Sent message to widget:', message);
    }

    // Force refresh of widget
    forceWidgetRefresh() {
        this.sendMessageToWidget('forceRefresh', {});
    }

    // Update widget notification count
    updateWidgetNotificationCount() {
        this.sendMessageToWidget('updateCount', {});
    }
}

// Initialize the integration when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const integration = new ChatWidgetIntegration();
    integration.init();

    // Request notification permission
    integration.requestNotificationPermission();

    // Make integration available globally for debugging
    window.ChatWidgetIntegration = integration;
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChatWidgetIntegration;
}