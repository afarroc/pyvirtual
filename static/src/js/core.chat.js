// Sistema de Notificaciones de Chat - Ultra Simple
// Basado en localStorage + Eventos del Navegador

(function() {
    'use strict';

    // Configuración del sistema
    const STORAGE_KEY = 'simple_chat_notifications';
    const MAX_NOTIFICATIONS = 10;

    let container = null;
    let isInitialized = false;
    let currentUserId = null;
    let notifications = [];

    // Inicializar el sistema
    function initChatNotifications() {
        if (isInitialized) return;
        isInitialized = true;

        console.log('🚀 Inicializando sistema de notificaciones simple...');

        // Solo inicializar en páginas de chat
        if (!window.location.pathname.startsWith('/chat/')) {
            console.log('❌ No es una página de chat');
            return;
        }

        // Obtener ID del usuario
        getUserId();

        // Crear interfaz
        createNotificationContainer();

        // Cargar notificaciones guardadas
        loadNotifications();

        // Escuchar mensajes nuevos
        setupMessageListener();

        // Exponer funciones globales
        window.addSimpleNotification = addNotification;
        window.markSimpleNotificationRead = markAsRead;
        window.removeSimpleNotification = removeNotification;
        window.clearAllSimpleNotifications = clearAllNotifications;
        window.debugSimpleNotifications = debugNotifications;

        console.log('✅ Sistema de notificaciones simple inicializado');

        // Crear notificación de bienvenida
        addNotification({
            title: '🔔 Notificaciones Activadas',
            message: 'Recibirás notificaciones cuando haya nuevos mensajes.',
            type: 'system'
        });
    }

    // Obtener ID del usuario
    function getUserId() {
        try {
            // Buscar en script JSON
            const script = document.getElementById('current-user');
            if (script) {
                currentUserId = JSON.parse(script.textContent);
                return;
            }

            // Buscar en variables globales
            if (window.user_id) {
                currentUserId = window.user_id;
                return;
            }

            // Fallback
            currentUserId = 'user_' + Date.now();
        } catch (error) {
            console.error('Error obteniendo user ID:', error);
            currentUserId = 'fallback_user';
        }
    }

    // Crear contenedor de notificaciones
    function createNotificationContainer() {
        container = document.createElement('div');
        container.id = 'simple-notifications';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 300px;
            max-height: 400px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 10000;
            font-family: Arial, sans-serif;
            display: none;
        `;

        // Header
        const header = document.createElement('div');
        header.style.cssText = `
            padding: 10px;
            background: #007bff;
            color: white;
            font-weight: bold;
            border-radius: 5px 5px 0 0;
            display: flex;
            justify-content: space-between;
        `;
        header.innerHTML = `
            <span>🔔 Notificaciones</span>
            <button onclick="clearAllSimpleNotifications()" style="background: none; border: none; color: white; cursor: pointer;">🗑️</button>
        `;

        // Lista
        const list = document.createElement('div');
        list.id = 'simple-notifications-list';
        list.style.cssText = 'max-height: 350px; overflow-y: auto;';

        container.appendChild(header);
        container.appendChild(list);
        document.body.appendChild(container);
    }

    // Escuchar mensajes nuevos
    function setupMessageListener() {
        // Interceptar WebSocket si existe
        const originalWebSocket = window.WebSocket;
        window.WebSocket = function(url, protocols) {
            const ws = new originalWebSocket(url, protocols);

            const originalOnMessage = ws.onmessage;
            ws.onmessage = function(event) {
                // Llamar al handler original
                if (originalOnMessage) {
                    originalOnMessage.call(this, event);
                }

                // Procesar para notificaciones
                try {
                    const data = JSON.parse(event.data);
                    if (data.message && data.user_id && data.user_id !== currentUserId) {
                        // Solo notificar si la pestaña no está activa
                        if (document.hidden) {
                            addNotification({
                                title: `💬 ${data.display_name || 'Usuario'}`,
                                message: data.message.length > 50 ?
                                    data.message.substring(0, 50) + '...' :
                                    data.message,
                                type: 'chat',
                                userId: data.user_id
                            });
                        }
                    }
                } catch (error) {
                    // Ignorar errores de parsing
                }
            };

            return ws;
        };

        // Escuchar eventos de visibilidad
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden) {
                // Marcar todas como leídas cuando se vuelve visible
                notifications.forEach(n => {
                    if (!n.read) markAsRead(n.id);
                });
            }
        });
    }

    // Agregar notificación
    function addNotification(notification) {
        const newNotification = {
            id: Date.now().toString(),
            title: notification.title || 'Nueva notificación',
            message: notification.message || '',
            timestamp: new Date().toISOString(),
            type: notification.type || 'info',
            read: false
        };

        notifications.unshift(newNotification);

        // Limitar cantidad
        if (notifications.length > MAX_NOTIFICATIONS) {
            notifications = notifications.slice(0, MAX_NOTIFICATIONS);
        }

        saveNotifications();
        renderNotifications();

        console.log('➕ Notificación agregada:', newNotification.title);
    }

    // Marcar como leída
    function markAsRead(notificationId) {
        const notification = notifications.find(n => n.id === notificationId);
        if (notification && !notification.read) {
            notification.read = true;
            saveNotifications();
            renderNotifications();
            console.log('✅ Notificación leída:', notificationId);
        }
    }

    // Eliminar notificación
    function removeNotification(notificationId) {
        notifications = notifications.filter(n => n.id !== notificationId);
        saveNotifications();
        renderNotifications();
        console.log('🗑️ Notificación eliminada:', notificationId);
    }

    // Limpiar todas
    function clearAllNotifications() {
        if (confirm('¿Eliminar todas las notificaciones?')) {
            notifications = [];
            saveNotifications();
            renderNotifications();
            console.log('🧹 Todas las notificaciones eliminadas');
        }
    }

    // Renderizar notificaciones
    function renderNotifications() {
        if (!container) return;

        const list = container.querySelector('#simple-notifications-list');
        if (!list) return;

        list.innerHTML = '';

        if (notifications.length === 0) {
            list.innerHTML = `
                <div style="padding: 20px; text-align: center; color: #666;">
                    📭 No hay notificaciones
                </div>
            `;
            container.style.display = 'none';
            return;
        }

        notifications.forEach(notification => {
            const item = document.createElement('div');
            item.style.cssText = `
                padding: 10px;
                border-bottom: 1px solid #eee;
                cursor: pointer;
                background: ${notification.read ? 'white' : '#f0f8ff'};
            `;

            item.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 5px;">${notification.title}</div>
                <div style="color: #666; margin-bottom: 5px;">${notification.message}</div>
                <div style="font-size: 12px; color: #999;">${formatTime(notification.timestamp)}</div>
                <button onclick="event.stopPropagation(); removeSimpleNotification('${notification.id}')"
                        style="float: right; background: none; border: none; color: #999; cursor: pointer;">×</button>
            `;

            item.addEventListener('click', () => markAsRead(notification.id));
            list.appendChild(item);
        });

        container.style.display = 'block';
    }

    // Formatear tiempo
    function formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Ahora';
        if (minutes < 60) return `Hace ${minutes}m`;
        if (hours < 24) return `Hace ${hours}h`;
        return `Hace ${days}d`;
    }

    // Guardar en localStorage
    function saveNotifications() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
        } catch (error) {
            console.error('Error guardando notificaciones:', error);
        }
    }

    // Cargar desde localStorage
    function loadNotifications() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                notifications = JSON.parse(stored);
                renderNotifications();
                console.log('📥 Notificaciones cargadas:', notifications.length);
            }
        } catch (error) {
            console.error('Error cargando notificaciones:', error);
            notifications = [];
        }
    }

    // Debug
    function debugNotifications() {
        console.log('=== SIMPLE NOTIFICATIONS DEBUG ===');
        console.log('📊 Total:', notifications.length);
        console.log('👤 User ID:', currentUserId);
        console.log('📱 Visible:', container ? container.style.display !== 'none' : false);

        notifications.forEach((n, i) => {
            console.log(`${i + 1}. ${n.title} (${n.read ? 'read' : 'unread'})`);
        });
    }

    // Inicializar cuando DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChatNotifications);
    } else {
        initChatNotifications();
    }

})();