/**
 * Management360 - Dashboard JavaScript
 * Funcionalidades: Header dropdowns, Sidebar con anidamiento multinivel,
 * Dashboard stats, tabs, charts, modales, inbox, mailbox y management panel
 */

(function() {
  'use strict';

  // ==========================================
  // UTILS
  // ==========================================
  const Utils = {
    getElement: function(selector) {
      return document.querySelector(selector);
    },
    getElements: function(selector) {
      return document.querySelectorAll(selector);
    },
    toggleClass: function(el, className) {
      if (el) el.classList.toggle(className);
    },
    addClass: function(el, className) {
      if (el) el.classList.add(className);
    },
    removeClass: function(el, className) {
      if (el) el.classList.remove(className);
    },
    hasClass: function(el, className) {
      return el ? el.classList.contains(className) : false;
    },
    on: function(el, event, handler) {
      if (typeof el === 'string') {
        document.querySelectorAll(el).forEach(e => e.addEventListener(event, handler));
      } else if (el && el.length) {
        el.forEach(e => e.addEventListener(event, handler));
      } else if (el) {
        el.addEventListener(event, handler);
      }
    },
    getCookie: function(name) {
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
    },
    escapeHtml: function(text) {
      if (!text) return '';
      return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
  };

  // ==========================================
  // DROPDOWN MANAGER
  // ==========================================
  const DropdownManager = {
    openDropdown: null,

    init: function() {
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.dropdown')) {
          this.closeAll();
        }
      });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.closeAll();
        }
      });
    },

    toggle: function(trigger, menu) {
      const isOpen = menu.classList.contains('show');
      this.closeAll();
      if (!isOpen) {
        menu.classList.add('show');
        trigger.setAttribute('aria-expanded', 'true');
        this.openDropdown = { trigger, menu };
      }
    },

    closeAll: function() {
      document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
        menu.classList.remove('show');
        const trigger = menu.closest('.dropdown').querySelector('.dropdown-toggle, .avatar, .icon-btn');
        if (trigger) trigger.setAttribute('aria-expanded', 'false');
      });
      this.openDropdown = null;
    }
  };

  // ==========================================
  // HEADER MODULE
  // ==========================================
  const HeaderModule = {
    init: function() {
      this.searchBar = Utils.getElement('#searchBar');
      this.searchInput = Utils.getElement('#searchInput');
      this.searchClear = Utils.getElement('#searchClear');

      this.initDropdowns();
      this.initSearch();
      this.initNotifications();
      this.initMessages();
      this.initMobileMenu();
    },

    initDropdowns: function() {
      // Quick Actions
      const qaToggle = Utils.getElement('#quickActionsToggle');
      const qaMenu = Utils.getElement('#quickActionsMenu');
      if (qaToggle && qaMenu) {
        qaToggle.addEventListener('click', (e) => {
          e.stopPropagation();
          DropdownManager.toggle(qaToggle, qaMenu);
        });
      }

      // Notifications
      const notifToggle = Utils.getElement('#notificationsToggle');
      const notifMenu = Utils.getElement('#notificationsMenu');
      if (notifToggle && notifMenu) {
        notifToggle.addEventListener('click', (e) => {
          e.stopPropagation();
          DropdownManager.toggle(notifToggle, notifMenu);
        });
      }

      // Messages
      const msgToggle = Utils.getElement('#messagesToggle');
      const msgMenu = Utils.getElement('#messagesMenu');
      if (msgToggle && msgMenu) {
        msgToggle.addEventListener('click', (e) => {
          e.stopPropagation();
          DropdownManager.toggle(msgToggle, msgMenu);
        });
      }

      // Profile
      const profileToggle = Utils.getElement('#profileToggle');
      const profileMenu = Utils.getElement('#profileMenu');
      if (profileToggle && profileMenu) {
        profileToggle.addEventListener('click', (e) => {
          e.stopPropagation();
          DropdownManager.toggle(profileToggle, profileMenu);
        });
      }
    },

    initSearch: function() {
      if (!this.searchInput) return;

      // Keyboard shortcut: Cmd+K or Ctrl+K
      document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          this.searchInput.focus();
          this.searchInput.select();
        }
      });

      // Show clear button when typing
      this.searchInput.addEventListener('input', () => {
        if (this.searchInput.value.length > 0) {
          Utils.addClass(this.searchBar, 'has-value');
        } else {
          Utils.removeClass(this.searchBar, 'has-value');
        }
      });

      // Clear search
      if (this.searchClear) {
        this.searchClear.addEventListener('click', () => {
          this.searchInput.value = '';
          Utils.removeClass(this.searchBar, 'has-value');
          this.searchInput.focus();
        });
      }
    },

    initNotifications: function() {
      // Mark all as read
      const markBtn = Utils.getElement('#markAllRead');
      if (markBtn) {
        markBtn.addEventListener('click', () => {
          const items = Utils.getElements('.notif-item.unread');
          items.forEach(item => item.classList.remove('unread'));
          const badge = Utils.getElement('#notifBadge');
          if (badge) badge.textContent = '0';
          
          this.showNotification('All notifications marked as read', 'success');
        });
      }

      // Dismiss individual notification
      const dismissBtns = Utils.getElements('.notif-dismiss');
      dismissBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const item = btn.closest('.notif-item');
          if (item) {
            item.style.transition = 'all 0.3s ease';
            item.style.opacity = '0';
            item.style.transform = 'translateX(20px)';
            setTimeout(() => item.remove(), 300);

            const badge = Utils.getElement('#notifBadge');
            if (badge) {
              const unread = Utils.getElements('.notif-item.unread').length;
              badge.textContent = unread;
              if (unread === 0) badge.textContent = '0';
            }
          }
        });
      });
    },

    initMessages: function() {
      const msgItems = Utils.getElements('.msg-item');
      msgItems.forEach(item => {
        item.addEventListener('click', () => {
          const unread = item.querySelector('.msg-unread');
          if (unread) unread.remove();
          const badge = document.querySelector('.icon-btn .fa-envelope')?.closest('.icon-btn')?.querySelector('.badge');
          if (badge) {
            const count = parseInt(badge.textContent) || 0;
            if (count > 0) {
              badge.textContent = count - 1;
              if (badge.textContent === '0') badge.style.display = 'none';
            }
          }
        });
      });
    },

    initMobileMenu: function() {
      const menuToggle = Utils.getElement('#menuToggle');
      const sidebar = Utils.getElement('#mainSidebar');

      if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', (e) => {
          e.stopPropagation();
          Utils.toggleClass(sidebar, 'open');
          const isOpen = Utils.hasClass(sidebar, 'open');
          menuToggle.setAttribute('aria-expanded', isOpen);
        });

        document.addEventListener('click', (e) => {
          if (window.innerWidth <= 768) {
            const isInside = sidebar.contains(e.target) || menuToggle.contains(e.target);
            if (!isInside) {
              Utils.removeClass(sidebar, 'open');
              menuToggle.setAttribute('aria-expanded', 'false');
            }
          }
        });

        window.addEventListener('resize', () => {
          if (window.innerWidth > 768) {
            Utils.removeClass(sidebar, 'open');
            menuToggle.setAttribute('aria-expanded', 'false');
          }
        });
      }
    },

    showNotification: function(message, type) {
      const types = {
        success: { icon: 'fa-check-circle', color: '#22c55e' },
        error: { icon: 'fa-exclamation-circle', color: '#ef4444' },
        warning: { icon: 'fa-exclamation-triangle', color: '#f59e0b' },
        info: { icon: 'fa-info-circle', color: '#0ea5e9' }
      };
      const config = types[type] || types.info;
      const notification = document.createElement('div');
      notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: white;
        border-left: 4px solid ${config.color};
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 12px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.875rem;
        transform: translateX(120%);
        transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        max-width: 400px;
      `;
      notification.innerHTML = `
        <i class="fas ${config.icon}" style="color:${config.color};font-size:1.2rem;"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:1.1rem;">
          <i class="fas fa-times"></i>
        </button>
      `;
      document.body.appendChild(notification);
      setTimeout(() => { notification.style.transform = 'translateX(0)'; }, 50);
      setTimeout(() => {
        notification.style.transform = 'translateX(120%)';
        setTimeout(() => notification.remove(), 400);
      }, 4000);
    }
  };

  // ==========================================
  // SIDEBAR MODULE - MULTI-LEVEL NAVIGATION
  // ==========================================
  const SidebarModule = {
    init: function() {
      this.initDropdownToggles();
      this.initActiveStates();
      this.initUpgrade();
      this.initNavigationLinks();
    },

    initDropdownToggles: function() {
      const toggles = document.querySelectorAll('.sidebar-nav-item.has-dropdown > .sidebar-nav-link.dropdown-toggle');
      
      toggles.forEach(toggle => {
        toggle.removeEventListener('click', this.handleToggle);
        toggle.addEventListener('click', this.handleToggle);
      });
    },

    handleToggle: function(e) {
      e.preventDefault();
      e.stopPropagation();

      const parentItem = this.closest('.sidebar-nav-item.has-dropdown');
      const parentUl = parentItem.closest('ul');
      
      if (parentUl) {
        const siblings = parentUl.querySelectorAll(':scope > .sidebar-nav-item.has-dropdown');
        siblings.forEach(sibling => {
          if (sibling !== parentItem && Utils.hasClass(sibling, 'open')) {
            Utils.removeClass(sibling, 'open');
            const siblingToggle = sibling.querySelector('.dropdown-toggle');
            if (siblingToggle) siblingToggle.setAttribute('aria-expanded', 'false');
          }
        });
      }

      Utils.toggleClass(parentItem, 'open');
      const isOpen = Utils.hasClass(parentItem, 'open');
      this.setAttribute('aria-expanded', isOpen);
    },

    initActiveStates: function() {
      const activeItems = document.querySelectorAll('.sidebar-dropdown .sidebar-nav-item.active');
      activeItems.forEach(item => {
        let parent = item.closest('.sidebar-nav-item.has-dropdown');
        while (parent) {
          Utils.addClass(parent, 'open');
          const toggle = parent.querySelector('.dropdown-toggle');
          if (toggle) toggle.setAttribute('aria-expanded', 'true');
          parent = parent.parentElement?.closest('.sidebar-nav-item.has-dropdown');
        }
      });
    },

    initNavigationLinks: function() {
      const links = Utils.getElements('.sidebar-nav a:not(.dropdown-toggle)');
      links.forEach(link => {
        link.addEventListener('click', (e) => {
          const li = link.closest('li');
          if (li) {
            const parentUl = li.closest('ul');
            if (parentUl) {
              const allLis = parentUl.querySelectorAll('li');
              allLis.forEach(l => Utils.removeClass(l, 'active'));
              Utils.addClass(li, 'active');
            }
            
            const sidebar = Utils.getElement('#mainSidebar');
            const menuToggle = Utils.getElement('#menuToggle');
            if (window.innerWidth <= 768 && sidebar) {
              Utils.removeClass(sidebar, 'open');
              if (menuToggle) menuToggle.setAttribute('aria-expanded', 'false');
            }
          }
        });
      });
    },

    initUpgrade: function() {
      const upgradeBtn = Utils.getElement('#upgradeBtn');
      if (upgradeBtn) {
        upgradeBtn.addEventListener('click', () => {
          HeaderModule.showNotification('🚀 Upgrade to Pro - All features unlocked!', 'success');
        });
      }
    }
  };

  // ==========================================
  // DASHBOARD MODULE
  // ==========================================
  const DashboardModule = {
    init: function() {
      this.initStats();
      this.initCharts();
      this.initTableSort();
      this.initTabs();
      this.initQuickActions();
      this.initDateRange();
      this.initRefresh();
      this.initModalHandlers();
      this.initDeleteItem();
      this.showWelcomeNotification();
    },

    initStats: function() {
      // Animate stat values
      const statValues = Utils.getElements('.stat-value');
      statValues.forEach(el => {
        const originalText = el.textContent.trim();
        const isCurrency = originalText.includes('$');
        const isNumber = !isCurrency && !isNaN(parseFloat(originalText.replace(/,/g, '')));

        if (isCurrency) {
          const num = parseFloat(originalText.replace(/[$,K]/g, ''));
          if (!isNaN(num)) {
            this.animateCounter(el, 0, num * 1000, 1500, (val) => {
              if (val >= 1000) {
                return '$' + (val / 1000).toFixed(1) + 'K';
              }
              return '$' + val.toFixed(0);
            });
          }
        } else if (isNumber) {
          const num = parseInt(originalText.replace(/,/g, ''));
          if (!isNaN(num)) {
            this.animateCounter(el, 0, num, 1500);
          }
        }
      });

      // Animate stat-number elements
      const statNumbers = document.querySelectorAll('.stat-number');
      statNumbers.forEach(el => {
        const text = el.textContent;
        const num = parseInt(text.replace(/,/g, ''));
        if (!isNaN(num) && num > 0) {
          let current = 0;
          const duration = 1000;
          const step = Math.max(1, Math.floor(num / 60));
          const interval = duration / (num / step);
          const timer = setInterval(() => {
            current += step;
            if (current >= num) {
              current = num;
              clearInterval(timer);
            }
            el.textContent = current.toLocaleString();
          }, interval);
        }
      });
    },

    animateCounter: function(el, start, end, duration, formatter) {
      const startTime = performance.now();
      const update = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + (end - start) * eased;

        if (formatter) {
          el.textContent = formatter(current);
        } else {
          el.textContent = Math.round(current).toLocaleString();
        }

        if (progress < 1) {
          requestAnimationFrame(update);
        }
      };
      requestAnimationFrame(update);
    },

    initCharts: function() {
      const periodBtns = Utils.getElements('[data-period]');
      periodBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          periodBtns.forEach(b => Utils.removeClass(b, 'active'));
          Utils.addClass(btn, 'active');

          const bars = Utils.getElements('.bar');
          bars.forEach((bar) => {
            const newHeight = 20 + Math.random() * 75;
            bar.style.height = newHeight + '%';
            const span = bar.querySelector('span');
            if (span) span.textContent = Math.round(newHeight);
          });
        });
      });
    },

    initTableSort: function() {
      const headers = Utils.getElements('.table th[data-sort]');
      let sortDirection = {};

      headers.forEach(header => {
        header.addEventListener('click', () => {
          const key = header.dataset.sort;
          sortDirection[key] = sortDirection[key] === 'asc' ? 'desc' : 'asc';

          const tbody = Utils.getElement('#projectsBody');
          if (!tbody) return;
          const rows = Array.from(tbody.querySelectorAll('tr'));

          rows.sort((a, b) => {
            let aVal = a.querySelector(`td:nth-child(${header.cellIndex + 1})`)?.textContent.trim() || '';
            let bVal = b.querySelector(`td:nth-child(${header.cellIndex + 1})`)?.textContent.trim() || '';

            if (key === 'progress') {
              aVal = parseInt(a.querySelector('.progress-fill')?.style.width || '0%');
              bVal = parseInt(b.querySelector('.progress-fill')?.style.width || '0%');
            }

            if (sortDirection[key] === 'asc') {
              return aVal > bVal ? 1 : -1;
            } else {
              return aVal < bVal ? 1 : -1;
            }
          });

          rows.forEach(row => tbody.appendChild(row));

          headers.forEach(h => {
            const icon = h.querySelector('i');
            if (icon) icon.className = 'fas fa-sort';
          });
          const icon = header.querySelector('i');
          if (icon) {
            icon.className = sortDirection[key] === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down';
          }
        });
      });
    },

    initTabs: function() {
      const tabs = document.querySelectorAll('.tab-btn');
      const contents = document.querySelectorAll('.tab-content');

      tabs.forEach(tab => {
        tab.addEventListener('click', () => {
          const target = tab.dataset.tab;
          tabs.forEach(t => Utils.removeClass(t, 'active'));
          Utils.addClass(tab, 'active');
          contents.forEach(content => {
            Utils.removeClass(content, 'active');
            if (content.id === 'tab-' + target) {
              Utils.addClass(content, 'active');
            }
          });
          localStorage.setItem('activeTab', target);
        });
      });

      const savedTab = localStorage.getItem('activeTab');
      if (savedTab) {
        const tabToActivate = document.querySelector(`.tab-btn[data-tab="${savedTab}"]`);
        if (tabToActivate) {
          tabToActivate.click();
        }
      }
    },

    initQuickActions: function() {
      const actionBtns = Utils.getElements('.quick-action-btn');
      actionBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          const label = btn.querySelector('span')?.textContent || 'Action';
          HeaderModule.showNotification(`🚀 ${label} triggered!`, 'info');
        });
      });
    },

    initDateRange: function() {
      const btn = Utils.getElement('#dateRangeBtn');
      if (btn) {
        const ranges = ['Today', 'This Week', 'This Month', 'This Quarter', 'This Year'];
        let currentIndex = 2;

        btn.addEventListener('click', () => {
          currentIndex = (currentIndex + 1) % ranges.length;
          btn.innerHTML = `<i class="fas fa-calendar-alt"></i> ${ranges[currentIndex]}`;
          btn.style.transition = 'all 0.3s ease';
          btn.style.transform = 'scale(0.95)';
          setTimeout(() => {
            btn.style.transform = 'scale(1)';
          }, 200);
        });
      }
    },

    initRefresh: function() {
      const btn = Utils.getElement('#refreshBtn');
      if (btn) {
        btn.addEventListener('click', () => {
          const icon = btn.querySelector('i');
          Utils.addClass(icon, 'fa-spin');
          btn.disabled = true;
          setTimeout(() => {
            Utils.removeClass(icon, 'fa-spin');
            btn.disabled = false;
            HeaderModule.showNotification('Dashboard refreshed successfully!', 'success');
          }, 1500);
        });
      }
    },

    initModalHandlers: function() {
      document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
          if (e.target === overlay) {
            Utils.removeClass(overlay, 'show');
          }
        });
      });

      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          document.querySelectorAll('.modal-overlay.show').forEach(modal => {
            Utils.removeClass(modal, 'show');
          });
        }
      });
    },

    initDeleteItem: function() {
      // Para botones de eliminar en todos los templates
      document.addEventListener('click', (e) => {
        const deleteBtn = e.target.closest('.admin-btn-delete, .btn-delete-item, .btn-delete-inbox');
        if (deleteBtn) {
          e.preventDefault();
          const itemId = deleteBtn.dataset.id;
          const title = deleteBtn.dataset.title || 'Item';
          if (window.deleteInboxItem) {
            window.deleteInboxItem(itemId, title);
          } else {
            if (confirm(`¿Estás seguro de eliminar el item "${title}"? Esta acción no se puede deshacer.`)) {
              const form = document.createElement('form');
              form.method = 'POST';
              const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
              form.innerHTML = `
                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
                <input type="hidden" name="action" value="delete">
              `;
              document.body.appendChild(form);
              form.action = `/events/inbox/process/${itemId}/`;
              form.submit();
            }
          }
        }
      });
    },

    showWelcomeNotification: function() {
      if (!sessionStorage.getItem('welcomeShown')) {
        setTimeout(() => {
          HeaderModule.showNotification('👋 Welcome back to Management360!', 'info');
          sessionStorage.setItem('welcomeShown', 'true');
        }, 1000);
      }
    }
  };

  // ==========================================
  // INBOX MODULE
  // ==========================================
  const InboxModule = {
    init: function() {
      this.initAI();
      this.initFilters();
      this.initQuickClassify();
      this.initPendienteToggle();
      this.initLoadMore();
      this.initQuickAddForm();
    },

    // ========== AI ASSISTANT ==========
    initAI: function() {
      const summaryBtn = document.getElementById('ai-refresh-btn');
      const summaryTrigger = document.getElementById('ai-summary-trigger');
      const sendBtn = document.getElementById('ai-send-btn');
      const chatInput = document.getElementById('ai-chat-input');

      if (summaryBtn) {
        summaryBtn.addEventListener('click', () => this.aiLoadSummary());
      }

      if (summaryTrigger) {
        summaryTrigger.addEventListener('click', (e) => {
          e.preventDefault();
          this.aiLoadSummary();
        });
      }

      if (sendBtn && chatInput) {
        sendBtn.addEventListener('click', () => this.aiSendMessage());
        chatInput.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            this.aiSendMessage();
          }
        });
      }

      // Configurar URLs desde data attributes
      this.aiSummaryUrl = document.querySelector('[data-ai-summary-url]')?.dataset.aiSummaryUrl || 
                          document.querySelector('#ai-summary-trigger')?.dataset.aiSummaryUrl;
      this.aiChatUrl = document.querySelector('[data-ai-chat-url]')?.dataset.aiChatUrl ||
                       document.querySelector('#ai-send-btn')?.dataset.aiChatUrl;
    },

    aiLoadSummary: async function() {
      const url = this.aiSummaryUrl || '/events/inbox/ai/summary/';
      const placeholder = document.getElementById('ai-placeholder');
      const content = document.getElementById('ai-analysis-content');
      const text = document.getElementById('ai-analysis-text');
      const badge = document.getElementById('ai-source-badge');
      const loading = document.getElementById('ai-loading');
      const refreshIcon = document.getElementById('ai-refresh-icon');
      const refreshBtn = document.getElementById('ai-refresh-btn');

      this._setAILoading(true, loading, placeholder, refreshIcon, refreshBtn);
      if (content) content.style.display = 'none';

      try {
        const resp = await fetch(url, {
          headers: {
            'X-CSRFToken': Utils.getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        const data = await resp.json();
        if (data.success) {
          if (text) text.textContent = data.analysis;
          if (badge) {
            badge.textContent = data.source === 'ollama' ? 'Ollama' : 'Análisis estático';
            badge.className = `status ${data.source === 'ollama' ? 'status-active' : 'status-pending'}`;
          }
          if (content) content.style.display = 'block';
          if (placeholder) placeholder.style.display = 'none';
        } else {
          if (placeholder) placeholder.innerHTML = '⚠️ ' + (data.error || 'Error al analizar');
        }
      } catch(e) {
        if (placeholder) placeholder.innerHTML = '⚠️ Error de conexión';
      } finally {
        this._setAILoading(false, loading, placeholder, refreshIcon, refreshBtn);
      }
    },

    aiSendMessage: async function() {
      const url = this.aiChatUrl || '/events/inbox/ai/chat/';
      const input = document.getElementById('ai-chat-input');
      const sendBtn = document.getElementById('ai-send-btn');
      const message = input?.value?.trim();
      if (!message) return;

      if (input) input.value = '';
      if (input) input.disabled = true;
      if (sendBtn) sendBtn.disabled = true;

      this._appendChat('user', message);

      const typingId = 'typing-' + Date.now();
      const zone = document.getElementById('ai-chat-history');
      const typing = document.createElement('div');
      typing.id = typingId;
      typing.className = 'activity-item chat-message';
      typing.style.justifyContent = 'flex-start';
      typing.innerHTML = `<div class="chat-bubble chat-bubble-assistant">
        <span class="spinner-small"></span> Pensando…</div>`;
      if (zone) {
        zone.appendChild(typing);
        zone.scrollTop = zone.scrollHeight;
      }

      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': Utils.getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify({ message })
        });
        const data = await resp.json();
        document.getElementById(typingId)?.remove();

        if (data.success) {
          this._appendChat('assistant', data.reply);
        } else {
          this._appendChat('assistant', '⚠️ ' + (data.error || 'Error al responder'));
        }
      } catch(e) {
        document.getElementById(typingId)?.remove();
        this._appendChat('assistant', '⚠️ Error de conexión con el asistente');
      } finally {
        if (input) input.disabled = false;
        if (sendBtn) sendBtn.disabled = false;
        if (input) input.focus();
      }
    },

    _setAILoading: function(on, loading, placeholder, icon, btn) {
      if (loading) loading.style.display = on ? 'flex' : 'none';
      if (placeholder) placeholder.style.display = on ? 'none' : 'block';
      if (icon) icon.className = on ? 'fas fa-sync fa-spin' : 'fas fa-sync';
      if (btn) btn.disabled = on;
    },

    _appendChat: function(role, text) {
      const zone = document.getElementById('ai-chat-history');
      if (!zone) return;
      const isUser = role === 'user';
      const div = document.createElement('div');
      div.className = 'activity-item chat-message';
      div.style.justifyContent = isUser ? 'flex-end' : 'flex-start';
      div.innerHTML = `
        <div class="chat-bubble ${isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}">
          ${Utils.escapeHtml(text)}
        </div>`;
      zone.appendChild(div);
      zone.scrollTop = zone.scrollHeight;
    },

    // ========== FILTERS ==========
    initFilters: function() {
      const filterBtns = {
        'filterPendientes': 'section-pendientes',
        'filterAccionables': 'section-accionables',
        'filterNoAccionables': 'section-no_accionables',
        'filterProcesados': 'section-procesados'
      };

      const filterPanel = document.getElementById('filterPendientes')?.closest('.section-card') || 
                         document.getElementById('clearFilters')?.closest('.section-card');
      const summaryPanel = document.getElementById('ai-refresh-btn')?.closest('.section-card');
      const aiPanel = document.getElementById('ai-assistant-panel');
      
      const itemSections = {
        'section-pendientes': document.getElementById('section-pendientes'),
        'section-accionables': document.getElementById('section-accionables'),
        'section-no_accionables': document.getElementById('section-no_accionables'),
        'section-procesados': document.getElementById('section-procesados')
      };

      Object.entries(filterBtns).forEach(([btnId, sectionId]) => {
        const btn = document.getElementById(btnId);
        if (btn) {
          btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            Object.values(itemSections).forEach(section => {
              if (section) section.style.display = 'none';
            });
            if (filterPanel) filterPanel.style.display = 'block';
            if (summaryPanel) summaryPanel.style.display = 'block';
            if (aiPanel) aiPanel.style.display = 'block';

            const target = itemSections[sectionId];
            if (target) target.style.display = 'block';
          });
        }
      });

      const clearBtn = document.getElementById('clearFilters');
      if (clearBtn) {
        clearBtn.addEventListener('click', function() {
          document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
          Object.values(itemSections).forEach(section => {
            if (section) section.style.display = 'block';
          });
          if (filterPanel) filterPanel.style.display = 'block';
          if (summaryPanel) summaryPanel.style.display = 'block';
          if (aiPanel) aiPanel.style.display = 'block';
        });
      }
    },

    // ========== QUICK CLASSIFY ==========
    initQuickClassify: function() {
      document.addEventListener('click', (e) => {
        const classifyBtn = e.target.closest('.btn-quick-classify');
        if (classifyBtn) {
          e.preventDefault();
          const itemId = classifyBtn.dataset.id;
          const category = classifyBtn.dataset.category;
          if (!itemId || !category) return;
          
          const label = category === 'accionable' ? 'Accionable' : 
                       category === 'no_accionable' ? 'No Accionable' : 'Pendiente';
          if (!confirm(`¿Marcar este item como "${label}"?`)) return;
          
          if (window.quickClassify) {
            window.quickClassify(itemId, category);
          } else {
            const form = document.createElement('form');
            form.method = 'POST';
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            form.innerHTML = `
              <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
              <input type="hidden" name="action" value="categorize">
              <input type="hidden" name="gtd_category" value="${category}">
            `;
            document.body.appendChild(form);
            form.action = `/events/inbox/process/${itemId}/`;
            form.submit();
          }
        }
      });
    },

    // ========== PENDIENTE TOGGLE ==========
    initPendienteToggle: function() {
      document.addEventListener('click', (e) => {
        const toggleBtn = e.target.closest('.pendiente-toggle');
        if (toggleBtn) {
          e.preventDefault();
          const card = toggleBtn.closest('.pendiente-card');
          if (!card) return;
          const extended = card.querySelector('.pendiente-extended');
          if (!extended) return;
          
          const isHidden = extended.style.display === 'none' || !extended.style.display;
          extended.style.display = isHidden ? 'block' : 'none';
          const icon = toggleBtn.querySelector('i');
          if (icon) {
            icon.className = isHidden ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
          }
          toggleBtn.innerHTML = isHidden ? 
            '<i class="fas fa-chevron-up" aria-hidden="true"></i> Menos opciones' : 
            '<i class="fas fa-chevron-down" aria-hidden="true"></i> Más opciones';
        }
      });
    },

    // ========== LOAD MORE ==========
    initLoadMore: function() {
      const loadBtn = document.getElementById('loadMorePendientes');
      if (loadBtn) {
        loadBtn.addEventListener('click', function() {
          this.disabled = true;
          const container = document.getElementById('pendientesContainer');
          const offset = container?.querySelectorAll('.pendiente-card').length || 0;
          
          fetch(`/events/inbox/api/pendientes/?offset=${offset}&limit=8`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
          })
          .then(response => response.json())
          .then(data => {
            if (data.success && data.items.length > 0) {
              data.items.forEach(item => {
                const card = InboxModule._createPendienteCard(item);
                if (container) container.appendChild(card);
              });
              
              const counter = document.querySelector('.pendiente-counter .counter-number');
              if (counter) {
                const total = parseInt(counter.textContent) + data.items.length;
                counter.textContent = total;
              }
              
              if (!data.has_more) {
                this.style.display = 'none';
              }
            }
            this.disabled = false;
          })
          .catch(() => {
            this.disabled = false;
          });
        });
      }
    },

    // ========== QUICK ADD FORM ==========
    initQuickAddForm: function() {
      const form = document.getElementById('quickAddForm');
      if (form) {
        form.addEventListener('submit', function(e) {
          // El formulario se envía normalmente con POST
          // Solo prevenimos si hay validación adicional
        });
      }
    },

    _createPendienteCard: function(item) {
      const div = document.createElement('div');
      div.className = 'pendiente-card';
      div.dataset.id = item.id;
      div.dataset.title = item.title;
      
      div.innerHTML = `
        ${item.priority ? `<span class="priority-indicator priority-${item.priority}"></span>` : ''}
        <div class="pendiente-header">
          <div class="pendiente-title">${Utils.escapeHtml(item.title)}</div>
          <span class="pendiente-badge">
            <i class="fas fa-clock" aria-hidden="true"></i>
            ${item.time_ago || 'Reciente'}
          </span>
        </div>
        ${item.description ? `<div class="pendiente-desc">${Utils.escapeHtml(item.description)}</div>` : ''}
        <div class="pendiente-meta">
          <span class="meta-item">
            <i class="fas fa-user" aria-hidden="true"></i>
            ${Utils.escapeHtml(item.created_by || 'Sistema')}
          </span>
          <span class="meta-item">
            <i class="fas fa-calendar-alt" aria-hidden="true"></i>
            ${item.created_at || ''}
          </span>
        </div>
        <div class="pendiente-actions">
          <button type="button" class="btn btn-sm btn-quick-accionable btn-quick-classify" data-id="${item.id}" data-category="accionable">
            <i class="fas fa-check-circle" aria-hidden="true"></i> Accionable
          </button>
          <button type="button" class="btn btn-sm btn-quick-no-accionable btn-quick-classify" data-id="${item.id}" data-category="no_accionable">
            <i class="fas fa-times-circle" aria-hidden="true"></i> No Accionable
          </button>
          <button type="button" class="btn btn-sm btn-quick-delete admin-btn-delete" data-id="${item.id}" data-title="${Utils.escapeHtml(item.title)}">
            <i class="fas fa-trash" aria-hidden="true"></i>
          </button>
        </div>
        <div class="text-center" style="margin-top:0.5rem;">
          <button type="button" class="btn btn-sm btn-ghost pendiente-toggle" style="font-size:0.6rem;color:var(--gray-400);">
            <i class="fas fa-chevron-down" aria-hidden="true"></i> Más opciones
          </button>
        </div>
        <div class="pendiente-extended" style="display:none;margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--gray-100);">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
            <a href="/events/inbox/process/${item.id}/" class="btn btn-sm btn-ghost" style="justify-content:center;">
              <i class="fas fa-gear" aria-hidden="true"></i> Procesar
            </a>
            <button type="button" class="btn btn-sm btn-ghost" onclick="window.location.href='/events/inbox/process/${item.id}/'" style="justify-content:center;">
              <i class="fas fa-pencil" aria-hidden="true"></i> Editar
            </button>
          </div>
        </div>
      `;
      
      return div;
    }
  };

  // ==========================================
  // MAILBOX MODULE
  // ==========================================
  const MailboxModule = {
    init: function() {
      this.initItemSelection();
      this.initFilter();
      this.initSearch();
      this.initNavigation();
      this.initQuickActions();
      this.initFilterButtons();
    },

    initItemSelection: function() {
      document.querySelectorAll('.mailbox-item').forEach(item => {
        item.addEventListener('click', function() {
          const itemId = this.dataset.itemId;
          if (itemId) {
            document.querySelectorAll('.mailbox-item').forEach(el => el.classList.remove('active'));
            this.classList.add('active');
            window.location.href = `/events/inbox/process/${itemId}/`;
          }
        });
      });
    },

    initFilterButtons: function() {
      const filterBtns = document.querySelectorAll('.mailbox-filter-btn');
      filterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
          filterBtns.forEach(b => b.classList.remove('active'));
          this.classList.add('active');
          const filter = this.dataset.filter;
          MailboxModule.filterByStatus(filter);
        });
      });
    },

    filterByStatus: function(status) {
      const items = document.querySelectorAll('.mailbox-item');
      const filterBtns = document.querySelectorAll('.mailbox-filter-btn');
      
      filterBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === status);
      });

      items.forEach(item => {
        let visible = true;
        if (status === 'pending') {
          visible = item.classList.contains('pending');
        } else if (status === 'processed') {
          visible = item.classList.contains('processed');
        }
        item.style.display = visible ? 'block' : 'none';
      });
    },

    initFilter: function() {
      // Los filtros ahora se manejan con los botones .mailbox-filter-btn
      // Esta función se mantiene por compatibilidad
    },

    initSearch: function() {
      const searchInput = document.getElementById('itemSearch');
      if (searchInput) {
        searchInput.addEventListener('keyup', function() {
          const term = this.value.toLowerCase();
          document.querySelectorAll('.mailbox-item').forEach(item => {
            const title = item.querySelector('.mailbox-item-title')?.textContent?.toLowerCase() || '';
            const preview = item.querySelector('.mailbox-item-preview')?.textContent?.toLowerCase() || '';
            const visible = title.includes(term) || preview.includes(term);
            item.style.display = visible ? 'block' : 'none';
          });
        });
      }
    },

    initNavigation: function() {
      const prevBtn = document.getElementById('prevBtn');
      const nextBtn = document.getElementById('nextBtn');
      
      // Obtener datos desde el contenedor
      const container = document.querySelector('.mailbox-layout');
      if (!container) return;
      
      const currentId = parseInt(container.dataset.currentId || '0');
      const itemIds = JSON.parse(container.dataset.itemIds || '[]');

      if (prevBtn && currentId && itemIds.length) {
        prevBtn.addEventListener('click', function() {
          const currentIndex = itemIds.indexOf(currentId);
          if (currentIndex > 0) {
            window.location.href = `/events/inbox/process/${itemIds[currentIndex - 1]}/`;
          }
        });
        // Actualizar estado del botón
        const currentIndex = itemIds.indexOf(currentId);
        prevBtn.disabled = currentIndex <= 0;
      }

      if (nextBtn && currentId && itemIds.length) {
        nextBtn.addEventListener('click', function() {
          const currentIndex = itemIds.indexOf(currentId);
          if (currentIndex < itemIds.length - 1) {
            window.location.href = `/events/inbox/process/${itemIds[currentIndex + 1]}/`;
          }
        });
        // Actualizar estado del botón
        const currentIndex = itemIds.indexOf(currentId);
        nextBtn.disabled = currentIndex >= itemIds.length - 1;
      }
    },

    initQuickActions: function() {
      document.querySelectorAll('.mailbox-detail-actions .btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const action = this.classList.contains('btn-success') ? 'process' :
                        this.classList.contains('btn-warning') ? 'archive' :
                        this.classList.contains('btn-danger') ? 'delete' : null;
          if (!action) return;

          const itemId = document.querySelector('input[name="item_id"]')?.value;
          if (!itemId) return;

          const actions = {
            process: { confirm: '¿Marcar este item como procesado?', value: 'reference' },
            archive: { confirm: '¿Archivar este item?', value: 'reference' },
            delete: { confirm: '¿Eliminar permanentemente este item?', value: 'delete' }
          };

          const config = actions[action];
          if (!config) return;

          if (confirm(config.confirm)) {
            const form = document.createElement('form');
            form.method = 'POST';
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            form.innerHTML = `
              <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
              <input type="hidden" name="action" value="${config.value}">
              <input type="hidden" name="item_id" value="${itemId}">
            `;
            document.body.appendChild(form);
            form.action = window.location.href;
            form.submit();
          }
        });
      });
    },

    // Función para seleccionar item programáticamente
    selectItem: function(itemId) {
      document.querySelectorAll('.mailbox-item').forEach(el => el.classList.remove('active'));
      const item = document.querySelector(`.mailbox-item[data-item-id="${itemId}"]`);
      if (item) {
        item.classList.add('active');
        window.location.href = `/events/inbox/process/${itemId}/`;
      }
    }
  };

  // Exponer funciones de Mailbox para uso global
  window.selectItem = function(itemId) {
    if (window.MailboxModule) {
      window.MailboxModule.selectItem(itemId);
    } else {
      window.location.href = `/events/inbox/process/${itemId}/`;
    }
  };

  window.filterByStatus = function(status) {
    const items = document.querySelectorAll('.mailbox-item');
    const filterBtns = document.querySelectorAll('.mailbox-filter-btn');
    
    filterBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.filter === status);
    });

    items.forEach(item => {
      let visible = true;
      if (status === 'pending') {
        visible = item.classList.contains('pending');
      } else if (status === 'processed') {
        visible = item.classList.contains('processed');
      }
      item.style.display = visible ? 'block' : 'none';
    });
  };

  window.navigateItem = function(direction) {
    const container = document.querySelector('.mailbox-layout');
    if (!container) return;
    
    const currentId = parseInt(container.dataset.currentId || '0');
    const itemIds = JSON.parse(container.dataset.itemIds || '[]');
    
    if (!currentId || !itemIds.length) return;
    
    const currentIndex = itemIds.indexOf(currentId);
    let newIndex = direction === 'next' ? currentIndex + 1 : currentIndex - 1;
    
    if (newIndex >= 0 && newIndex < itemIds.length) {
      window.location.href = `/events/inbox/process/${itemIds[newIndex]}/`;
    }
  };

  window.quickAction = function(action) {
    const itemId = document.querySelector('input[name="item_id"]')?.value;
    if (!itemId) return;

    const actions = {
      process: { confirm: '¿Marcar este item como procesado?', value: 'reference' },
      archive: { confirm: '¿Archivar este item?', value: 'reference' },
      delete: { confirm: '¿Eliminar permanentemente este item?', value: 'delete' }
    };

    const config = actions[action];
    if (!config) return;

    if (confirm(config.confirm)) {
      const form = document.createElement('form');
      form.method = 'POST';
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
      form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
        <input type="hidden" name="action" value="${config.value}">
        <input type="hidden" name="item_id" value="${itemId}">
      `;
      document.body.appendChild(form);
      form.action = window.location.href;
      form.submit();
    }
  };

  // ==========================================
  // MANAGEMENT PANEL MODULE
  // ==========================================
  const ManagementPanelModule = {
    init: function() {
      this.autoRefreshInterval = null;
      this.currentInteractionId = null;
      this.initRefresh();
      this.initAutoProcessing();
      this.initQueueControls();
      this.initSettings();
      this.initModals();
    },

    initRefresh: function() {
      const refreshBtn = document.getElementById('btn-refresh');
      if (refreshBtn) {
        refreshBtn.addEventListener('click', () => this.loadQueueData());
      }
    },

    initAutoProcessing: function() {
      const pauseBtn = document.getElementById('btn-pause-auto');
      if (pauseBtn) {
        pauseBtn.addEventListener('click', () => this.toggleAutoProcessing());
      }
      // Iniciar auto-refresh
      this.startAutoRefresh();
    },

    initQueueControls: function() {
      // Delegación de eventos para los botones de colas
      document.querySelectorAll('[data-queue]').forEach(btn => {
        btn.addEventListener('click', function() {
          const queueType = this.dataset.queue;
          const action = this.dataset.action;
          if (queueType && action) {
            ManagementPanelModule.processQueue(queueType, action);
          }
        });
      });
    },

    initSettings: function() {
      const settings = ['auto-email-processing', 'auto-call-queue', 'auto-chat-routing', 'processing-interval', 'max-concurrent'];
      settings.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.addEventListener('change', () => this.updateSettings());
        }
      });
    },

    initModals: function() {
      // Asignar función de confirmación a nivel global
      window.confirmAssignment = function() {
        ManagementPanelModule.confirmAssignment();
      };
      window.markAsResolved = function() {
        ManagementPanelModule.markAsResolved();
      };
    },

    loadQueueData: function() {
      const url = '/events/inbox/management/api/queue-data/';
      fetch(url, {
        method: 'GET',
        headers: {
          'X-CSRFToken': Utils.getCookie('csrftoken'),
          'Content-Type': 'application/json'
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          this.updateMetrics(data.data);
        }
      })
      .catch(error => console.error('Error loading queue data:', error));

      // Cargar colas específicas
      this.loadQueue('email', 'email-queue', document.getElementById('email-queue-count'));
      this.loadQueue('call', 'call-queue', document.getElementById('call-queue-count'));
      this.loadQueue('chat', 'chat-queue', document.getElementById('chat-queue-count'));
    },

    loadQueue: function(type, containerId, countEl) {
      const url = `/events/inbox/management/api/${type}-queue/`;
      const container = document.getElementById(containerId);
      if (!container) return;

      fetch(url, {
        method: 'GET',
        headers: {
          'X-CSRFToken': Utils.getCookie('csrftoken'),
          'Content-Type': 'application/json'
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          if (data.data.length === 0) {
            container.innerHTML = `<div class="text-center text-muted py-3">No hay ${type === 'email' ? 'emails' : type === 'call' ? 'llamadas' : 'chats'} pendientes</div>`;
            if (countEl) countEl.textContent = '0';
            return;
          }

          const typeLabels = { email: 'Email', call: 'Call', chat: 'Chat' };
          container.innerHTML = data.data.map(item => `
            <div class="queue-item ${type} ${item.priority === 'alta' ? 'high-priority' : ''}" data-interaction-id="${item.id}" data-type="${type}">
              <div class="flex justify-between items-start">
                <div class="flex-1">
                  <div class="queue-item-title">${Utils.escapeHtml(item.title)}</div>
                  <div class="queue-item-meta">${Utils.escapeHtml(item.sender || item.caller || item.customer || '')}</div>
                  ${item.waitTime ? `<div class="queue-item-meta text-warning">Wait: ${item.waitTime}</div>` : ''}
                  ${item.messages ? `<div class="queue-item-meta text-info">${item.messages} messages</div>` : ''}
                </div>
                <div class="text-right">
                  <span class="queue-item-badge ${item.priority === 'urgente' ? 'badge-danger' : item.priority === 'alta' ? 'badge-warning' : 'badge-secondary'}">${item.priority || 'media'}</span>
                  <span class="status-indicator ${item.status === 'active' ? 'active' : item.status === 'paused' ? 'paused' : 'pending'}"></span>
                </div>
              </div>
              <div class="queue-item-meta">${item.time || ''}</div>
            </div>
          `).join('');

          // Añadir evento de click a los items de cola
          container.querySelectorAll('.queue-item').forEach(el => {
            el.addEventListener('click', function() {
              const id = this.dataset.interactionId;
              const type = this.dataset.type;
              if (id && type) {
                ManagementPanelModule.showInteractionDetails(id, type);
              }
            });
          });

          if (countEl) countEl.textContent = data.data.length;
        }
      })
      .catch(error => {
        container.innerHTML = `<div class="text-center text-danger py-3">Error de conexión</div>`;
      });
    },

    updateMetrics: function(data) {
      const metrics = {
        'active-items': data.active,
        'pending-items': data.pending,
        'emails-count': data.emails,
        'calls-count': data.calls,
        'chats-count': data.chats,
        'email-queue-count': data.emails,
        'call-queue-count': data.calls,
        'chat-queue-count': data.chats
      };

      Object.entries(metrics).forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      });
    },

    processQueue: function(queueType, action) {
      const confirmMessages = {
        email: { process: '¿Procesar automáticamente la cola de emails?', pause: '¿Pausar cola de emails?' },
        call: { activate: '¿Activar cola de llamadas entrantes?', pause: '¿Pausar cola de llamadas?' },
        chat: { process: '¿Procesar automáticamente la cola de chats?', pause: '¿Pausar cola de chats?' }
      };

      const msg = confirmMessages[queueType]?.[action];
      if (msg && !confirm(msg)) return;

      fetch('/events/inbox/management/api/process-queue/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': Utils.getCookie('csrftoken'),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ queue_type: queueType, action: action })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          HeaderModule.showNotification(`Cola ${queueType} procesada exitosamente`, 'success');
          this.loadQueueData();
        } else {
          HeaderModule.showNotification('Error: ' + (data.error || 'Error al procesar'), 'error');
        }
      })
      .catch(() => {
        HeaderModule.showNotification('Error de conexión', 'error');
      });
    },

    toggleAutoProcessing: function() {
      const btn = document.getElementById('btn-pause-auto');
      if (!btn) return;

      const icon = btn.querySelector('i');
      const isPaused = icon.classList.contains('fa-play-circle');
      
      if (isPaused) {
        // Reanudar
        icon.className = 'fas fa-pause-circle';
        btn.innerHTML = '<i class="fas fa-pause-circle" aria-hidden="true"></i> Pause Auto-Processing';
        btn.className = 'btn btn-warning';
        this.startAutoRefresh();
      } else {
        // Pausar
        icon.className = 'fas fa-play-circle';
        btn.innerHTML = '<i class="fas fa-play-circle" aria-hidden="true"></i> Resume Auto-Processing';
        btn.className = 'btn btn-success';
        if (this.autoRefreshInterval) {
          clearInterval(this.autoRefreshInterval);
          this.autoRefreshInterval = null;
        }
      }
    },

    updateSettings: function() {
      const formData = new FormData();
      const settings = ['auto-email-processing', 'auto-call-queue', 'auto-chat-routing', 'processing-interval', 'max-concurrent'];
      settings.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          formData.append(id, el.type === 'checkbox' ? el.checked : el.value);
        }
      });

      fetch('/events/inbox/management/api/update-settings/', {
        method: 'POST',
        headers: { 'X-CSRFToken': Utils.getCookie('csrftoken') },
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          HeaderModule.showNotification('Configuración actualizada', 'success');
        }
      })
      .catch(error => console.error('Error updating settings:', error));
    },

    startAutoRefresh: function() {
      if (this.autoRefreshInterval) clearInterval(this.autoRefreshInterval);
      this.autoRefreshInterval = setInterval(() => this.loadQueueData(), 30000);
    },

    showInteractionDetails: function(id, type) {
      this.currentInteractionId = id;
      const title = { email: 'Email Details', call: 'Call Details', chat: 'Chat Details' }[type] || 'Details';
      const body = document.getElementById('interactionModalBody');
      if (body) {
        body.innerHTML = `<div class="text-center text-muted py-4">Detalles de ${title.toLowerCase()} para ID ${id}</div>`;
      }
      const label = document.getElementById('interactionModalLabel');
      if (label) label.textContent = title;
      
      // Guardar ID para acciones
      document.querySelector('[data-interaction-id]')?.setAttribute('data-interaction-id', id);
      
      openModal('interactionModal');
    },

    confirmAssignment: function() {
      const agent = document.getElementById('agent-select')?.value;
      if (!agent) {
        HeaderModule.showNotification('Por favor selecciona un agente', 'warning');
        return;
      }

      const interactionId = this.currentInteractionId || document.querySelector('[data-interaction-id]')?.dataset.interactionId;
      if (!interactionId) {
        HeaderModule.showNotification('No hay interacción seleccionada', 'warning');
        return;
      }

      const formData = new FormData();
      formData.append('interaction_id', interactionId);
      formData.append('agent_type', agent);
      formData.append('priority', document.getElementById('priority-select')?.value || 'media');
      formData.append('notes', document.getElementById('notes')?.value || '');

      fetch('/events/inbox/management/api/assign-agent/', {
        method: 'POST',
        headers: { 'X-CSRFToken': Utils.getCookie('csrftoken') },
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          HeaderModule.showNotification(`Asignado a ${agent}`, 'success');
          this.loadQueueData();
          closeModal('interactionModal');
          closeModal('assignModal');
        } else {
          HeaderModule.showNotification('Error: ' + (data.error || 'Error al asignar'), 'error');
        }
      })
      .catch(() => {
        HeaderModule.showNotification('Error de conexión', 'error');
      });
    },

    markAsResolved: function() {
      const interactionId = this.currentInteractionId || document.querySelector('[data-interaction-id]')?.dataset.interactionId;
      if (!interactionId) {
        HeaderModule.showNotification('No hay interacción seleccionada', 'warning');
        return;
      }

      const resolutionNotes = prompt('Notas de resolución (opcional):', '');
      const formData = new FormData();
      formData.append('interaction_id', interactionId);
      if (resolutionNotes) formData.append('resolution_notes', resolutionNotes);

      fetch('/events/inbox/management/api/mark-resolved/', {
        method: 'POST',
        headers: { 'X-CSRFToken': Utils.getCookie('csrftoken') },
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          HeaderModule.showNotification('Interacción marcada como resuelta', 'success');
          this.loadQueueData();
          closeModal('interactionModal');
        } else {
          HeaderModule.showNotification('Error: ' + (data.error || 'Error al marcar como resuelta'), 'error');
        }
      })
      .catch(() => {
        HeaderModule.showNotification('Error de conexión', 'error');
      });
    }
  };

  // Exponer ManagementPanel para uso en inline
  window.ManagementPanel = ManagementPanelModule;
  window.MailboxModule = MailboxModule;

  // ==========================================
  // ALERTS MODULE
  // ==========================================
  const AlertsModule = {
    init: function() {
      this.initDismiss();
      this.initAutoDismiss();
    },

    initDismiss: function() {
      const dismissBtns = document.querySelectorAll('.alert-dismiss');
      dismissBtns.forEach(btn => {
        btn.addEventListener('click', function() {
          const alert = this.closest('.alert');
          if (alert) {
            alert.classList.add('dismissing');
            setTimeout(() => {
              alert.remove();
              AlertsModule.checkEmpty();
            }, 300);
          }
        });
      });
    },

    initAutoDismiss: function() {
      const successAlerts = document.querySelectorAll('.alert-success');
      successAlerts.forEach(alert => {
        setTimeout(() => {
          if (alert.parentNode) {
            alert.classList.add('dismissing');
            setTimeout(() => {
              alert.remove();
              AlertsModule.checkEmpty();
            }, 300);
          }
        }, 5000);
      });
    },

    checkEmpty: function() {
      const container = document.getElementById('alertsContainer');
      if (container && container.children.length === 0) {
        container.style.display = 'none';
      }
    }
  };

  // ==========================================
  // GLOBAL FUNCTIONS (for inline usage)
  // ==========================================
  window.openModal = function(id) {
    const modal = document.getElementById(id);
    if (modal) Utils.addClass(modal, 'show');
  };

  window.closeModal = function(id) {
    const modal = document.getElementById(id);
    if (modal) Utils.removeClass(modal, 'show');
  };

  window.deleteInboxItem = function(itemId, title) {
    if (confirm(`¿Estás seguro de eliminar el item "${title}"? Esta acción no se puede deshacer.`)) {
      const form = document.createElement('form');
      form.method = 'POST';
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
      form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
        <input type="hidden" name="action" value="delete">
      `;
      document.body.appendChild(form);
      form.action = `/events/inbox/process/${itemId}/`;
      form.submit();
    }
  };

  window.markAsProcessed = function(itemId) {
    if (!confirm('¿Marcar este item como procesado?')) return;
    const form = document.createElement('form');
    form.method = 'POST';
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    form.innerHTML = `
      <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
      <input type="hidden" name="action" value="reference">
    `;
    document.body.appendChild(form);
    form.action = `/events/inbox/process/${itemId}/`;
    form.submit();
  };

  window.quickClassify = function(itemId, category) {
    const label = category === 'accionable' ? 'Accionable' : 
                  category === 'no_accionable' ? 'No Accionable' : 'Pendiente';
    if (!confirm(`¿Marcar este item como "${label}"?`)) return;
    
    const form = document.createElement('form');
    form.method = 'POST';
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    form.innerHTML = `
      <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
      <input type="hidden" name="action" value="categorize">
      <input type="hidden" name="gtd_category" value="${category}">
    `;
    document.body.appendChild(form);
    form.action = `/events/inbox/process/${itemId}/`;
    form.submit();
  };

  window.togglePendienteExtendido = function(btn) {
    const card = btn.closest('.pendiente-card');
    if (!card) return;
    const extended = card.querySelector('.pendiente-extended');
    if (!extended) return;
    
    const isHidden = extended.style.display === 'none' || !extended.style.display;
    extended.style.display = isHidden ? 'block' : 'none';
    const icon = btn.querySelector('i');
    if (icon) {
      icon.className = isHidden ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
    }
    btn.innerHTML = isHidden ? 
      '<i class="fas fa-chevron-up" aria-hidden="true"></i> Menos opciones' : 
      '<i class="fas fa-chevron-down" aria-hidden="true"></i> Más opciones';
  };

  window.classifyAll = function() {
    if (!confirm('¿Clasificar todos los items pendientes automáticamente?')) return;
    
    const form = document.createElement('form');
    form.method = 'POST';
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    form.innerHTML = `
      <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
      <input type="hidden" name="action" value="classify_all">
    `;
    document.body.appendChild(form);
    form.action = `/events/inbox/bulk-action/`;
    form.submit();
  };

  window.expandAllPendientes = function() {
    const cards = document.querySelectorAll('.pendiente-card');
    const isExpanded = cards[0]?.querySelector('.pendiente-extended')?.style.display === 'block';
    
    cards.forEach(card => {
      const extended = card.querySelector('.pendiente-extended');
      const btn = card.querySelector('.pendiente-toggle');
      if (extended) {
        extended.style.display = isExpanded ? 'none' : 'block';
        if (btn) {
          const icon = btn.querySelector('i');
          if (isExpanded) {
            btn.innerHTML = '<i class="fas fa-chevron-down" aria-hidden="true"></i> Más opciones';
          } else {
            btn.innerHTML = '<i class="fas fa-chevron-up" aria-hidden="true"></i> Menos opciones';
          }
        }
      }
    });
  };

  window.loadMorePendientes = function() {
    const btn = event?.target?.closest('.btn');
    if (btn) btn.disabled = true;
    
    const container = document.getElementById('pendientesContainer');
    if (!container) return;
    const offset = container.querySelectorAll('.pendiente-card').length;
    
    fetch(`/events/inbox/api/pendientes/?offset=${offset}&limit=8`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success && data.items.length > 0) {
        data.items.forEach(item => {
          const card = InboxModule._createPendienteCard(item);
          container.appendChild(card);
        });
        
        const counter = document.querySelector('.pendiente-counter .counter-number');
        if (counter) {
          const total = parseInt(counter.textContent) + data.items.length;
          counter.textContent = total;
        }
        
        if (!data.has_more && btn) {
          btn.style.display = 'none';
        }
      }
      if (btn) btn.disabled = false;
    })
    .catch(() => {
      if (btn) btn.disabled = false;
    });
  };

  window.refreshMailbox = function() {
    window.location.reload();
  };

  window.processQueue = function(queueType, action) {
    if (window.ManagementPanel) {
      window.ManagementPanel.processQueue(queueType, action);
    }
  };

  window.quickAction = function(action) {
    const itemId = document.querySelector('input[name="item_id"]')?.value;
    if (!itemId) return;

    const actions = {
      process: { confirm: '¿Marcar este item como procesado?', value: 'reference' },
      archive: { confirm: '¿Archivar este item?', value: 'reference' },
      delete: { confirm: '¿Eliminar permanentemente este item?', value: 'delete' }
    };

    const config = actions[action];
    if (!config) return;

    if (confirm(config.confirm)) {
      const form = document.createElement('form');
      form.method = 'POST';
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
      form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
        <input type="hidden" name="action" value="${config.value}">
        <input type="hidden" name="item_id" value="${itemId}">
      `;
      document.body.appendChild(form);
      form.action = window.location.href;
      form.submit();
    }
  };

  // ==========================================
  // INIT
  // ==========================================
  document.addEventListener('DOMContentLoaded', function() {
    // Módulos principales
    DropdownManager.init();
    HeaderModule.init();
    SidebarModule.init();
    DashboardModule.init();
    AlertsModule.init();

    // Módulos específicos de Inbox
    if (document.querySelector('.pendiente-card') || document.getElementById('ai-assistant-panel')) {
      InboxModule.init();
    }

    // Módulo de Mailbox
    if (document.querySelector('.mailbox-layout')) {
      MailboxModule.init();
    }

    // Módulo de Management Panel
    if (document.getElementById('btn-refresh') || document.querySelector('.queue-item')) {
      ManagementPanelModule.init();
    }

    // Animar filas de tabla
    document.querySelectorAll('.admin-inbox-row, .panel-row, .inbox-row, tbody tr:not(.empty-state-cell)').forEach((row, index) => {
      if (!row.classList.contains('empty-state-cell')) {
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';
        setTimeout(() => {
          row.style.transition = 'all 0.3s ease-out';
          row.style.opacity = '1';
          row.style.transform = 'translateX(0)';
        }, index * 50);
      }
    });
  });

  // Cleanup on page unload
  window.addEventListener('beforeunload', function() {
    if (ManagementPanelModule.autoRefreshInterval) {
      clearInterval(ManagementPanelModule.autoRefreshInterval);
    }
  });

})();