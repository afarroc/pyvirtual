// Sistema de Notificaciones de Chat - Versión Simple y Funcional
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


})();