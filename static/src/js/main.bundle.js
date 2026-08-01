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

})();// Sistema de Notificaciones de Chat - Versión Simple y Funcional
// Basado en Service Worker + IndexedDB + Polling

(function() {
    'use strict';

    // Configuración del sistema
    const DB_NAME = 'ChatNotificationsDB';
    const DB_VERSION = 1;
    const STORE_NAME = 'notifications';
    const POLLING_INTERVAL = 30000; // 30 segundos
    const MAX_NOTIFICATIONS = 20;

    let db = null;
    let container = null;
    let pollingInterval = null;
    let isInitialized = false;
    let currentUserId = null;
    let currentUserName = null;
    let lastMessageId = null;
    let notifications = [];

    // Inicializar IndexedDB
    function initDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                db = request.result;
                resolve(db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                    store.createIndex('read', 'read', { unique: false });
                }
            };
        });
    }

    // Función principal de inicialización
    async function initChatNotifications() {
        if (isInitialized) return;
        isInitialized = true;

        console.log('🚀 Inicializando sistema de notificaciones de chat...');

        // Solo inicializar en páginas de chat
        if (!window.location.pathname.startsWith('/chat/')) {
            console.log('❌ No es una página de chat, cancelando inicialización');
            return;
        }

        try {
            // Inicializar base de datos
            await initDB();

            // Obtener información del usuario
            await getUserInfo();

            // Crear interfaz
            createNotificationContainer();

            // Cargar notificaciones existentes
            await loadNotifications();

            // Configurar polling para nuevos mensajes
            startPolling();

            // Exponer funciones globales
            window.addChatNotification = addNotification;
            window.markChatNotificationRead = markAsRead;
            window.removeChatNotification = removeNotification;
            window.clearAllChatNotifications = clearAllNotifications;
            window.debugChatNotifications = debugNotifications;

            console.log('✅ Sistema de notificaciones inicializado');

            // Mostrar notificación de bienvenida
            await addNotification({
                id: 'welcome_' + Date.now(),
                title: '🔔 Notificaciones Activadas',
                message: 'Recibirás notificaciones cuando haya nuevos mensajes en el chat.',
                type: 'system'
            });

        } catch (error) {
            console.error('❌ Error inicializando sistema:', error);
        }
    }

    // Obtener información del usuario
    async function getUserInfo() {
        try {
            // Buscar en elementos JSON script (como en room.html)
            const currentUserScript = document.getElementById('current-user');
            if (currentUserScript) {
                currentUserId = JSON.parse(currentUserScript.textContent);
                console.log('👤 Usuario identificado desde script JSON:', currentUserId);
                return;
            }

            // Buscar en variables globales
            if (window.user_id) {
                currentUserId = window.user_id;
                currentUserName = window.user_name || 'Usuario';
                console.log('👤 Usuario identificado desde variables globales:', currentUserId);
                return;
            }

            // Fallback: buscar en localStorage
            const stored = localStorage.getItem('chat_user_info');
            if (stored) {
                const userInfo = JSON.parse(stored);
                currentUserId = userInfo.id;
                currentUserName = userInfo.name;
                console.log('👤 Usuario identificado desde localStorage:', currentUserId);
                return;
            }

            // Último recurso: ID temporal
            currentUserId = 'user_' + Date.now();
            currentUserName = 'Usuario';
            console.warn('⚠️ Usando ID temporal:', currentUserId);

        } catch (error) {
            console.error('❌ Error obteniendo información del usuario:', error);
            currentUserId = 'fallback_user';
            currentUserName = 'Usuario';
        }
    }

    // Crear contenedor de notificaciones
    function createNotificationContainer() {
        container = document.createElement('div');
        container.id = 'chat-notifications-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 350px;
            max-height: 500px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            font-family: Arial, sans-serif;
            display: none;
        `;

        // Header
        const header = document.createElement('div');
        header.style.cssText = `
            padding: 12px 16px;
            background: #007bff;
            color: white;
            font-weight: bold;
            border-radius: 8px 8px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        `;
        header.innerHTML = `
            <span>🔔 Notificaciones</span>
            <button onclick="clearAllChatNotifications()" style="
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                font-size: 16px;
            ">🗑️</button>
        `;

        // Lista de notificaciones
        const list = document.createElement('div');
        list.id = 'chat-notifications-list';
        list.style.cssText = `
            max-height: 400px;
            overflow-y: auto;
        `;

        container.appendChild(header);
        container.appendChild(list);
        document.body.appendChild(container);
    }

    // Sistema de polling para verificar nuevos mensajes
    function startPolling() {
        if (pollingInterval) return;

        pollingInterval = setInterval(async () => {
            try {
                await checkForNewMessages();
            } catch (error) {
                console.error('Error en polling:', error);
            }
        }, POLLING_INTERVAL);

        console.log('🔄 Polling iniciado cada', POLLING_INTERVAL / 1000, 'segundos');
    }

    // Verificar nuevos mensajes desde el servidor
    async function checkForNewMessages() {
        if (!currentUserId) return;

        try {
            const response = await fetch('/chat/api/unread-messages/', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                },
                credentials: 'same-origin'
            });

            if (response.ok) {
                const data = await response.json();
                if (data.messages && data.messages.length > 0) {
                    for (const msg of data.messages) {
                        if (msg.user_id !== currentUserId) { // No notificar mensajes propios
                            await addNotification({
                                id: `msg_${msg.id}`,
                                title: `💬 ${msg.display_name || 'Usuario'}`,
                                message: msg.content.length > 100 ?
                                    msg.content.substring(0, 100) + '...' :
                                    msg.content,
                                type: 'chat',
                                timestamp: msg.timestamp,
                                roomId: msg.room_id,
                                userId: msg.user_id
                            });
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error verificando mensajes:', error);
        }
    }

    // Cargar notificaciones desde IndexedDB
    async function loadNotifications() {
        if (!db) return;

        const transaction = db.transaction([STORE_NAME], 'readonly');
        const store = transaction.objectStore(STORE_NAME);
        const index = store.index('timestamp');

        return new Promise((resolve) => {
            const request = index.openCursor(null, 'prev'); // Más recientes primero
            const loadedNotifications = [];

            request.onsuccess = function(event) {
                const cursor = event.target.result;
                if (cursor) {
                    loadedNotifications.push(cursor.value);
                    cursor.continue();
                } else {
                    // Filtrar notificaciones expiradas (7 días)
                    const now = Date.now();
                    const validNotifications = loadedNotifications.filter(n =>
                        (now - new Date(n.timestamp).getTime()) < (7 * 24 * 60 * 60 * 1000)
                    );

                    // Limitar a máximo
                    notifications = validNotifications.slice(0, MAX_NOTIFICATIONS);
                    renderNotifications();
                    resolve(notifications);
                }
            };

            request.onerror = function() {
                console.error('Error cargando notificaciones');
                resolve([]);
            };
        });
    }

    // Agregar nueva notificación
    async function addNotification(notification) {
        if (!db) return;

        const newNotification = {
            id: notification.id || Date.now().toString(),
            title: notification.title || 'Nueva notificación',
            message: notification.message || '',
            timestamp: notification.timestamp || new Date().toISOString(),
            type: notification.type || 'chat',
            roomId: notification.roomId || null,
            userId: notification.userId || null,
            read: false
        };

        // Verificar si ya existe
        const existing = await getNotification(newNotification.id);
        if (existing) return;

        // Guardar en IndexedDB
        const transaction = db.transaction([STORE_NAME], 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        store.add(newNotification);

        // Agregar a la lista en memoria
        notifications.unshift(newNotification);

        // Limitar cantidad
        if (notifications.length > MAX_NOTIFICATIONS) {
            notifications = notifications.slice(0, MAX_NOTIFICATIONS);
        }

        renderNotifications();

        // Mostrar notificación del navegador si está permitido
        if (document.hidden && 'Notification' in window && Notification.permission === 'granted') {
            new Notification(newNotification.title, {
                body: newNotification.message,
                icon: '/static/favicon.ico'
            });
        }

        console.log('➕ Notificación agregada:', newNotification.title);
    }

    // Obtener notificación específica
    function getNotification(id) {
        return new Promise((resolve) => {
            if (!db) {
                resolve(null);
                return;
            }

            const transaction = db.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.get(id);

            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => resolve(null);
        });
    }

    // Marcar notificación como leída
    async function markAsRead(notificationId) {
        if (!db) return;

        const transaction = db.transaction([STORE_NAME], 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        const request = store.get(notificationId);

        request.onsuccess = function(event) {
            const notification = event.target.result;
            if (notification && !notification.read) {
                notification.read = true;
                store.put(notification);
                renderNotifications();
                console.log('✅ Notificación marcada como leída:', notificationId);
            }
        };
    }

    // Eliminar notificación
    async function removeNotification(notificationId) {
        if (!db) return;

        const transaction = db.transaction([STORE_NAME], 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        store.delete(notificationId);

        // Remover de la lista en memoria
        notifications = notifications.filter(n => n.id !== notificationId);
        renderNotifications();

        console.log('🗑️ Notificación eliminada:', notificationId);
    }

    // Limpiar todas las notificaciones
    async function clearAllNotifications() {
        if (!db) return;

        if (!confirm('¿Estás seguro de que quieres eliminar todas las notificaciones?')) {
            return;
        }

        const transaction = db.transaction([STORE_NAME], 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        store.clear();

        notifications = [];
        renderNotifications();

        console.log('🧹 Todas las notificaciones eliminadas');
    }

    // Renderizar notificaciones
    function renderNotifications() {
        if (!container) return;

        const list = container.querySelector('#chat-notifications-list');
        if (!list) return;

        list.innerHTML = '';

        if (notifications.length === 0) {
            list.innerHTML = `
                <div style="padding: 40px 20px; text-align: center; color: #666;">
                    <div style="font-size: 24px; margin-bottom: 10px;">📭</div>
                    <div>No hay notificaciones</div>
                </div>
            `;
            container.style.display = 'none';
            return;
        }

        notifications.forEach(notification => {
            const item = document.createElement('div');
            item.className = `notification-item ${notification.read ? 'read' : 'unread'}`;
            item.style.cssText = `
                padding: 12px 16px;
                border-bottom: 1px solid #eee;
                cursor: pointer;
                background: ${notification.read ? 'white' : '#f0f8ff'};
                transition: background 0.2s;
            `;

            item.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 4px; color: #333;">
                    ${notification.title}
                </div>
                <div style="color: #666; margin-bottom: 8px; line-height: 1.4;">
                    ${notification.message}
                </div>
                <div style="font-size: 12px; color: #999;">
                    ${formatTime(notification.timestamp)}
                </div>
                <button onclick="event.stopPropagation(); removeChatNotification('${notification.id}')"
                        style="position: absolute; top: 8px; right: 8px; background: none; border: none; color: #999; cursor: pointer; font-size: 16px;">
                    ×
                </button>
            `;

            item.addEventListener('click', () => markAsRead(notification.id));
            item.addEventListener('mouseenter', () => item.style.background = '#f5f5f5');
            item.addEventListener('mouseleave', () => item.style.background = notification.read ? 'white' : '#f0f8ff');

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
        if (days < 7) return `Hace ${days}d`;
        return date.toLocaleDateString();
    }

    // Función de debug
    function debugNotifications() {
        console.log('=== CHAT NOTIFICATIONS DEBUG ===');
        console.log('📊 Total notifications:', notifications.length);
        console.log('👤 Current user ID:', currentUserId);
        console.log('💾 IndexedDB:', db ? 'Connected' : 'Not connected');
        console.log('🔄 Polling:', pollingInterval ? 'Active' : 'Inactive');
        console.log('📱 Container visible:', container ? container.style.display !== 'none' : false);

        notifications.forEach((n, i) => {
            console.log(`  ${i + 1}. ${n.title} (${n.read ? 'read' : 'unread'})`);
        });
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChatNotifications);
    } else {
        initChatNotifications();
    }

    // Cleanup al cerrar
    window.addEventListener('beforeunload', function() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        if (db) {
            db.close();
        }
    });


})();/**
 * Notification System API Client
 * Handles all notification-related functionality through REST API
 */

class NotificationManager {
    constructor() {
        this.baseUrl = '/chat/api/notifications';
        this.intervalId = null;
        this.refreshTimeout = null;
        this.isInitialized = false;
        this.lastTotalUnread = 0;
    }

    /**
     * Initialize the notification system
     */
    init() {
        if (this.isInitialized) return;

        this.loadNotifications();
        this.setupPeriodicRefresh();
        this.bindEvents();

        this.isInitialized = true;

        // Force an immediate refresh after 2 seconds to catch any missed notifications
        setTimeout(() => {
            this.loadNotifications();
        }, 2000);
    }

    /**
     * Load unread notifications from API
     */
    async loadNotifications() {
        try {
            const response = await fetch(`${this.baseUrl}/unread/`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin'
            });


            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            let data;
            try {
                data = await response.json();
            } catch (jsonError) {
                console.error('Failed to parse JSON response:', jsonError);
                throw new Error('Invalid JSON response from server');
            }


            // Validate response data
            if (typeof data !== 'object' || data === null) {
                throw new Error('Invalid response format');
            }

            // Ensure total_unread is a valid number
            const totalUnread = typeof data.total_unread === 'number' ? data.total_unread : 0;

            // Only update if count has changed to avoid unnecessary DOM updates
            if (totalUnread !== this.lastTotalUnread) {
                this.updateBadge(totalUnread);
                this.displayNotifications(data.notifications || []);
                this.lastTotalUnread = totalUnread;
            } else {
            }

        } catch (error) {
            console.error('Error loading notifications:', error);
            this.showError('Failed to load notifications');
        }
    }

    /**
     * Mark notifications as read
     */
    async markAsRead(notificationIds) {
        // Validate input
        if (!Array.isArray(notificationIds)) {
            console.error('notificationIds must be an array');
            this.showError('Invalid notification IDs format');
            return false;
        }

        try {
            const response = await fetch(`${this.baseUrl}/mark-read/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin',
                body: JSON.stringify({ notification_ids: notificationIds })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.success) {
                await this.loadNotifications(); // Refresh the list
                return true;
            } else {
                throw new Error(data.error || 'Failed to mark notifications as read');
            }

        } catch (error) {
            console.error('Error marking notifications as read:', error);
            this.showError('Failed to mark notifications as read. Please try again.');
            return false;
        }
    }

    /**
     * Update notification badge
     */
    updateBadge(count) {

        const badge = document.getElementById('header-notification-badge');
        const markAllBtn = document.getElementById('header-mark-all-read-btn');


        if (!badge) {
            console.error('Notification badge element not found! Available elements:', document.querySelectorAll('[id*="notification"]'));
            return;
        }

        // Update last count
        this.lastTotalUnread = count;

        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.style.display = 'block';
            if (markAllBtn) {
                markAllBtn.style.display = 'block';
            }
        } else {
            badge.style.display = 'none';
            if (markAllBtn) {
                markAllBtn.style.display = 'none';
            }
        }
    }

    /**
     * Display notifications in the dropdown
     */
    displayNotifications(notifications) {
        const container = document.getElementById('header-notifications-list');

        if (!container) {
            return;
        }

        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center p-4">
                    <i class="bi bi-bell-slash fs-1 text-muted"></i>
                    <p class="text-muted mt-2">No notifications</p>
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        notifications.slice(0, 5).forEach(notification => {
            const notificationElement = document.createElement('li');
            notificationElement.className = 'notification-item border-bottom';
            notificationElement.setAttribute('data-id', notification.id);
            notificationElement.innerHTML = `
                <i class="bi bi-chat-dots text-primary me-2"></i>
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${this.escapeHtml(notification.title)}</h6>
                        <p class="mb-1 text-muted small">${this.escapeHtml(notification.message)}</p>
                        <small class="text-muted">${this.formatDate(notification.created_at)}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary ms-2" data-notification-id="${notification.id}">
                        <i class="bi bi-check"></i>
                    </button>
                </div>
            `;
            container.appendChild(notificationElement);
        });

        // Add "View all" link if there are more than 5
        if (notifications.length > 5) {
            const viewAllElement = document.createElement('li');
            viewAllElement.className = 'text-center p-2';
            viewAllElement.innerHTML = `
                <a href="/chat/room/" class="text-primary">
                    View all ${notifications.length} notifications
                </a>
            `;
            container.appendChild(viewAllElement);
        }
    }

    /**
     * Setup periodic refresh
     */
    setupPeriodicRefresh() {
        // Refresh every 30 seconds
        this.intervalId = setInterval(() => {
            this.loadNotifications();
        }, 30000);
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Mark individual notification as read
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-notification-id]')) {
                const notificationId = e.target.closest('[data-notification-id]').getAttribute('data-notification-id');
                if (notificationId) {
                    this.markAsRead([notificationId]);
                }
            }
        });

        // Mark all notifications as read
        const markAllBtn = document.getElementById('header-mark-all-read-btn');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', async () => {
                try {
                    const success = await this.markAsRead([]); // Empty array marks all as read
                    if (success) {
                    }
                } catch (error) {
                    console.error('Error marking all notifications as read:', error);
                    this.showError('Failed to mark all notifications as read');
                }
            });
        } else {
        }

        // Listen for new messages to update counter immediately
        this.setupWebSocketListener();
    }

    /**
     * Setup WebSocket listener for real-time updates
     */
    setupWebSocketListener() {
        // Listen for chat messages and update counter immediately
        document.addEventListener('chatMessageReceived', () => {
            // Update immediately when a new message is received
            this.forceRefresh();
        });

        // Also listen for any WebSocket messages that might indicate new content
        document.addEventListener('websocketMessage', (event) => {
            const data = event.detail;
            if (data.type === 'chat_message' || data.type === 'message') {
                this.forceRefresh();
            }
        });

        // Listen for storage events (in case multiple tabs are open)
        window.addEventListener('storage', (event) => {
            if (event.key === 'chat_new_message') {
                this.forceRefresh();
            }
        });

        // Listen for widget events
        document.addEventListener('messagesMarkedAsRead', (event) => {
            this.forceRefresh();
        });

        // Listen for new messages from widget
        document.addEventListener('widgetNewMessage', (event) => {
            this.forceRefresh();
        });

        // Listen for room view events to mark messages as read
        document.addEventListener('roomViewed', (event) => {
            const roomId = event.detail?.roomId;
            if (roomId) {
                // Mark messages as read for this room
                this.markRoomMessagesAsRead(roomId);
            }
        });
    }

    /**
     * Force immediate refresh of notifications
     */
    forceRefresh() {
        // Clear any pending refresh
        if (this.refreshTimeout) {
            clearTimeout(this.refreshTimeout);
        }
        // Refresh immediately
        this.loadNotifications();
    }

    /**
     * Mark messages in a specific room as read
     */
    async markRoomMessagesAsRead(roomId) {
        try {
            const response = await fetch('/chat/api/chat/reset-unread/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin',
                body: JSON.stringify({ room_id: roomId })
            });

            if (response.ok) {
                // Refresh notifications after marking as read
                setTimeout(() => this.loadNotifications(), 500);
            } else {
                console.error('Failed to mark room messages as read:', response.status);
            }
        } catch (error) {
            console.error('Error marking room messages as read:', error);
        }
    }

    /**
     * Get CSRF token
     */
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.querySelector('#csrf-form [name=csrfmiddlewaretoken]')?.value ||
               document.querySelector('#dummy-csrf-form [name=csrfmiddlewaretoken]')?.value || '';
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Format date for display
     */
    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch (e) {
            return dateString;
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'm360-alert m360-alert-danger m360-alert-dismissible m360-d-flex m360-items-center';
        errorDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; position: fixed;';
        errorDiv.setAttribute('role', 'alert');
        errorDiv.innerHTML = `
            <i class="bi bi-exclamation-triangle-fill m360-mr-2"></i>
            <div class="m360-flex-1">${message}</div>
            <button type="button" class="m360-alert-dismiss" aria-label="Cerrar">✕</button>
        `;

        document.body.appendChild(errorDiv);

        const closeBtn = errorDiv.querySelector('.m360-alert-dismiss');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => errorDiv.remove());
        }

        setTimeout(() => {
            if (errorDiv.parentNode) errorDiv.remove();
        }, 5000);
    }

    /**
     * Cleanup resources
     */
    destroy() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.isInitialized = false;
    }

    /**
     * Debug function to check notification system status
     */
    debug() {
    }

    /**
     * Test function to create a test notification
     */
    async testCreateNotification() {
        try {
            const response = await fetch(`${this.baseUrl}/test-create/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    message: 'Test notification from frontend',
                    room_id: 1
                })
            });

            if (response.ok) {
                const result = await response.json();
                // Refresh notifications after creating test
                setTimeout(() => this.loadNotifications(), 1000);
            } else {
                console.error('Failed to create test notification:', response.status);
            }
        } catch (error) {
            console.error('Error creating test notification:', error);
        }
    }

    /**
     * Check if user is authenticated
     */
    checkAuthentication() {
        return document.querySelector('[data-user-authenticated="true"]') ||
               document.body.classList.contains('authenticated') ||
               document.body.hasAttribute('data-user-authenticated') ||
               document.querySelector('meta[name="user-authenticated"][content="true"]') ||
               (window.django && window.django.user && window.django.user.is_authenticated);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize for authenticated users
    const isAuthenticated = document.querySelector('[data-user-authenticated="true"]') ||
                            document.body.classList.contains('authenticated') ||
                            document.body.hasAttribute('data-user-authenticated') ||
                            document.querySelector('meta[name="user-authenticated"][content="true"]') ||
                            (window.django && window.django.user && window.django.user.is_authenticated);


    if (isAuthenticated) {
        const notificationManager = new NotificationManager();
        notificationManager.init();

        // Make debug and test functions available globally
        window.updateNotificationCount = () => notificationManager.loadNotifications();
        window.forceNotificationRefresh = () => notificationManager.forceRefresh();

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            notificationManager.destroy();
        });
    } else {
    }
});

// Export for potential use in other scripts
window.NotificationManager = NotificationManager;// Chat Widget Integration System
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
}/**
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

})();// process_inbox_item.js
// Funciones JavaScript para la vista de procesamiento de inbox items

// ============================================================================
// CONSTANTES Y CONFIGURACIÓN
// ============================================================================

const API_ENDPOINTS = {
    TASKS: '/events/inbox/api/tasks/',
    PROJECTS: '/events/inbox/api/projects/',
    BULK_ACTION: '/events/inbox/admin/bulk-action/'
};

const EVENT_LISTENERS = {
    TASK_SEARCH: 'taskSearch',
    PROJECT_SEARCH: 'projectSearch',
    TASK_ITEMS: 'taskList',
    PROJECT_ITEMS: 'projectList'
};

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

/**
 * Muestra un modal de alerta
 */
function showAlertModal(title, message, type = 'info') {
    const modal = new bootstrap.Modal(document.getElementById('alertModal'));
    const modalTitle = document.getElementById('alertModalLabel');
    const modalBody = document.getElementById('alertModalBody');

    const icons = {
        'success': 'bi-check-circle-fill text-success',
        'danger': 'bi-exclamation-triangle-fill text-danger',
        'warning': 'bi-exclamation-triangle-fill text-warning',
        'info': 'bi-info-circle-fill text-info'
    };

    modalTitle.innerHTML = `<i class="bi ${icons[type] || icons['info']} me-2"></i>${title}`;
    modalBody.innerHTML = `<p class="mb-0">${message}</p>`;

    modal.show();
}

/**
 * Muestra un modal de confirmación
 */
function showConfirmModal(title, message, type = 'warning', onConfirm, onCancel) {
    const modalHtml = `
        <div class="modal fade" id="confirmModal" tabindex="-1" aria-labelledby="confirmModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="confirmModalLabel">
                            <i class="bi bi-question-circle-fill text-${type} me-2"></i>${title}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p class="mb-0">${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="confirmCancelBtn">Cancelar</button>
                        <button type="button" class="btn btn-${type}" id="confirmOkBtn">Confirmar</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    const confirmBtn = document.getElementById('confirmOkBtn');
    const cancelBtn = document.getElementById('confirmCancelBtn');

    confirmBtn.addEventListener('click', () => {
        modal.hide();
        if (onConfirm) onConfirm();
        setTimeout(() => {
            document.getElementById('confirmModal').remove();
        }, 300);
    });

    cancelBtn.addEventListener('click', () => {
        modal.hide();
        if (onCancel) onCancel();
        setTimeout(() => {
            document.getElementById('confirmModal').remove();
        }, 300);
    });

    document.getElementById('confirmModal').addEventListener('hidden.bs.modal', () => {
        if (onCancel) onCancel();
        document.getElementById('confirmModal').remove();
    });

    modal.show();
}

/**
 * Obtiene el token CSRF del documento
 */
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

/**
 * Maneja errores de API de manera consistente
 */
function handleApiError(error, context = 'operación') {
    console.error(`[ERROR] ${context}:`, error);
    
    let errorMessage = 'Error en la operación';
    if (error instanceof Error) {
        errorMessage = error.message;
    } else if (typeof error === 'string') {
        errorMessage = error;
    }
    
    showAlertModal('Error', errorMessage, 'danger');
}

// ============================================================================
// FUNCIONES DE SELECTORES (TAREAS/PROYECTOS)
// ============================================================================

/**
 * Muestra el selector de tareas
 */
function showTaskSelector() {
    console.log('[SHOW_TASK_SELECTOR] Iniciando apertura del modal de tareas');
    const modal = new bootstrap.Modal(document.getElementById('taskSelectorModal'));
    modal.show();
    loadAvailableTasks();
}

/**
 * Carga tareas disponibles desde la API
 */
function loadAvailableTasks() {
    console.log('[LOAD_TASKS] Iniciando carga de tareas disponibles');
    const taskList = document.getElementById('taskList');
    if (!taskList) return;

    taskList.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Cargando tareas...</div>';

    fetch(API_ENDPOINTS.TASKS, {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (response.status === 404) {
            return loadSampleTasks();
        }
        return response.json();
    })
    .then(data => {
        if (data?.tasks?.length > 0) {
            console.log('[LOAD_TASKS] Datos recibidos:', data.tasks.length, 'tareas');
            renderTaskList(data.tasks);
        } else if (!data) {
            // Ya manejado por loadSampleTasks()
        } else {
            renderEmptyTaskList();
        }
    })
    .catch(error => {
        console.error('[LOAD_TASKS] Error:', error);
        renderTaskError();
    });
}

/**
 * Carga datos de ejemplo cuando la API no está disponible
 */
function loadSampleTasks() {
    const taskList = document.getElementById('taskList');
    const sampleTasks = [
        { 
            id: 1, 
            title: 'Revisar documentación del proyecto', 
            description: 'Actualizar la documentación técnica', 
            priority: 'alta',
            status: 'Pendiente'
        },
        { 
            id: 2, 
            title: 'Implementar nueva funcionalidad', 
            description: 'Desarrollar el módulo de reportes', 
            priority: 'media',
            status: 'En progreso'
        },
        { 
            id: 3, 
            title: 'Corregir bugs menores', 
            description: 'Arreglar issues reportados por usuarios', 
            priority: 'baja',
            status: 'Completado'
        }
    ];

    renderTaskList(sampleTasks);
}

/**
 * Renderiza la lista de tareas
 */
function renderTaskList(tasks) {
    const taskList = document.getElementById('taskList');
    
    taskList.innerHTML = tasks.map(task => `
        <div class="list-group-item task-item" onclick="selectTask(${task.id}, '${escapeHtml(task.title)}')">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${escapeHtml(task.title)}</h6>
                    <small class="text-muted">${escapeHtml(task.description || 'Sin descripción')}</small>
                </div>
                <div class="d-flex flex-column align-items-end gap-1">
                    <span class="badge bg-${getPriorityBadgeClass(task.priority)}">${task.priority || 'media'}</span>
                    <span class="badge bg-secondary">${task.status || 'Sin estado'}</span>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Renderiza lista vacía de tareas
 */
function renderEmptyTaskList() {
    const taskList = document.getElementById('taskList');
    taskList.innerHTML = '<div class="text-center text-muted py-3">No hay tareas disponibles</div>';
}

/**
 * Renderiza error en carga de tareas
 */
function renderTaskError() {
    const taskList = document.getElementById('taskList');
    taskList.innerHTML = '<div class="text-center text-danger py-3">Error al cargar tareas</div>';
    showAlertModal('Error', 'No se pudieron cargar las tareas disponibles', 'danger');
}

/**
 * Selecciona una tarea
 */
function selectTask(taskId, taskTitle) {
    console.log('[SELECT_TASK] Tarea seleccionada:', taskId, taskTitle);
    
    const selectedTaskInfo = document.getElementById('selectedTaskInfo');
    if (selectedTaskInfo) {
        selectedTaskInfo.innerHTML = `
            <div class="selected-info-panel">
                <h6 class="mb-1"><i class="bi bi-check-circle me-2"></i>Tarea Seleccionada</h6>
                <p class="mb-0">${taskTitle}</p>
                <input type="hidden" name="task_id" value="${taskId}">
                <div class="mt-2">
                    <button type="submit" name="action" value="link_to_task" class="btn btn-success btn-sm">
                        <i class="bi bi-link me-1"></i>Vincular a esta tarea
                    </button>
                </div>
            </div>
        `;
    }
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('taskSelectorModal'));
    if (modal) modal.hide();
    
    scrollToElement('selectedTaskInfo');
}

// ============================================================================
// FUNCIONES DE PROYECTOS
// ============================================================================

/**
 * Muestra el selector de proyectos
 */
function showProjectSelector() {
    console.log('[SHOW_PROJECT_SELECTOR] Iniciando apertura del modal de proyectos');
    const modal = new bootstrap.Modal(document.getElementById('projectSelectorModal'));
    modal.show();
    loadAvailableProjects();
}

/**
 * Carga proyectos disponibles desde la API
 */
function loadAvailableProjects() {
    console.log('[LOAD_PROJECTS] Iniciando carga de proyectos disponibles');
    const projectList = document.getElementById('projectList');
    if (!projectList) return;

    projectList.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Cargando proyectos...</div>';

    fetch(API_ENDPOINTS.PROJECTS, {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (response.status === 404) {
            return loadSampleProjects();
        }
        return response.json();
    })
    .then(data => {
        if (data?.projects?.length > 0) {
            console.log('[LOAD_PROJECTS] Datos recibidos:', data.projects.length, 'proyectos');
            renderProjectList(data.projects);
        } else if (!data) {
            // Ya manejado por loadSampleProjects()
        } else {
            renderEmptyProjectList();
        }
    })
    .catch(error => {
        console.error('[LOAD_PROJECTS] Error:', error);
        renderProjectError();
    });
}

/**
 * Carga datos de ejemplo para proyectos
 */
function loadSampleProjects() {
    const projectList = document.getElementById('projectList');
    const sampleProjects = [
        { 
            id: 1, 
            title: 'Sistema de Gestión de Proyectos', 
            description: 'Desarrollo completo del sistema GTD', 
            status: 'En progreso',
            task_count: 15
        },
        { 
            id: 2, 
            title: 'Migración a nueva plataforma', 
            description: 'Actualización tecnológica del sistema', 
            status: 'Planificación',
            task_count: 8
        },
        { 
            id: 3, 
            title: 'Implementación de API REST', 
            description: 'Desarrollo de endpoints para integración', 
            status: 'Pendiente',
            task_count: 5
        }
    ];

    renderProjectList(sampleProjects);
}

/**
 * Renderiza la lista de proyectos
 */
function renderProjectList(projects) {
    const projectList = document.getElementById('projectList');
    
    projectList.innerHTML = projects.map(project => `
        <div class="list-group-item project-item" onclick="selectProject(${project.id}, '${escapeHtml(project.title)}')">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${escapeHtml(project.title)}</h6>
                    <small class="text-muted">${escapeHtml(project.description || 'Sin descripción')}</small>
                    ${project.task_count ? `<small class="d-block text-info mt-1"><i class="bi bi-list-task me-1"></i>${project.task_count} tareas</small>` : ''}
                </div>
                <span class="badge ${getStatusBadgeClass(project.status)}">${project.status || 'Sin estado'}</span>
            </div>
        </div>
    `).join('');
}

/**
 * Renderiza lista vacía de proyectos
 */
function renderEmptyProjectList() {
    const projectList = document.getElementById('projectList');
    projectList.innerHTML = '<div class="text-center text-muted py-3">No hay proyectos disponibles</div>';
}

/**
 * Renderiza error en carga de proyectos
 */
function renderProjectError() {
    const projectList = document.getElementById('projectList');
    projectList.innerHTML = '<div class="text-center text-danger py-3">Error al cargar proyectos</div>';
    showAlertModal('Error', 'No se pudieron cargar los proyectos disponibles', 'danger');
}

/**
 * Selecciona un proyecto
 */
function selectProject(projectId, projectTitle) {
    console.log('[SELECT_PROJECT] Proyecto seleccionado:', projectId, projectTitle);
    
    const selectedProjectInfo = document.getElementById('selectedProjectInfo');
    if (selectedProjectInfo) {
        selectedProjectInfo.innerHTML = `
            <div class="selected-info-panel">
                <h6 class="mb-1"><i class="bi bi-check-circle me-2"></i>Proyecto Seleccionado</h6>
                <p class="mb-0">${projectTitle}</p>
                <input type="hidden" name="project_id" value="${projectId}">
                <div class="mt-2">
                    <button type="submit" name="action" value="link_to_project" class="btn btn-success btn-sm">
                        <i class="bi bi-link me-1"></i>Vincular a este proyecto
                    </button>
                </div>
            </div>
        `;
    }
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('projectSelectorModal'));
    if (modal) modal.hide();
    
    scrollToElement('selectedProjectInfo');
}

// ============================================================================
// FUNCIONES DE BÚSQUEDA Y FILTRADO
// ============================================================================

/**
 * Inicializa la búsqueda en tiempo real para tareas
 */
function initTaskSearch() {
    const taskSearch = document.getElementById('taskSearch');
    if (taskSearch) {
        taskSearch.addEventListener('input', function() {
            filterListItems('taskList', this.value.toLowerCase());
        });
    }
}

/**
 * Inicializa la búsqueda en tiempo real para proyectos
 */
function initProjectSearch() {
    const projectSearch = document.getElementById('projectSearch');
    if (projectSearch) {
        projectSearch.addEventListener('input', function() {
            filterListItems('projectList', this.value.toLowerCase());
        });
    }
}

/**
 * Filtra elementos de lista por término de búsqueda
 */
function filterListItems(listId, searchTerm) {
    const items = document.querySelectorAll(`#${listId} .list-group-item`);
    
    items.forEach(item => {
        const title = item.querySelector('h6')?.textContent?.toLowerCase() || '';
        const description = item.querySelector('small')?.textContent?.toLowerCase() || '';
        
        if (title.includes(searchTerm) || description.includes(searchTerm)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

// ============================================================================
// FUNCIONES DE GESTIÓN DE INBOX ITEMS
// ============================================================================

/**
 * Elimina un item del inbox
 */
function deleteInboxItem(itemId, title) {
    console.log('[DELETE_INBOX_ITEM] Iniciando eliminación:', itemId, title);
    
    showConfirmModal(
        `¿Eliminar item?`,
        `¿Estás seguro de que quieres eliminar "${title}"? Esta acción no se puede deshacer.`,
        'danger',
        () => {
            console.log('[DELETE_INBOX_ITEM] Usuario confirmó eliminación');
            performDeleteInboxItem(itemId);
        },
        () => {
            console.log('[DELETE_INBOX_ITEM] Usuario canceló eliminación');
        }
    );
}

/**
 * Realiza la eliminación del item
 */
function performDeleteInboxItem(itemId) {
    const csrfToken = getCSRFToken();
    
    fetch(API_ENDPOINTS.BULK_ACTION, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `action=delete&selected_items=${itemId}`
    })
    .then(response => response.text())
    .then(text => {
        try {
            const data = JSON.parse(text);
            handleDeleteResponse(data);
        } catch (error) {
            console.error('[DELETE_INBOX_ITEM] Error parseando respuesta:', error);
            showAlertModal('Error', 'Respuesta inválida del servidor', 'danger');
        }
    })
    .catch(error => {
        console.error('[DELETE_INBOX_ITEM] Error en la solicitud:', error);
        showAlertModal('Error', 'Error de conexión con el servidor', 'danger');
    });
}

/**
 * Maneja la respuesta de eliminación
 */
function handleDeleteResponse(data) {
    if (data.success) {
        showAlertModal('Item eliminado', 'El item ha sido eliminado exitosamente.', 'success');
        setTimeout(() => {
            window.location.href = '/events/inbox/';
        }, 1500);
    } else {
        showAlertModal('Error al eliminar', data.error || 'Error desconocido', 'danger');
    }
}

// ============================================================================
// FUNCIONES AUXILIARES
// ============================================================================

/**
 * Obtiene la clase CSS para badges de prioridad
 */
function getPriorityBadgeClass(priority) {
    const classes = {
        'alta': 'danger',
        'media': 'warning',
        'baja': 'secondary',
        'high': 'danger',
        'medium': 'warning',
        'low': 'secondary'
    };
    return classes[priority?.toLowerCase()] || 'secondary';
}

/**
 * Obtiene la clase CSS para badges de estado
 */
function getStatusBadgeClass(status) {
    const classes = {
        'en progreso': 'bg-primary',
        'planificación': 'bg-info',
        'pendiente': 'bg-warning',
        'completado': 'bg-success',
        'cancelado': 'bg-danger'
    };
    return classes[status?.toLowerCase()] || 'bg-secondary';
}

/**
 * Escapa HTML para prevenir XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Desplaza la vista a un elemento específico
 */
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Alterna entre vista de cuadrícula y lista
 */
function toggleActionView(viewType) {
    const actionCards = document.querySelectorAll('.action-card');
    
    actionCards.forEach(card => {
        if (viewType === 'list') {
            card.classList.add('list-view');
            card.classList.remove('grid-view');
        } else {
            card.classList.add('grid-view');
            card.classList.remove('list-view');
        }
    });
    
    // Actualizar estado del botón
    const buttons = document.querySelectorAll('.btn-group-sm .btn');
    buttons.forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
}

// ============================================================================
// FUNCIONES DE INICIALIZACIÓN
// ============================================================================

/**
 * Inicializa todas las funcionalidades cuando el DOM está listo
 */
function initializeInboxProcessing() {
    console.log('[INIT] Inicializando procesamiento de inbox');
    
    // Inicializar búsquedas
    initTaskSearch();
    initProjectSearch();
    
    // Configurar event listeners para formularios
    setupFormListeners();
    
    // Configurar animaciones y efectos
    setupAnimations();
    
    console.log('[INIT] Procesamiento de inbox inicializado');
}

/**
 * Configura listeners para formularios
 */
function setupFormListeners() {
    const processForm = document.getElementById('processForm');
    if (processForm) {
        processForm.addEventListener('submit', function(event) {
            // Validación adicional antes de enviar
            const action = event.submitter?.value;
            if (action === 'link_to_task' && !this.querySelector('[name="task_id"]')) {
                event.preventDefault();
                showAlertModal('Selección requerida', 'Por favor selecciona una tarea primero', 'warning');
                return;
            }
            if (action === 'link_to_project' && !this.querySelector('[name="project_id"]')) {
                event.preventDefault();
                showAlertModal('Selección requerida', 'Por favor selecciona un proyecto primero', 'warning');
                return;
            }
            
            // Mostrar indicador de procesamiento
            const submitButton = event.submitter;
            if (submitButton) {
                const originalText = submitButton.innerHTML;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';
                submitButton.disabled = true;
                
                // Restaurar después de 5 segundos por si algo falla
                setTimeout(() => {
                    submitButton.innerHTML = originalText;
                    submitButton.disabled = false;
                }, 5000);
            }
        });
    }
}

/**
 * Configura animaciones y efectos visuales
 */
function setupAnimations() {
    // Efecto hover en tarjetas de acción
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.zIndex = '10';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.zIndex = '1';
        });
    });
    
    // Efecto click en items de lista
    const listItems = document.querySelectorAll('.task-item, .project-item');
    listItems.forEach(item => {
        item.addEventListener('click', function() {
            // Remover selección anterior
            this.parentNode.querySelectorAll('.selected').forEach(selected => {
                selected.classList.remove('selected');
            });
            // Agregar selección actual
            this.classList.add('selected');
        });
    });
}

// ============================================================================
// EVENTOS GLOBALES
// ============================================================================

/**
 * Maneja errores no capturados
 */
window.addEventListener('error', function(event) {
    console.error('[GLOBAL_ERROR]', event.error);
    showAlertModal('Error inesperado', 'Ocurrió un error inesperado. Por favor recarga la página.', 'danger');
});

/**
 * Maneja promesas rechazadas no capturadas
 */
window.addEventListener('unhandledrejection', function(event) {
    console.error('[UNHANDLED_REJECTION]', event.reason);
    showAlertModal('Error en promesa', 'Ocurrió un error en una operación asíncrona.', 'warning');
});

// ============================================================================
// INICIALIZACIÓN CUANDO EL DOM ESTÁ LISTO
// ============================================================================

document.addEventListener('DOMContentLoaded', initializeInboxProcessing);

// ============================================================================
// EXPORTACIONES (para módulos)
// ============================================================================

// Exportar funciones principales para uso en otros módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showAlertModal,
        showConfirmModal,
        showTaskSelector,
        showProjectSelector,
        deleteInboxItem,
        initializeInboxProcessing
    };
}// ============================================================================
// INICIALIZACIÓN DE BOOTSTRAP Y VARIABLES GLOBALES
// ============================================================================

// Almacenar instancias de modales para un mejor control
let modals = {};
// Variable para evitar doble envío
let isSubmitting = false;

// Inicializar cuando el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    console.log('Process Inbox Item JS inicializado');
    
    // Inicializar todos los modales de Bootstrap
    initializeModals();
    
    // Inicializar opciones de proyecto y evento
    toggleProjectOptions();
    toggleEventOptions();
    
    // Configurar event listeners
    setupEventListeners();
    
    // Configurar búsquedas en tiempo real
    setupSearchFilters();
    
    // Actualizar vista previa inicial
    updateCreationPreview();
    
    // Configurar formulario de clasificación
    setupClassificationForm();
});

// ============================================================================
// INICIALIZACIÓN DE MODALES
// ============================================================================

function initializeModals() {
    // Lista de IDs de modales a inicializar
    const modalIds = ['taskSelectorModal', 'projectSelectorModal', 'eventSelectorModal', 'alertModal'];
    
    modalIds.forEach(id => {
        const modalElement = document.getElementById(id);
        if (modalElement) {
            try {
                // Crear instancia del modal de Bootstrap
                modals[id] = new bootstrap.Modal(modalElement);
                console.log(`Modal ${id} inicializado correctamente`);
                
                // Agregar event listeners para depuración
                modalElement.addEventListener('show.bs.modal', () => {
                    console.log(`Mostrando modal: ${id}`);
                });
                
                modalElement.addEventListener('shown.bs.modal', () => {
                    console.log(`Modal ${id} mostrado completamente`);
                    // Cargar datos según el tipo de modal
                    if (id === 'taskSelectorModal') loadAvailableTasks();
                    if (id === 'projectSelectorModal') loadAvailableProjects();
                    if (id === 'eventSelectorModal') loadAvailableEvents();
                });
                
            } catch (error) {
                console.error(`Error inicializando modal ${id}:`, error);
            }
        } else {
            console.warn(`Elemento modal ${id} no encontrado en el DOM`);
        }
    });
}

// ============================================================================
// FUNCIONES DE CONFIGURACIÓN DE CREACIÓN
// ============================================================================

// Mostrar/ocultar opciones de proyecto
function toggleProjectOptions() {
    const projectOption = document.getElementById('projectOption');
    if (!projectOption) return;
    
    const existingProjectSelect = document.getElementById('existingProjectSelect');
    const taskContextPreview = document.getElementById('taskContextPreview');
    const taskProjectPreview = document.getElementById('taskProjectPreview');
    const projectEventPreview = document.getElementById('projectEventPreview');
    
    // Mostrar/ocultar selector de proyecto existente
    if (existingProjectSelect) {
        existingProjectSelect.style.display = projectOption.value === 'existing' ? 'block' : 'none';
    }
    
    // Actualizar vistas previas
    if (projectOption.value === 'new') {
        if (taskContextPreview) taskContextPreview.textContent = 'Tarea en nuevo proyecto';
        if (taskProjectPreview) taskProjectPreview.textContent = 'Nuevo proyecto';
        if (projectEventPreview) projectEventPreview.textContent = 'Nuevo';
    } else if (projectOption.value === 'existing') {
        if (taskContextPreview) taskContextPreview.textContent = 'Tarea en proyecto existente';
        if (taskProjectPreview) taskProjectPreview.textContent = 'Existente (seleccionar)';
        if (projectEventPreview) projectEventPreview.textContent = 'Del proyecto';
    } else {
        if (taskContextPreview) taskContextPreview.textContent = 'Tarea independiente';
        if (taskProjectPreview) taskProjectPreview.textContent = 'Ninguno';
        if (projectEventPreview) projectEventPreview.textContent = 'Nuevo';
    }
    
    updateCreationPreview();
}

// Mostrar/ocultar opciones de evento
function toggleEventOptions() {
    const eventOption = document.getElementById('eventOption');
    if (!eventOption) return;
    
    const existingEventSelect = document.getElementById('existingEventSelect');
    const taskEventPreview = document.getElementById('taskEventPreview');
    const projectEventPreview = document.getElementById('projectEventPreview');
    
    // Mostrar/ocultar selector de evento existente
    if (existingEventSelect) {
        existingEventSelect.style.display = eventOption.value === 'existing' ? 'block' : 'none';
    }
    
    // Actualizar vistas previas
    if (eventOption.value === 'new') {
        if (taskEventPreview) taskEventPreview.textContent = 'Nuevo';
        if (projectEventPreview) projectEventPreview.textContent = 'Nuevo';
    } else if (eventOption.value === 'existing') {
        if (taskEventPreview) taskEventPreview.textContent = 'Existente (seleccionar)';
        if (projectEventPreview) projectEventPreview.textContent = 'Existente (seleccionar)';
    } else {
        if (taskEventPreview) taskEventPreview.textContent = 'Sin evento';
        if (projectEventPreview) projectEventPreview.textContent = 'Sin evento';
    }
    
    updateCreationPreview();
}

// Actualizar vista previa de creación
function updateCreationPreview() {
    const projectOption = document.getElementById('projectOption');
    const eventOption = document.getElementById('eventOption');
    const previewText = document.getElementById('previewText');
    
    if (!projectOption || !eventOption || !previewText) return;
    
    const projectMessages = {
        'new': '📁 <strong>Nuevo proyecto</strong> creado automáticamente',
        'existing': '📁 <strong>Proyecto existente</strong> seleccionado',
        'none': '📁 <strong>Sin proyecto</strong> asociado'
    };
    
    const eventMessages = {
        'new': '📅 <strong>Nuevo evento</strong> creado automáticamente',
        'existing': '📅 <strong>Evento existente</strong> seleccionado',
        'none': '📅 <strong>Sin evento</strong> asociado'
    };
    
    const preview = [
        projectMessages[projectOption.value] || projectMessages.none,
        eventMessages[eventOption.value] || eventMessages.new
    ];
    
    previewText.innerHTML = preview.join('<br>');
}

// ============================================================================
// CONFIGURACIÓN DE EVENT LISTENERS
// ============================================================================

function setupEventListeners() {
    // Configurar cambios en selectores de proyecto y evento
    const projectOption = document.getElementById('projectOption');
    const eventOption = document.getElementById('eventOption');
    
    if (projectOption) {
        projectOption.addEventListener('change', function() {
            console.log('Proyecto cambiado a:', this.value);
            toggleProjectOptions();
        });
    }
    
    if (eventOption) {
        eventOption.addEventListener('change', function() {
            console.log('Evento cambiado a:', this.value);
            toggleEventOptions();
        });
    }
    
    // Configurar botones de confirmación en modales
    const linkEventBtn = document.getElementById('linkEventConfirmBtn');
    if (linkEventBtn) {
        linkEventBtn.addEventListener('click', linkToSelectedEvent);
    }
    
    const linkProjectBtn = document.getElementById('linkProjectConfirmBtn');
    if (linkProjectBtn) {
        linkProjectBtn.addEventListener('click', linkToSelectedProject);
    }
    
    // Capturar el envío del formulario para incluir las opciones seleccionadas
    const processForm = document.getElementById('processForm');
    if (processForm) {
        processForm.addEventListener('submit', function(e) {
            console.log('Formulario enviado con:');
            console.log('- project_option:', document.getElementById('projectOption').value);
            console.log('- event_option:', document.getElementById('eventOption').value);
            console.log('- assigned_to:', document.querySelector('[name="assigned_to"]').value);
        });
    }
}

// ============================================================================
// FUNCIONES DE CARGA DE DATOS (TAREAS, PROYECTOS, EVENTOS)
// ============================================================================

// Función genérica para cargar datos
async function loadData(endpoint, listElementId, sampleData, itemTemplate, fallbackMessage) {
    const listElement = document.getElementById(listElementId);
    if (!listElement) {
        console.warn(`Elemento ${listElementId} no encontrado`);
        return;
    }

    listElement.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Cargando...</div>';

    try {
        const response = await fetch(endpoint, {
            method: 'GET',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });

        let data;
        if (!response.ok) {
            console.log(`API ${endpoint} no disponible (${response.status}), mostrando datos de ejemplo`);
            data = { items: sampleData };
        } else {
            data = await response.json();
        }

        // Procesar diferentes formatos de respuesta
        let items = [];
        if (data && data.items) items = data.items;
        else if (data && data.tasks) items = data.tasks;
        else if (data && data.projects) items = data.projects;
        else if (data && data.events) items = data.events;
        else if (Array.isArray(data)) items = data;

        if (items && items.length > 0) {
            listElement.innerHTML = items.map(itemTemplate).join('');
        } else {
            listElement.innerHTML = `<div class="text-center text-muted py-3">${fallbackMessage}</div>`;
        }
    } catch (error) {
        console.error(`Error cargando ${endpoint}:`, error);
        // Mostrar datos de ejemplo como fallback
        if (sampleData && sampleData.length > 0) {
            listElement.innerHTML = sampleData.map(itemTemplate).join('');
        } else {
            listElement.innerHTML = '<div class="text-center text-danger">Error al cargar datos</div>';
        }
    }
}

// Cargar tareas disponibles
function loadAvailableTasks() {
    const sampleTasks = [
        { id: 1, title: 'Revisar documentación del proyecto', description: 'Actualizar la documentación técnica', priority: 'alta' },
        { id: 2, title: 'Implementar nueva funcionalidad', description: 'Desarrollar el módulo de reportes', priority: 'media' },
        { id: 3, title: 'Corregir bugs menores', description: 'Arreglar issues reportados por usuarios', priority: 'baja' }
    ];

    const taskTemplate = task => `
        <div class="list-group-item task-item" onclick="selectTask(${task.id}, '${task.title.replace(/'/g, "\\'")}')">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${task.title}</h6>
                    <small class="text-muted">${task.description || 'Sin descripción'}</small>
                </div>
                <span class="badge bg-${task.priority === 'alta' ? 'danger' : task.priority === 'media' ? 'warning' : 'secondary'}">
                    ${task.priority}
                </span>
            </div>
        </div>`;

    loadData(
        '/events/inbox/api/tasks/',
        'taskList',
        sampleTasks,
        taskTemplate,
        'No hay tareas disponibles'
    );
}

// Cargar proyectos disponibles
function loadAvailableProjects() {
    const sampleProjects = [
        { id: 1, title: 'Sistema de Gestión de Proyectos', description: 'Desarrollo completo del sistema GTD', status: 'En progreso' },
        { id: 2, title: 'Migración a nueva plataforma', description: 'Actualización tecnológica del sistema', status: 'Planificación' },
        { id: 3, title: 'Implementación de API REST', description: 'Desarrollo de endpoints para integración', status: 'Pendiente' }
    ];

    const projectTemplate = project => `
        <div class="list-group-item project-item" data-project-id="${project.id}">
            <div class="form-check">
                <input class="form-check-input" type="radio" name="selected_project" 
                       id="project${project.id}" value="${project.id}">
                <label class="form-check-label w-100" for="project${project.id}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">${project.title}</h6>
                            <small class="text-muted">${project.description || 'Sin descripción'}</small>
                        </div>
                        <span class="badge bg-primary">${project.status}</span>
                    </div>
                </label>
            </div>
        </div>`;

    loadData(
        '/events/inbox/api/projects/',
        'projectList',
        sampleProjects,
        projectTemplate,
        'No hay proyectos disponibles'
    );
}

// Cargar eventos disponibles
function loadAvailableEvents() {
    const sampleEvents = [
        { id: 1, title: 'Reunión de Proyecto Alpha', description: 'Revisión semanal del proyecto', status: 'En progreso' },
        { id: 2, title: 'Lanzamiento Beta', description: 'Presentación del lanzamiento beta', status: 'Planificado' },
        { id: 3, title: 'Capacitación del Equipo', description: 'Sesión de capacitación técnica', status: 'Completado' }
    ];

    const eventTemplate = event => `
        <div class="list-group-item event-item" data-event-id="${event.id}">
            <div class="form-check">
                <input class="form-check-input" type="radio" name="selected_event" 
                       id="event${event.id}" value="${event.id}">
                <label class="form-check-label w-100" for="event${event.id}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">${event.title}</h6>
                            <small class="text-muted">${event.description || 'Sin descripción'}</small>
                        </div>
                        <span class="badge bg-primary">${event.status}</span>
                    </div>
                </label>
            </div>
        </div>`;

    loadData(
        '/events/inbox/api/events/',
        'eventList',
        sampleEvents,
        eventTemplate,
        'No hay eventos disponibles'
    );
}

// ============================================================================
// CONFIGURACIÓN DE FILTROS DE BÚSQUEDA
// ============================================================================

function setupSearchFilters() {
    const setupSearch = (searchId, itemSelector) => {
        const searchElement = document.getElementById(searchId);
        if (!searchElement) return;
        
        searchElement.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            const items = document.querySelectorAll(itemSelector);
            
            items.forEach(item => {
                const title = item.querySelector('h6')?.textContent.toLowerCase() || '';
                const description = item.querySelector('small')?.textContent.toLowerCase() || '';
                const matches = title.includes(searchTerm) || description.includes(searchTerm);
                item.style.display = matches ? '' : 'none';
            });
        });
    };
    
    setupSearch('taskSearch', '#taskList .task-item');
    setupSearch('projectSearch', '#projectList .project-item');
    setupSearch('eventSearch', '#eventList .event-item');
}

// ============================================================================
// FUNCIONES DE SELECCIÓN Y VINCULACIÓN
// ============================================================================

// Seleccionar tarea
window.selectTask = function(taskId, taskTitle) {
    const selectedTaskInfo = document.getElementById('selectedTaskInfo');
    if (selectedTaskInfo) {
        selectedTaskInfo.innerHTML = `
            <div class="alert alert-success">
                <h6 class="mb-1"><i class="bi bi-check-circle me-2"></i>Tarea Seleccionada</h6>
                <p class="mb-0">${taskTitle}</p>
                <input type="hidden" name="selected_task_id" value="${taskId}">
                <button type="button" class="btn btn-sm btn-primary mt-2" onclick="confirmTaskLink(${taskId}, '${taskTitle.replace(/'/g, "\\'")}')">
                    <i class="bi bi-link me-1"></i>Confirmar Vinculación
                </button>
            </div>`;
    }
    
    // Cerrar modal
    if (modals['taskSelectorModal']) {
        modals['taskSelectorModal'].hide();
    }
};

// Confirmar vinculación de tarea
window.confirmTaskLink = function(taskId, taskTitle) {
    const form = document.createElement('form');
    form.method = 'post';
    form.action = window.location.href;
    form.style.display = 'none';
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
        <input type="hidden" name="action" value="link_to_task">
        <input type="hidden" name="task_id" value="${taskId}">
    `;
    
    document.body.appendChild(form);
    form.submit();
};

// Vincular a proyecto seleccionado
window.linkToSelectedProject = function() {
    const selectedProject = document.querySelector('input[name="selected_project"]:checked');
    if (!selectedProject) {
        showAlertModal('Selección requerida', 'Por favor, selecciona un proyecto para vincular.', 'warning');
        return;
    }
    
    const projectId = selectedProject.value;
    const projectTitle = document.querySelector(`label[for="project${projectId}"] h6`)?.textContent || 'Proyecto seleccionado';
    
    const form = document.createElement('form');
    form.method = 'post';
    form.action = window.location.href;
    form.style.display = 'none';
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
        <input type="hidden" name="action" value="link_to_project">
        <input type="hidden" name="project_id" value="${projectId}">
    `;
    
    document.body.appendChild(form);
    form.submit();
};

// Vincular a evento seleccionado
window.linkToSelectedEvent = function() {
    const selectedEvent = document.querySelector('input[name="selected_event"]:checked');
    if (!selectedEvent) {
        showAlertModal('Selección requerida', 'Por favor, selecciona un evento para vincular.', 'warning');
        return;
    }
    
    const eventId = selectedEvent.value;
    const eventTitle = document.querySelector(`label[for="event${eventId}"] h6`)?.textContent || 'Evento seleccionado';
    
    const form = document.createElement('form');
    form.method = 'post';
    form.action = window.location.href;
    form.style.display = 'none';
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
        <input type="hidden" name="action" value="link_to_event">
        <input type="hidden" name="event_id" value="${eventId}">
    `;
    
    document.body.appendChild(form);
    form.submit();
};

// ============================================================================
// FUNCIONES DE UTILIDAD - MODALES Y MENSAJES
// ============================================================================

// Mostrar modal de alerta
function showAlertModal(title, message, type = 'info') {
    const modalElement = document.getElementById('alertModal');
    if (!modalElement) {
        alert(`${title}: ${message}`);
        return;
    }
    
    const icons = {
        'success': 'bi-check-circle-fill text-success',
        'danger': 'bi-exclamation-triangle-fill text-danger',
        'warning': 'bi-exclamation-triangle-fill text-warning',
        'info': 'bi-info-circle-fill text-info'
    };

    document.getElementById('alertModalLabel').innerHTML = 
        `<i class="bi ${icons[type] || icons['info']} me-2"></i>${title}`;
    document.getElementById('alertModalBody').innerHTML = `<p class="mb-0">${message}</p>`;
    
    // Usar la instancia guardada o crear una nueva
    if (modals['alertModal']) {
        modals['alertModal'].show();
    } else {
        try {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
            modals['alertModal'] = modal;
        } catch (error) {
            console.error('Error mostrando modal de alerta:', error);
            alert(`${title}: ${message}`);
        }
    }
}

// Función de depuración
window.testModals = function() {
    console.log('=== TEST DE CONFIGURACIÓN ===');
    console.log('projectOption:', document.getElementById('projectOption')?.value);
    console.log('eventOption:', document.getElementById('eventOption')?.value);
    console.log('assigned_to:', document.querySelector('[name="assigned_to"]')?.value);
    
    showAlertModal('Test', 'La configuración está funcionando correctamente.', 'success');
};

// ============================================================================
// FUNCIONES DE CLASIFICACIÓN GTD - VERSIÓN DEFINITIVA CORREGIDA
// ============================================================================

// Configurar formulario de clasificación
function setupClassificationForm() {
    const confidenceRange = document.getElementById('confidenceRange');
    const confidenceValue = document.getElementById('confidenceValue');
    
    if (confidenceRange && confidenceValue) {
        confidenceValue.textContent = confidenceRange.value;
        
        confidenceRange.addEventListener('input', function() {
            confidenceValue.textContent = this.value;
        });
    }
    
    // Configurar el formulario de clasificación - ELIMINAR EVENTOS DUPLICADOS
    const classificationForm = document.getElementById('classificationForm');
    if (classificationForm) {
        // Remover cualquier evento submit previo para evitar duplicados
        classificationForm.removeEventListener('submit', handleClassificationSubmit);
        
        // Agregar el nuevo manejador con prevención de envío tradicional
        classificationForm.addEventListener('submit', function(e) {
            e.preventDefault(); // IMPORTANTE: Prevenir envío tradicional
            e.stopPropagation(); // Detener propagación del evento
            
            if (!isSubmitting) {
                handleClassificationSubmit(e);
            }
            return false; // Asegurar que no se propague
        });
    }
    
    // Configurar botón de confirmación de reclasificación
    const confirmReclassifyBtn = document.getElementById('confirmReclassifyBtn');
    if (confirmReclassifyBtn) {
        confirmReclassifyBtn.removeEventListener('click', confirmReclassification);
        confirmReclassifyBtn.addEventListener('click', confirmReclassification);
    }
    
    // Cargar historial cuando se abra el modal
    const reclassifyHistoryModal = document.getElementById('reclassifyHistoryModal');
    if (reclassifyHistoryModal) {
        reclassifyHistoryModal.removeEventListener('show.bs.modal', loadClassificationHistory);
        reclassifyHistoryModal.addEventListener('show.bs.modal', loadClassificationHistory);
    }
}

// Manejar envío del formulario de clasificación - VERSIÓN CORREGIDA
async function handleClassificationSubmit(e) {
    // Asegurar que el evento se previene múltiples veces
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Evitar doble envío
    if (isSubmitting) {
        console.log('Ya se está procesando una solicitud');
        return;
    }
    
    const form = document.getElementById('classificationForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const submitBtn = document.getElementById('saveClassificationBtn');
    if (!submitBtn) return;
    
    const originalText = submitBtn.innerHTML;
    
    // Marcar como enviando
    isSubmitting = true;
    
    // Mostrar estado de carga
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
    
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Mostrar vista previa de cambios para reclasificación
            if (data.changed) {
                showReclassifyPreview(data.old_values, data.new_values);
                // Restaurar el botón (se manejará en la reclasificación)
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            } else {
                showAlertModal('Clasificación guardada', 'Los cambios han sido guardados exitosamente.', 'success');
                // Actualizar la sección de consenso inmediatamente
                await updateConsensusDisplay();
                
                // Actualizar los valores mostrados en el formulario
                updateFormValues(data.new_values);
                
                // Restaurar el botón
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        } else {
            showAlertModal('Error', data.error || 'Error al guardar la clasificación', 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    } catch (error) {
        console.error('Error:', error);
        showAlertModal('Error', 'Error de conexión al guardar la clasificación', 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    } finally {
        // Restaurar estado después de un tiempo
        setTimeout(() => {
            isSubmitting = false;
        }, 1000);
    }
    
    return false; // Asegurar que no se propague
}

// Actualizar los valores del formulario después de guardar
function updateFormValues(newValues) {
    // Actualizar categoría GTD
    const gtdCategorySelect = document.getElementById('gtdCategory');
    if (gtdCategorySelect && newValues.gtd_category) {
        gtdCategorySelect.value = newValues.gtd_category;
    }
    
    // Actualizar tipo de acción
    const actionTypeSelect = document.getElementById('actionType');
    if (actionTypeSelect) {
        if (newValues.action_type) {
            actionTypeSelect.value = newValues.action_type;
        } else {
            actionTypeSelect.value = '';
        }
    }
    
    // Actualizar prioridad
    const prioritySelect = document.getElementById('priority');
    if (prioritySelect && newValues.priority) {
        prioritySelect.value = newValues.priority;
    }
    
    // Actualizar confianza si está presente
    const confidenceRange = document.getElementById('confidenceRange');
    const confidenceValue = document.getElementById('confidenceValue');
    if (confidenceRange && newValues.confidence) {
        confidenceRange.value = newValues.confidence;
        if (confidenceValue) confidenceValue.textContent = newValues.confidence;
    }
}

// Mostrar vista previa de reclasificación - CORREGIDA
function showReclassifyPreview(oldValues, newValues) {
    const oldPreview = document.getElementById('oldClassificationPreview');
    const newPreview = document.getElementById('newClassificationPreview');
    
    if (oldPreview && newPreview) {
        oldPreview.innerHTML = `
            <span class="badge bg-secondary me-1">${oldValues.gtd_category || 'No definida'}</span>
            <span class="badge bg-info me-1">${oldValues.action_type || 'No definida'}</span>
            <span class="badge bg-${oldValues.priority === 'alta' ? 'danger' : oldValues.priority === 'media' ? 'warning' : 'success'}">${oldValues.priority || 'media'}</span>
        `;
        
        newPreview.innerHTML = `
            <span class="badge bg-secondary me-1">${newValues.gtd_category}</span>
            <span class="badge bg-info me-1">${newValues.action_type || 'No definida'}</span>
            <span class="badge bg-${newValues.priority === 'alta' ? 'danger' : newValues.priority === 'media' ? 'warning' : 'success'}">${newValues.priority}</span>
        `;
        
        // Guardar los datos para la confirmación
        window.pendingClassification = {
            old: oldValues,
            new: newValues
        };
        
        // Mostrar modal de confirmación
        const modal = new bootstrap.Modal(document.getElementById('reclassifyConfirmModal'));
        modal.show();
    }
}

// Confirmar reclasificación - CORREGIDA
function confirmReclassification() {
    if (!window.pendingClassification) return;
    
    // Cerrar modal de confirmación
    const confirmModal = bootstrap.Modal.getInstance(document.getElementById('reclassifyConfirmModal'));
    if (confirmModal) {
        confirmModal.hide();
    }
    
    const submitBtn = document.getElementById('saveClassificationBtn');
    if (!submitBtn) return;
    
    const originalText = submitBtn.innerHTML;
    
    // Mostrar estado de carga
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Reclasificando...';
    
    // Enviar el formulario realmente
    const form = document.getElementById('classificationForm');
    const formData = new FormData(form);
    
    // Agregar indicador de reclasificación
    formData.append('reclassification', 'true');
    
    // Enviar el formulario vía fetch
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlertModal('Reclasificación exitosa', 'El item ha sido reclasificado correctamente.', 'success');
            // Actualizar consenso
            updateConsensusDisplay();
            // Actualizar valores del formulario
            updateFormValues(data.new_values);
        } else {
            showAlertModal('Error', data.error || 'Error al reclasificar', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlertModal('Error', 'Error al procesar la reclasificación', 'danger');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
        window.pendingClassification = null;
        isSubmitting = false;
    });
}

// Cargar historial de clasificaciones - MEJORADA
async function loadClassificationHistory() {
    const historyList = document.getElementById('classificationHistoryList');
    if (!historyList) return;
    
    const itemId = document.querySelector('[data-inbox-item-id]')?.dataset.inboxItemId;
    if (!itemId) {
        historyList.innerHTML = '<div class="alert alert-danger text-center">ID de item no encontrado</div>';
        return;
    }
    
    historyList.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-warning" role="status"></div><p class="mt-2">Cargando historial...</p></div>';
    
    try {
        const response = await fetch(`/events/inbox/api/classification-history/${itemId}/`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        if (data.success && data.history && data.history.length > 0) {
            let html = '<div class="timeline">';
            
            data.history.forEach((item, index) => {
                const date = new Date(item.created_at);
                const formattedDate = date.toLocaleDateString('es-ES', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                html += `
                    <div class="timeline-item ${index === 0 ? 'latest' : ''}">
                        <div class="timeline-badge ${item.action === 'reclassified' ? 'bg-warning' : 'bg-info'}">
                            <i class="bi ${item.action === 'reclassified' ? 'bi-arrow-repeat' : 'bi-tag'}"></i>
                        </div>
                        <div class="timeline-content card mb-3">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <h6 class="card-subtitle mb-2 text-muted">
                                        <i class="bi bi-person-circle me-1"></i>${item.user || 'Sistema'}
                                    </h6>
                                    <small class="text-muted">${formattedDate}</small>
                                </div>
                                <div class="row mt-2">
                                    <div class="col-md-6">
                                        <strong>Anterior:</strong><br>
                                        <span class="badge bg-secondary me-1">${item.old_values?.gtd_category || 'N/A'}</span>
                                        <span class="badge bg-info me-1">${item.old_values?.action_type || 'N/A'}</span>
                                        <span class="badge bg-${item.old_values?.priority === 'alta' ? 'danger' : item.old_values?.priority === 'media' ? 'warning' : 'success'}">${item.old_values?.priority || 'N/A'}</span>
                                    </div>
                                    <div class="col-md-6">
                                        <strong>Nueva:</strong><br>
                                        <span class="badge bg-secondary me-1">${item.new_values?.gtd_category || 'N/A'}</span>
                                        <span class="badge bg-info me-1">${item.new_values?.action_type || 'N/A'}</span>
                                        <span class="badge bg-${item.new_values?.priority === 'alta' ? 'danger' : item.new_values?.priority === 'media' ? 'warning' : 'success'}">${item.new_values?.priority || 'N/A'}</span>
                                    </div>
                                </div>
                                ${item.notes ? `<p class="mt-2 mb-0 small"><i class="bi bi-chat-text me-1"></i>${item.notes}</p>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            historyList.innerHTML = html;
        } else {
            historyList.innerHTML = '<div class="alert alert-info text-center">No hay historial de clasificaciones para este item.</div>';
        }
    } catch (error) {
        console.error('Error cargando historial:', error);
        historyList.innerHTML = '<div class="alert alert-danger text-center">Error al cargar el historial de clasificaciones.</div>';
    }
}

// Función para reclasificar rápidamente desde el panel
window.quickReclassify = function(category, action, priority) {
    const form = document.getElementById('classificationForm');
    if (!form) return;
    
    // Actualizar valores del formulario
    if (category) document.querySelector('[name="gtd_category"]').value = category;
    if (action) document.querySelector('[name="action_type"]').value = action;
    if (priority) document.querySelector('[name="priority"]').value = priority;
    
    // Enviar formulario si no está enviando
    if (!isSubmitting) {
        // Disparar el evento submit
        const event = new Event('submit', { cancelable: true });
        form.dispatchEvent(event);
    }
};

// ============================================================================
// FUNCIÓN PARA ACTUALIZAR EL CONSENSO - MEJORADA
// ============================================================================

// Actualizar la sección de consenso después de una clasificación
async function updateConsensusDisplay() {
    const itemId = document.querySelector('[data-inbox-item-id]')?.dataset.inboxItemId;
    if (!itemId) return;
    
    try {
        const response = await fetch(`/events/inbox/api/consensus/${itemId}/`);
        if (!response.ok) return;
        
        const data = await response.json();
        
        if (data.success) {
            // Actualizar categoría de consenso
            const consensusCategoryEl = document.querySelector('.consensus-item:first-child .badge');
            if (consensusCategoryEl) {
                consensusCategoryEl.textContent = data.consensus_category ? 
                    data.consensus_category.charAt(0).toUpperCase() + data.consensus_category.slice(1) : 
                    'Sin consenso';
            }
            
            // Actualizar tipo de acción de consenso
            const consensusActionEl = document.querySelector('.consensus-item:nth-child(2) .badge');
            if (consensusActionEl) {
                consensusActionEl.textContent = data.consensus_action ? 
                    data.consensus_action.charAt(0).toUpperCase() + data.consensus_action.slice(1) : 
                    'Sin consenso';
            }
            
            // Actualizar número de votos
            const votesEl = document.querySelector('.consensus-item:last-child .badge');
            if (votesEl) {
                votesEl.textContent = `${data.votes} usuario(s)`;
            }
            
            console.log('Consenso actualizado:', data);
        }
    } catch (error) {
        console.error('Error actualizando consenso:', error);
    }
}// static/events/js/task-panel.js

document.addEventListener('DOMContentLoaded', function() {
    // ============================================================
    // ESTADO GLOBAL DE LA APLICACIÓN
    // ============================================================
    const AppState = {
        tasks: new Map(), // Almacena datos de tareas por ID
        filters: {
            status: '',
            project: '',
            search: ''
        },
        selectedTasks: new Set(),
        views: {
            current: localStorage.getItem('taskViewPreference') || 'table',
            compact: localStorage.getItem('compactView') === 'true'
        },
        stats: {
            total: 0,
            visible: 0,
            completed: 0,
            inProgress: 0,
            blocked: 0,
            pending: 0
        },
        projects: new Map(), // Almacena datos de proyectos
        statusColors: {
            'In Progress': '#007bff',
            'Completed': '#28a745',
            'Blocked': '#dc3545',
            'To Do': '#6c757d'
        }
    };

    // ============================================================
    // INICIALIZACIÓN DE DATOS
    // ============================================================
    function initializeTaskData() {
        // Inicializar desde vista tabla (fuente principal de datos)
        document.querySelectorAll('.task-row').forEach(row => {
            const taskId = row.dataset.taskId;
            const taskData = {
                id: taskId,
                status: row.dataset.status,
                priority: row.dataset.priority,
                project: row.dataset.project,
                projectStatus: row.dataset.projectStatus,
                dueDate: row.dataset.dueDate,
                title: row.querySelector('.task-title')?.textContent.trim() || '',
                assignedTo: row.querySelector('.task-assigned')?.textContent.trim() || '',
                element: row,
                // Guardar referencias a elementos en otras vistas
                kanbanElements: [],
                cardElements: []
            };
            
            AppState.tasks.set(taskId, taskData);
        });
        
        // Sincronizar con vista kanban
        document.querySelectorAll('.kanban-card').forEach(card => {
            const taskId = card.dataset.taskId;
            if (AppState.tasks.has(taskId)) {
                AppState.tasks.get(taskId).kanbanElements.push(card);
            }
        });
        
        // Sincronizar con vista cards
        document.querySelectorAll('#cardsContainer .card').forEach(card => {
            const switch_ = card.querySelector('.task-status-switch');
            if (switch_) {
                const taskId = switch_.dataset.taskId;
                if (AppState.tasks.has(taskId)) {
                    AppState.tasks.get(taskId).cardElements.push(card);
                }
            }
        });
        
        updateStats();
    }

    // ============================================================
    // FUNCIONES DE UTILIDAD
    // ============================================================
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'danger'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        const container = document.querySelector('.toast-container') || createToastContainer();
        container.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    function createToastContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }

    function changeTaskStatusAjax(taskId, newStatusName, action = null) {
        const statusUrl = window.taskPanelConfig.changeStatusUrl;
        const formData = new FormData();
        formData.append('task_id', taskId);
        
        if (action) {
            formData.append('action', action);
        } else {
            formData.append('new_status_name', newStatusName);
        }
        
        return fetch(statusUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                return data;
            } else {
                throw new Error(data.error || 'Error updating task status');
            }
        });
    }

    // ============================================================
    // ACTUALIZACIÓN DE UI (TODAS LAS VISTAS)
    // ============================================================
    function updateTaskStatus(taskId, newStatus) {
        const task = AppState.tasks.get(taskId);
        if (!task) return;
        
        const oldStatus = task.status;
        task.status = newStatus;
        
        // Actualizar vista tabla
        updateTableRow(taskId, newStatus);
        
        // Actualizar vista kanban
        updateKanbanCards(taskId, newStatus, oldStatus);
        
        // Actualizar vista cards
        updateCardsView(taskId, newStatus);
        
        // Actualizar estadísticas
        updateStats();
        
        // Re-aplicar filtros si es necesario
        if (AppState.filters.status || AppState.filters.project || AppState.filters.search) {
            filterTasks();
        }
        
        // Efecto visual de actualización
        highlightUpdatedTask(taskId);
    }

    function updateTableRow(taskId, newStatus) {
        const taskRow = document.querySelector(`tr[data-task-id="${taskId}"]`);
        if (!taskRow) return;
        
        // Actualizar atributo data-status
        taskRow.setAttribute('data-status', newStatus);
        
        // Actualizar badge de estado
        const statusBadge = taskRow.querySelector('.status-badge');
        if (statusBadge) {
            const iconElement = statusBadge.querySelector('.status-icon');
            const iconHTML = iconElement ? iconElement.outerHTML + ' ' : '';
            const statusText = statusBadge.querySelector('.status-text');
            if (statusText) statusText.textContent = newStatus;
            
            statusBadge.style.backgroundColor = AppState.statusColors[newStatus] || '#6c757d';
        }
        
        // Actualizar indicador de estado
        const statusIndicator = taskRow.querySelector('.status-indicator');
        if (statusIndicator) {
            const indicators = {
                'In Progress': '<i class="bi bi-arrow-clockwise"></i> Active',
                'Completed': '<i class="bi bi-check-circle"></i> Done',
                'Blocked': '<i class="bi bi-slash-circle"></i> Blocked',
                'To Do': '<i class="bi bi-circle"></i> Pending'
            };
            statusIndicator.innerHTML = indicators[newStatus] || '';
        }
        
        // Actualizar barra de progreso
        const progressBar = taskRow.querySelector('.task-progress-bar');
        if (progressBar) {
            if (newStatus === 'Completed') {
                progressBar.style.width = '100%';
                progressBar.className = 'progress-bar bg-success task-progress-bar';
            } else if (newStatus === 'In Progress') {
                progressBar.style.width = '50%';
                progressBar.className = 'progress-bar bg-primary task-progress-bar';
            } else {
                progressBar.style.width = '0%';
                progressBar.className = 'progress-bar bg-secondary task-progress-bar';
            }
        }
        
        // Actualizar duración
        const durationCell = taskRow.querySelector('.duration-cell');
        if (durationCell) {
            if (newStatus === 'In Progress') {
                durationCell.innerHTML = `
                    <div class="d-flex flex-column">
                        <small class="text-info d-block duration-time">
                            <i class="bi bi-clock"></i> Just now
                        </small>
                        <small class="text-muted duration-status" style="font-size: 0.7rem;">Active</small>
                    </div>
                `;
            } else if (newStatus === 'Completed') {
                durationCell.innerHTML = `
                    <div class="d-flex flex-column">
                        <small class="text-success d-block duration-time">
                            <i class="bi bi-check-circle"></i> Completed
                        </small>
                        <small class="text-muted duration-status" style="font-size: 0.7rem;">Done</small>
                    </div>
                `;
            } else {
                durationCell.innerHTML = '<small class="text-muted">-</small>';
            }
        }
        
        // Actualizar controles extendidos
        const extendedControls = taskRow.querySelector('.task-extended-controls');
        const switchElement = taskRow.querySelector('.task-status-switch');
        
        if (extendedControls) {
            if (newStatus === 'In Progress') {
                extendedControls.classList.remove('d-none');
            } else {
                extendedControls.classList.add('d-none');
                const completeCheckbox = extendedControls.querySelector('.task-complete-checkbox');
                if (completeCheckbox) completeCheckbox.checked = false;
            }
        }
        
        if (switchElement) {
            switchElement.checked = newStatus === 'In Progress';
            switchElement.disabled = newStatus === 'Completed';
        }
    }

    function updateKanbanCards(taskId, newStatus, oldStatus) {
        const task = AppState.tasks.get(taskId);
        if (!task) return;
        
        task.kanbanElements.forEach(card => {
            if (!card) return;
            
            // Mover tarjeta a la columna correspondiente
            const targetColumn = document.querySelector(`.kanban-column-body[data-status="${getStatusId(newStatus)}"]`);
            const sourceColumn = card.closest('.kanban-column-body');
            
            if (targetColumn && sourceColumn !== targetColumn) {
                // Clonar para mantener eventos
                const newCard = card.cloneNode(true);
                newCard.dataset.taskId = taskId;
                
                // Actualizar contenido de la tarjeta
                const statusBadge = newCard.querySelector('.badge');
                if (statusBadge) {
                    statusBadge.style.backgroundColor = AppState.statusColors[newStatus] || '#6c757d';
                    statusBadge.innerHTML = getStatusIcon(newStatus) + ' ' + newStatus;
                }
                
                const switch_ = newCard.querySelector('.task-status-switch');
                if (switch_) {
                    switch_.checked = newStatus === 'In Progress';
                    switch_.disabled = newStatus === 'Completed';
                }
                
                // Reemplazar en el DOM
                targetColumn.appendChild(newCard);
                card.remove();
                
                // Actualizar referencia
                const index = task.kanbanElements.indexOf(card);
                task.kanbanElements[index] = newCard;
                
                // Re-attach event listeners
                attachKanbanEvents(newCard);
            } else {
                // Solo actualizar contenido si está en la misma columna
                const statusBadge = card.querySelector('.badge');
                if (statusBadge) {
                    statusBadge.style.backgroundColor = AppState.statusColors[newStatus] || '#6c757d';
                    statusBadge.innerHTML = getStatusIcon(newStatus) + ' ' + newStatus;
                }
                
                const switch_ = card.querySelector('.task-status-switch');
                if (switch_) {
                    switch_.checked = newStatus === 'In Progress';
                    switch_.disabled = newStatus === 'Completed';
                }
            }
        });
    }

    function updateCardsView(taskId, newStatus) {
        const task = AppState.tasks.get(taskId);
        if (!task) return;
        
        task.cardElements.forEach(card => {
            if (!card) return;
            
            // Actualizar badge de estado
            const statusBadge = card.querySelector('.badge');
            if (statusBadge) {
                statusBadge.style.backgroundColor = AppState.statusColors[newStatus] || '#6c757d';
                statusBadge.textContent = newStatus;
            }
            
            // Actualizar barra de progreso
            const progressBar = card.querySelector('.progress-bar');
            if (progressBar) {
                if (newStatus === 'Completed') {
                    progressBar.style.width = '100%';
                    progressBar.className = 'progress-bar bg-success';
                } else if (newStatus === 'In Progress') {
                    progressBar.style.width = '50%';
                    progressBar.className = 'progress-bar bg-primary';
                } else {
                    progressBar.style.width = '0%';
                    progressBar.className = 'progress-bar bg-secondary';
                }
            }
            
            // Actualizar switch
            const switch_ = card.querySelector('.task-status-switch');
            if (switch_) {
                switch_.checked = newStatus === 'In Progress';
                switch_.disabled = newStatus === 'Completed';
            }
        });
    }

    function getStatusIcon(status) {
        const icons = {
            'In Progress': '<i class="bi bi-arrow-repeat"></i>',
            'Completed': '<i class="bi bi-check-circle"></i>',
            'Blocked': '<i class="bi bi-exclamation-triangle"></i>',
            'To Do': '<i class="bi bi-circle"></i>'
        };
        return icons[status] || '';
    }

    function getStatusId(statusName) {
        const statusMap = {
            'To Do': 1,
            'In Progress': 2,
            'Completed': 3,
            'Blocked': 4
        };
        return statusMap[statusName] || 1;
    }

    function attachKanbanEvents(card) {
        // Drag and drop events
        card.setAttribute('draggable', 'true');
        
        card.addEventListener('dragstart', function(e) {
            this.classList.add('dragging');
            e.dataTransfer.setData('text/plain', this.dataset.taskId);
        });

        card.addEventListener('dragend', function(e) {
            this.classList.remove('dragging');
        });
        
        // Switch event
        const switch_ = card.querySelector('.task-status-switch');
        if (switch_) {
            switch_.removeEventListener('change', handleSwitchChange);
            switch_.addEventListener('change', handleSwitchChange);
        }
    }

    function handleSwitchChange(e) {
        e.stopPropagation();
        const switch_ = e.target;
        const taskId = switch_.dataset.taskId;
        const isChecked = switch_.checked;
        
        if (switch_.disabled) return;
        switch_.disabled = true;
        
        const action = isChecked ? 'activate' : 'deactivate';
        
        changeTaskStatusAjax(taskId, null, action)
            .then(data => {
                showToast(data.message || 'Estado actualizado', 'success');
                updateTaskStatus(taskId, isChecked ? 'In Progress' : 'To Do');
            })
            .catch(error => {
                console.error('Error:', error);
                switch_.checked = !isChecked;
                showToast(error.message, 'error');
            })
            .finally(() => {
                switch_.disabled = false;
            });
    }

    function highlightUpdatedTask(taskId) {
        // Resaltar la tarea actualizada en todas las vistas
        const selectors = [
            `tr[data-task-id="${taskId}"]`,
            `.kanban-card[data-task-id="${taskId}"]`,
            `#cardsContainer .card:has(.task-status-switch[data-task-id="${taskId}"])`
        ];
        
        selectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                el.classList.add('stat-updated');
                setTimeout(() => el.classList.remove('stat-updated'), 500);
            });
        });
    }

    // ============================================================
    // ACTUALIZACIÓN DE ESTADÍSTICAS
    // ============================================================
    function updateStats() {
        const totalTasks = AppState.tasks.size;
        let completed = 0, inProgress = 0, blocked = 0, pending = 0;
        
        AppState.tasks.forEach(task => {
            if (task.status === 'Completed') completed++;
            else if (task.status === 'In Progress') inProgress++;
            else if (task.status === 'Blocked') blocked++;
            else if (task.status === 'To Do') pending++;
        });
        
        AppState.stats = {
            total: totalTasks,
            visible: document.querySelectorAll('.task-row:not([style*="display: none"])').length,
            completed,
            inProgress,
            blocked,
            pending
        };
        
        updateStatsUI();
        updateProjectProgress();
    }

    function updateStatsUI() {
        const stats = AppState.stats;
        const total = stats.total || 1;
        
        // Actualizar contadores
        const elements = {
            total: document.getElementById('totalTasksCount'),
            inProgress: document.getElementById('inProgressTasksCount'),
            completed: document.getElementById('completedTasksCount'),
            pending: document.getElementById('pendingTasksCount'),
            visible: document.getElementById('visibleTasks')
        };
        
        if (elements.total) elements.total.textContent = stats.total;
        if (elements.inProgress) elements.inProgress.textContent = stats.inProgress;
        if (elements.completed) elements.completed.textContent = stats.completed;
        if (elements.pending) elements.pending.textContent = stats.pending;
        if (elements.visible) elements.visible.textContent = stats.visible;
        
        // Calcular porcentajes
        const percentages = {
            inProgress: Math.round((stats.inProgress / total) * 100) || 0,
            completed: Math.round((stats.completed / total) * 100) || 0,
            pending: Math.round((stats.pending / total) * 100) || 0
        };
        
        // Actualizar badges
        const badges = {
            inProgress: document.getElementById('inProgressPercentBadge'),
            completed: document.getElementById('completedPercentBadge'),
            pending: document.getElementById('pendingPercentBadge')
        };
        
        if (badges.inProgress) {
            badges.inProgress.textContent = percentages.inProgress + '%';
            updateBadgeColor(badges.inProgress, percentages.inProgress);
        }
        if (badges.completed) {
            badges.completed.textContent = percentages.completed + '%';
            updateBadgeColor(badges.completed, percentages.completed);
        }
        if (badges.pending) {
            badges.pending.textContent = percentages.pending + '%';
            updateBadgeColor(badges.pending, percentages.pending);
        }
        
        // Actualizar barras de progreso
        const progressBars = {
            inProgress: document.getElementById('inProgressProgressBar'),
            completed: document.getElementById('completedProgressBar'),
            pending: document.getElementById('pendingProgressBar')
        };
        
        if (progressBars.inProgress) progressBars.inProgress.style.width = percentages.inProgress + '%';
        if (progressBars.completed) progressBars.completed.style.width = percentages.completed + '%';
        if (progressBars.pending) progressBars.pending.style.width = percentages.pending + '%';
    }

    function updateBadgeColor(badge, percentage) {
        badge.classList.remove('bg-success', 'bg-warning', 'bg-danger', 'bg-opacity-10', 'text-success', 'text-warning', 'text-danger');
        
        if (percentage >= 70) {
            badge.classList.add('bg-success', 'bg-opacity-10', 'text-success');
        } else if (percentage >= 30) {
            badge.classList.add('bg-warning', 'bg-opacity-10', 'text-warning');
        } else {
            badge.classList.add('bg-danger', 'bg-opacity-10', 'text-danger');
        }
    }

    function updateProjectProgress() {
        const projectStats = new Map();
        
        AppState.tasks.forEach(task => {
            if (task.project) {
                if (!projectStats.has(task.project)) {
                    projectStats.set(task.project, {
                        total: 0,
                        completed: 0
                    });
                }
                const stats = projectStats.get(task.project);
                stats.total++;
                if (task.status === 'Completed') stats.completed++;
            }
        });
        
        projectStats.forEach((stats, projectId) => {
            const percentage = stats.total > 0 ? (stats.completed / stats.total * 100) : 0;
            document.querySelectorAll(`[data-project-id="${projectId}"] .project-progress`).forEach(el => {
                el.style.width = `${percentage}%`;
            });
        });
    }

    // ============================================================
    // FILTROS Y BÚSQUEDA
    // ============================================================
    function filterTasks() {
        const status = AppState.filters.status;
        const projectId = AppState.filters.project;
        const searchQuery = AppState.filters.search.toLowerCase();
        
        let visibleCount = 0;
        
        AppState.tasks.forEach(task => {
            const row = task.element;
            if (!row) return;
            
            const statusMatch = !status || task.status === status;
            const projectMatch = !projectId || task.project === projectId;
            const searchMatch = !searchQuery || 
                task.title.toLowerCase().includes(searchQuery) ||
                (task.assignedTo && task.assignedTo.toLowerCase().includes(searchQuery));
            
            const isVisible = statusMatch && projectMatch && searchMatch;
            
            // Actualizar visibilidad en tabla
            row.style.display = isVisible ? '' : 'none';
            
            // Actualizar visibilidad en kanban
            task.kanbanElements.forEach(card => {
                if (card) card.style.display = isVisible ? '' : 'none';
            });
            
            // Actualizar visibilidad en cards
            task.cardElements.forEach(card => {
                if (card) {
                    const cardContainer = card.closest('.col-xl-4, .col-lg-6, .col-md-6');
                    if (cardContainer) {
                        cardContainer.style.display = isVisible ? '' : 'none';
                    }
                }
            });
            
            if (isVisible) visibleCount++;
            
            // Deseleccionar si está oculto
            if (!isVisible) {
                const checkbox = row.querySelector('.task-checkbox');
                if (checkbox && checkbox.checked) {
                    checkbox.checked = false;
                    AppState.selectedTasks.delete(task.id);
                }
            }
        });
        
        AppState.stats.visible = visibleCount;
        updateStatsUI();
        updateSelectedCount();
    }

    // ============================================================
    // SELECCIÓN MASIVA
    // ============================================================
    const selectAllCheckbox = document.getElementById('selectAllTasks');
    const deleteSelectedBtn = document.getElementById('deleteSelected');
    const exportSelectedBtn = document.getElementById('exportSelected');

    function updateSelectedCount() {
        if (!deleteSelectedBtn || !exportSelectedBtn || !selectAllCheckbox) return;
        
        AppState.selectedTasks.clear();
        document.querySelectorAll('.task-checkbox:checked:not([style*="display: none"])').forEach(cb => {
            AppState.selectedTasks.add(cb.value);
        });
        
        const count = AppState.selectedTasks.size;
        const visibleCheckboxes = document.querySelectorAll('.task-checkbox:not([style*="display: none"])');
        const totalVisible = visibleCheckboxes.length;
        
        deleteSelectedBtn.disabled = count === 0;
        
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = count > 0 && count === totalVisible;
            selectAllCheckbox.indeterminate = count > 0 && count < totalVisible;
        }
        
        deleteSelectedBtn.innerHTML = `<i class="bi bi-trash"></i> Delete ${count > 0 ? `(${count})` : ''}`;
        exportSelectedBtn.innerHTML = `<i class="bi bi-download"></i> Export ${count > 0 ? `(${count})` : ''}`;
    }

    // ============================================================
    // VISTAS
    // ============================================================
    const viewButtons = document.querySelectorAll('[data-view]');
    const viewContainers = {
        'table': document.getElementById('tableView'),
        'kanban': document.getElementById('kanbanView'),
        'cards': document.getElementById('cardsView')
    };

    function switchView(view) {
        AppState.views.current = view;
        
        viewButtons.forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-view="${view}"]`)?.classList.add('active');
        
        Object.keys(viewContainers).forEach(key => {
            if (viewContainers[key]) {
                viewContainers[key].style.display = key === view ? 'block' : 'none';
            }
        });
        
        localStorage.setItem('taskViewPreference', view);
    }

    // ============================================================
    // COMPACT VIEW
    // ============================================================
    const compactToggle = document.getElementById('compactViewToggle');
    if (compactToggle) {
        const checkIcon = compactToggle.querySelector('.bi-check2');
        
        compactToggle.addEventListener('click', function(e) {
            e.preventDefault();
            const isActive = AppState.views.compact;
            
            if (isActive) {
                checkIcon.style.display = 'none';
                document.body.classList.remove('compact-view');
            } else {
                checkIcon.style.display = 'block';
                document.body.classList.add('compact-view');
            }
            
            AppState.views.compact = !isActive;
            localStorage.setItem('compactView', AppState.views.compact);
        });
        
        if (AppState.views.compact) {
            compactToggle.click();
        }
    }

    // ============================================================
    // MANEJADORES DE EVENTOS
    // ============================================================

    // Búsqueda
    const searchInput = document.getElementById('searchInput');
    let searchTimeout;

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                AppState.filters.search = this.value;
                filterTasks();
            }, 300);
        });
    }

    // Filtros
    const statusFilter = document.getElementById('statusFilter');
    const projectFilter = document.getElementById('projectFilter');
    const clearFiltersBtn = document.getElementById('clearFilters');

    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            AppState.filters.status = this.value;
            filterTasks();
        });
    }

    if (projectFilter) {
        projectFilter.addEventListener('change', function() {
            AppState.filters.project = this.value;
            filterTasks();
        });
    }

    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            if (searchInput) {
                searchInput.value = '';
                AppState.filters.search = '';
            }
            if (statusFilter) {
                statusFilter.value = '';
                AppState.filters.status = '';
            }
            if (projectFilter) {
                projectFilter.value = '';
                AppState.filters.project = '';
            }
            filterTasks();
        });
    }

    // Cambio de vista
    viewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const view = this.getAttribute('data-view');
            switchView(view);
        });
    });

    // Switches de estado (tabla)
    document.querySelectorAll('.task-status-switch').forEach(switchElement => {
        switchElement.addEventListener('change', handleSwitchChange);
    });

    // Checkbox de completado
    document.addEventListener('change', function(e) {
        const target = e.target;
        
        if (target.classList.contains('task-checkbox')) {
            updateSelectedCount();
            return;
        }
        
        if (target.classList.contains('task-complete-checkbox')) {
            e.stopPropagation();
            
            const checkbox = target;
            const taskId = checkbox.dataset.taskId;
            
            if (checkbox.checked && !checkbox.disabled) {
                if (confirm('¿Marcar como completada? Esto actualizará el proyecto asociado.')) {
                    checkbox.disabled = true;
                    
                    changeTaskStatusAjax(taskId, 'Completed')
                        .then(data => {
                            showToast('Tarea completada', 'success');
                            updateTaskStatus(taskId, 'Completed');
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            checkbox.checked = false;
                            showToast(error.message, 'error');
                        })
                        .finally(() => {
                            checkbox.disabled = false;
                        });
                } else {
                    checkbox.checked = false;
                }
            }
        }
    });

    // Opciones de estado
    document.addEventListener('click', function(e) {
        const target = e.target.closest('.task-status-option, .task-block-option');
        if (!target) return;
        
        e.preventDefault();
        e.stopPropagation();
        
        const taskId = target.dataset.taskId;
        
        if (target.classList.contains('task-status-option')) {
            const statusName = target.dataset.statusName;
            if (confirm(`¿Cambiar estado a "${statusName}"?`)) {
                changeTaskStatusAjax(taskId, statusName)
                    .then(data => {
                        showToast(`Estado cambiado a ${statusName}`, 'success');
                        updateTaskStatus(taskId, statusName);
                    })
                    .catch(error => {
                        showToast(error.message, 'error');
                    });
            }
        } else if (target.classList.contains('task-block-option')) {
            if (confirm('¿Marcar como Bloqueada?')) {
                changeTaskStatusAjax(taskId, 'Blocked')
                    .then(data => {
                        showToast('Tarea bloqueada', 'success');
                        updateTaskStatus(taskId, 'Blocked');
                    })
                    .catch(error => {
                        showToast(error.message, 'error');
                    });
            }
        }
    });

    // Seleccionar todos
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function(e) {
            e.stopPropagation();
            
            const isChecked = this.checked;
            document.querySelectorAll('.task-checkbox:not([style*="display: none"])').forEach(checkbox => {
                checkbox.checked = isChecked;
            });
            
            updateSelectedCount();
        });
    }

    // Acciones masivas
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', function() {
            const selectedIds = Array.from(AppState.selectedTasks);
            if (selectedIds.length === 0) return;
            
            if (confirm(`¿Eliminar ${selectedIds.length} tarea(s)?`)) {
                console.log('Bulk delete IDs:', selectedIds);
                showToast(`Eliminando ${selectedIds.length} tareas...`, 'info');
            }
        });
    }

    if (exportSelectedBtn) {
        exportSelectedBtn.addEventListener('click', function() {
            const selectedIds = Array.from(AppState.selectedTasks);
            if (selectedIds.length === 0) return;
            
            console.log('Export selected IDs:', selectedIds);
            showToast(`Exportando ${selectedIds.length} tareas...`, 'info');
        });
    }

    // Drag and drop para kanban
    document.querySelectorAll('.kanban-column-body').forEach(column => {
        column.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });

        column.addEventListener('dragleave', function(e) {
            this.classList.remove('drag-over');
        });

        column.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');

            const taskId = e.dataTransfer.getData('text/plain');
            const draggedCard = document.querySelector(`.kanban-card[data-task-id="${taskId}"]`);
            
            if (draggedCard) {
                const newStatus = getStatusNameFromColumn(this.dataset.status);
                if (newStatus) {
                    this.appendChild(draggedCard);
                    updateTaskStatus(taskId, newStatus);
                }
            }
        });
    });

    function getStatusNameFromColumn(statusId) {
        const statusMap = {
            '1': 'To Do',
            '2': 'In Progress',
            '3': 'Completed',
            '4': 'Blocked'
        };
        return statusMap[statusId];
    }

    // ============================================================
    // ATALOS DE TECLADO
    // ============================================================
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'f' && searchInput) {
            e.preventDefault();
            searchInput.focus();
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '3') {
            e.preventDefault();
            const viewIndex = parseInt(e.key) - 1;
            const views = ['table', 'kanban', 'cards'];
            switchView(views[viewIndex]);
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
            e.preventDefault();
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = !selectAllCheckbox.checked;
                selectAllCheckbox.dispatchEvent(new Event('change'));
            }
        }
    });

    // ============================================================
    // INICIALIZACIÓN
    // ============================================================
    initializeTaskData();
    updateStats();
    switchView(AppState.views.current);
    
    // Sincronización periódica
    setInterval(() => {
        console.log('Checking for updates...');
        // Aquí podrías hacer peticiones ligeras para actualizar datos
    }, 30000);

        // ============================================================
    // MANEJO DE COLUMNAS KANBAN DINÁMICAS (ACTUALIZADO)
    // ============================================================
    
    // Definición de todas las columnas posibles
    const KANBAN_COLUMNS = [
        { id: 1, name: 'To Do', icon: 'bi-list-task', color: 'bg-light', headerColor: 'bg-light' },
        { id: 2, name: 'In Progress', icon: 'bi-arrow-repeat', color: 'bg-warning', headerColor: 'bg-warning' },
        { id: 3, name: 'Completed', icon: 'bi-check-circle', color: 'bg-success', headerColor: 'bg-success' },
        { id: 4, name: 'Blocked', icon: 'bi-exclamation-triangle', color: 'bg-danger', headerColor: 'bg-danger' }
    ];
    
    function ensureKanbanColumn(statusName, statusId) {
        const columnWrapper = document.querySelector(`.kanban-column-wrapper[data-status-name="${statusName}"]`);
        
        if (columnWrapper) {
            return columnWrapper.querySelector('.kanban-column-body');
        }
        
        // Crear nueva columna si no existe
        return createKanbanColumn(statusName, statusId);
    }
    
    function createKanbanColumn(statusName, statusId) {
        const template = document.getElementById('kanban-column-template');
        const kanbanBoard = document.getElementById('kanbanBoard');
        
        if (!template || !kanbanBoard) return null;
        
        // Clonar el template
        const columnWrapper = template.content.cloneNode(true).querySelector('.kanban-column-wrapper');
        
        // Configurar atributos
        columnWrapper.dataset.statusId = statusId;
        columnWrapper.dataset.statusName = statusName;
        
        // Configurar header según el tipo de columna
        const columnConfig = KANBAN_COLUMNS.find(col => col.name === statusName) || KANBAN_COLUMNS[0];
        
        const header = columnWrapper.querySelector('.card-header');
        header.className = `card-header d-flex justify-content-between align-items-center ${columnConfig.headerColor}`;
        if (['In Progress', 'Completed', 'Blocked'].includes(statusName)) {
            header.querySelector('h6').classList.add('text-white');
            header.querySelector('small').classList.add('text-white-50');
        }
        
        // Configurar título e icono
        const titleSpan = columnWrapper.querySelector('.kanban-column-title');
        titleSpan.textContent = statusName;
        
        const icon = columnWrapper.querySelector('h6 i');
        icon.className = `bi ${columnConfig.icon} me-2`;
        
        // Configurar column body
        const columnBody = columnWrapper.querySelector('.kanban-column-body');
        columnBody.dataset.statusId = statusId;
        columnBody.dataset.statusName = statusName;
        
        // Configurar botón de añadir tarea
        const addBtn = columnWrapper.querySelector('.add-task-btn');
        addBtn.href = `/events/tasks/create/?status=${statusId}`;
        
        // Añadir al board
        kanbanBoard.appendChild(columnWrapper);
        
        // Configurar eventos drag & drop
        setupKanbanColumnEvents(columnBody);
        
        return columnBody;
    }
    
    function setupKanbanColumnEvents(columnBody) {
        columnBody.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });
    
        columnBody.addEventListener('dragleave', function(e) {
            this.classList.remove('drag-over');
        });
    
        columnBody.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
    
            const taskId = e.dataTransfer.getData('text/plain');
            const draggedCard = document.querySelector(`.kanban-card[data-task-id="${taskId}"]`);
            
            if (draggedCard) {
                const newStatusName = this.dataset.statusName;
                if (newStatusName) {
                    this.appendChild(draggedCard);
                    updateTaskStatus(taskId, newStatusName);
                    updateKanbanColumnCounts();
                }
            }
        });
    }
    
    // NUEVA FUNCIÓN: Eliminar columnas vacías
    function removeEmptyKanbanColumns() {
        document.querySelectorAll('.kanban-column-wrapper').forEach(wrapper => {
            const columnBody = wrapper.querySelector('.kanban-column-body');
            const cards = columnBody.querySelectorAll('.kanban-card:not([style*="display: none"])');
            
            // Si no hay tarjetas visibles, eliminar la columna
            if (cards.length === 0) {
                wrapper.remove();
            }
        });
    }
    
    // ACTUALIZADA: Actualizar contadores y ocultar columnas vacías
    function updateKanbanColumnCounts() {
        document.querySelectorAll('.kanban-column-wrapper').forEach(wrapper => {
            const columnBody = wrapper.querySelector('.kanban-column-body');
            const cards = columnBody.querySelectorAll('.kanban-card:not([style*="display: none"])');
            const count = cards.length;
            
            const countSpan = wrapper.querySelector('.kanban-column-count');
            const countBadge = wrapper.querySelector('.kanban-count-badge');
            
            if (countSpan) countSpan.textContent = `${count} tasks`;
            if (countBadge) countBadge.textContent = count;
            
            // Mostrar/ocultar empty state
            const emptyState = wrapper.querySelector('.kanban-empty-state');
            if (emptyState) {
                emptyState.style.display = count === 0 ? 'block' : 'none';
            }
        });
        
        // Eliminar columnas completamente vacías
        removeEmptyKanbanColumns();
    }
    
    // Sobrescribir la función updateKanbanCards para usar columnas dinámicas
    function updateKanbanCards(taskId, newStatus, oldStatus) {
        const task = AppState.tasks.get(taskId);
        if (!task) return;
        
        // Asegurar que existe la columna destino
        const targetColumnBody = ensureKanbanColumn(newStatus, getStatusId(newStatus));
        if (!targetColumnBody) return;
        
        task.kanbanElements.forEach(card => {
            if (!card) return;
            
            const sourceColumn = card.closest('.kanban-column-body');
            
            if (targetColumnBody !== sourceColumn) {
                // Clonar para mantener eventos
                const newCard = card.cloneNode(true);
                newCard.dataset.taskId = taskId;
                
                // Actualizar contenido de la tarjeta
                updateKanbanCardContent(newCard, newStatus);
                
                // Añadir a la columna destino
                targetColumnBody.appendChild(newCard);
                
                // Remover de la columna origen
                card.remove();
                
                // Actualizar referencia
                const index = task.kanbanElements.indexOf(card);
                task.kanbanElements[index] = newCard;
                
                // Re-attach event listeners
                attachKanbanEvents(newCard);
            } else {
                // Solo actualizar contenido si está en la misma columna
                updateKanbanCardContent(card, newStatus);
            }
        });
        
        // Actualizar contadores de todas las columnas
        updateKanbanColumnCounts();
    }
    
    function updateKanbanCardContent(card, newStatus) {
        // Actualizar badge de estado
        const statusBadge = card.querySelector('.badge');
        if (statusBadge) {
            statusBadge.style.backgroundColor = AppState.statusColors[newStatus] || '#6c757d';
            statusBadge.innerHTML = getStatusIcon(newStatus) + ' ' + newStatus;
        }
        
        // Actualizar switch
        const switch_ = card.querySelector('.task-status-switch');
        if (switch_) {
            switch_.checked = newStatus === 'In Progress';
            switch_.disabled = newStatus === 'Completed';
        }
    }
    
    // Inicializar eventos de drag & drop en todas las columnas existentes
    function initializeKanbanDragAndDrop() {
        document.querySelectorAll('.kanban-column-body').forEach(columnBody => {
            setupKanbanColumnEvents(columnBody);
        });
    }
    
    // Modificar la función initializeTaskData para incluir la inicialización de kanban
    const originalInitializeTaskData = initializeTaskData;
    initializeTaskData = function() {
        originalInitializeTaskData();
        
        // Asegurar que existen todas las columnas kanban necesarias SOLO si tienen tareas
        // Ya no creamos todas las columnas por defecto
        
        // Inicializar drag & drop
        initializeKanbanDragAndDrop();
        
        // Actualizar contadores
        updateKanbanColumnCounts();
    };
    
    // Reemplazar la función original
    window.initializeTaskData = initializeTaskData;
    
    // ACTUALIZAR también la función filterTasks para manejar columnas vacías
    const originalFilterTasks = filterTasks;
    filterTasks = function() {
        originalFilterTasks();
        
        // Después de filtrar, actualizar columnas kanban
        if (AppState.views.current === 'kanban') {
            updateKanbanColumnCounts();
        }
    };
    
    // Reemplazar la función original
    window.filterTasks = filterTasks;
  
  
  
});/**
 * TASK PANEL SPECIFIC SCRIPTS
 * Task-specific JavaScript functionality
 */

(function() {
    'use strict';

    // Task Panel Configuration
    const taskPanelConfig = {
        searchInputId: 'taskSearchInput',
        selectedCountId: 'taskSelectedCount',
        selectAllId: 'taskSelectAll',
        checkboxName: 'selected_tasks',
        tableSelector: '.datatable tbody tr',
        tabSelector: '#taskTabs .nav-link'
    };

    // Initialize Task Panel
    function initTaskPanel() {
        // Initialize PanelManager with task-specific config
        window.PanelManager.init(taskPanelConfig);

        // Override bulk action URL for tasks
        window.PanelManager.getBulkActionUrl = function(action) {
            return '/events/tasks/bulk-action/';
        };

        // Bind task-specific events
        bindTaskEvents();
    }

    // Bind task-specific events
    function bindTaskEvents() {
        // Task-specific event bindings can be added here
        console.log('Task panel initialized');
    }

    // Task-specific functions
    window.clearTaskSearch = function() {
        window.PanelManager.clearSearch();
    };

    window.exportTasks = function() {
        window.PanelManager.exportItems('/events/tasks/export/');
    };

    window.toggleTaskSelectAll = function() {
        const selectAllCheckbox = document.getElementById('taskSelectAll');
        window.PanelManager.toggleSelectAll(selectAllCheckbox.checked);
    };

    window.bulkTaskAction = function(action) {
        const confirmMessages = {
            'delete': '¿Está seguro de que desea eliminar {count} tarea(s)? Esta acción no se puede deshacer.',
            'activate': '¿Está seguro de que desea activar {count} tarea(s)?',
            'complete': '¿Está seguro de que desea marcar como completada(s) {count} tarea(s)?'
        };

        window.PanelManager.bulkAction(action, confirmMessages[action]);
    };

    window.toggleTaskView = function(viewType) {
        window.PanelManager.toggleView(viewType);
    };

    window.refreshTaskData = function() {
        window.PanelManager.refreshData();
    };

    window.filterTasksByStatus = function(statusId) {
        window.PanelManager.filterByStatus(statusId);
    };

    // Auto-initialize when DOM is ready and we're on task panel
    document.addEventListener('DOMContentLoaded', function() {
        // Check if we're on a task panel page
        if (document.querySelector('.task-panel') || window.location.pathname.includes('/tasks/')) {
            initTaskPanel();
        }
    });

})();/**
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

})();/**
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

})();/**
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
});/**
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

})();/**
 * Content Manager JavaScript
 * Handles the creation and management of content blocks
 */

// Variables globales
let selectedContentType = '';

document.addEventListener('DOMContentLoaded', function() {
    initializeContentManager();
});

function initializeContentManager() {
    // Inicializar selectores de tipo de contenido
    initializeContentTypeSelector();

    // Inicializar filtros de búsqueda
    initializeFilters();

    // Inicializar formulario de creación
    initializeCreateForm();
}

function initializeContentTypeSelector() {
    document.querySelectorAll('.content-type-card').forEach(card => {
        card.addEventListener('click', function() {
            selectContentType(this.dataset.type);
        });
    });
}

function selectContentType(contentType) {
    // Remover selección anterior
    document.querySelectorAll('.content-type-card').forEach(c => c.classList.remove('selected'));

    // Seleccionar este
    const selectedCard = document.querySelector(`[data-type="${contentType}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    selectedContentType = contentType;
    document.getElementById('selectedContentType').value = selectedContentType;

    // Habilitar botón de crear
    const createButton = document.getElementById('createButton');
    if (createButton) {
        createButton.disabled = false;
    }

    // Mostrar campos específicos
    showContentFields(selectedContentType);
}

function showContentFields(contentType) {
    const contentFields = document.getElementById('contentFields');
    const dynamicFields = document.getElementById('dynamicFields');
    const sectionTitle = document.getElementById('contentSectionTitle');

    if (!contentFields || !dynamicFields || !sectionTitle) return;

    contentFields.style.display = 'block';

    let fieldsHtml = '';

    switch(contentType) {
        case 'html':
        case 'bootstrap':
            sectionTitle.innerHTML = '<i class="bi bi-code-slash text-primary"></i> Código HTML/Bootstrap';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Código HTML/Bootstrap *</label>
                    <textarea class="form-control" name="html_content" rows="10" placeholder="Ingresa tu código HTML o Bootstrap aquí..." required></textarea>
                    <div class="form-text">Puedes incluir clases de Bootstrap y estilos personalizados</div>
                </div>
            `;
            break;

        case 'markdown':
            sectionTitle.innerHTML = '<i class="bi bi-markdown text-success"></i> Contenido Markdown';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Contenido Markdown *</label>
                    <textarea class="form-control" name="markdown_content" rows="10" placeholder="# Título Principal\n\nEste es un **texto en negrita** y este es *itálico*.\n\n- Elemento de lista 1\n- Elemento de lista 2\n\n\`\`\`python\nprint('Hola Mundo')\n\`\`\`" required></textarea>
                    <div class="form-text">Soporta encabezados, listas, código, enlaces, imágenes, etc.</div>
                </div>
            `;
            break;

        case 'json':
            sectionTitle.innerHTML = '<i class="bi bi-braces text-warning"></i> Contenido Estructurado JSON';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Elementos Estructurados (JSON)</label>
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle me-2"></i>
                        Este tipo permite crear contenido complejo con múltiples elementos estructurados para lecciones.
                    </div>
                    <div class="text-end mb-2">
                        <button type="button" class="btn btn-sm btn-outline-primary" onclick="addStructuredElement()">
                            <i class="bi bi-plus-circle me-1"></i>Agregar Elemento
                        </button>
                    </div>
                    <div id="structuredElements" class="border rounded p-3" style="min-height: 200px;">
                        <!-- Los elementos se agregarán aquí dinámicamente -->
                        <p class="text-muted text-center">Haz clic en "Agregar Elemento" para comenzar</p>
                    </div>
                </div>
            `;
            break;

        case 'text':
            sectionTitle.innerHTML = '<i class="bi bi-textarea-t text-info"></i> Texto Simple';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Contenido de Texto *</label>
                    <textarea class="form-control" name="text_content" rows="6" placeholder="Ingresa el contenido de texto aquí..." required></textarea>
                </div>
            `;
            break;

        case 'image':
            sectionTitle.innerHTML = '<i class="bi bi-image text-danger"></i> Imagen';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">URL de la Imagen *</label>
                        <input type="url" class="form-control" name="image_url" placeholder="https://ejemplo.com/imagen.jpg" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto Alternativo</label>
                        <input type="text" class="form-control" name="image_alt" placeholder="Descripción de la imagen">
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Pie de Foto</label>
                    <input type="text" class="form-control" name="image_caption" placeholder="Texto que aparece debajo de la imagen">
                </div>
            `;
            break;

        case 'video':
            sectionTitle.innerHTML = '<i class="bi bi-play-circle text-success"></i> Video';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">URL del Video *</label>
                    <input type="url" class="form-control" name="video_url" placeholder="https://www.youtube.com/watch?v=..." required>
                    <div class="form-text">Soporta YouTube, Vimeo y URLs directas de video</div>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Descripción</label>
                        <input type="text" class="form-control" name="video_description" placeholder="Breve descripción del video">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Duración (minutos)</label>
                        <input type="number" class="form-control" name="video_duration" min="1" placeholder="15">
                    </div>
                </div>
            `;
            break;

        case 'quote':
            sectionTitle.innerHTML = '<i class="bi bi-quote text-secondary"></i> Cita';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Texto de la Cita *</label>
                    <textarea class="form-control" name="quote_text" rows="3" placeholder="La educación es el arma más poderosa..." required></textarea>
                </div>
                <div class="mb-3">
                    <label class="form-label">Autor de la Cita</label>
                    <input type="text" class="form-control" name="quote_author" placeholder="Nelson Mandela">
                </div>
            `;
            break;

        case 'code':
            sectionTitle.innerHTML = '<i class="bi bi-terminal text-dark"></i> Código';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Lenguaje de Programación *</label>
                        <select class="form-select" name="code_language" required>
                            <option value="text">Texto Plano</option>
                            <option value="python">Python</option>
                            <option value="javascript">JavaScript</option>
                            <option value="html">HTML</option>
                            <option value="css">CSS</option>
                            <option value="java">Java</option>
                            <option value="cpp">C++</option>
                            <option value="c">C</option>
                            <option value="php">PHP</option>
                            <option value="ruby">Ruby</option>
                            <option value="sql">SQL</option>
                            <option value="bash">Bash</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Título del Código</label>
                        <input type="text" class="form-control" name="code_title" placeholder="Ejemplo de función">
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Código Fuente *</label>
                    <textarea class="form-control font-monospace" name="code_content" rows="8" placeholder="def hello_world():\n    print('Hello, World!')" required></textarea>
                </div>
            `;
            break;

        case 'list':
            sectionTitle.innerHTML = '<i class="bi bi-list-ul text-primary"></i> Lista';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Tipo de Lista *</label>
                    <select class="form-select" name="list_type" required>
                        <option value="unordered">Lista No Ordenada</option>
                        <option value="ordered">Lista Ordenada</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Elementos de la Lista *</label>
                    <textarea class="form-control" name="list_items" rows="6" placeholder="Elemento 1&#10;Elemento 2&#10;Elemento 3" required></textarea>
                    <div class="form-text">Cada línea representa un elemento de la lista</div>
                </div>
            `;
            break;

        case 'table':
            sectionTitle.innerHTML = '<i class="bi bi-table text-info"></i> Tabla';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Encabezados (separados por coma) *</label>
                    <input type="text" class="form-control" name="table_headers" placeholder="Nombre, Edad, Ciudad" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Filas de Datos *</label>
                    <textarea class="form-control" name="table_rows" rows="6" placeholder="Juan, 25, Madrid&#10;María, 30, Barcelona&#10;Pedro, 35, Valencia" required></textarea>
                    <div class="form-text">Cada línea es una fila, valores separados por coma</div>
                </div>
            `;
            break;

        case 'card':
            sectionTitle.innerHTML = '<i class="bi bi-card-text text-warning"></i> Tarjeta';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Título de la Tarjeta *</label>
                        <input type="text" class="form-control" name="card_title" placeholder="Título principal" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto de la Tarjeta *</label>
                        <textarea class="form-control" name="card_text" rows="2" placeholder="Contenido de la tarjeta" required></textarea>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">URL del Botón</label>
                        <input type="url" class="form-control" name="card_button_url" placeholder="https://ejemplo.com">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto del Botón</label>
                        <input type="text" class="form-control" name="card_button_text" placeholder="Ver más" value="Ver más">
                    </div>
                </div>
            `;
            break;

        case 'alert':
            sectionTitle.innerHTML = '<i class="bi bi-exclamation-triangle text-warning"></i> Alerta';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Tipo de Alerta *</label>
                        <select class="form-select" name="alert_type" required>
                            <option value="primary">Primario</option>
                            <option value="secondary">Secundario</option>
                            <option value="success">Éxito</option>
                            <option value="danger">Peligro</option>
                            <option value="warning">Advertencia</option>
                            <option value="info">Información</option>
                            <option value="light">Claro</option>
                            <option value="dark">Oscuro</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Mensaje de Alerta *</label>
                        <input type="text" class="form-control" name="alert_message" placeholder="Texto del mensaje de alerta" required>
                    </div>
                </div>
            `;
            break;

        case 'button':
            sectionTitle.innerHTML = '<i class="bi bi-hand-index-thumb text-info"></i> Botón';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto del Botón *</label>
                        <input type="text" class="form-control" name="button_text" placeholder="Haz clic aquí" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">URL del Botón *</label>
                        <input type="url" class="form-control" name="button_url" placeholder="https://ejemplo.com" required>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Estilo del Botón</label>
                        <select class="form-select" name="button_style">
                            <option value="primary">Primario</option>
                            <option value="secondary">Secundario</option>
                            <option value="success">Éxito</option>
                            <option value="danger">Peligro</option>
                            <option value="warning">Advertencia</option>
                            <option value="info">Información</option>
                            <option value="light">Claro</option>
                            <option value="dark">Oscuro</option>
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Tamaño del Botón</label>
                        <select class="form-select" name="button_size">
                            <option value="sm">Pequeño</option>
                            <option value="md" selected>Mediano</option>
                            <option value="lg">Grande</option>
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Ícono (opcional)</label>
                        <input type="text" class="form-control" name="button_icon" placeholder="bi-star, bi-heart, etc.">
                        <div class="form-text">Nombre del ícono de Bootstrap Icons</div>
                    </div>
                </div>
            `;
            break;

        case 'form':
            sectionTitle.innerHTML = '<i class="bi bi-ui-checks text-success"></i> Formulario';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">URL de Acción del Formulario *</label>
                    <input type="url" class="form-control" name="form_action" placeholder="/procesar-formulario" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Campos del Formulario (JSON)</label>
                    <textarea class="form-control font-monospace" name="form_fields" rows="8" placeholder='[
  {"type": "text", "name": "nombre", "label": "Nombre", "required": true},
  {"type": "email", "name": "email", "label": "Correo Electrónico", "required": true},
  {"type": "textarea", "name": "mensaje", "label": "Mensaje", "placeholder": "Escribe tu mensaje aquí"}
]'></textarea>
                    <div class="form-text">Define los campos del formulario en formato JSON</div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Texto del Botón de Envío</label>
                    <input type="text" class="form-control" name="form_submit_text" placeholder="Enviar" value="Enviar">
                </div>
            `;
            break;

        case 'divider':
            sectionTitle.innerHTML = '<i class="bi bi-dash text-muted"></i> Separador';
            fieldsHtml = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    El separador es un elemento visual simple que no requiere configuración adicional.
                </div>
            `;
            break;

        case 'icon':
            sectionTitle.innerHTML = '<i class="bi bi-star text-warning"></i> Ícono';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Ícono *</label>
                        <input type="text" class="form-control" name="icon_name" placeholder="star" required>
                        <div class="form-text">Nombre del ícono de Bootstrap Icons (sin "bi-")</div>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Color</label>
                        <select class="form-select" name="icon_color">
                            <option value="primary">Primario</option>
                            <option value="secondary">Secundario</option>
                            <option value="success">Éxito</option>
                            <option value="danger">Peligro</option>
                            <option value="warning">Advertencia</option>
                            <option value="info">Información</option>
                            <option value="dark">Oscuro</option>
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Texto Adicional</label>
                        <input type="text" class="form-control" name="icon_text" placeholder="Texto opcional junto al ícono">
                    </div>
                </div>
            `;
            break;

        case 'progress':
            sectionTitle.innerHTML = '<i class="bi bi-bar-chart text-success"></i> Barra de Progreso';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Valor del Progreso (0-100) *</label>
                        <input type="number" class="form-control" name="progress_value" min="0" max="100" value="50" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Color de la Barra</label>
                        <select class="form-select" name="progress_color">
                            <option value="primary">Primario</option>
                            <option value="secondary">Secundario</option>
                            <option value="success">Éxito</option>
                            <option value="danger">Peligro</option>
                            <option value="warning">Advertencia</option>
                            <option value="info">Información</option>
                            <option value="dark">Oscuro</option>
                        </select>
                    </div>
                </div>
            `;
            break;

        case 'badge':
            sectionTitle.innerHTML = '<i class="bi bi-tag text-info"></i> Insignia';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto de la Insignia *</label>
                        <input type="text" class="form-control" name="badge_text" placeholder="Nuevo" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Color de la Insignia</label>
                        <select class="form-select" name="badge_color">
                            <option value="primary">Primario</option>
                            <option value="secondary">Secundario</option>
                            <option value="success">Éxito</option>
                            <option value="danger">Peligro</option>
                            <option value="warning">Advertencia</option>
                            <option value="info">Información</option>
                            <option value="dark">Oscuro</option>
                        </select>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Ícono (opcional)</label>
                    <input type="text" class="form-control" name="badge_icon" placeholder="bi-star">
                    <div class="form-text">Nombre del ícono de Bootstrap Icons</div>
                </div>
            `;
            break;

        case 'timeline':
            sectionTitle.innerHTML = '<i class="bi bi-timeline text-primary"></i> Línea de Tiempo';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Elementos de la Línea de Tiempo (JSON)</label>
                    <textarea class="form-control font-monospace" name="timeline_items" rows="8" placeholder='[
  {"title": "Evento 1", "description": "Descripción del primer evento", "date": "2024-01-01", "color": "primary"},
  {"title": "Evento 2", "description": "Descripción del segundo evento", "date": "2024-02-01", "color": "success"}
]'></textarea>
                    <div class="form-text">Define los elementos de la línea de tiempo en formato JSON</div>
                </div>
            `;
            break;

        default:
            fieldsHtml = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Tipo de contenido no reconocido. Los campos se cargarán dinámicamente.
                </div>
            `;
    }

    dynamicFields.innerHTML = fieldsHtml;
}

function initializeFilters() {
    // Filtros de búsqueda (si existen)
    const searchInput = document.getElementById('searchBlocks');
    const typeFilter = document.getElementById('filterType');
    const visibilityFilter = document.getElementById('filterVisibility');

    if (searchInput) searchInput.addEventListener('input', filterBlocks);
    if (typeFilter) typeFilter.addEventListener('change', filterBlocks);
    if (visibilityFilter) visibilityFilter.addEventListener('change', filterBlocks);
}

function filterBlocks() {
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    const typeFilterValue = typeFilter ? typeFilter.value : '';
    const visibilityFilterValue = visibilityFilter ? visibilityFilter.value : '';

    const blocks = document.querySelectorAll('.block-card');

    blocks.forEach(block => {
        const title = block.querySelector('.block-title').textContent.toLowerCase();
        const type = block.dataset.type;
        const visibility = block.dataset.visibility;

        const matchesSearch = title.includes(searchTerm);
        const matchesType = !typeFilterValue || type === typeFilterValue;
        const matchesVisibility = !visibilityFilterValue || visibility === visibilityFilterValue;

        if (matchesSearch && matchesType && matchesVisibility) {
            block.style.display = '';
        } else {
            block.style.display = 'none';
        }
    });
}

function initializeCreateForm() {
    const createForm = document.getElementById('createBlockForm');
    if (createForm) {
        createForm.addEventListener('submit', handleCreateFormSubmit);
    }
}

function handleCreateFormSubmit(e) {
    e.preventDefault();

    // Validar que se haya seleccionado un tipo de contenido
    if (!selectedContentType) {
        alert('Por favor selecciona un tipo de contenido');
        return;
    }

    const formData = new FormData(this);

    // Procesar elementos estructurados si existen
    if (selectedContentType === 'json') {
        const structuredElements = [];
        const elementDivs = document.querySelectorAll('.structured-element');

        elementDivs.forEach((elementDiv, index) => {
            const elementData = {
                type: elementDiv.querySelector('.element-type').value,
                title: elementDiv.querySelector(`input[name="structured_elements[${index}][title]"]`)?.value || '',
            };

            // Agregar campos específicos según el tipo
            const type = elementData.type;
            switch(type) {
                case 'heading':
                    elementData.level = elementDiv.querySelector(`select[name="structured_elements[${index}][level]"]`).value;
                    elementData.content = elementDiv.querySelector(`input[name="structured_elements[${index}][content]"]`).value;
                    break;
                case 'text':
                    elementData.content = elementDiv.querySelector(`textarea[name="structured_elements[${index}][content]"]`).value;
                    break;
                case 'list':
                    elementData.ordered = elementDiv.querySelector(`select[name="structured_elements[${index}][ordered]"]`).value;
                    elementData.items = elementDiv.querySelector(`textarea[name="structured_elements[${index}][items]"]`).value.split('\n').filter(item => item.trim());
                    break;
                case 'image':
                    elementData.content = elementDiv.querySelector(`input[name="structured_elements[${index}][content]"]`).value;
                    break;
                case 'video':
                    elementData.content = elementDiv.querySelector(`input[name="structured_elements[${index}][content]"]`).value;
                    break;
                case 'code':
                    elementData.language = elementDiv.querySelector(`input[name="structured_elements[${index}][language]"]`).value;
                    elementData.code = elementDiv.querySelector(`textarea[name="structured_elements[${index}][code]"]`).value;
                    break;
                case 'exercise':
                    elementData.content = elementDiv.querySelector(`textarea[name="structured_elements[${index}][content]"]`).value;
                    elementData.difficulty = elementDiv.querySelector(`select[name="structured_elements[${index}][difficulty]"]`).value;
                    elementData.estimated_time = elementDiv.querySelector(`input[name="structured_elements[${index}][estimated_time]"]`).value;
                    break;
            }

            structuredElements.push(elementData);
        });

        formData.set('json_content', JSON.stringify(structuredElements));
    }

    // Mostrar indicador de carga
    const submitButton = document.getElementById('createButton');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Creando...';
    submitButton.disabled = true;

    fetch(`/courses/content/create/${selectedContentType}/`, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (response.ok) {
            // Recargar la página para mostrar el nuevo bloque
            location.reload();
        } else {
            return response.json().then(data => {
                if (data.errors) {
                    // Mostrar errores de validación
                    let errorMessage = 'Errores de validación:\n';
                    for (const [field, messages] of Object.entries(data.errors)) {
                        errorMessage += `${field}: ${messages.join(', ')}\n`;
                    }
                    alert(errorMessage);
                } else {
                    alert('Error al crear el bloque');
                }
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error de conexión al crear el bloque');
    })
    .finally(() => {
        // Restaurar el botón
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    });
}

// Funciones para gestionar elementos estructurados
function addStructuredElement() {
    const container = document.getElementById('structuredElements');
    const elementCount = container.querySelectorAll('.structured-element').length;

    const elementHtml = `
        <div class="structured-element border rounded p-3 mb-3" data-index="${elementCount}">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0">Elemento ${elementCount + 1}</h6>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeStructuredElement(this)">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Tipo de Elemento</label>
                    <select class="form-select element-type" name="structured_elements[${elementCount}][type]" onchange="updateElementFields(this)">
                        <option value="heading">Encabezado</option>
                        <option value="text">Texto</option>
                        <option value="list">Lista</option>
                        <option value="image">Imagen</option>
                        <option value="video">Video</option>
                        <option value="code">Código</option>
                        <option value="exercise">Ejercicio</option>
                    </select>
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Título (opcional)</label>
                    <input type="text" class="form-control" name="structured_elements[${elementCount}][title]" placeholder="Título del elemento">
                </div>
            </div>
            <div class="element-fields">
                <!-- Los campos específicos se cargarán aquí -->
            </div>
        </div>
    `;

    if (elementCount === 0) {
        container.innerHTML = '';
    }

    container.insertAdjacentHTML('beforeend', elementHtml);

    // Inicializar campos para el primer elemento
    const firstElement = container.lastElementChild;
    const typeSelect = firstElement.querySelector('.element-type');
    updateElementFields(typeSelect);
}

function removeStructuredElement(button) {
    button.closest('.structured-element').remove();

    // Reordenar índices si es necesario
    const elements = document.querySelectorAll('.structured-element');
    elements.forEach((el, index) => {
        el.dataset.index = index;
        el.querySelector('h6').textContent = `Elemento ${index + 1}`;

        // Actualizar nombres de campos
        const inputs = el.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.name) {
                input.name = input.name.replace(/\[\d+\]/, `[${index}]`);
            }
        });
    });
}

function updateElementFields(select) {
    const elementDiv = select.closest('.structured-element');
    const fieldsContainer = elementDiv.querySelector('.element-fields');
    const elementIndex = elementDiv.dataset.index;
    const elementType = select.value;

    let fieldsHtml = '';

    switch(elementType) {
        case 'heading':
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Nivel del Encabezado</label>
                        <select class="form-select" name="structured_elements[${elementIndex}][level]">
                            <option value="1">H1</option>
                            <option value="2">H2</option>
                            <option value="3">H3</option>
                            <option value="4">H4</option>
                            <option value="5">H5</option>
                            <option value="6">H6</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto del Encabezado *</label>
                        <input type="text" class="form-control" name="structured_elements[${elementIndex}][content]" required>
                    </div>
                </div>
            `;
            break;

        case 'text':
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Contenido de Texto *</label>
                    <textarea class="form-control" name="structured_elements[${elementIndex}][content]" rows="4" required></textarea>
                </div>
            `;
            break;

        case 'list':
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Tipo de Lista</label>
                    <select class="form-select" name="structured_elements[${elementIndex}][ordered]">
                        <option value="false">Lista No Ordenada</option>
                        <option value="true">Lista Ordenada</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Elementos de la Lista *</label>
                    <textarea class="form-control" name="structured_elements[${elementIndex}][items]" rows="4" placeholder="Elemento 1&#10;Elemento 2&#10;Elemento 3" required></textarea>
                    <div class="form-text">Cada línea representa un elemento de la lista</div>
                </div>
            `;
            break;

        case 'image':
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">URL de la Imagen *</label>
                    <input type="url" class="form-control" name="structured_elements[${elementIndex}][content]" required>
                </div>
            `;
            break;

        case 'video':
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">URL del Video *</label>
                    <input type="url" class="form-control" name="structured_elements[${elementIndex}][content]" required>
                </div>
            `;
            break;

        case 'code':
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Lenguaje</label>
                        <input type="text" class="form-control" name="structured_elements[${elementIndex}][language]" placeholder="python">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Código *</label>
                        <textarea class="form-control font-monospace" name="structured_elements[${elementIndex}][code]" rows="6" required></textarea>
                    </div>
                </div>
            `;
            break;

        case 'exercise':
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Descripción del Ejercicio *</label>
                    <textarea class="form-control" name="structured_elements[${elementIndex}][content]" rows="4" required></textarea>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Dificultad</label>
                        <select class="form-select" name="structured_elements[${elementIndex}][difficulty]">
                            <option value="beginner">Principiante</option>
                            <option value="intermediate">Intermedio</option>
                            <option value="advanced">Avanzado</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Tiempo Estimado (min)</label>
                        <input type="number" class="form-control" name="structured_elements[${elementIndex}][estimated_time]" min="1">
                    </div>
                </div>
            `;
            break;
    }

    fieldsContainer.innerHTML = fieldsHtml;
}

// Funciones para gestionar bloques
function previewBlock(slug) {
    fetch(`/courses/content/${slug}/preview/`)
        .then(response => response.text())
        .then(html => {
            document.getElementById('previewContent').innerHTML = html;
            new bootstrap.Modal(document.getElementById('previewModal')).show();
        })
        .catch(error => {
            console.error('Error loading preview:', error);
            document.getElementById('previewContent').innerHTML = '<div class="alert alert-danger">Error al cargar la vista previa</div>';
            new bootstrap.Modal(document.getElementById('previewModal')).show();
        });
}

function duplicateBlock(slug) {
    if (confirm('¿Estás seguro de que quieres duplicar este bloque?')) {
        fetch(`/courses/content/${slug}/duplicate/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => {
            if (response.ok) {
                location.reload();
            } else {
                alert('Error al duplicar el bloque');
            }
        });
    }
}

function deleteBlock(slug, title) {
    if (confirm(`¿Estás seguro de que quieres eliminar el bloque "${title}"?`)) {
        fetch(`/courses/content/${slug}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => {
            if (response.ok) {
                location.reload();
            } else {
                alert('Error al eliminar el bloque');
            }
        });
    }
}

// Funciones para el panel de creación
function openCreatePanel(type) {
    const panel = document.querySelector('.content-panel');
    if (panel) {
        panel.classList.add('open');
        // Si se especifica un tipo, seleccionarlo
        if (type) {
            const select = document.getElementById('panelContentType');
            if (select) {
                select.value = type;
                changePanelContentType();
            }
        }
    }
}

function closeCreatePanel() {
    const panel = document.querySelector('.content-panel');
    if (panel) {
        panel.classList.remove('open');
    }
}

function changePanelContentType() {
    const select = document.getElementById('panelContentType');
    const form = document.getElementById('panelCreateForm');
    const initialMessage = document.getElementById('panelInitialMessage');
    const dynamicFields = document.getElementById('panelDynamicFields');

    if (!select || !form || !initialMessage || !dynamicFields) return;

    const type = select.value;
    if (type) {
        form.style.display = 'block';
        initialMessage.style.display = 'none';
        document.getElementById('panelBlockType').value = type;

        // Aquí puedes agregar lógica para mostrar campos específicos según el tipo
        // Por simplicidad, mostramos todos los campos básicos
        dynamicFields.innerHTML = '';
    } else {
        form.style.display = 'none';
        initialMessage.style.display = 'block';
    }
}

function showCreateOptions() {
    // Mostrar opciones adicionales de creación
    alert('Funcionalidad adicional próximamente');
}// Content Manager Forms - JavaScript modular para gestión de formularios
// Agrupa tipos de contenido en categorías lógicas para simplificar la UX

class ContentManagerForms {
    constructor() {
        this.selectedCategory = null;
        this.selectedType = null;
        this.currentStep = 1;
        this.maxSteps = 1;
        this.formData = {};
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupValidation();
    }

    // Categorías de contenido organizadas lógicamente
    getContentCategories() {
        return {
            text: {
                name: 'Contenido de Texto',
                icon: 'bi-textarea-t',
                color: 'text-info',
                types: ['text', 'markdown', 'quote']
            },
            media: {
                name: 'Multimedia',
                icon: 'bi-play-circle',
                color: 'text-success',
                types: ['image', 'video']
            },
            interactive: {
                name: 'Elementos Interactivos',
                icon: 'bi-hand-index-thumb',
                color: 'text-warning',
                types: ['button', 'form', 'alert', 'badge', 'progress']
            },
            structural: {
                name: 'Estructural',
                icon: 'bi-grid-3x3-gap',
                color: 'text-primary',
                types: ['html', 'bootstrap', 'json', 'list', 'table', 'card', 'timeline']
            },
            utility: {
                name: 'Utilidades',
                icon: 'bi-gear',
                color: 'text-secondary',
                types: ['code', 'divider', 'icon']
            }
        };
    }

    bindEvents() {
        // Selección de categoría
        document.addEventListener('click', (e) => {
            if (e.target.closest('.category-card')) {
                const category = e.target.closest('.category-card').dataset.category;
                this.selectCategory(category);
            }
        });

        // Selección de tipo de contenido
        document.addEventListener('click', (e) => {
            if (e.target.closest('.content-type-btn')) {
                const type = e.target.closest('.content-type-btn').dataset.type;
                this.selectContentType(type);
            }
        });

        // Navegación del wizard
        document.addEventListener('click', (e) => {
            if (e.target.matches('.wizard-next')) {
                this.nextStep();
            }
            if (e.target.matches('.wizard-prev')) {
                this.prevStep();
            }
        });

        // Validación en tiempo real
        document.addEventListener('input', (e) => {
            if (e.target.matches('input[required], textarea[required], select[required]')) {
                this.validateField(e.target);
            }
        });
    }

    selectCategory(category) {
        this.selectedCategory = category;
        this.selectedType = null;
        this.currentStep = 1;

        // Actualizar UI
        document.querySelectorAll('.category-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-category="${category}"]`).classList.add('selected');

        // Mostrar tipos de la categoría
        this.showCategoryTypes(category);

        // Ocultar formulario hasta seleccionar tipo
        this.hideForm();
    }

    showCategoryTypes(category) {
        const categories = this.getContentCategories();
        const categoryData = categories[category];
        const typesContainer = document.getElementById('contentTypesContainer');

        if (!categoryData) return;

        const typesHtml = categoryData.types.map(type => {
            const typeInfo = this.getTypeInfo(type);
            return `
                <button class="content-type-btn" data-type="${type}">
                    <div class="type-icon">
                        <i class="bi ${typeInfo.icon}"></i>
                    </div>
                    <div class="type-info">
                        <div class="type-name">${typeInfo.name}</div>
                        <div class="type-desc">${typeInfo.description}</div>
                    </div>
                </button>
            `;
        }).join('');

        typesContainer.innerHTML = `
            <div class="category-header">
                <i class="bi ${categoryData.icon} ${categoryData.color} me-2"></i>
                ${categoryData.name}
            </div>
            <div class="types-grid">
                ${typesHtml}
            </div>
        `;
    }

    selectContentType(type) {
        this.selectedType = type;

        // Actualizar UI
        document.querySelectorAll('.content-type-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        document.querySelector(`[data-type="${type}"]`).classList.add('selected');

        // Determinar si necesita wizard
        const needsWizard = this.typeNeedsWizard(type);
        this.maxSteps = needsWizard ? 2 : 1;

        // Mostrar formulario
        this.showForm(type);
        this.updateWizardNavigation();
    }

    typeNeedsWizard(type) {
        // Tipos que necesitan configuración avanzada
        return ['json', 'form', 'table', 'timeline'].includes(type);
    }

    showForm(type) {
        const formContainer = document.getElementById('contentFormContainer');
        const typeInfo = this.getTypeInfo(type);

        // Header del formulario
        const headerHtml = `
            <div class="form-header">
                <div class="form-title">
                    <i class="bi ${typeInfo.icon} me-2"></i>
                    ${typeInfo.name}
                </div>
                <div class="form-description">${typeInfo.description}</div>
            </div>
        `;

        // Campos del formulario
        const fieldsHtml = this.getTypeFields(type);

        // Navegación del wizard si es necesario
        const wizardNav = this.maxSteps > 1 ? this.getWizardNavigation() : '';

        formContainer.innerHTML = `
            ${headerHtml}
            <form id="contentBlockForm" method="post">
                ${fieldsHtml}
                ${wizardNav}
            </form>
        `;

        // Mostrar contenedor
        formContainer.style.display = 'block';

        // Inicializar campos específicos
        this.initTypeSpecificFields(type);
    }

    hideForm() {
        document.getElementById('contentFormContainer').style.display = 'none';
    }

    getTypeFields(type) {
        const fields = {
            // Campos básicos para todos los tipos
            basic: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-8 mb-3">
                            <label class="form-label">Título *</label>
                            <input type="text" class="form-control" name="title" required>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Categoría</label>
                            <input type="text" class="form-control" name="category" placeholder="ej: Introducción">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Descripción</label>
                        <textarea class="form-control" name="description" rows="2" placeholder="Breve descripción del contenido"></textarea>
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Etiquetas</label>
                            <input type="text" class="form-control" name="tags" placeholder="separadas por coma">
                        </div>
                        <div class="col-md-6 mb-3">
                            <div class="form-check mt-4">
                                <input class="form-check-input" type="checkbox" name="is_public" id="isPublic">
                                <label class="form-check-label" for="isPublic">
                                    Contenido público
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
            `,

            // Campos específicos por tipo
            text: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Contenido de Texto *</label>
                        <textarea class="form-control" name="text_content" rows="6" placeholder="Ingresa el contenido de texto aquí..." required></textarea>
                    </div>
                </div>
            `,

            markdown: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Contenido Markdown *</label>
                        <textarea class="form-control" name="markdown_content" rows="8" placeholder="# Título\\n\\nContenido en **Markdown**..." required></textarea>
                        <div class="form-text">Soporta encabezados, listas, código, enlaces, imágenes, etc.</div>
                    </div>
                </div>
            `,

            quote: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Texto de la Cita *</label>
                        <textarea class="form-control" name="quote_text" rows="3" placeholder="La educación es el arma más poderosa..." required></textarea>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Autor de la Cita</label>
                        <input type="text" class="form-control" name="quote_author" placeholder="Nelson Mandela">
                    </div>
                </div>
            `,

            image: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-8 mb-3">
                            <label class="form-label">URL de la Imagen *</label>
                            <input type="url" class="form-control" name="image_url" placeholder="https://ejemplo.com/imagen.jpg" required>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Texto Alternativo</label>
                            <input type="text" class="form-control" name="image_alt" placeholder="Descripción de la imagen">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Pie de Foto</label>
                        <input type="text" class="form-control" name="image_caption" placeholder="Texto que aparece debajo de la imagen">
                    </div>
                </div>
            `,

            video: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">URL del Video *</label>
                        <input type="url" class="form-control" name="video_url" placeholder="https://www.youtube.com/watch?v=..." required>
                        <div class="form-text">Soporta YouTube, Vimeo y URLs directas de video</div>
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Descripción</label>
                            <input type="text" class="form-control" name="video_description" placeholder="Breve descripción del video">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Duración (minutos)</label>
                            <input type="number" class="form-control" name="video_duration" min="1" placeholder="15">
                        </div>
                    </div>
                </div>
            `,

            button: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Texto del Botón *</label>
                            <input type="text" class="form-control" name="button_text" placeholder="Haz clic aquí" required>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">URL del Botón *</label>
                            <input type="url" class="form-control" name="button_url" placeholder="https://ejemplo.com" required>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Estilo del Botón</label>
                            <select class="form-select" name="button_style">
                                <option value="primary">Primario</option>
                                <option value="secondary">Secundario</option>
                                <option value="success">Éxito</option>
                                <option value="danger">Peligro</option>
                                <option value="warning">Advertencia</option>
                                <option value="info">Información</option>
                            </select>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Tamaño del Botón</label>
                            <select class="form-select" name="button_size">
                                <option value="sm">Pequeño</option>
                                <option value="md" selected>Mediano</option>
                                <option value="lg">Grande</option>
                            </select>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Ícono (opcional)</label>
                            <input type="text" class="form-control" name="button_icon" placeholder="bi-star">
                            <div class="form-text">Nombre del ícono de Bootstrap Icons</div>
                        </div>
                    </div>
                </div>
            `,

            alert: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Tipo de Alerta *</label>
                            <select class="form-select" name="alert_type" required>
                                <option value="primary">Primario</option>
                                <option value="success">Éxito</option>
                                <option value="danger">Peligro</option>
                                <option value="warning">Advertencia</option>
                                <option value="info">Información</option>
                            </select>
                        </div>
                        <div class="col-md-8 mb-3">
                            <label class="form-label">Mensaje de Alerta *</label>
                            <input type="text" class="form-control" name="alert_message" placeholder="Texto del mensaje de alerta" required>
                        </div>
                    </div>
                </div>
            `,

            badge: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Texto de la Insignia *</label>
                            <input type="text" class="form-control" name="badge_text" placeholder="Nuevo" required>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Color de la Insignia</label>
                            <select class="form-select" name="badge_color">
                                <option value="primary">Primario</option>
                                <option value="success">Éxito</option>
                                <option value="danger">Peligro</option>
                                <option value="warning">Advertencia</option>
                                <option value="info">Información</option>
                            </select>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Ícono (opcional)</label>
                        <input type="text" class="form-control" name="badge_icon" placeholder="bi-star">
                        <div class="form-text">Nombre del ícono de Bootstrap Icons</div>
                    </div>
                </div>
            `,

            progress: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Valor del Progreso (0-100) *</label>
                            <input type="number" class="form-control" name="progress_value" min="0" max="100" value="50" required>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Color de la Barra</label>
                            <select class="form-select" name="progress_color">
                                <option value="primary">Primario</option>
                                <option value="success">Éxito</option>
                                <option value="info">Información</option>
                                <option value="warning">Advertencia</option>
                                <option value="danger">Peligro</option>
                            </select>
                        </div>
                    </div>
                </div>
            `,

            html: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Código HTML *</label>
                        <textarea class="form-control font-monospace" name="html_content" rows="10" placeholder="<div>Tu código HTML aquí</div>" required></textarea>
                        <div class="form-text">Puedes incluir clases de Bootstrap y estilos personalizados</div>
                    </div>
                </div>
            `,

            bootstrap: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Código HTML/Bootstrap *</label>
                        <textarea class="form-control font-monospace" name="html_content" rows="10" placeholder="<div class='alert alert-primary'>Tu código Bootstrap aquí</div>" required></textarea>
                        <div class="form-text">Utiliza componentes y clases de Bootstrap</div>
                    </div>
                </div>
            `,

            code: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Lenguaje de Programación *</label>
                            <select class="form-select" name="code_language" required>
                                <option value="text">Texto Plano</option>
                                <option value="python">Python</option>
                                <option value="javascript">JavaScript</option>
                                <option value="html">HTML</option>
                                <option value="css">CSS</option>
                                <option value="java">Java</option>
                                <option value="cpp">C++</option>
                                <option value="sql">SQL</option>
                                <option value="bash">Bash</option>
                            </select>
                        </div>
                        <div class="col-md-8 mb-3">
                            <label class="form-label">Título del Código</label>
                            <input type="text" class="form-control" name="code_title" placeholder="Ejemplo de función">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Código Fuente *</label>
                        <textarea class="form-control font-monospace" name="code_content" rows="8" placeholder="def hello_world():\\n    print('Hello, World!')" required></textarea>
                    </div>
                </div>
            `,

            list: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Tipo de Lista *</label>
                        <select class="form-select" name="list_type" required>
                            <option value="unordered">Lista No Ordenada</option>
                            <option value="ordered">Lista Ordenada</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Elementos de la Lista *</label>
                        <textarea class="form-control" name="list_items" rows="6" placeholder="Elemento 1\\nElemento 2\\nElemento 3" required></textarea>
                        <div class="form-text">Cada línea representa un elemento de la lista</div>
                    </div>
                </div>
            `,

            table: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Encabezados (separados por coma) *</label>
                        <input type="text" class="form-control" name="table_headers" placeholder="Nombre, Edad, Ciudad" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Filas de Datos *</label>
                        <textarea class="form-control" name="table_rows" rows="6" placeholder="Juan, 25, Madrid\\nMaría, 30, Barcelona\\nPedro, 35, Valencia" required></textarea>
                        <div class="form-text">Cada línea es una fila, valores separados por coma</div>
                    </div>
                </div>
            `,

            card: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Título de la Tarjeta *</label>
                            <input type="text" class="form-control" name="card_title" placeholder="Título principal" required>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Texto de la Tarjeta *</label>
                            <textarea class="form-control" name="card_text" rows="2" placeholder="Contenido de la tarjeta" required></textarea>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">URL del Botón</label>
                            <input type="url" class="form-control" name="card_button_url" placeholder="https://ejemplo.com">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Texto del Botón</label>
                            <input type="text" class="form-control" name="card_button_text" placeholder="Ver más" value="Ver más">
                        </div>
                    </div>
                </div>
            `,

            divider: `
                <div class="form-step" data-step="1">
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle me-2"></i>
                        El separador es un elemento visual simple que no requiere configuración adicional.
                    </div>
                </div>
            `,

            icon: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Ícono *</label>
                            <input type="text" class="form-control" name="icon_name" placeholder="star" required>
                            <div class="form-text">Nombre del ícono de Bootstrap Icons (sin "bi-")</div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Color</label>
                            <select class="form-select" name="icon_color">
                                <option value="primary">Primario</option>
                                <option value="success">Éxito</option>
                                <option value="danger">Peligro</option>
                                <option value="warning">Advertencia</option>
                                <option value="info">Información</option>
                            </select>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Texto Adicional</label>
                            <input type="text" class="form-control" name="icon_text" placeholder="Texto opcional junto al ícono">
                        </div>
                    </div>
                </div>
            `,

            // Tipos que usan wizard
            json: `
                <div class="form-step" data-step="1">
                    <div class="alert alert-info mb-3">
                        <i class="bi bi-info-circle me-2"></i>
                        Este tipo permite crear contenido complejo con múltiples elementos estructurados.
                    </div>
                    <div class="text-center mb-4">
                        <button type="button" class="btn btn-primary" onclick="contentManagerForms.addStructuredElement()">
                            <i class="bi bi-plus-circle me-1"></i>Agregar Elemento
                        </button>
                    </div>
                    <div id="structuredElements" class="structured-elements-container">
                        <p class="text-muted text-center">Haz clic en "Agregar Elemento" para comenzar</p>
                    </div>
                </div>
            `,

            form: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">URL de Acción del Formulario *</label>
                        <input type="url" class="form-control" name="form_action" placeholder="/procesar-formulario" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Campos del Formulario (JSON)</label>
                        <textarea class="form-control font-monospace" name="form_fields" rows="8" placeholder='[
  {"type": "text", "name": "nombre", "label": "Nombre", "required": true},
  {"type": "email", "name": "email", "label": "Correo Electrónico", "required": true},
  {"type": "textarea", "name": "mensaje", "label": "Mensaje", "placeholder": "Escribe tu mensaje aquí"}
]'></textarea>
                        <div class="form-text">Define los campos del formulario en formato JSON</div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Texto del Botón de Envío</label>
                        <input type="text" class="form-control" name="form_submit_text" placeholder="Enviar" value="Enviar">
                    </div>
                </div>
            `,

            timeline: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Elementos de la Línea de Tiempo (JSON)</label>
                        <textarea class="form-control font-monospace" name="timeline_items" rows="8" placeholder='[
  {"title": "Evento 1", "description": "Descripción del primer evento", "date": "2024-01-01", "color": "primary"},
  {"title": "Evento 2", "description": "Descripción del segundo evento", "date": "2024-02-01", "color": "success"}
]'></textarea>
                        <div class="form-text">Define los elementos de la línea de tiempo en formato JSON</div>
                    </div>
                </div>
            `
        };

        // Combinar campos básicos con específicos
        const basicFields = fields.basic;
        const specificFields = fields[type] || '<div class="alert alert-warning">Tipo de contenido no soportado</div>';

        return basicFields + specificFields;
    }

    getWizardNavigation() {
        return `
            <div class="wizard-navigation mt-4">
                <div class="d-flex justify-content-between align-items-center">
                    <button type="button" class="btn btn-outline-secondary wizard-prev" ${this.currentStep === 1 ? 'disabled' : ''}>
                        <i class="bi bi-arrow-left me-1"></i>Anterior
                    </button>
                    <div class="wizard-steps">
                        Paso ${this.currentStep} de ${this.maxSteps}
                    </div>
                    <button type="button" class="btn btn-primary wizard-next" ${this.currentStep === this.maxSteps ? 'disabled' : ''}>
                        Siguiente<i class="bi bi-arrow-right ms-1"></i>
                    </button>
                </div>
            </div>
        `;
    }

    nextStep() {
        if (this.currentStep < this.maxSteps) {
            this.currentStep++;
            this.updateWizardSteps();
            this.updateWizardNavigation();
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateWizardSteps();
            this.updateWizardNavigation();
        }
    }

    updateWizardSteps() {
        document.querySelectorAll('.form-step').forEach(step => {
            const stepNum = parseInt(step.dataset.step);
            step.style.display = stepNum === this.currentStep ? 'block' : 'none';
        });
    }

    updateWizardNavigation() {
        const prevBtn = document.querySelector('.wizard-prev');
        const nextBtn = document.querySelector('.wizard-next');
        const stepsIndicator = document.querySelector('.wizard-steps');

        if (prevBtn) prevBtn.disabled = this.currentStep === 1;
        if (nextBtn) nextBtn.disabled = this.currentStep === this.maxSteps;
        if (stepsIndicator) stepsIndicator.textContent = `Paso ${this.currentStep} de ${this.maxSteps}`;
    }

    getTypeInfo(type) {
        const typeMap = {
            text: { name: 'Texto Simple', icon: 'bi-textarea-t', description: 'Contenido de texto plano' },
            markdown: { name: 'Markdown', icon: 'bi-markdown', description: 'Contenido con formato Markdown' },
            quote: { name: 'Cita', icon: 'bi-quote', description: 'Cita o testimonial' },
            image: { name: 'Imagen', icon: 'bi-image', description: 'Imagen con descripción' },
            video: { name: 'Video', icon: 'bi-play-circle', description: 'Video embebido' },
            button: { name: 'Botón', icon: 'bi-hand-index-thumb', description: 'Botón interactivo' },
            alert: { name: 'Alerta', icon: 'bi-exclamation-triangle', description: 'Mensaje de alerta' },
            badge: { name: 'Insignia', icon: 'bi-tag', description: 'Insignia o etiqueta' },
            progress: { name: 'Barra de Progreso', icon: 'bi-bar-chart', description: 'Indicador de progreso' },
            html: { name: 'HTML', icon: 'bi-code-slash', description: 'Código HTML personalizado' },
            bootstrap: { name: 'Bootstrap', icon: 'bi-bootstrap', description: 'Componentes Bootstrap' },
            code: { name: 'Código', icon: 'bi-terminal', description: 'Bloque de código' },
            list: { name: 'Lista', icon: 'bi-list-ul', description: 'Lista ordenada o no ordenada' },
            table: { name: 'Tabla', icon: 'bi-table', description: 'Tabla de datos' },
            card: { name: 'Tarjeta', icon: 'bi-card-text', description: 'Tarjeta informativa' },
            divider: { name: 'Separador', icon: 'bi-dash', description: 'Separador visual' },
            icon: { name: 'Ícono', icon: 'bi-star', description: 'Ícono decorativo' },
            json: { name: 'Contenido Estructurado', icon: 'bi-braces', description: 'Contenido complejo estructurado' },
            form: { name: 'Formulario', icon: 'bi-ui-checks', description: 'Formulario personalizado' },
            timeline: { name: 'Línea de Tiempo', icon: 'bi-timeline', description: 'Línea de tiempo de eventos' }
        };
        return typeMap[type] || { name: 'Desconocido', icon: 'bi-question', description: 'Tipo no definido' };
    }

    initTypeSpecificFields(type) {
        // Inicializaciones específicas por tipo
        if (type === 'json') {
            // Para contenido estructurado, inicializar contenedor vacío
            this.structuredElementsCount = 0;
        }
    }

    addStructuredElement() {
        this.structuredElementsCount = (this.structuredElementsCount || 0) + 1;
        const container = document.getElementById('structuredElements');

        if (this.structuredElementsCount === 1) {
            container.innerHTML = '';
        }

        const elementHtml = `
            <div class="structured-element card mb-3" data-index="${this.structuredElementsCount}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Elemento ${this.structuredElementsCount}</h6>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="contentManagerForms.removeStructuredElement(this)">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Tipo de Elemento</label>
                            <select class="form-select element-type" name="structured_elements[${this.structuredElementsCount}][type]" onchange="contentManagerForms.updateElementFields(this)">
                                <option value="heading">Encabezado</option>
                                <option value="text">Texto</option>
                                <option value="list">Lista</option>
                                <option value="image">Imagen</option>
                                <option value="video">Video</option>
                                <option value="code">Código</option>
                                <option value="exercise">Ejercicio</option>
                            </select>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Título (opcional)</label>
                            <input type="text" class="form-control" name="structured_elements[${this.structuredElementsCount}][title]" placeholder="Título del elemento">
                        </div>
                    </div>
                    <div class="element-fields">
                        <!-- Los campos específicos se cargarán aquí -->
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', elementHtml);

        // Inicializar campos para el nuevo elemento
        const newElement = container.lastElementChild;
        const typeSelect = newElement.querySelector('.element-type');
        this.updateElementFields(typeSelect);
    }

    removeStructuredElement(button) {
        button.closest('.structured-element').remove();
        this.updateStructuredElementsIndices();
    }

    updateStructuredElementsIndices() {
        const elements = document.querySelectorAll('.structured-element');
        elements.forEach((element, index) => {
            const newIndex = index + 1;
            element.dataset.index = newIndex;
            element.querySelector('h6').textContent = `Elemento ${newIndex}`;

            // Actualizar nombres de campos
            const inputs = element.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                if (input.name) {
                    input.name = input.name.replace(/\[\d+\]/, `[${newIndex}]`);
                }
            });
        });
        this.structuredElementsCount = elements.length;
    }

    updateElementFields(select) {
        const elementDiv = select.closest('.structured-element');
        const fieldsContainer = elementDiv.querySelector('.element-fields');
        const elementIndex = elementDiv.dataset.index;
        const elementType = select.value;

        let fieldsHtml = '';

        switch(elementType) {
            case 'heading':
                fieldsHtml = `
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Nivel del Encabezado</label>
                            <select class="form-select" name="structured_elements[${elementIndex}][level]">
                                <option value="1">H1</option>
                                <option value="2">H2</option>
                                <option value="3">H3</option>
                                <option value="4">H4</option>
                                <option value="5">H5</option>
                                <option value="6">H6</option>
                            </select>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Texto del Encabezado *</label>
                            <input type="text" class="form-control" name="structured_elements[${elementIndex}][content]" required>
                        </div>
                    </div>
                `;
                break;

            case 'text':
                fieldsHtml = `
                    <div class="mb-3">
                        <label class="form-label">Contenido de Texto *</label>
                        <textarea class="form-control" name="structured_elements[${elementIndex}][content]" rows="4" required></textarea>
                    </div>
                `;
                break;

            case 'list':
                fieldsHtml = `
                    <div class="mb-3">
                        <label class="form-label">Tipo de Lista</label>
                        <select class="form-select" name="structured_elements[${elementIndex}][ordered]">
                            <option value="false">Lista No Ordenada</option>
                            <option value="true">Lista Ordenada</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Elementos de la Lista *</label>
                        <textarea class="form-control" name="structured_elements[${elementIndex}][items]" rows="4" placeholder="Elemento 1\nElemento 2\nElemento 3" required></textarea>
                        <div class="form-text">Cada línea representa un elemento de la lista</div>
                    </div>
                `;
                break;

            case 'image':
                fieldsHtml = `
                    <div class="mb-3">
                        <label class="form-label">URL de la Imagen *</label>
                        <input type="url" class="form-control" name="structured_elements[${elementIndex}][content]" required>
                    </div>
                `;
                break;

            case 'video':
                fieldsHtml = `
                    <div class="mb-3">
                        <label class="form-label">URL del Video *</label>
                        <input type="url" class="form-control" name="structured_elements[${elementIndex}][content]" required>
                    </div>
                `;
                break;

            case 'code':
                fieldsHtml = `
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Lenguaje</label>
                            <input type="text" class="form-control" name="structured_elements[${elementIndex}][language]" placeholder="python">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Código *</label>
                            <textarea class="form-control font-monospace" name="structured_elements[${elementIndex}][code]" rows="6" required></textarea>
                        </div>
                    </div>
                `;
                break;

            case 'exercise':
                fieldsHtml = `
                    <div class="mb-3">
                        <label class="form-label">Descripción del Ejercicio *</label>
                        <textarea class="form-control" name="structured_elements[${elementIndex}][content]" rows="4" required></textarea>
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Dificultad</label>
                            <select class="form-select" name="structured_elements[${elementIndex}][difficulty]">
                                <option value="beginner">Principiante</option>
                                <option value="intermediate">Intermedio</option>
                                <option value="advanced">Avanzado</option>
                            </select>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Tiempo Estimado (min)</label>
                            <input type="number" class="form-control" name="structured_elements[${elementIndex}][estimated_time]" min="1">
                        </div>
                    </div>
                `;
                break;
        }

        fieldsContainer.innerHTML = fieldsHtml;
    }

    setupValidation() {
        // Configurar validación visual
        document.addEventListener('blur', (e) => {
            if (e.target.matches('input[required], textarea[required], select[required]')) {
                this.validateField(e.target);
            }
        });
    }

    validateField(field) {
        const isValid = field.checkValidity();
        field.classList.toggle('is-valid', isValid && field.value.trim() !== '');
        field.classList.toggle('is-invalid', !isValid && field.value.trim() === '');

        // Mostrar/ocultar mensaje de error
        let feedback = field.parentNode.querySelector('.invalid-feedback');
        if (!isValid && field.value.trim() === '') {
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = 'Este campo es obligatorio';
                field.parentNode.appendChild(feedback);
            }
            feedback.style.display = 'block';
        } else if (feedback) {
            feedback.style.display = 'none';
        }
    }

    // Método para obtener datos del formulario
    getFormData() {
        const form = document.getElementById('contentBlockForm');
        if (!form) return null;

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Procesar elementos estructurados si existen
        if (this.selectedType === 'json') {
            data.structured_elements = this.getStructuredElementsData();
        }

        return data;
    }

    getStructuredElementsData() {
        const elements = document.querySelectorAll('.structured-element');
        const structuredData = [];

        elements.forEach((element, index) => {
            const elementIndex = index + 1;
            const elementData = {
                type: element.querySelector(`select[name="structured_elements[${elementIndex}][type]"]`).value,
                title: element.querySelector(`input[name="structured_elements[${elementIndex}][title]"]`).value || '',
            };

            // Agregar campos específicos según el tipo
            const type = elementData.type;
            switch(type) {
                case 'heading':
                    elementData.level = element.querySelector(`select[name="structured_elements[${elementIndex}][level]"]`).value;
                    elementData.content = element.querySelector(`input[name="structured_elements[${elementIndex}][content]"]`).value;
                    break;
                case 'text':
                    elementData.content = element.querySelector(`textarea[name="structured_elements[${elementIndex}][content]"]`).value;
                    break;
                case 'list':
                    elementData.ordered = element.querySelector(`select[name="structured_elements[${elementIndex}][ordered]"]`).value;
                    elementData.items = element.querySelector(`textarea[name="structured_elements[${elementIndex}][items]"]`).value.split('\n').filter(item => item.trim());
                    break;
                case 'image':
                case 'video':
                    elementData.content = element.querySelector(`input[name="structured_elements[${elementIndex}][content]"]`).value;
                    break;
                case 'code':
                    elementData.language = element.querySelector(`input[name="structured_elements[${elementIndex}][language]"]`).value;
                    elementData.code = element.querySelector(`textarea[name="structured_elements[${elementIndex}][code]"]`).value;
                    break;
                case 'exercise':
                    elementData.content = element.querySelector(`textarea[name="structured_elements[${elementIndex}][content]"]`).value;
                    elementData.difficulty = element.querySelector(`select[name="structured_elements[${elementIndex}][difficulty]"]`).value;
                    elementData.estimated_time = element.querySelector(`input[name="structured_elements[${elementIndex}][estimated_time]"]`).value;
                    break;
            }

            structuredData.push(elementData);
        });

        return structuredData;
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.contentManagerForms = new ContentManagerForms();
});(function () {
  "use strict";

  const toggle = document.querySelector('[data-nav-toggle]');
  const menu = document.querySelector('[data-nav-menu]');
  if (!toggle || !menu) return;

  const closeMenu = function () {
    menu.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
  };

  toggle.addEventListener('click', function () {
    const isOpen = menu.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });

  document.addEventListener('click', function (event) {
    if (!menu.contains(event.target) && !toggle.contains(event.target)) {
      closeMenu();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      closeMenu();
    }
  });

  const dropdowns = menu.querySelectorAll('.nav__dropdown');
  dropdowns.forEach(function (dropdown) {
    const trigger = dropdown.closest('li');
    if (!trigger) return;

    const triggerLink = trigger.querySelector(':scope > .nav__link');
    if (!triggerLink) return;

    triggerLink.addEventListener('click', function (event) {
      if (window.innerWidth <= 768) {
        event.preventDefault();
        const isOpen = dropdown.classList.toggle('is-open');
        dropdowns.forEach(function (other) {
          if (other !== dropdown) {
            other.classList.remove('is-open');
          }
        });
      }
    });
  });

  menu.addEventListener('click', function (event) {
    if (event.target.closest('.nav__dropdown')) {
      return;
    }
    dropdowns.forEach(function (dropdown) {
      dropdown.classList.remove('is-open');
    });
  });
})();

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
});// edit_section.js - Versión mejorada con soporte completo para formsets dinámicos

document.addEventListener('DOMContentLoaded', function() {
    initializeFormsetHandlers();
    initializeDeleteHandlers();
    initializeFormValidation();
    initializeImagePreview();
    initializeStepIndicators();
    initializeCharacterCounter();
    initializeErrorHandling();
});

/**
 * ============================================
 * FORMSETS DINÁMICOS - USANDO TEMPLATES
 * ============================================
 */

function initializeFormsetHandlers() {
    // Inicializar botones de añadir usando templates ocultos
    document.querySelectorAll('.add-formset-row').forEach(button => {
        button.removeEventListener('click', addFormsetRowHandler);
        button.addEventListener('click', addFormsetRowHandler);
    });
}

function addFormsetRowHandler(e) {
    e.preventDefault();
    const button = e.currentTarget;
    const prefix = button.dataset.prefix;
    addFormsetRow(prefix, button);
}

/**
 * Añade una nueva fila a un formset usando su template oculto
 */
function addFormsetRow(prefix, button) {
    console.log('Ejecutando addFormsetRow para prefix:', prefix);
    
    const container = button.closest('.card-body').querySelector('.formsets-container');
    
    // Versión simple: el ID del template es prefix + '-template'
    const templateId = prefix + '-template';
    console.log('Buscando template con ID:', templateId);
    
    const template = document.getElementById(templateId);

    if (!container) {
        console.error('Container no encontrado para prefix:', prefix);
        showToast('Error: No se encontró el contenedor', 'danger');
        return;
    }

    if (!template) {
        console.error('Template no encontrado para ID:', templateId);
        console.log('Templates disponibles:', Array.from(document.querySelectorAll('[id$="-template"]')).map(el => el.id));
        showToast('Error: No se encontró la plantilla', 'danger');
        return;
    }

    // ... resto del código igual ...

    // Obtener y actualizar TOTAL_FORMS
    const totalForms = document.querySelector(`input[name="${prefix}-TOTAL_FORMS"]`);
    if (!totalForms) {
        console.error('TOTAL_FORMS no encontrado para prefix:', prefix);
        showToast('Error: No se encontró el contador de formularios', 'danger');
        return;
    }

    const currentTotal = parseInt(totalForms.value);
    const newIndex = currentTotal;
    totalForms.value = currentTotal + 1;

    console.log('Total actual:', currentTotal, 'Nuevo índice:', newIndex); // Para depuración

    // Clonar el template y quitar clases ocultas
    const newForm = template.cloneNode(true);
    newForm.classList.remove('formset-row-template', 'd-none');
    newForm.id = ''; // Eliminar id del template

    // Reemplazar __prefix__ en todos los atributos name, id y for
    replacePrefixInElement(newForm, '__prefix__', newIndex);

    // Limpiar valores de los campos
    clearFormValues(newForm);

    // Eliminar mensajes de error previos
    clearFormErrors(newForm);

    // Añadir el nuevo formulario al contenedor
    container.appendChild(newForm);

    // Re-inicializar manejadores de DELETE en la nueva fila
    initializeDeleteHandlers(newForm);

    // Animar la entrada del nuevo formulario
    animateNewRow(newForm);

    // Mostrar notificación de éxito
    showToast('Elemento añadido correctamente', 'success');
}

/**
 * Reemplaza __prefix__ en todos los atributos name, id y for
 */
function replacePrefixInElement(element, searchPattern, newIndex) {
    const attributesToCheck = ['name', 'id', 'for', 'data-target', 'data-field'];
    
    element.querySelectorAll('[name*="__prefix__"], [id*="__prefix__"], [for*="__prefix__"], [data-target*="__prefix__"], [data-field*="__prefix__"]').forEach(el => {
        attributesToCheck.forEach(attr => {
            if (el.hasAttribute(attr) && el.getAttribute(attr).includes('__prefix__')) {
                el.setAttribute(attr, el.getAttribute(attr).replace(/__prefix__/g, newIndex));
            }
        });
    });

    // También verificar elementos que puedan tener __prefix__ en su texto (como labels)
    element.querySelectorAll('label').forEach(label => {
        if (label.htmlFor) {
            label.htmlFor = label.htmlFor.replace(/__prefix__/g, newIndex);
        }
    });
}

/**
 * Limpia los valores de los campos del formulario
 */
function clearFormValues(form) {
    form.querySelectorAll('input:not([type=checkbox]), select, textarea').forEach(input => {
        input.value = '';
        input.classList.remove('is-invalid', 'is-valid');
        
        // Eliminar cualquier placeholder que pueda haber quedado
        if (input.placeholder && input.placeholder.includes('__prefix__')) {
            input.placeholder = input.placeholder.replace(/__prefix__/g, '');
        }
    });

    form.querySelectorAll('input[type=checkbox]').forEach(checkbox => {
        checkbox.checked = false;
        checkbox.classList.remove('is-invalid', 'is-valid');
    });
}

/**
 * Limpia mensajes de error de un formulario
 */
function clearFormErrors(form) {
    form.querySelectorAll('.error-message, .invalid-feedback, .alert-danger').forEach(el => {
        el.remove();
    });
    
    form.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
        el.classList.remove('is-invalid', 'is-valid');
    });
}

/**
 * Anima la entrada de una nueva fila
 */
function animateNewRow(row) {
    row.style.opacity = '0';
    row.style.transform = 'translateY(20px)';
    row.style.transition = 'all 0.3s ease';

    setTimeout(() => {
        row.style.opacity = '1';
        row.style.transform = 'translateY(0)';
    }, 50);

    // Añadir un pequeño efecto de resaltado
    setTimeout(() => {
        row.style.backgroundColor = '#f0f7ff';
        setTimeout(() => {
            row.style.backgroundColor = '';
        }, 500);
    }, 100);
}

/**
 * Muestra un toast notification
 */
function showToast(message, type = 'info') {
    // Eliminar toasts anteriores para evitar acumulación
    const existingToasts = document.querySelectorAll('.toast-notification');
    existingToasts.forEach(toast => toast.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast-notification alert alert-${type} alert-dismissible fade show`;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '250px';
    toast.style.maxWidth = '350px';
    toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    toast.style.borderRadius = '8px';
    
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'danger' ? 'exclamation-triangle' : 
                 type === 'warning' ? 'exclamation-circle' : 'info-circle';
    
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-${icon} me-2 fs-5"></i>
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(toast);

    // Auto-cerrar después de 3 segundos
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * ============================================
 * MANEJADORES DE ELIMINACIÓN
 * ============================================
 */

function initializeDeleteHandlers(container = document) {
    // Buscar checkboxes DELETE dentro de delete-row-btn o cualquier checkbox con DELETE en su nombre
    container.querySelectorAll('.delete-row-btn input[type="checkbox"], input[type="checkbox"][name$="-DELETE"]').forEach(checkbox => {
        checkbox.removeEventListener('change', handleDeleteCheckbox);
        checkbox.addEventListener('change', handleDeleteCheckbox);
    });
}

function handleDeleteCheckbox(event) {
    const checkbox = event.target;
    const row = checkbox.closest('.formset-row');
    
    if (!row) return;

    if (checkbox.checked) {
        // Marcar para eliminación
        row.style.opacity = '0.6';
        row.style.backgroundColor = '#fff5f5';
        row.style.transition = 'all 0.3s ease';
        row.classList.add('marked-for-deletion');

        // Deshabilitar inputs del formulario a eliminar (excepto el checkbox DELETE)
        row.querySelectorAll('input:not([type=checkbox]), select, textarea').forEach(input => {
            input.disabled = true;
            input.classList.add('text-muted');
        });

        // Mostrar indicador visual
        const deleteLabel = checkbox.closest('label');
        if (deleteLabel) {
            deleteLabel.style.fontWeight = 'bold';
            deleteLabel.style.color = '#dc3545';
        }

        // Animación sutil
        row.style.transform = 'scale(0.98)';
        setTimeout(() => {
            row.style.transform = 'scale(1)';
        }, 200);

    } else {
        // Desmarcar eliminación
        row.style.opacity = '1';
        row.style.backgroundColor = '';
        row.classList.remove('marked-for-deletion');

        // Rehabilitar inputs
        row.querySelectorAll('input:not([type=checkbox]), select, textarea').forEach(input => {
            input.disabled = false;
            input.classList.remove('text-muted');
        });

        // Restaurar estilo del label
        const deleteLabel = checkbox.closest('label');
        if (deleteLabel) {
            deleteLabel.style.fontWeight = '';
            deleteLabel.style.color = '';
        }
    }
}

/**
 * ============================================
 * VALIDACIÓN DE FORMULARIOS
 * ============================================
 */

function initializeFormValidation() {
    const form = document.getElementById('curriculum-form');
    if (!form) return;

    // Validación en tiempo real
    form.querySelectorAll('input, select, textarea').forEach(field => {
        field.addEventListener('input', function() {
            validateField(this);
        });

        field.addEventListener('blur', function() {
            validateField(this, true);
        });
    });

    // Validación al enviar
    form.addEventListener('submit', handleFormSubmit);
}

/**
 * Valida un campo individual
 */
function validateField(field, showError = false) {
    if (field.hasAttribute('required') && !field.value.trim()) {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');

        if (showError) {
            addErrorMessage(field, 'Este campo es obligatorio.');
        }
        return false;
    } else {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
        
        // Remover mensaje de error si existe
        removeErrorMessage(field);
        return true;
    }
}

/**
 * Añade mensaje de error para un campo
 */
function addErrorMessage(field, message) {
    const container = field.closest('.mb-3') || field.closest('.form-group') || field.parentNode;
    
    // Verificar si ya existe un mensaje de error
    let errorMsg = container.querySelector('.error-message, .invalid-feedback');
    
    if (!errorMsg) {
        errorMsg = document.createElement('div');
        errorMsg.className = 'error-message';
        errorMsg.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${message}`;
        container.appendChild(errorMsg);
    } else {
        errorMsg.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${message}`;
    }
}

/**
 * Remueve mensaje de error de un campo
 */
function removeErrorMessage(field) {
    const container = field.closest('.mb-3') || field.closest('.form-group') || field.parentNode;
    const errorMsg = container.querySelector('.error-message, .invalid-feedback');
    if (errorMsg) {
        errorMsg.remove();
    }
}

/**
 * Maneja el envío del formulario
 */
function handleFormSubmit(e) {
    const form = e.currentTarget;
    const requiredFields = form.querySelectorAll('[required]');
    let hasErrors = false;
    let firstInvalid = null;
    const missingFields = [];

    // Limpiar mensajes de error anteriores
    form.querySelectorAll('.error-message, .invalid-feedback').forEach(el => el.remove());

    // Validar cada campo requerido
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            hasErrors = true;
            field.classList.add('is-invalid');

            if (!firstInvalid) {
                firstInvalid = field;
            }

            // Obtener label del campo
            const label = field.closest('.mb-3')?.querySelector('label')?.innerText || 
                         field.placeholder || 
                         'Campo';
            
            missingFields.push(label.replace(' *', '').replace(' (opcional)', ''));

            // Añadir mensaje de error
            addErrorMessage(field, 'Este campo es obligatorio.');
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        }
    });

    if (hasErrors) {
        e.preventDefault();

        // Scroll al primer campo con error
        if (firstInvalid) {
            firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            highlightField(firstInvalid);
        }

        // Mostrar resumen de errores
        showErrorSummary(missingFields);

        // Animación en el botón de submit
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.classList.add('field-error');
            setTimeout(() => {
                submitBtn.classList.remove('field-error');
            }, 500);
        }
    } else {
        // Mostrar estado de carga
        showLoadingState(form);
    }
}

/**
 * Resalta un campo con error
 */
function highlightField(field) {
    field.classList.add('focus-highlight');
    field.focus();
    
    setTimeout(() => {
        field.classList.remove('focus-highlight');
    }, 3000);
}

/**
 * Muestra un resumen de errores
 */
function showErrorSummary(missingFields) {
    // Verificar si ya existe un resumen
    let summary = document.getElementById('errorSummary');
    
    if (!summary) {
        summary = document.createElement('div');
        summary.id = 'errorSummary';
        summary.className = 'error-summary';
        
        const form = document.getElementById('curriculum-form');
        form.parentNode.insertBefore(summary, form);
    }

    summary.innerHTML = `
        <h6><i class="bi bi-exclamation-triangle-fill me-2"></i>Campos obligatorios faltantes:</h6>
        <ul>
            ${missingFields.map(field => `<li>${field}</li>`).join('')}
        </ul>
        <p class="mb-0 small text-muted">Por favor completa todos los campos requeridos antes de continuar.</p>
    `;

    // Scroll al resumen
    summary.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Muestra estado de carga en el botón submit
 */
function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Guardando...';
        submitBtn.disabled = true;

        // Si hay un error, restaurar después de un tiempo
        setTimeout(() => {
            if (submitBtn.disabled) {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        }, 5000);
    }
}

/**
 * ============================================
 * PREVISUALIZACIÓN DE IMAGEN
 * ============================================
 */

function initializeImagePreview() {
    const fileInput = document.querySelector('input[type="file"][name="profile_picture"]');
    
    if (fileInput) {
        fileInput.addEventListener('change', handleImagePreview);
    }
}

function handleImagePreview(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validar tipo de archivo
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
    if (!validTypes.includes(file.type)) {
        showToast('Formato no válido. Use JPG, PNG o GIF.', 'danger');
        event.target.value = '';
        return;
    }

    // Validar tamaño (máximo 2MB)
    if (file.size > 2 * 1024 * 1024) {
        showToast('La imagen no puede superar los 2MB.', 'danger');
        event.target.value = '';
        return;
    }

    const reader = new FileReader();
    
    reader.onload = function(e) {
        // Buscar o crear contenedor de preview
        let previewContainer = document.getElementById('profile-preview');
        
        if (!previewContainer) {
            previewContainer = document.createElement('div');
            previewContainer.id = 'profile-preview';
            previewContainer.className = 'mt-3';
            
            const fileInputContainer = event.target.closest('.mb-3, .form-group');
            if (fileInputContainer) {
                fileInputContainer.appendChild(previewContainer);
            }
        }

        previewContainer.innerHTML = `
            <div class="card bg-light">
                <div class="card-body">
                    <h6 class="card-title">Vista previa</h6>
                    <img src="${e.target.result}" alt="Preview" class="img-thumbnail" style="max-height: 150px; border-radius: 8px;">
                    <p class="small text-muted mt-2 mb-0">${file.name}</p>
                </div>
            </div>
        `;
        
        showToast('Imagen cargada correctamente', 'success');
    };

    reader.readAsDataURL(file);
}

/**
 * ============================================
 * INDICADORES DE PROGRESO
 * ============================================
 */

function initializeStepIndicators() {
    const progressBar = document.querySelector('.progress-bar');
    const steps = document.querySelectorAll('.step-indicator, .nav-link');
    
    if (steps.length > 0 && progressBar) {
        steps.forEach((step, index) => {
            step.addEventListener('mouseenter', function() {
                const percentage = ((index + 1) / steps.length) * 100;
                
                const originalWidth = progressBar.style.width;
                
                progressBar.style.transition = 'width 0.2s ease';
                progressBar.style.width = percentage + '%';
                
                setTimeout(() => {
                    progressBar.style.width = originalWidth;
                }, 500);
            });
        });
    }

    // Actualizar contador de secciones
    updateSectionCounter();
}

function updateSectionCounter() {
    const counter = document.getElementById('sectionCounter');
    if (!counter) return;

    const totalSections = document.querySelectorAll('.card[id^="section-"]').length;
    counter.textContent = `${totalSections} secciones`;
}

/**
 * ============================================
 * CONTADOR DE CARACTERES
 * ============================================
 */

function initializeCharacterCounter() {
    const bioField = document.querySelector('#id_bio, textarea[name="bio"]');
    
    if (bioField) {
        const counter = document.getElementById('counter-full_name') || 
                       createCharacterCounter(bioField);

        updateCharacterCount(bioField, counter);

        bioField.addEventListener('input', function() {
            updateCharacterCount(this, counter);
        });
    }
}

function createCharacterCounter(field) {
    const container = field.closest('.mb-3') || field.parentNode;
    const counter = document.createElement('div');
    counter.className = 'field-counter';
    container.appendChild(counter);
    return counter;
}

function updateCharacterCount(field, counter) {
    if (!counter) return;
    
    const length = field.value.length;
    counter.textContent = `${length} caracteres`;

    // Feedback visual por longitud
    counter.classList.remove('text-muted', 'warning', 'danger');
    
    if (length > 500) {
        counter.classList.add('danger');
        counter.style.color = '#dc3545';
    } else if (length > 300) {
        counter.classList.add('warning');
        counter.style.color = '#ffc107';
    } else {
        counter.style.color = '#6c757d';
    }
}

/**
 * ============================================
 * MANEJO DE ERRORES DEL SERVIDOR
 * ============================================
 */

function initializeErrorHandling() {
    // Enfocar primer error si existe resumen de errores
    if (document.querySelector('.error-summary')) {
        focusFirstError();
    }

    // Manejar clics en enlaces de error
    document.querySelectorAll('.error-link').forEach(link => {
        link.addEventListener('click', handleErrorLinkClick);
    });
}

function focusFirstError() {
    const errorFields = document.querySelectorAll('.is-invalid, .error-message');
    
    if (errorFields.length > 0) {
        const firstError = errorFields[0];
        const input = firstError.tagName === 'INPUT' || 
                     firstError.tagName === 'SELECT' || 
                     firstError.tagName === 'TEXTAREA' 
                     ? firstError 
                     : firstError.previousElementSibling;

        if (input) {
            setTimeout(() => {
                input.scrollIntoView({ behavior: 'smooth', block: 'center' });
                input.classList.add('focus-highlight');
                input.focus();

                setTimeout(() => {
                    input.classList.remove('focus-highlight');
                }, 3000);
            }, 100);
        }
    }
}

function handleErrorLinkClick(e) {
    e.preventDefault();
    
    const fieldName = this.dataset.field;
    const targetField = document.getElementById(`id_${fieldName}`) || 
                       document.querySelector(`[name="${fieldName}"]`);

    if (targetField) {
        targetField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        targetField.classList.add('focus-highlight');
        targetField.focus();

        setTimeout(() => {
            targetField.classList.remove('focus-highlight');
        }, 3000);
    }
}

/**
 * ============================================
 * UTILIDADES GENERALES
 * ============================================
 */

// Auto-guardado opcional (descomentar si se desea)
/*
let autoSaveTimer;
const form = document.getElementById('curriculum-form');

if (form) {
    form.addEventListener('input', function() {
        clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(() => {
            // Aquí iría la lógica de auto-guardado
            console.log('Auto-saving...');
            showToast('Guardando cambios...', 'info');
        }, 2000);
    });
}
*/

// Exportar funciones para uso global si es necesario
window.showToast = showToast;
window.addFormsetRow = addFormsetRow;(function () {
  "use strict";

  const grid = document.getElementById('grid');
  const typeFilter = document.getElementById('typeFilter');
  const ocrFilter = document.getElementById('ocrFilter');
  const pdfaFilter = document.getElementById('pdfaFilter');
  const searchInput = document.getElementById('search');
  const resetButton = document.getElementById('resetFilters');

  if (!grid) return;

  const getCardData = function (card) {
    return {
      type: (card.getAttribute('data-type') || '').toLowerCase(),
      ocr: (card.getAttribute('data-ocr') || '').toLowerCase(),
      pdfa: (card.getAttribute('data-pdfa') || '').toLowerCase(),
      title: (card.querySelector('.m360-text-lg')?.textContent || '').toLowerCase(),
      id: (card.querySelector('.m360-text-muted')?.textContent || '').toLowerCase(),
    };
  };

  const matchesCard = function (card) {
    const data = getCardData(card);
    const searchTerm = (searchInput?.value || '').trim().toLowerCase();

    const matchesType = !typeFilter?.value || data.type === typeFilter.value.toLowerCase();
    const matchesOcr = !ocrFilter?.value || data.ocr === ocrFilter.value.toLowerCase();
    const matchesPdfa = !pdfaFilter?.value || data.pdfa === pdfaFilter.value.toLowerCase();
    const matchesSearch = !searchTerm || data.title.includes(searchTerm) || data.id.includes(searchTerm);

    return matchesType && matchesOcr && matchesPdfa && matchesSearch;
  };

  const applyFilters = function () {
    const cards = grid.querySelectorAll('.m360-card');
    cards.forEach(function (card) {
      const visible = matchesCard(card);
      card.style.display = visible ? '' : 'none';
    });
  };

  const resetFilters = function () {
    if (typeFilter) typeFilter.value = '';
    if (ocrFilter) ocrFilter.value = '';
    if (pdfaFilter) pdfaFilter.value = '';
    if (searchInput) searchInput.value = '';
    applyFilters();
  };

  if (typeFilter) typeFilter.addEventListener('change', applyFilters);
  if (ocrFilter) ocrFilter.addEventListener('change', applyFilters);
  if (pdfaFilter) pdfaFilter.addEventListener('change', applyFilters);
  if (searchInput) searchInput.addEventListener('input', applyFilters);
  if (resetButton) resetButton.addEventListener('click', resetFilters);
})();
