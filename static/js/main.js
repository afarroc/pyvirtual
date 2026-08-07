/**
 * Management360 - Dashboard JavaScript
 * Funcionalidades: Header dropdowns, Sidebar con anidamiento multinivel,
 * Dashboard stats, tabs, charts, modales, inbox, mailbox, management panel, kanban y eisenhower
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
        document.querySelectorAll(el).forEach(function(e) {
          e.addEventListener(event, handler);
        });
      } else if (el && el.length) {
        el.forEach(function(e) {
          e.addEventListener(event, handler);
        });
      } else if (el) {
        el.addEventListener(event, handler);
      }
    },
    getCookie: function(name) {
      var cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
          var cookie = cookies[i].trim();
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
      document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
          DropdownManager.closeAll();
        }
      });
      document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
          DropdownManager.closeAll();
        }
      });
    },

    toggle: function(trigger, menu) {
      var isOpen = menu.classList.contains('show');
      this.closeAll();
      if (!isOpen) {
        menu.classList.add('show');
        trigger.setAttribute('aria-expanded', 'true');
        this.openDropdown = { trigger: trigger, menu: menu };
      }
    },

    closeAll: function() {
      document.querySelectorAll('.dropdown-menu.show').forEach(function(menu) {
        menu.classList.remove('show');
        var trigger = menu.closest('.dropdown').querySelector('.dropdown-toggle, .avatar, .icon-btn');
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
      var qaToggle = Utils.getElement('#quickActionsToggle');
      var qaMenu = Utils.getElement('#quickActionsMenu');
      if (qaToggle && qaMenu) {
        qaToggle.addEventListener('click', function(e) {
          e.stopPropagation();
          DropdownManager.toggle(qaToggle, qaMenu);
        });
      }

      // Notifications
      var notifToggle = Utils.getElement('#notificationsToggle');
      var notifMenu = Utils.getElement('#notificationsMenu');
      if (notifToggle && notifMenu) {
        notifToggle.addEventListener('click', function(e) {
          e.stopPropagation();
          DropdownManager.toggle(notifToggle, notifMenu);
        });
      }

      // Messages
      var msgToggle = Utils.getElement('#messagesToggle');
      var msgMenu = Utils.getElement('#messagesMenu');
      if (msgToggle && msgMenu) {
        msgToggle.addEventListener('click', function(e) {
          e.stopPropagation();
          DropdownManager.toggle(msgToggle, msgMenu);
        });
      }

      // Profile
      var profileToggle = Utils.getElement('#profileToggle');
      var profileMenu = Utils.getElement('#profileMenu');
      if (profileToggle && profileMenu) {
        profileToggle.addEventListener('click', function(e) {
          e.stopPropagation();
          DropdownManager.toggle(profileToggle, profileMenu);
        });
      }
    },

    initSearch: function() {
      if (!this.searchInput) return;

      // Keyboard shortcut: Cmd+K or Ctrl+K
      document.addEventListener('keydown', function(e) {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          HeaderModule.searchInput.focus();
          HeaderModule.searchInput.select();
        }
      });

      // Show clear button when typing
      this.searchInput.addEventListener('input', function() {
        if (HeaderModule.searchInput.value.length > 0) {
          Utils.addClass(HeaderModule.searchBar, 'has-value');
        } else {
          Utils.removeClass(HeaderModule.searchBar, 'has-value');
        }
      });

      // Clear search
      if (this.searchClear) {
        this.searchClear.addEventListener('click', function() {
          HeaderModule.searchInput.value = '';
          Utils.removeClass(HeaderModule.searchBar, 'has-value');
          HeaderModule.searchInput.focus();
        });
      }
    },

    initNotifications: function() {
      // Mark all as read
      var markBtn = Utils.getElement('#markAllRead');
      if (markBtn) {
        markBtn.addEventListener('click', function() {
          var items = Utils.getElements('.notif-item.unread');
          items.forEach(function(item) { item.classList.remove('unread'); });
          var badge = Utils.getElement('#notifBadge');
          if (badge) badge.textContent = '0';
          
          HeaderModule.showNotification('All notifications marked as read', 'success');
        });
      }

      // Dismiss individual notification
      var dismissBtns = Utils.getElements('.notif-dismiss');
      dismissBtns.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          var item = btn.closest('.notif-item');
          if (item) {
            item.style.transition = 'all 0.3s ease';
            item.style.opacity = '0';
            item.style.transform = 'translateX(20px)';
            setTimeout(function() { item.remove(); }, 300);

            var badge = Utils.getElement('#notifBadge');
            if (badge) {
              var unread = Utils.getElements('.notif-item.unread').length;
              badge.textContent = unread;
              if (unread === 0) badge.textContent = '0';
            }
          }
        });
      });
    },

    initMessages: function() {
      var msgItems = Utils.getElements('.msg-item');
      msgItems.forEach(function(item) {
        item.addEventListener('click', function() {
          var unread = item.querySelector('.msg-unread');
          if (unread) unread.remove();
          var badge = document.querySelector('.icon-btn .fa-envelope')?.closest('.icon-btn')?.querySelector('.badge');
          if (badge) {
            var count = parseInt(badge.textContent) || 0;
            if (count > 0) {
              badge.textContent = count - 1;
              if (badge.textContent === '0') badge.style.display = 'none';
            }
          }
        });
      });
    },

    initMobileMenu: function() {
      var menuToggle = Utils.getElement('#menuToggle');
      var sidebar = Utils.getElement('#mainSidebar');

      if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function(e) {
          e.stopPropagation();
          Utils.toggleClass(sidebar, 'open');
          var isOpen = Utils.hasClass(sidebar, 'open');
          menuToggle.setAttribute('aria-expanded', isOpen);
        });

        document.addEventListener('click', function(e) {
          if (window.innerWidth <= 768) {
            var isInside = sidebar.contains(e.target) || menuToggle.contains(e.target);
            if (!isInside) {
              Utils.removeClass(sidebar, 'open');
              menuToggle.setAttribute('aria-expanded', 'false');
            }
          }
        });

        window.addEventListener('resize', function() {
          if (window.innerWidth > 768) {
            Utils.removeClass(sidebar, 'open');
            menuToggle.setAttribute('aria-expanded', 'false');
          }
        });
      }
    },

    showNotification: function(message, type) {
      var types = {
        success: { icon: 'fa-check-circle', color: '#22c55e' },
        error: { icon: 'fa-exclamation-circle', color: '#ef4444' },
        warning: { icon: 'fa-exclamation-triangle', color: '#f59e0b' },
        info: { icon: 'fa-info-circle', color: '#0ea5e9' }
      };
      var config = types[type] || types.info;
      var notification = document.createElement('div');
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
      setTimeout(function() { notification.style.transform = 'translateX(0)'; }, 50);
      setTimeout(function() {
        notification.style.transform = 'translateX(120%)';
        setTimeout(function() { notification.remove(); }, 400);
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
      var toggles = document.querySelectorAll('.sidebar-nav-item.has-dropdown > .sidebar-nav-link.dropdown-toggle');
      
      toggles.forEach(function(toggle) {
        toggle.removeEventListener('click', SidebarModule.handleToggle);
        toggle.addEventListener('click', SidebarModule.handleToggle);
      });
    },

    handleToggle: function(e) {
      e.preventDefault();
      e.stopPropagation();

      var parentItem = this.closest('.sidebar-nav-item.has-dropdown');
      var parentUl = parentItem.closest('ul');
      
      if (parentUl) {
        var siblings = parentUl.querySelectorAll(':scope > .sidebar-nav-item.has-dropdown');
        siblings.forEach(function(sibling) {
          if (sibling !== parentItem && Utils.hasClass(sibling, 'open')) {
            Utils.removeClass(sibling, 'open');
            var siblingToggle = sibling.querySelector('.dropdown-toggle');
            if (siblingToggle) siblingToggle.setAttribute('aria-expanded', 'false');
          }
        });
      }

      Utils.toggleClass(parentItem, 'open');
      var isOpen = Utils.hasClass(parentItem, 'open');
      this.setAttribute('aria-expanded', isOpen);
    },

    initActiveStates: function() {
      var activeItems = document.querySelectorAll('.sidebar-dropdown .sidebar-nav-item.active');
      activeItems.forEach(function(item) {
        var parent = item.closest('.sidebar-nav-item.has-dropdown');
        while (parent) {
          Utils.addClass(parent, 'open');
          var toggle = parent.querySelector('.dropdown-toggle');
          if (toggle) toggle.setAttribute('aria-expanded', 'true');
          parent = parent.parentElement?.closest('.sidebar-nav-item.has-dropdown');
        }
      });
    },

    initNavigationLinks: function() {
      var links = Utils.getElements('.sidebar-nav a:not(.dropdown-toggle)');
      links.forEach(function(link) {
        link.addEventListener('click', function(e) {
          var li = link.closest('li');
          if (li) {
            var parentUl = li.closest('ul');
            if (parentUl) {
              var allLis = parentUl.querySelectorAll('li');
              allLis.forEach(function(l) { Utils.removeClass(l, 'active'); });
              Utils.addClass(li, 'active');
            }
            
            var sidebar = Utils.getElement('#mainSidebar');
            var menuToggle = Utils.getElement('#menuToggle');
            if (window.innerWidth <= 768 && sidebar) {
              Utils.removeClass(sidebar, 'open');
              if (menuToggle) menuToggle.setAttribute('aria-expanded', 'false');
            }
          }
        });
      });
    },

    initUpgrade: function() {
      var upgradeBtn = Utils.getElement('#upgradeBtn');
      if (upgradeBtn) {
        upgradeBtn.addEventListener('click', function() {
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
      var statValues = Utils.getElements('.stat-value');
      statValues.forEach(function(el) {
        var originalText = el.textContent.trim();
        var isCurrency = originalText.includes('$');
        var isNumber = !isCurrency && !isNaN(parseFloat(originalText.replace(/,/g, '')));

        if (isCurrency) {
          var num = parseFloat(originalText.replace(/[$,K]/g, ''));
          if (!isNaN(num)) {
            DashboardModule.animateCounter(el, 0, num * 1000, 1500, function(val) {
              if (val >= 1000) {
                return '$' + (val / 1000).toFixed(1) + 'K';
              }
              return '$' + val.toFixed(0);
            });
          }
        } else if (isNumber) {
          var num = parseInt(originalText.replace(/,/g, ''));
          if (!isNaN(num)) {
            DashboardModule.animateCounter(el, 0, num, 1500);
          }
        }
      });

      // Animate stat-number elements
      var statNumbers = document.querySelectorAll('.stat-number');
      statNumbers.forEach(function(el) {
        var text = el.textContent;
        var num = parseInt(text.replace(/,/g, ''));
        if (!isNaN(num) && num > 0) {
          var current = 0;
          var duration = 1000;
          var step = Math.max(1, Math.floor(num / 60));
          var interval = duration / (num / step);
          var timer = setInterval(function() {
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
      var startTime = performance.now();
      var update = function(currentTime) {
        var elapsed = currentTime - startTime;
        var progress = Math.min(elapsed / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        var current = start + (end - start) * eased;

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
      var periodBtns = Utils.getElements('[data-period]');
      periodBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
          periodBtns.forEach(function(b) { Utils.removeClass(b, 'active'); });
          Utils.addClass(btn, 'active');

          var bars = Utils.getElements('.bar');
          bars.forEach(function(bar) {
            var newHeight = 20 + Math.random() * 75;
            bar.style.height = newHeight + '%';
            var span = bar.querySelector('span');
            if (span) span.textContent = Math.round(newHeight);
          });
        });
      });
    },

    initTableSort: function() {
      var headers = Utils.getElements('.table th[data-sort]');
      var sortDirection = {};

      headers.forEach(function(header) {
        header.addEventListener('click', function() {
          var key = header.dataset.sort;
          sortDirection[key] = sortDirection[key] === 'asc' ? 'desc' : 'asc';

          var tbody = Utils.getElement('#projectsBody');
          if (!tbody) return;
          var rows = Array.from(tbody.querySelectorAll('tr'));

          rows.sort(function(a, b) {
            var aVal = a.querySelector('td:nth-child(' + (header.cellIndex + 1) + ')')?.textContent.trim() || '';
            var bVal = b.querySelector('td:nth-child(' + (header.cellIndex + 1) + ')')?.textContent.trim() || '';

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

          rows.forEach(function(row) { tbody.appendChild(row); });

          headers.forEach(function(h) {
            var icon = h.querySelector('i');
            if (icon) icon.className = 'fas fa-sort';
          });
          var icon = header.querySelector('i');
          if (icon) {
            icon.className = sortDirection[key] === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down';
          }
        });
      });
    },

    initTabs: function() {
      var tabs = document.querySelectorAll('.tab-btn');
      var contents = document.querySelectorAll('.tab-content');

      tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
          var target = tab.dataset.tab;
          tabs.forEach(function(t) { Utils.removeClass(t, 'active'); });
          Utils.addClass(tab, 'active');
          contents.forEach(function(content) {
            Utils.removeClass(content, 'active');
            if (content.id === 'tab-' + target) {
              Utils.addClass(content, 'active');
            }
          });
          localStorage.setItem('activeTab', target);
        });
      });

      var savedTab = localStorage.getItem('activeTab');
      if (savedTab) {
        var tabToActivate = document.querySelector('.tab-btn[data-tab="' + savedTab + '"]');
        if (tabToActivate) {
          tabToActivate.click();
        }
      }
    },

    initQuickActions: function() {
      var actionBtns = Utils.getElements('.quick-action-btn');
      actionBtns.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.preventDefault();
          var label = btn.querySelector('span')?.textContent || 'Action';
          HeaderModule.showNotification('🚀 ' + label + ' triggered!', 'info');
        });
      });
    },

    initDateRange: function() {
      var btn = Utils.getElement('#dateRangeBtn');
      if (btn) {
        var ranges = ['Today', 'This Week', 'This Month', 'This Quarter', 'This Year'];
        var currentIndex = 2;

        btn.addEventListener('click', function() {
          currentIndex = (currentIndex + 1) % ranges.length;
          btn.innerHTML = '<i class="fas fa-calendar-alt"></i> ' + ranges[currentIndex];
          btn.style.transition = 'all 0.3s ease';
          btn.style.transform = 'scale(0.95)';
          setTimeout(function() {
            btn.style.transform = 'scale(1)';
          }, 200);
        });
      }
    },

    initRefresh: function() {
      var btn = Utils.getElement('#refreshBtn');
      if (btn) {
        btn.addEventListener('click', function() {
          var icon = btn.querySelector('i');
          Utils.addClass(icon, 'fa-spin');
          btn.disabled = true;
          setTimeout(function() {
            Utils.removeClass(icon, 'fa-spin');
            btn.disabled = false;
            HeaderModule.showNotification('Dashboard refreshed successfully!', 'success');
          }, 1500);
        });
      }
    },

    initModalHandlers: function() {
      document.querySelectorAll('.modal-overlay').forEach(function(overlay) {
        overlay.addEventListener('click', function(e) {
          if (e.target === overlay) {
            Utils.removeClass(overlay, 'show');
          }
        });
      });

      document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
          document.querySelectorAll('.modal-overlay.show').forEach(function(modal) {
            Utils.removeClass(modal, 'show');
          });
        }
      });
    },

    initDeleteItem: function() {
      document.addEventListener('click', function(e) {
        var deleteBtn = e.target.closest('.admin-btn-delete, .btn-delete-item, .btn-delete-inbox');
        if (deleteBtn) {
          e.preventDefault();
          var itemId = deleteBtn.dataset.id;
          var title = deleteBtn.dataset.title || 'Item';
          if (window.deleteInboxItem) {
            window.deleteInboxItem(itemId, title);
          } else {
            if (confirm('¿Estás seguro de eliminar el item "' + title + '"? Esta acción no se puede deshacer.')) {
              var form = document.createElement('form');
              form.method = 'POST';
              var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
              form.innerHTML = `
                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
                <input type="hidden" name="action" value="delete">
              `;
              document.body.appendChild(form);
              form.action = '/events/inbox/process/' + itemId + '/';
              form.submit();
            }
          }
        }
      });
    },

    showWelcomeNotification: function() {
      if (!sessionStorage.getItem('welcomeShown')) {
        setTimeout(function() {
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
      var summaryBtn = document.getElementById('ai-refresh-btn');
      var summaryTrigger = document.getElementById('ai-summary-trigger');
      var sendBtn = document.getElementById('ai-send-btn');
      var chatInput = document.getElementById('ai-chat-input');

      if (summaryBtn) {
        summaryBtn.addEventListener('click', function() { InboxModule.aiLoadSummary(); });
      }

      if (summaryTrigger) {
        summaryTrigger.addEventListener('click', function(e) {
          e.preventDefault();
          InboxModule.aiLoadSummary();
        });
      }

      if (sendBtn && chatInput) {
        sendBtn.addEventListener('click', function() { InboxModule.aiSendMessage(); });
        chatInput.addEventListener('keydown', function(e) {
          if (e.key === 'Enter') {
            e.preventDefault();
            InboxModule.aiSendMessage();
          }
        });
      }

      this.aiSummaryUrl = document.querySelector('[data-ai-summary-url]')?.dataset.aiSummaryUrl || 
                          document.querySelector('#ai-summary-trigger')?.dataset.aiSummaryUrl;
      this.aiChatUrl = document.querySelector('[data-ai-chat-url]')?.dataset.aiChatUrl ||
                       document.querySelector('#ai-send-btn')?.dataset.aiChatUrl;
    },

    aiLoadSummary: async function() {
      var url = this.aiSummaryUrl || '/events/inbox/ai/summary/';
      var placeholder = document.getElementById('ai-placeholder');
      var content = document.getElementById('ai-analysis-content');
      var text = document.getElementById('ai-analysis-text');
      var badge = document.getElementById('ai-source-badge');
      var loading = document.getElementById('ai-loading');
      var refreshIcon = document.getElementById('ai-refresh-icon');
      var refreshBtn = document.getElementById('ai-refresh-btn');

      this._setAILoading(true, loading, placeholder, refreshIcon, refreshBtn);
      if (content) content.style.display = 'none';

      try {
        var resp = await fetch(url, {
          headers: {
            'X-CSRFToken': Utils.getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        var data = await resp.json();
        if (data.success) {
          if (text) text.textContent = data.analysis;
          if (badge) {
            badge.textContent = data.source === 'ollama' ? 'Ollama' : 'Análisis estático';
            badge.className = 'status ' + (data.source === 'ollama' ? 'status-active' : 'status-pending');
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
      var url = this.aiChatUrl || '/events/inbox/ai/chat/';
      var input = document.getElementById('ai-chat-input');
      var sendBtn = document.getElementById('ai-send-btn');
      var message = input?.value?.trim();
      if (!message) return;

      if (input) input.value = '';
      if (input) input.disabled = true;
      if (sendBtn) sendBtn.disabled = true;

      this._appendChat('user', message);

      var typingId = 'typing-' + Date.now();
      var zone = document.getElementById('ai-chat-history');
      var typing = document.createElement('div');
      typing.id = typingId;
      typing.className = 'activity-item chat-message';
      typing.style.justifyContent = 'flex-start';
      typing.innerHTML = '<div class="chat-bubble chat-bubble-assistant">' +
        '<span class="spinner-small"></span> Pensando…</div>';
      if (zone) {
        zone.appendChild(typing);
        zone.scrollTop = zone.scrollHeight;
      }

      try {
        var resp = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': Utils.getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify({ message: message })
        });
        var data = await resp.json();
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
      var zone = document.getElementById('ai-chat-history');
      if (!zone) return;
      var isUser = role === 'user';
      var div = document.createElement('div');
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
      var filterBtns = {
        'filterPendientes': 'section-pendientes',
        'filterAccionables': 'section-accionables',
        'filterNoAccionables': 'section-no_accionables',
        'filterProcesados': 'section-procesados'
      };

      var filterPanel = document.getElementById('filterPendientes')?.closest('.section-card') || 
                         document.getElementById('clearFilters')?.closest('.section-card');
      var summaryPanel = document.getElementById('ai-refresh-btn')?.closest('.section-card');
      var aiPanel = document.getElementById('ai-assistant-panel');
      
      var itemSections = {
        'section-pendientes': document.getElementById('section-pendientes'),
        'section-accionables': document.getElementById('section-accionables'),
        'section-no_accionables': document.getElementById('section-no_accionables'),
        'section-procesados': document.getElementById('section-procesados')
      };

      Object.entries(filterBtns).forEach(function(entry) {
        var btnId = entry[0];
        var sectionId = entry[1];
        var btn = document.getElementById(btnId);
        if (btn) {
          btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
            this.classList.add('active');

            Object.values(itemSections).forEach(function(section) {
              if (section) section.style.display = 'none';
            });
            if (filterPanel) filterPanel.style.display = 'block';
            if (summaryPanel) summaryPanel.style.display = 'block';
            if (aiPanel) aiPanel.style.display = 'block';

            var target = itemSections[sectionId];
            if (target) target.style.display = 'block';
          });
        }
      });

      var clearBtn = document.getElementById('clearFilters');
      if (clearBtn) {
        clearBtn.addEventListener('click', function() {
          document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
          Object.values(itemSections).forEach(function(section) {
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
      document.addEventListener('click', function(e) {
        var classifyBtn = e.target.closest('.btn-quick-classify');
        if (classifyBtn) {
          e.preventDefault();
          var itemId = classifyBtn.dataset.id;
          var category = classifyBtn.dataset.category;
          if (!itemId || !category) return;
          
          var label = category === 'accionable' ? 'Accionable' : 
                       category === 'no_accionable' ? 'No Accionable' : 'Pendiente';
          if (!confirm('¿Marcar este item como "' + label + '"?')) return;
          
          if (window.quickClassify) {
            window.quickClassify(itemId, category);
          } else {
            var form = document.createElement('form');
            form.method = 'POST';
            var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            form.innerHTML = `
              <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
              <input type="hidden" name="action" value="categorize">
              <input type="hidden" name="gtd_category" value="${category}">
            `;
            document.body.appendChild(form);
            form.action = '/events/inbox/process/' + itemId + '/';
            form.submit();
          }
        }
      });
    },

    // ========== PENDIENTE TOGGLE ==========
    initPendienteToggle: function() {
      document.addEventListener('click', function(e) {
        var toggleBtn = e.target.closest('.pendiente-toggle');
        if (toggleBtn) {
          e.preventDefault();
          var card = toggleBtn.closest('.pendiente-card');
          if (!card) return;
          var extended = card.querySelector('.pendiente-extended');
          if (!extended) return;
          
          var isHidden = extended.style.display === 'none' || !extended.style.display;
          extended.style.display = isHidden ? 'block' : 'none';
          var icon = toggleBtn.querySelector('i');
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
      var loadBtn = document.getElementById('loadMorePendientes');
      if (loadBtn) {
        loadBtn.addEventListener('click', function() {
          this.disabled = true;
          var container = document.getElementById('pendientesContainer');
          var offset = container?.querySelectorAll('.pendiente-card').length || 0;
          
          fetch('/events/inbox/api/pendientes/?offset=' + offset + '&limit=8', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
          })
          .then(function(response) { return response.json(); })
          .then(function(data) {
            if (data.success && data.items.length > 0) {
              data.items.forEach(function(item) {
                var card = InboxModule._createPendienteCard(item);
                if (container) container.appendChild(card);
              });
              
              var counter = document.querySelector('.pendiente-counter .counter-number');
              if (counter) {
                var total = parseInt(counter.textContent) + data.items.length;
                counter.textContent = total;
              }
              
              if (!data.has_more) {
                this.style.display = 'none';
              }
            }
            this.disabled = false;
          }.bind(this))
          ['catch'](function() {
            this.disabled = false;
          }.bind(this));
        });
      }
    },

    // ========== QUICK ADD FORM ==========
    initQuickAddForm: function() {
      var form = document.getElementById('quickAddForm');
      if (form) {
        form.addEventListener('submit', function(e) {
          // El formulario se envía normalmente con POST
        });
      }
    },

    _createPendienteCard: function(item) {
      var div = document.createElement('div');
      div.className = 'pendiente-card';
      div.dataset.id = item.id;
      div.dataset.title = item.title;
      
      var html = '';
      if (item.priority) {
        html += '<span class="priority-indicator priority-' + item.priority + '"></span>';
      }
      html += `
        <div class="pendiente-header">
          <div class="pendiente-title">${Utils.escapeHtml(item.title)}</div>
          <span class="pendiente-badge">
            <i class="fas fa-clock" aria-hidden="true"></i>
            ${item.time_ago || 'Reciente'}
          </span>
        </div>
        ${item.description ? '<div class="pendiente-desc">' + Utils.escapeHtml(item.description) + '</div>' : ''}
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
      div.innerHTML = html;
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
      this.initDataAttributes();
    },

    initItemSelection: function() {
      document.querySelectorAll('.mailbox-item').forEach(function(item) {
        item.addEventListener('click', function() {
          var itemId = this.dataset.itemId;
          if (itemId) {
            document.querySelectorAll('.mailbox-item').forEach(function(el) { el.classList.remove('active'); });
            this.classList.add('active');
            window.location.href = '/events/inbox/process/' + itemId + '/';
          }
        });
      });
    },

    initFilterButtons: function() {
      var filterBtns = document.querySelectorAll('.mailbox-filter-btn');
      filterBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
          filterBtns.forEach(function(b) { b.classList.remove('active'); });
          this.classList.add('active');
          var filter = this.dataset.filter;
          MailboxModule.filterByStatus(filter);
        });
      });
    },

    initDataAttributes: function() {
      var container = document.querySelector('.mailbox-layout');
      if (!container) return;

      if (!container.dataset.currentId) {
        container.dataset.currentId = '0';
      }
      if (!container.dataset.itemIds) {
        container.dataset.itemIds = '[]';
      }
    },

    filterByStatus: function(status) {
      var items = document.querySelectorAll('.mailbox-item');
      var filterBtns = document.querySelectorAll('.mailbox-filter-btn');
      
      filterBtns.forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.filter === status);
      });

      items.forEach(function(item) {
        var visible = true;
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
    },

    initSearch: function() {
      var searchInput = document.getElementById('itemSearch');
      if (searchInput) {
        searchInput.addEventListener('keyup', function() {
          var term = this.value.toLowerCase();
          document.querySelectorAll('.mailbox-item').forEach(function(item) {
            var title = item.querySelector('.mailbox-item-title')?.textContent?.toLowerCase() || '';
            var preview = item.querySelector('.mailbox-item-preview')?.textContent?.toLowerCase() || '';
            var visible = title.includes(term) || preview.includes(term);
            item.style.display = visible ? 'block' : 'none';
          });
        });
      }
    },

    initNavigation: function() {
      var prevBtn = document.getElementById('prevBtn');
      var nextBtn = document.getElementById('nextBtn');
      
      var container = document.querySelector('.mailbox-layout');
      if (!container) return;
      
      var currentId = parseInt(container.dataset.currentId || '0');
      var itemIds = JSON.parse(container.dataset.itemIds || '[]');

      if (prevBtn && currentId && itemIds.length) {
        prevBtn.addEventListener('click', function() {
          var currentIndex = itemIds.indexOf(currentId);
          if (currentIndex > 0) {
            window.location.href = '/events/inbox/process/' + itemIds[currentIndex - 1] + '/';
          }
        });
        var currentIndex = itemIds.indexOf(currentId);
        prevBtn.disabled = currentIndex <= 0;
      }

      if (nextBtn && currentId && itemIds.length) {
        nextBtn.addEventListener('click', function() {
          var currentIndex = itemIds.indexOf(currentId);
          if (currentIndex < itemIds.length - 1) {
            window.location.href = '/events/inbox/process/' + itemIds[currentIndex + 1] + '/';
          }
        });
        var currentIndex = itemIds.indexOf(currentId);
        nextBtn.disabled = currentIndex >= itemIds.length - 1;
      }
    },

    initQuickActions: function() {
      document.querySelectorAll('.mailbox-detail-actions .btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var action = this.classList.contains('btn-success') ? 'process' :
                        this.classList.contains('btn-warning') ? 'archive' :
                        this.classList.contains('btn-danger') ? 'delete' : null;
          if (!action) return;

          var itemId = document.querySelector('input[name="item_id"]')?.value;
          if (!itemId) return;

          var actions = {
            process: { confirm: '¿Marcar este item como procesado?', value: 'reference' },
            archive: { confirm: '¿Archivar este item?', value: 'reference' },
            delete: { confirm: '¿Eliminar permanentemente este item?', value: 'delete' }
          };

          var config = actions[action];
          if (!config) return;

          if (confirm(config.confirm)) {
            var form = document.createElement('form');
            form.method = 'POST';
            var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
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

    selectItem: function(itemId) {
      document.querySelectorAll('.mailbox-item').forEach(function(el) { el.classList.remove('active'); });
      var item = document.querySelector('.mailbox-item[data-item-id="' + itemId + '"]');
      if (item) {
        item.classList.add('active');
        window.location.href = '/events/inbox/process/' + itemId + '/';
      }
    }
  };

  // Exponer funciones de Mailbox para uso global
  window.selectItem = function(itemId) {
    if (window.MailboxModule) {
      window.MailboxModule.selectItem(itemId);
    } else {
      window.location.href = '/events/inbox/process/' + itemId + '/';
    }
  };

  window.filterByStatus = function(status) {
    var items = document.querySelectorAll('.mailbox-item');
    var filterBtns = document.querySelectorAll('.mailbox-filter-btn');
    
    filterBtns.forEach(function(btn) {
      btn.classList.toggle('active', btn.dataset.filter === status);
    });

    items.forEach(function(item) {
      var visible = true;
      if (status === 'pending') {
        visible = item.classList.contains('pending');
      } else if (status === 'processed') {
        visible = item.classList.contains('processed');
      }
      item.style.display = visible ? 'block' : 'none';
    });
  };

  window.navigateItem = function(direction) {
    var container = document.querySelector('.mailbox-layout');
    if (!container) return;
    
    var currentId = parseInt(container.dataset.currentId || '0');
    var itemIds = JSON.parse(container.dataset.itemIds || '[]');
    
    if (!currentId || !itemIds.length) return;
    
    var currentIndex = itemIds.indexOf(currentId);
    var newIndex = direction === 'next' ? currentIndex + 1 : currentIndex - 1;
    
    if (newIndex >= 0 && newIndex < itemIds.length) {
      window.location.href = '/events/inbox/process/' + itemIds[newIndex] + '/';
    }
  };

  window.quickAction = function(action) {
    var itemId = document.querySelector('input[name="item_id"]')?.value;
    if (!itemId) return;

    var actions = {
      process: { confirm: '¿Marcar este item como procesado?', value: 'reference' },
      archive: { confirm: '¿Archivar este item?', value: 'reference' },
      delete: { confirm: '¿Eliminar permanentemente este item?', value: 'delete' }
    };

    var config = actions[action];
    if (!config) return;

    if (confirm(config.confirm)) {
      var form = document.createElement('form');
      form.method = 'POST';
      var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
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
      var refreshBtn = document.getElementById('btn-refresh');
      if (refreshBtn) {
        refreshBtn.addEventListener('click', function() { ManagementPanelModule.loadQueueData(); });
      }
    },

    initAutoProcessing: function() {
      var pauseBtn = document.getElementById('btn-pause-auto');
      if (pauseBtn) {
        pauseBtn.addEventListener('click', function() { ManagementPanelModule.toggleAutoProcessing(); });
      }
      this.startAutoRefresh();
    },

    initQueueControls: function() {
      document.querySelectorAll('[data-queue]').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var queueType = this.dataset.queue;
          var action = this.dataset.action;
          if (queueType && action) {
            ManagementPanelModule.processQueue(queueType, action);
          }
        });
      });
    },

    initSettings: function() {
      var settings = ['auto-email-processing', 'auto-call-queue', 'auto-chat-routing', 'processing-interval', 'max-concurrent'];
      settings.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) {
          el.addEventListener('change', function() { ManagementPanelModule.updateSettings(); });
        }
      });
    },

    initModals: function() {
      window.confirmAssignment = function() {
        ManagementPanelModule.confirmAssignment();
      };
      window.markAsResolved = function() {
        ManagementPanelModule.markAsResolved();
      };
    },

    loadQueueData: function() {
      var url = '/events/inbox/management/api/queue-data/';
      fetch(url, {
        method: 'GET',
        headers: {
          'X-CSRFToken': Utils.getCookie('csrftoken'),
          'Content-Type': 'application/json'
        }
      })
      .then(function(response) { return response.json(); })
      .then(function(data) {
        if (data.success) {
          ManagementPanelModule.updateMetrics(data.data);
        }
      })
      ['catch'](function(error) { console.error('Error loading queue data:', error); });

      this.loadQueue('email', 'email-queue', document.getElementById('email-queue-count'));
      this.loadQueue('call', 'call-queue', document.getElementById('call-queue-count'));
      this.loadQueue('chat', 'chat-queue', document.getElementById('chat-queue-count'));
    },

    loadQueue: function(type, containerId, countEl) {
      var url = '/events/inbox/management/api/' + type + '-queue/';
      var container = document.getElementById(containerId);
      if (!container) return;

      fetch(url, {
        method: 'GET',
        headers: {
          'X-CSRFToken': Utils.getCookie('csrftoken'),
          'Content-Type': 'application/json'
        }
      })
      .then(function(response) { return response.json(); })
      .then(function(data) {
        if (data.success) {
          if (data.data.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-3">No hay ' + (type === 'email' ? 'emails' : type === 'call' ? 'llamadas' : 'chats') + ' pendientes</div>';
            if (countEl) countEl.textContent = '0';
            return;
          }

          var typeLabels = { email: 'Email', call: 'Call', chat: 'Chat' };
          container.innerHTML = data.data.map(function(item) {
            return `
              <div class="queue-item ${type} ${item.priority === 'alta' ? 'high-priority' : ''}" data-interaction-id="${item.id}" data-type="${type}">
                <div class="flex justify-between items-start">
                  <div class="flex-1">
                    <div class="queue-item-title">${Utils.escapeHtml(item.title)}</div>
                    <div class="queue-item-meta">${Utils.escapeHtml(item.sender || item.caller || item.customer || '')}</div>
                    ${item.waitTime ? '<div class="queue-item-meta text-warning">Wait: ' + item.waitTime + '</div>' : ''}
                    ${item.messages ? '<div class="queue-item-meta text-info">' + item.messages + ' messages</div>' : ''}
                  </div>
                  <div class="text-right">
                    <span class="queue-item-badge ${item.priority === 'urgente' ? 'badge-danger' : item.priority === 'alta' ? 'badge-warning' : 'badge-secondary'}">${item.priority || 'media'}</span>
                    <span class="status-indicator ${item.status === 'active' ? 'active' : item.status === 'paused' ? 'paused' : 'pending'}"></span>
                  </div>
                </div>
                <div class="queue-item-meta">${item.time || ''}</div>
              </div>
            `;
          }).join('');

          container.querySelectorAll('.queue-item').forEach(function(el) {
            el.addEventListener('click', function() {
              var id = this.dataset.interactionId;
              var type = this.dataset.type;
              if (id && type) {
                ManagementPanelModule.showInteractionDetails(id, type);
              }
            });
          });

          if (countEl) countEl.textContent = data.data.length;
        }
      })
      ['catch'](function(error) {
        container.innerHTML = '<div class="text-center text-danger py-3">Error de conexión</div>';
      });
    },

    updateMetrics: function(data) {
      var metrics = {
        'active-items': data.active,
        'pending-items': data.pending,
        'emails-count': data.emails,
        'calls-count': data.calls,
        'chats-count': data.chats,
        'email-queue-count': data.emails,
        'call-queue-count': data.calls,
        'chat-queue-count': data.chats
      };

      Object.entries(metrics).forEach(function(entry) {
        var id = entry[0];
        var value = entry[1];
        var el = document.getElementById(id);
        if (el) el.textContent = value;
      });
    },

    processQueue: function(queueType, action) {
      var confirmMessages = {
        email: { process: '¿Procesar automáticamente la cola de emails?', pause: '¿Pausar cola de emails?' },
        call: { activate: '¿Activar cola de llamadas entrantes?', pause: '¿Pausar cola de llamadas?' },
        chat: { process: '¿Procesar automáticamente la cola de chats?', pause: '¿Pausar cola de chats?' }
      };

      var msg = confirmMessages[queueType]?.[action];
      if (msg && !confirm(msg)) return;

      fetch('/events/inbox/management/api/process-queue/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': Utils.getCookie('csrftoken'),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ queue_type: queueType, action: action })
      })
      .then(function(response) { return response.json(); })
      .then(function(data) {
        if (data.success) {
          HeaderModule.showNotification('Cola ' + queueType + ' procesada exitosamente', 'success');
          ManagementPanelModule.loadQueueData();
        } else {
          HeaderModule.showNotification('Error: ' + (data.error || 'Error al procesar'), 'error');
        }
      })
      ['catch'](function() {
        HeaderModule.showNotification('Error de conexión', 'error');
      });
    },

    toggleAutoProcessing: function() {
      var btn = document.getElementById('btn-pause-auto');
      if (!btn) return;

      var icon = btn.querySelector('i');
      var isPaused = icon.classList.contains('fa-play-circle');
      
      if (isPaused) {
        icon.className = 'fas fa-pause-circle';
        btn.innerHTML = '<i class="fas fa-pause-circle" aria-hidden="true"></i> Pause Auto-Processing';
        btn.className = 'btn btn-warning';
        this.startAutoRefresh();
      } else {
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
      var formData = new FormData();
      var settings = ['auto-email-processing', 'auto-call-queue', 'auto-chat-routing', 'processing-interval', 'max-concurrent'];
      settings.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) {
          formData.append(id, el.type === 'checkbox' ? el.checked : el.value);
        }
      });

      fetch('/events/inbox/management/api/update-settings/', {
        method: 'POST',
        headers: { 'X-CSRFToken': Utils.getCookie('csrftoken') },
        body: formData
      })
      .then(function(response) { return response.json(); })
      .then(function(data) {
        if (data.success) {
          HeaderModule.showNotification('Configuración actualizada', 'success');
        }
      })
      ['catch'](function(error) { console.error('Error updating settings:', error); });
    },

    startAutoRefresh: function() {
      if (this.autoRefreshInterval) clearInterval(this.autoRefreshInterval);
      this.autoRefreshInterval = setInterval(function() { ManagementPanelModule.loadQueueData(); }, 30000);
    },

    showInteractionDetails: function(id, type) {
      this.currentInteractionId = id;
      var title = { email: 'Email Details', call: 'Call Details', chat: 'Chat Details' }[type] || 'Details';
      var body = document.getElementById('interactionModalBody');
      if (body) {
        body.innerHTML = '<div class="text-center text-muted py-4">Detalles de ' + title.toLowerCase() + ' para ID ' + id + '</div>';
      }
      var label = document.getElementById('interactionModalLabel');
      if (label) label.textContent = title;
      
      document.querySelector('[data-interaction-id]')?.setAttribute('data-interaction-id', id);
      
      openModal('interactionModal');
    },

    confirmAssignment: function() {
      var agent = document.getElementById('agent-select')?.value;
      if (!agent) {
        HeaderModule.showNotification('Por favor selecciona un agente', 'warning');
        return;
      }

      var interactionId = this.currentInteractionId || document.querySelector('[data-interaction-id]')?.dataset.interactionId;
      if (!interactionId) {
        HeaderModule.showNotification('No hay interacción seleccionada', 'warning');
        return;
      }

      var formData = new FormData();
      formData.append('interaction_id', interactionId);
      formData.append('agent_type', agent);
      formData.append('priority', document.getElementById('priority-select')?.value || 'media');
      formData.append('notes', document.getElementById('notes')?.value || '');

      fetch('/events/inbox/management/api/assign-agent/', {
        method: 'POST',
        headers: { 'X-CSRFToken': Utils.getCookie('csrftoken') },
        body: formData
      })
      .then(function(response) { return response.json(); })
      .then(function(data) {
        if (data.success) {
          HeaderModule.showNotification('Asignado a ' + agent, 'success');
          ManagementPanelModule.loadQueueData();
          closeModal('interactionModal');
          closeModal('assignModal');
        } else {
          HeaderModule.showNotification('Error: ' + (data.error || 'Error al asignar'), 'error');
        }
      })
      ['catch'](function() {
        HeaderModule.showNotification('Error de conexión', 'error');
      });
    },

    markAsResolved: function() {
      var interactionId = this.currentInteractionId || document.querySelector('[data-interaction-id]')?.dataset.interactionId;
      if (!interactionId) {
        HeaderModule.showNotification('No hay interacción seleccionada', 'warning');
        return;
      }

      var resolutionNotes = prompt('Notas de resolución (opcional):', '');
      var formData = new FormData();
      formData.append('interaction_id', interactionId);
      if (resolutionNotes) formData.append('resolution_notes', resolutionNotes);

      fetch('/events/inbox/management/api/mark-resolved/', {
        method: 'POST',
        headers: { 'X-CSRFToken': Utils.getCookie('csrftoken') },
        body: formData
      })
      .then(function(response) { return response.json(); })
      .then(function(data) {
        if (data.success) {
          HeaderModule.showNotification('Interacción marcada como resuelta', 'success');
          ManagementPanelModule.loadQueueData();
          closeModal('interactionModal');
        } else {
          HeaderModule.showNotification('Error: ' + (data.error || 'Error al marcar como resuelta'), 'error');
        }
      })
      ['catch'](function() {
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
      var dismissBtns = document.querySelectorAll('.alert-dismiss');
      dismissBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
          var alert = this.closest('.alert');
          if (alert) {
            alert.classList.add('dismissing');
            setTimeout(function() {
              alert.remove();
              AlertsModule.checkEmpty();
            }, 300);
          }
        });
      });
    },

    initAutoDismiss: function() {
      var successAlerts = document.querySelectorAll('.alert-success');
      successAlerts.forEach(function(alert) {
        setTimeout(function() {
          if (alert.parentNode) {
            alert.classList.add('dismissing');
            setTimeout(function() {
              alert.remove();
              AlertsModule.checkEmpty();
            }, 300);
          }
        }, 5000);
      });
    },

    checkEmpty: function() {
      var container = document.getElementById('alertsContainer');
      if (container && container.children.length === 0) {
        container.style.display = 'none';
      }
    }
  };

  // ==========================================
  // KANBAN MODULE
  // ==========================================
  const KanbanModule = {
    init: function() {
      this.initDragAndDrop();
      this.initFilters();
      this.initTaskInteractions();
      this.initKeyboardShortcuts();
      this.initThemeToggle();
      this.initViewMode();
      this.initSorting();
      this.initExport();
      this.initMetrics();
      this.initGTDTools();
    },

    // ========== DRAG AND DROP ==========
    initDragAndDrop: function() {
      var taskCards = document.querySelectorAll('.kanban-task-card[draggable="true"], .kanban-card[draggable="true"], .kanban-enhanced-card[draggable="true"], .kanban-organized-task-card[draggable="true"]');
      var columns = document.querySelectorAll('.kanban-column, .kanban-column-modern, .kanban-enhanced-column, .kanban-organized-column');

      taskCards.forEach(function(card) {
        card.addEventListener('dragstart', KanbanModule.handleDragStart);
        card.addEventListener('dragend', KanbanModule.handleDragEnd);
      });

      columns.forEach(function(column) {
        column.addEventListener('dragover', KanbanModule.handleDragOver);
        column.addEventListener('drop', KanbanModule.handleDrop);
        column.addEventListener('dragleave', KanbanModule.handleDragLeave);
      });
    },

    handleDragStart: function(e) {
      e.dataTransfer.setData('text/plain', e.target.dataset.taskId);
      e.target.classList.add('dragging');
      document.body.classList.add('dragging-active');
    },

    handleDragEnd: function(e) {
      e.target.classList.remove('dragging');
      document.querySelectorAll('.kanban-column, .kanban-column-modern, .kanban-enhanced-column, .kanban-organized-column').forEach(function(col) {
        col.classList.remove('drag-over');
      });
      document.body.classList.remove('dragging-active');
    },

    handleDragOver: function(e) {
      e.preventDefault();
      e.currentTarget.classList.add('drag-over');
    },

    handleDragLeave: function(e) {
      e.currentTarget.classList.remove('drag-over');
    },

    handleDrop: function(e) {
      e.preventDefault();
      e.currentTarget.classList.remove('drag-over');
      var taskId = e.dataTransfer.getData('text/plain');
      var newStatus = e.currentTarget.dataset.status;
      if (taskId && newStatus) {
        KanbanModule.moveTaskToColumn(taskId, newStatus, e.currentTarget);
      }
    },

    moveTaskToColumn: function(taskId, newStatus, targetColumn) {
      var card = document.querySelector('[data-task-id="' + taskId + '"]');
      if (!card) return;

      var originalContent = card.innerHTML;
      card.innerHTML = `
        <div class="flex items-center justify-center p-3">
          <div class="kanban-spinner"></div>
          <span class="ml-2">Moviendo tarea...</span>
        </div>
      `;

      fetch('/events/tasks/status/ajax/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || Utils.getCookie('csrftoken')
        },
        body: 'task_id=' + taskId + '&new_status_name=' + newStatus
      })
      .then(function(response) { return response.json(); })
      .then(function(data) {
        if (data.success) {
          var newColumn = targetColumn.querySelector('.kanban-column-tasks, .kanban-column-tasks-modern, .kanban-enhanced-column-tasks, .kanban-organized-column-tasks');
          if (newColumn) {
            var emptyState = newColumn.querySelector('.kanban-empty, .kanban-empty-modern, .kanban-enhanced-empty, .kanban-organized-empty');
            if (emptyState) emptyState.remove();
            newColumn.appendChild(card);
            KanbanModule.updateColumnCounts();
            setTimeout(function() {
              card.innerHTML = originalContent;
              card.style.animation = 'none';
              setTimeout(function() { card.style.animation = ''; }, 10);
              KanbanModule.showKanbanToast('Tarea movida exitosamente', 'success');
            }, 300);
          }
        } else {
          card.innerHTML = originalContent;
          KanbanModule.showKanbanToast(data.error || 'Error al mover la tarea', 'error');
        }
      })
      ['catch'](function(error) {
        card.innerHTML = originalContent;
        KanbanModule.showKanbanToast('Error de conexión', 'error');
        console.error('Error:', error);
      });
    },

    updateColumnCounts: function() {
      document.querySelectorAll('.kanban-column, .kanban-column-modern, .kanban-enhanced-column, .kanban-organized-column').forEach(function(column) {
        var count = column.querySelectorAll('.kanban-task-card, .kanban-card-modern, .kanban-enhanced-card, .kanban-organized-task-card').length;
        var countElement = column.querySelector('.kanban-task-count, .kanban-column-count, .kanban-enhanced-column-count, .kanban-organized-column-count');
        if (countElement) countElement.textContent = count;
      });
    },

    // ========== FILTERS ==========
    initFilters: function() {
      var filterTags = document.querySelectorAll('.kanban-filter-tag, .filter-tag, .kanban-enhanced-filter-tag, .kanban-organized-filter-tag');
      var statusFilters = document.querySelectorAll('.kanban-status-filter, .status-filter');

      filterTags.forEach(function(tag) {
        tag.addEventListener('click', function() {
          this.classList.toggle('active');
          KanbanModule.applyFilters();
        });
      });

      statusFilters.forEach(function(filter) {
        filter.addEventListener('click', function() {
          this.classList.toggle('active');
          KanbanModule.applyFilters();
        });
      });

      var projectFilter = document.getElementById('projectFilter');
      var userFilter = document.getElementById('userFilter');

      if (projectFilter) {
        projectFilter.addEventListener('change', function() { KanbanModule.applyFilters(); });
      }

      if (userFilter) {
        userFilter.addEventListener('change', function() { KanbanModule.applyFilters(); });
      }
    },

    applyFilters: function() {
      var activeTagFilters = Array.from(document.querySelectorAll('.kanban-filter-tag.active, .filter-tag.active, .kanban-enhanced-filter-tag.active, .kanban-organized-filter-tag.active'))
        .map(function(tag) { return tag.dataset.tagId; });

      var activeStatusFilters = Array.from(document.querySelectorAll('.kanban-status-filter.active, .status-filter.active'))
        .map(function(filter) { return filter.dataset.status; });

      var projectFilter = document.getElementById('projectFilter');
      var userFilter = document.getElementById('userFilter');

      var taskCards = document.querySelectorAll('.kanban-task-card, .kanban-card-modern, .kanban-enhanced-card, .kanban-organized-task-card');

      taskCards.forEach(function(card) {
        var shouldShow = true;

        if (activeTagFilters.length > 0) {
          var taskTags = Array.from(card.querySelectorAll('.kanban-task-tag, .kanban-card-tag, .kanban-enhanced-card-tag, .kanban-organized-task-tag'))
            .map(function(tag) { return tag.textContent.trim(); });
          shouldShow = shouldShow && activeTagFilters.some(function(filterId) { return taskTags.includes(filterId); });
        }

        if (activeStatusFilters.length > 0) {
          var cardStatus = card.closest('[data-status]')?.dataset.status;
          shouldShow = shouldShow && activeStatusFilters.includes(cardStatus);
        }

        if (projectFilter && projectFilter.value) {
          var taskProject = card.querySelector('.kanban-task-project a, .kanban-card-project, .kanban-enhanced-meta-item a')?.textContent?.trim();
          shouldShow = shouldShow && taskProject?.includes(projectFilter.options[projectFilter.selectedIndex]?.text);
        }

        card.style.display = shouldShow ? '' : 'none';
      });

      this.updateColumnCounts();
      var visibleCount = document.querySelectorAll('.kanban-task-card[style*="display: block"], .kanban-card-modern[style*="display: block"], .kanban-enhanced-card[style*="display: block"], .kanban-organized-task-card[style*="display: block"]').length;
      this.showKanbanToast('Mostrando ' + visibleCount + ' tareas', 'info');
    },

    clearAllFilters: function() {
      document.querySelectorAll('.kanban-filter-tag.active, .filter-tag.active, .kanban-enhanced-filter-tag.active, .kanban-organized-filter-tag.active, .kanban-status-filter.active, .status-filter.active')
        .forEach(function(el) { el.classList.remove('active'); });

      var projectFilter = document.getElementById('projectFilter');
      var userFilter = document.getElementById('userFilter');
      if (projectFilter) projectFilter.value = '';
      if (userFilter) userFilter.value = '';

      this.applyFilters();
      this.showKanbanToast('Filtros limpiados', 'info');
    },

    // ========== TASK INTERACTIONS ==========
    initTaskInteractions: function() {
      var taskCards = document.querySelectorAll('.kanban-task-card, .kanban-card-modern, .kanban-enhanced-card, .kanban-organized-task-card');
      
      taskCards.forEach(function(card) {
        card.addEventListener('click', function(e) {
          if (e.target.closest('.kanban-task-actions, .kanban-card-footer, .kanban-enhanced-card-footer, .kanban-organized-task-actions, .btn, a')) {
            return;
          }
          var taskId = this.dataset.taskId;
          if (taskId) {
            window.location.href = '/events/tasks/' + taskId + '/';
          }
        });
      });
    },

    // ========== KEYBOARD SHORTCUTS ==========
    initKeyboardShortcuts: function() {
      document.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
          return;
        }

        switch(e.key) {
          case '+':
            e.preventDefault();
            document.querySelector('[data-modal="createTaskModal"], [data-m360-open="#createTaskModal"]')?.click();
            break;
          case 'f':
            if (e.ctrlKey || e.metaKey) {
              e.preventDefault();
              document.querySelector('[data-modal="filterModal"], [data-m360-open="#filterModal"], [data-modal="advancedFilterModal"]')?.click();
            }
            break;
          case 't':
            if (e.ctrlKey || e.metaKey) {
              e.preventDefault();
              KanbanModule.toggleTheme();
            }
            break;
          case 'Escape':
            KanbanModule.clearAllFilters();
            break;
          case 'r':
            if (e.ctrlKey || e.metaKey) {
              e.preventDefault();
              KanbanModule.refreshKanban();
            }
            break;
        }
      });
    },

    // ========== THEME TOGGLE ==========
    initThemeToggle: function() {
      var themeToggle = document.getElementById('themeToggle') || document.getElementById('themeToggleEnhanced') || document.getElementById('themeToggleOrganized');
      var themeIcon = document.getElementById('themeIcon') || document.getElementById('themeIconEnhanced') || document.getElementById('themeIconOrganized');

      if (themeToggle) {
        themeToggle.addEventListener('click', function() { KanbanModule.toggleTheme(); });
      }

      var savedTheme = localStorage.getItem('kanbanTheme') || 'light';
      this.setTheme(savedTheme);
    },

    toggleTheme: function() {
      var currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      var newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      this.setTheme(newTheme);
      localStorage.setItem('kanbanTheme', newTheme);
      this.showKanbanToast('Tema cambiado a ' + (newTheme === 'dark' ? 'oscuro' : 'claro'), 'info');
    },

    setTheme: function(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      var themeIcon = document.getElementById('themeIcon') || document.getElementById('themeIconEnhanced') || document.getElementById('themeIconOrganized');
      if (themeIcon) {
        themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
      }
    },

    // ========== VIEW MODE ==========
    initViewMode: function() {
      var viewSelect = document.getElementById('viewMode') || document.getElementById('viewModeEnhanced') || document.getElementById('viewModeOrganized');
      if (viewSelect) {
        viewSelect.addEventListener('change', function() {
          var board = document.getElementById('kanbanBoard') || document.getElementById('kanbanBoardEnhanced') || document.getElementById('kanbanBoardOrganized');
          if (board) {
            board.className = board.className.replace(/\b(normal|compact|detailed)-view\b/g, '') + ' ' + this.value + '-view';
            KanbanModule.showKanbanToast('Vista cambiada a ' + this.value, 'info');
          }
        });
      }
    },

    // ========== SORTING ==========
    initSorting: function() {
      var sortSelect = document.getElementById('sortBy') || document.getElementById('sortByEnhanced') || document.getElementById('sortByOrganized');
      if (sortSelect) {
        sortSelect.addEventListener('change', function() {
          KanbanModule.applySorting(this.value);
        });
      }
    },

    applySorting: function(sortBy) {
      var columns = document.querySelectorAll('.kanban-column, .kanban-column-modern, .kanban-enhanced-column, .kanban-organized-column');
      
      columns.forEach(function(column) {
        var tasks = Array.from(column.querySelectorAll('.kanban-task-card, .kanban-card-modern, .kanban-enhanced-card, .kanban-organized-task-card'));
        var tasksContainer = column.querySelector('.kanban-column-tasks, .kanban-column-tasks-modern, .kanban-enhanced-column-tasks, .kanban-organized-column-tasks');
        if (!tasksContainer) return;

        tasks.sort(function(a, b) {
          var valueA, valueB;
          switch(sortBy) {
            case 'title':
              valueA = a.querySelector('.kanban-task-title, .kanban-card-title, .kanban-enhanced-card-title, .kanban-organized-task-title')?.textContent?.toLowerCase() || '';
              valueB = b.querySelector('.kanban-task-title, .kanban-card-title, .kanban-enhanced-card-title, .kanban-organized-task-title')?.textContent?.toLowerCase() || '';
              break;
            case 'created_at':
              valueA = new Date(a.dataset.createdAt || 0);
              valueB = new Date(b.dataset.createdAt || 0);
              break;
            case 'priority':
              valueA = a.classList.contains('important') ? 0 : 1;
              valueB = b.classList.contains('important') ? 0 : 1;
              break;
            default: // updated_at
              valueA = new Date(a.querySelector('.kanban-task-date, .kanban-card-date, .kanban-enhanced-card-date, .kanban-organized-task-date')?.textContent || 0);
              valueB = new Date(b.querySelector('.kanban-task-date, .kanban-card-date, .kanban-enhanced-card-date, .kanban-organized-task-date')?.textContent || 0);
          }
          if (valueA < valueB) return -1;
          if (valueA > valueB) return 1;
          return 0;
        });

        tasks.forEach(function(task) { tasksContainer.appendChild(task); });
      });

      var labels = {
        'updated_at': 'fecha de actualización',
        'created_at': 'fecha de creación',
        'title': 'título',
        'priority': 'prioridad',
        'assignee': 'asignado a'
      };
      this.showKanbanToast('Ordenado por ' + (labels[sortBy] || sortBy), 'info');
    },

    // ========== EXPORT ==========
    initExport: function() {
      document.querySelectorAll('[onclick*="exportKanban"]').forEach(function(btn) {
        btn.removeAttribute('onclick');
        btn.addEventListener('click', function() {
          var format = this.dataset.format || 'json';
          KanbanModule.exportKanban(format);
        });
      });
    },

    exportKanban: function(format) {
      var tasks = [];
      document.querySelectorAll('.kanban-task-card, .kanban-card-modern, .kanban-enhanced-card, .kanban-organized-task-card').forEach(function(card) {
        tasks.push({
          id: card.dataset.taskId,
          title: card.querySelector('.kanban-task-title, .kanban-card-title, .kanban-enhanced-card-title, .kanban-organized-task-title')?.textContent?.trim() || '',
          status: card.closest('[data-status]')?.dataset.status || '',
          important: card.classList.contains('important'),
          project: card.querySelector('.kanban-task-project, .kanban-card-project, .kanban-enhanced-meta-item')?.textContent?.trim() || '',
          assignee: card.querySelector('.kanban-task-assignee, .kanban-card-assignee, .kanban-enhanced-meta-item')?.textContent?.trim() || '',
          updatedAt: card.querySelector('.kanban-task-date, .kanban-card-date, .kanban-enhanced-card-date, .kanban-organized-task-date')?.textContent?.trim() || ''
        });
      });

      var data = {
        tasks: tasks,
        exportDate: new Date().toISOString(),
        format: format
      };

      switch(format) {
        case 'json':
          this.exportAsJSON(data);
          break;
        case 'csv':
          this.exportAsCSV(data);
          break;
        case 'pdf':
          this.showKanbanToast('Exportación PDF próximamente', 'info');
          break;
        default:
          this.showKanbanToast('Formato no soportado', 'error');
      }
    },

    exportAsJSON: function(data) {
      var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'kanban-export-' + new Date().toISOString().split('T')[0] + '.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      this.showKanbanToast('Exportado como JSON', 'success');
    },

    exportAsCSV: function(data) {
      var headers = ['ID', 'Título', 'Estado', 'Importante', 'Proyecto', 'Asignado a', 'Última actualización'];
      var rows = data.tasks.map(function(task) {
        return [
          task.id,
          '"' + task.title.replace(/"/g, '""') + '"',
          task.status,
          task.important ? 'Sí' : 'No',
          '"' + task.project.replace(/"/g, '""') + '"',
          '"' + task.assignee.replace(/"/g, '""') + '"',
          task.updatedAt
        ];
      });
      var csvContent = [headers.join(','), ...rows.map(function(row) { return row.join(','); })].join('\n');
      var blob = new Blob([csvContent], { type: 'text/csv' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'kanban-export-' + new Date().toISOString().split('T')[0] + '.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      this.showKanbanToast('Exportado como CSV', 'success');
    },

    // ========== METRICS ==========
    initMetrics: function() {
      var metricsBtn = document.querySelector('[data-modal="metricsModal"]');
      if (metricsBtn) {
        metricsBtn.addEventListener('click', function() { KanbanModule.loadMetrics(); });
      }
    },

    loadMetrics: function() {
      var totalTasks = document.querySelectorAll('.kanban-task-card, .kanban-card-modern, .kanban-enhanced-card, .kanban-organized-task-card').length;
      var completedTasks = document.querySelectorAll('.kanban-task-card[data-status="completed"], .kanban-card-modern[data-status="completed"], .kanban-enhanced-card[data-status="completed"], .kanban-organized-task-card[data-status="completed"]').length;
      var inProgressTasks = document.querySelectorAll('.kanban-task-card[data-status="in-progress"], .kanban-card-modern[data-status="in-progress"], .kanban-enhanced-card[data-status="in-progress"], .kanban-organized-task-card[data-status="in-progress"]').length;

      var metrics = {
        avgTasksPerDay: Math.round(totalTasks / 7),
        completionRate: totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0,
        avgTimeInProgress: '2.3 días',
        activeProjects: new Set(document.querySelectorAll('.kanban-task-project a, .kanban-card-project, .kanban-enhanced-meta-item a')?.length || 0).size || 0
      };

      var metricElements = {
        avgTasksPerDay: document.getElementById('avgTasksPerDay'),
        completionRate: document.getElementById('completionRate'),
        avgTimeInProgress: document.getElementById('avgTimeInProgress'),
        activeProjects: document.getElementById('activeProjects')
      };

      Object.entries(metricElements).forEach(function(entry) {
        var key = entry[0];
        var el = entry[1];
        if (el) {
          el.textContent = metrics[key] !== undefined ? metrics[key] : '-';
        }
      });
    },

    // ========== GTD TOOLS ==========
    initGTDTools: function() {
      document.querySelectorAll('.gtd-tool-card[data-url]').forEach(function(card) {
        card.addEventListener('click', function() {
          var url = this.dataset.url;
          if (url) {
            window.location.href = url;
          }
        });
      });
    },

    navigateToGTDTool: function(element) {
      var url = element.dataset.url;
      if (url) {
        window.location.href = url;
      }
    },

    showWeeklyReview: function() {
      this.showKanbanToast('Weekly Review - Próximamente', 'info');
    },

    // ========== REFRESH ==========
    refreshKanban: function() {
      this.showKanbanToast('Actualizando...', 'info');
      setTimeout(function() {
        window.location.reload();
      }, 1000);
    },

    // ========== TOAST ==========
    showKanbanToast: function(message, type) {
      type = type || 'info';
      var toast = document.createElement('div');
      toast.className = 'kanban-toast';
      toast.setAttribute('role', 'alert');
      var iconClass = type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-triangle' : 'fa-info-circle';
      var bgColor = type === 'success' ? 'var(--green)' : type === 'error' ? 'var(--red)' : 'var(--blue)';
      toast.style.cssText = `
        position: fixed; bottom: 80px; right: 20px; z-index: 9999;
        min-width: 300px; padding: 12px 16px;
        background: ${bgColor}; color: #fff;
        border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        display: flex; align-items: center; gap: 8px;
        animation: slideInRight 0.3s ease;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.875rem;
      `;
      toast.innerHTML = '<i class="fas ' + iconClass + '" aria-hidden="true"></i><span>' + message + '</span>';
      document.body.appendChild(toast);
      setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(function() { if (toast.parentNode) document.body.removeChild(toast); }, 300);
      }, 3000);
    },

    // ========== CREATE TASK ==========
    createQuickTask: function() {
      var form = document.getElementById('quickCreateTaskForm') || 
                   document.getElementById('quickCreateTaskFormEnhanced') || 
                   document.getElementById('quickCreateTaskFormOrganized');
      if (!form) return;

      if (!form.title.value.trim()) {
        this.showKanbanToast('El título es obligatorio', 'error');
        return;
      }

      var modal = form.closest('.modal-overlay') || document.getElementById('createTaskModal') || document.getElementById('createTaskModalEnhanced') || document.getElementById('createTaskModalOrganized');
      var submitBtn = modal ? modal.querySelector('.modal-actions button[type="button"]:last-child') : form.querySelector('button[type="button"]:last-child');
      if (!submitBtn) return;

      var originalText = submitBtn.innerHTML;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando...';
      submitBtn.disabled = true;

      var formData = new FormData(form);
      var self = this;
      fetch(form.action || '/events/tasks/create/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
      })
      .then(function(response) { return response.json(); })
      .then(function(data) {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
        if (data.success) {
          self.showKanbanToast(data.message || 'Tarea creada exitosamente!', 'success');
          form.reset();
          closeModal('createTaskModal');
          closeModal('createTaskModalEnhanced');
          closeModal('createTaskModalOrganized');
          setTimeout(function() { window.location.reload(); }, 1000);
        } else {
          self.showKanbanToast(data.error || 'Error al crear la tarea', 'error');
        }
      })
      ['catch'](function() {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
        self.showKanbanToast('Error de conexión', 'error');
      });
    }
  };

  // Exponer KanbanModule globalmente
  window.KanbanModule = KanbanModule;

  // Exponer funciones globales de Kanban
  window.refreshKanban = function() { KanbanModule.refreshKanban(); };
  window.exportKanban = function(format) { KanbanModule.exportKanban(format); };
  window.toggleTheme = function() { KanbanModule.toggleTheme(); };
  window.toggleThemeEnhanced = function() { KanbanModule.toggleTheme(); };
  window.toggleThemeOrganized = function() { KanbanModule.toggleTheme(); };
  window.refreshKanbanEnhanced = function() { KanbanModule.refreshKanban(); };
  window.refreshKanbanOrganized = function() { KanbanModule.refreshKanban(); };
  window.exportKanbanEnhanced = function() { KanbanModule.exportKanban('json'); };
  window.exportKanbanOrganized = function() { KanbanModule.exportKanban('json'); };
  window.clearAllFilters = function() { KanbanModule.clearAllFilters(); };
  window.clearAllFiltersEnhanced = function() { KanbanModule.clearAllFilters(); };
  window.clearAllFiltersOrganized = function() { KanbanModule.clearAllFilters(); };
  window.createQuickTask = function() { KanbanModule.createQuickTask(); };
  window.createQuickTaskEnhanced = function() { KanbanModule.createQuickTask(); };
  window.createQuickTaskOrganized = function() { KanbanModule.createQuickTask(); };
  window.navigateToGTDTool = function(el) { KanbanModule.navigateToGTDTool(el); };
  window.showWeeklyReview = function() { KanbanModule.showWeeklyReview(); };
  window.toggleComments = function(taskId) {
    var card = document.querySelector('[data-task-id="' + taskId + '"]');
    if (card) {
      var comments = card.querySelector('.kanban-card-comments');
      if (comments) {
        comments.style.display = comments.style.display === 'none' ? 'block' : 'none';
      }
    }
  };

  // ==========================================
  // EISENHOWER MODULE
  // ==========================================
  const EisenhowerModule = {
    init: function() {
      this.initDropdowns();
    },

    initDropdowns: function() {
      document.querySelectorAll('[data-dropdown]').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          var menuId = this.dataset.dropdown;
          var menu = document.getElementById(menuId);
          if (!menu) return;

          var isOpen = menu.classList.contains('show');
          document.querySelectorAll('.dropdown-menu.show').forEach(function(m) { m.classList.remove('show'); });

          if (!isOpen) {
            menu.classList.add('show');
            this.setAttribute('aria-expanded', 'true');
          }
        });
      });

      document.addEventListener('click', function() {
        document.querySelectorAll('.dropdown-menu.show').forEach(function(menu) {
          menu.classList.remove('show');
          var btn = document.querySelector('[data-dropdown="' + menu.id + '"]');
          if (btn) btn.setAttribute('aria-expanded', 'false');
        });
      });
    },

    moveTask: function(taskId, newQuadrant) {
      var quadrantNames = {
        urgent_important: 'Urgente e Importante',
        important_not_urgent: 'Importante pero No Urgente',
        urgent_not_important: 'Urgente pero No Importante',
        not_urgent_important: 'No Urgente ni Importante'
      };

      var btn = window.event?.target?.closest('.dropdown-item');
      if (!btn) return;

      var originalText = btn.innerHTML;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Moviendo...';
      btn.style.pointerEvents = 'none';

      var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

      fetch('/events/eisenhower/move/' + taskId + '/' + newQuadrant + '/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        }
      })
      .then(function(response) { return response.json(); })
      .then(function(data) {
        if (data.success) {
          var message = data.message || 'Tarea movida a: ' + (quadrantNames[newQuadrant] || newQuadrant);
          if (window.HeaderModule) {
            window.HeaderModule.showNotification(message, 'success');
          } else {
            alert(message);
          }

          var taskCard = document.querySelector('[data-task-id="' + taskId + '"]');
          if (taskCard) {
            taskCard.style.transition = 'all 0.3s ease';
            taskCard.style.opacity = '0';
            taskCard.style.transform = 'scale(0.8)';
            setTimeout(function() {
              taskCard.remove();
              EisenhowerModule.updateQuadrantCounts();
            }, 300);
          }
        } else {
          if (window.HeaderModule) {
            window.HeaderModule.showNotification('Error: ' + data.error, 'error');
          } else {
            alert('Error: ' + data.error);
          }
        }
      })
      ['catch'](function(error) {
        console.error('Error:', error);
        if (window.HeaderModule) {
          window.HeaderModule.showNotification('Error al mover la tarea', 'error');
        } else {
          alert('Error al mover la tarea');
        }
      })
      ['finally'](function() {
        btn.innerHTML = originalText;
        btn.style.pointerEvents = 'auto';
      });
    },

    updateQuadrantCounts: function() {
      document.querySelectorAll('.eisenhower-quadrant').forEach(function(quadrant) {
        var countBadge = quadrant.querySelector('.quadrant-count');
        var taskCards = quadrant.querySelectorAll('.eisenhower-task-card');
        if (countBadge) {
          countBadge.textContent = taskCards.length;
        }
      });

      var quadrants = ['urgent_important', 'important_not_urgent', 'urgent_not_important', 'not_urgent_important'];
      var summaryItems = document.querySelectorAll('.eisenhower-summary-item');

      quadrants.forEach(function(key, index) {
        var count = document.querySelectorAll('.eisenhower-quadrant[data-quadrant="' + key + '"] .eisenhower-task-card').length;
        if (summaryItems[index]) {
          var h4 = summaryItems[index].querySelector('h4');
          if (h4) h4.textContent = count;
        }
      });
    }
  };

  // ==========================================
  // GLOBAL FUNCTIONS (for inline usage)
  // ==========================================
  window.openModal = function(id) {
    var modal = document.getElementById(id);
    if (modal) Utils.addClass(modal, 'show');
  };

  window.closeModal = function(id) {
    var modal = document.getElementById(id);
    if (modal) Utils.removeClass(modal, 'show');
  };

  window.deleteInboxItem = function(itemId, title) {
    if (confirm('¿Estás seguro de eliminar el item "' + title + '"? Esta acción no se puede deshacer.')) {
      var form = document.createElement('form');
      form.method = 'POST';
      var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
      form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
        <input type="hidden" name="action" value="delete">
      `;
      document.body.appendChild(form);
      form.action = '/events/inbox/process/' + itemId + '/';
      form.submit();
    }
  };

  window.markAsProcessed = function(itemId) {
    if (!confirm('¿Marcar este item como procesado?')) return;
    var form = document.createElement('form');
    form.method = 'POST';
    var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    form.innerHTML = `
      <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
      <input type="hidden" name="action" value="reference">
    `;
    document.body.appendChild(form);
    form.action = '/events/inbox/process/' + itemId + '/';
    form.submit();
  };

  window.quickClassify = function(itemId, category) {
    var label = category === 'accionable' ? 'Accionable' : 
                  category === 'no_accionable' ? 'No Accionable' : 'Pendiente';
    if (!confirm('¿Marcar este item como "' + label + '"?')) return;
    
    var form = document.createElement('form');
    form.method = 'POST';
    var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    form.innerHTML = `
      <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
      <input type="hidden" name="action" value="categorize">
      <input type="hidden" name="gtd_category" value="${category}">
    `;
    document.body.appendChild(form);
    form.action = '/events/inbox/process/' + itemId + '/';
    form.submit();
  };

  window.moveTask = function(taskId, newQuadrant) {
    if (window.EisenhowerModule) {
      window.EisenhowerModule.moveTask(taskId, newQuadrant);
    }
  };

  window.updateQuadrantCounts = function() {
    if (window.EisenhowerModule) {
      window.EisenhowerModule.updateQuadrantCounts();
    }
  };

  window.togglePendienteExtendido = function(btn) {
    var card = btn.closest('.pendiente-card');
    if (!card) return;
    var extended = card.querySelector('.pendiente-extended');
    if (!extended) return;
    
    var isHidden = extended.style.display === 'none' || !extended.style.display;
    extended.style.display = isHidden ? 'block' : 'none';
    var icon = btn.querySelector('i');
    if (icon) {
      icon.className = isHidden ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
    }
    btn.innerHTML = isHidden ? 
      '<i class="fas fa-chevron-up" aria-hidden="true"></i> Menos opciones' : 
      '<i class="fas fa-chevron-down" aria-hidden="true"></i> Más opciones';
  };

  window.classifyAll = function() {
    if (!confirm('¿Clasificar todos los items pendientes automáticamente?')) return;
    
    var form = document.createElement('form');
    form.method = 'POST';
    var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    form.innerHTML = `
      <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken ? csrfToken.value : ''}">
      <input type="hidden" name="action" value="classify_all">
    `;
    document.body.appendChild(form);
    form.action = '/events/inbox/bulk-action/';
    form.submit();
  };

  window.expandAllPendientes = function() {
    var cards = document.querySelectorAll('.pendiente-card');
    var isExpanded = cards[0]?.querySelector('.pendiente-extended')?.style.display === 'block';
    
    cards.forEach(function(card) {
      var extended = card.querySelector('.pendiente-extended');
      var btn = card.querySelector('.pendiente-toggle');
      if (extended) {
        extended.style.display = isExpanded ? 'none' : 'block';
        if (btn) {
          var icon = btn.querySelector('i');
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
    var btn = event?.target?.closest('.btn');
    if (btn) btn.disabled = true;
    
    var container = document.getElementById('pendientesContainer');
    if (!container) return;
    var offset = container.querySelectorAll('.pendiente-card').length;
    
    fetch('/events/inbox/api/pendientes/?offset=' + offset + '&limit=8', {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
      if (data.success && data.items.length > 0) {
        data.items.forEach(function(item) {
          var card = InboxModule._createPendienteCard(item);
          container.appendChild(card);
        });
        
        var counter = document.querySelector('.pendiente-counter .counter-number');
        if (counter) {
          var total = parseInt(counter.textContent) + data.items.length;
          counter.textContent = total;
        }
        
        if (!data.has_more && btn) {
          btn.style.display = 'none';
        }
      }
      if (btn) btn.disabled = false;
    })
    ['catch'](function() {
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
    var itemId = document.querySelector('input[name="item_id"]')?.value;
    if (!itemId) return;

    var actions = {
      process: { confirm: '¿Marcar este item como procesado?', value: 'reference' },
      archive: { confirm: '¿Archivar este item?', value: 'reference' },
      delete: { confirm: '¿Eliminar permanentemente este item?', value: 'delete' }
    };

    var config = actions[action];
    if (!config) return;

    if (confirm(config.confirm)) {
      var form = document.createElement('form');
      form.method = 'POST';
      var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
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

    // Módulo de Kanban (detectar cualquier elemento de kanban)
    if (document.querySelector('.kanban-board, .kanban-board-modern, .kanban-enhanced-board, .kanban-organized-board')) {
      KanbanModule.init();
    }

    // Módulo de Eisenhower
    if (document.querySelector('.eisenhower-grid')) {
      EisenhowerModule.init();
    }

    // ==========================================
    // PROCESS INBOX MODULE
    // ==========================================
    const ProcessInboxModule = {
      init: function() {
        this.initModals();
        this.toggleProjectOptions();
        this.toggleEventOptions();
        this.setupEventListeners();
        this.setupSearchFilters();
        this.updateCreationPreview();
        this.setupClassificationForm();
      },

      initModals: function() {
        const modalIds = ['taskSelectorModal', 'projectSelectorModal', 'eventSelectorModal', 'alertModal', 'reclassifyHistoryModal', 'reclassifyConfirmModal'];
        modalIds.forEach(function(id) {
          const el = document.getElementById(id);
          if (!el) return;
          el.addEventListener('click', function(e) {
            if (e.target === el) closeModal(id);
          });
        });
      },

      toggleProjectOptions: function() {
        const projectOption = document.getElementById('projectOption');
        if (!projectOption) return;
        
        const existingProjectSelect = document.getElementById('existingProjectSelect');
        const taskContextPreview = document.getElementById('taskContextPreview');
        const taskProjectPreview = document.getElementById('taskProjectPreview');
        const projectEventPreview = document.getElementById('projectEventPreview');
        
        if (existingProjectSelect) {
          existingProjectSelect.style.display = projectOption.value === 'existing' ? 'block' : 'none';
        }
        
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
        
        ProcessInboxModule.updateCreationPreview();
      },

      toggleEventOptions: function() {
        const eventOption = document.getElementById('eventOption');
        if (!eventOption) return;
        
        const existingEventSelect = document.getElementById('existingEventSelect');
        const taskEventPreview = document.getElementById('taskEventPreview');
        const projectEventPreview = document.getElementById('projectEventPreview');
        
        if (existingEventSelect) {
          existingEventSelect.style.display = eventOption.value === 'existing' ? 'block' : 'none';
        }
        
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
        
        ProcessInboxModule.updateCreationPreview();
      },

      updateCreationPreview: function() {
        const projectOption = document.getElementById('projectOption');
        const eventOption = document.getElementById('eventOption');
        const previewText = document.getElementById('previewText');
        if (!projectOption || !eventOption || !previewText) return;
        
        const projectMessages = {
          new: '📁 <strong>Nuevo proyecto</strong> creado automáticamente',
          existing: '📁 <strong>Proyecto existente</strong> seleccionado',
          none: '📁 <strong>Sin proyecto</strong> asociado'
        };
        const eventMessages = {
          new: '📅 <strong>Nuevo evento</strong> creado automáticamente',
          existing: '📅 <strong>Evento existente</strong> seleccionado',
          none: '📅 <strong>Sin evento</strong> asociado'
        };
        previewText.innerHTML = [
          projectMessages[projectOption.value] || projectMessages.none,
          eventMessages[eventOption.value] || eventMessages.new
        ].join('<br>');
      },

      setupEventListeners: function() {
        const projectOption = document.getElementById('projectOption');
        const eventOption = document.getElementById('eventOption');
        
        if (projectOption) {
          projectOption.addEventListener('change', function() {
            ProcessInboxModule.toggleProjectOptions();
          });
        }
        if (eventOption) {
          eventOption.addEventListener('change', function() {
            ProcessInboxModule.toggleEventOptions();
          });
        }
        
        const linkEventBtn = document.getElementById('linkEventConfirmBtn');
        if (linkEventBtn) linkEventBtn.addEventListener('click', ProcessInboxModule.linkToSelectedEvent);
        const linkProjectBtn = document.getElementById('linkProjectConfirmBtn');
        if (linkProjectBtn) linkProjectBtn.addEventListener('click', ProcessInboxModule.linkToSelectedProject);
        
        const processForm = document.getElementById('processForm');
        if (processForm) {
          processForm.addEventListener('submit', function(e) {
            console.log('Formulario enviado con:', {
              project_option: document.getElementById('projectOption').value,
              event_option: document.getElementById('eventOption').value,
              assigned_to: document.querySelector('[name="assigned_to"]').value
            });
          });
        }
      },

      loadData: async function(endpoint, listElementId, sampleData, itemTemplate, fallbackMessage) {
        const listElement = document.getElementById(listElementId);
        if (!listElement) return;
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
          let data = response.ok ? await response.json() : { items: sampleData };
          let items = data.items || data.tasks || data.projects || data.events || [];
          if (items && items.length) {
            listElement.innerHTML = items.map(itemTemplate).join('');
          } else {
            listElement.innerHTML = `<div class="text-center text-muted py-3">${fallbackMessage}</div>`;
          }
        } catch (error) {
          console.error('Error cargando ' + endpoint + ':', error);
          listElement.innerHTML = sampleData && sampleData.length
            ? sampleData.map(itemTemplate).join('')
            : '<div class="text-center text-danger">Error al cargar datos</div>';
        }
      },

      loadAvailableTasks: function() {
        const sampleTasks = [
          { id: 1, title: 'Revisar documentación del proyecto', description: 'Actualizar la documentación técnica', priority: 'alta' },
          { id: 2, title: 'Implementar nueva funcionalidad', description: 'Desarrollar el módulo de reportes', priority: 'media' },
          { id: 3, title: 'Corregir bugs menores', description: 'Arreglar issues reportados por usuarios', priority: 'baja' }
        ];
        const taskTemplate = task => `
          <div class="list-group-item task-item" onclick="ProcessInboxModule.selectTask(${task.id}, '${task.title.replace(/'/g, "\\'")}')">
            <div class="d-flex justify-content-between align-items-start">
              <div>
                <h6 class="mb-1">${task.title}</h6>
                <small class="text-muted">${task.description || 'Sin descripción'}</small>
              </div>
              <span class="badge bg-${task.priority === 'alta' ? 'danger' : task.priority === 'media' ? 'warning' : 'secondary'}">${task.priority}</span>
            </div>
          </div>`;
        ProcessInboxModule.loadData('/events/inbox/api/tasks/', 'taskList', sampleTasks, taskTemplate, 'No hay tareas disponibles');
      },

      loadAvailableProjects: function() {
        const sampleProjects = [
          { id: 1, title: 'Sistema de Gestión de Proyectos', description: 'Desarrollo completo del sistema GTD', status: 'En progreso' },
          { id: 2, title: 'Migración a nueva plataforma', description: 'Actualización tecnológica del sistema', status: 'Planificación' },
          { id: 3, title: 'Implementación de API REST', description: 'Desarrollo de endpoints para integración', status: 'Pendiente' }
        ];
        const projectTemplate = project => `
          <div class="list-group-item project-item" data-project-id="${project.id}">
            <div class="form-check">
              <input class="form-check-input" type="radio" name="selected_project" id="project${project.id}" value="${project.id}">
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
        ProcessInboxModule.loadData('/events/inbox/api/projects/', 'projectList', sampleProjects, projectTemplate, 'No hay proyectos disponibles');
      },

      loadAvailableEvents: function() {
        const sampleEvents = [
          { id: 1, title: 'Reunión de Proyecto Alpha', description: 'Revisión semanal del proyecto', status: 'En progreso' },
          { id: 2, title: 'Lanzamiento Beta', description: 'Presentación del lanzamiento beta', status: 'Planificado' },
          { id: 3, title: 'Capacitación del Equipo', description: 'Sesión de capacitación técnica', status: 'Completado' }
        ];
        const eventTemplate = event => `
          <div class="list-group-item event-item" data-event-id="${event.id}">
            <div class="form-check">
              <input class="form-check-input" type="radio" name="selected_event" id="event${event.id}" value="${event.id}">
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
        ProcessInboxModule.loadData('/events/inbox/api/events/', 'eventList', sampleEvents, eventTemplate, 'No hay eventos disponibles');
      },

      setupSearchFilters: function() {
        const setupSearch = (searchId, itemSelector) => {
          const searchElement = document.getElementById(searchId);
          if (!searchElement) return;
          searchElement.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            document.querySelectorAll(itemSelector).forEach(item => {
              const title = item.querySelector('h6')?.textContent.toLowerCase() || '';
              const description = item.querySelector('small')?.textContent.toLowerCase() || '';
              item.style.display = (title.includes(searchTerm) || description.includes(searchTerm)) ? '' : 'none';
            });
          });
        };
        setupSearch('taskSearch', '#taskList .task-item');
        setupSearch('projectSearch', '#projectList .project-item');
        setupSearch('eventSearch', '#eventList .event-item');
      },

      selectTask: function(taskId, taskTitle) {
        const selectedTaskInfo = document.getElementById('selectedTaskInfo');
        if (selectedTaskInfo) {
          selectedTaskInfo.innerHTML = `
            <div class="alert alert-success">
              <h6 class="mb-1"><i class="fas fa-check-circle me-2"></i>Tarea Seleccionada</h6>
              <p class="mb-0">${taskTitle}</p>
              <input type="hidden" name="selected_task_id" value="${taskId}">
              <button type="button" class="btn btn-sm btn-primary mt-2" onclick="ProcessInboxModule.confirmTaskLink(${taskId}, '${taskTitle.replace(/'/g, "\\'")}')">
                <i class="fas fa-link me-1"></i>Confirmar Vinculación
              </button>
            </div>`;
        }
        closeModal('taskSelectorModal');
      },

      confirmTaskLink: function(taskId, taskTitle) {
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
      },

      linkToSelectedProject: function() {
        const selectedProject = document.querySelector('input[name="selected_project"]:checked');
        if (!selectedProject) {
          ProcessInboxModule.showAlertModal('Selección requerida', 'Por favor, selecciona un proyecto para vincular.', 'warning');
          return;
        }
        const projectId = selectedProject.value;
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
      },

      linkToSelectedEvent: function() {
        const selectedEvent = document.querySelector('input[name="selected_event"]:checked');
        if (!selectedEvent) {
          ProcessInboxModule.showAlertModal('Selección requerida', 'Por favor, selecciona un evento para vincular.', 'warning');
          return;
        }
        const eventId = selectedEvent.value;
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
      },

      showAlertModal: function(title, message, type) {
        type = type || 'info';
        const modalElement = document.getElementById('alertModal');
        if (!modalElement) {
          alert(title + ': ' + message);
          return;
        }
        const icons = {
          success: 'fa-check-circle text-success',
          danger: 'fa-exclamation-triangle text-danger',
          warning: 'fa-exclamation-triangle text-warning',
          info: 'fa-info-circle text-info'
        };
        document.getElementById('alertModalLabel').innerHTML = '<i class="fas ' + (icons[type] || icons.info) + ' me-2"></i>' + title;
        document.getElementById('alertModalBody').innerHTML = '<p class="mb-0">' + message + '</p>';
        openModal('alertModal');
      },

      setupClassificationForm: function() {
        const confidenceRange = document.getElementById('confidenceRange');
        const confidenceValue = document.getElementById('confidenceValue');
        if (confidenceRange && confidenceValue) {
          confidenceValue.textContent = confidenceRange.value;
          confidenceRange.addEventListener('input', function() {
            confidenceValue.textContent = this.value;
          });
        }
        
        const classificationForm = document.getElementById('classificationForm');
        if (classificationForm) {
          classificationForm.removeEventListener('submit', ProcessInboxModule.handleClassificationSubmit);
          classificationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (!window.isSubmitting) {
              ProcessInboxModule.handleClassificationSubmit(e);
            }
            return false;
          });
        }
        
        const confirmReclassifyBtn = document.getElementById('confirmReclassifyBtn');
        if (confirmReclassifyBtn) {
          confirmReclassifyBtn.removeEventListener('click', ProcessInboxModule.confirmReclassification);
          confirmReclassifyBtn.addEventListener('click', ProcessInboxModule.confirmReclassification);
        }
        
        const reclassifyHistoryModal = document.getElementById('reclassifyHistoryModal');
        if (reclassifyHistoryModal) {
          reclassifyHistoryModal.removeEventListener('show.bs.modal', ProcessInboxModule.loadClassificationHistory);
          reclassifyHistoryModal.addEventListener('show.bs.modal', ProcessInboxModule.loadClassificationHistory);
        }
      },

      handleClassificationSubmit: async function(e) {
        if (e) {
          e.preventDefault();
          e.stopPropagation();
        }
        if (window.isSubmitting) {
          console.log('Ya se está procesando una solicitud');
          return;
        }
        const form = document.getElementById('classificationForm');
        if (!form) return;
        const formData = new FormData(form);
        const submitBtn = document.getElementById('saveClassificationBtn');
        if (!submitBtn) return;
        const originalText = submitBtn.innerHTML;
        window.isSubmitting = true;
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
          if (!response.ok) throw new Error('HTTP error! status: ' + response.status);
          const data = await response.json();
          if (data.success) {
            if (data.changed) {
              ProcessInboxModule.showReclassifyPreview(data.old_values, data.new_values);
              submitBtn.disabled = false;
              submitBtn.innerHTML = originalText;
            } else {
              ProcessInboxModule.showAlertModal('Clasificación guardada', 'Los cambios han sido guardados exitosamente.', 'success');
              await ProcessInboxModule.updateConsensusDisplay();
              ProcessInboxModule.updateFormValues(data.new_values);
              submitBtn.disabled = false;
              submitBtn.innerHTML = originalText;
            }
          } else {
            ProcessInboxModule.showAlertModal('Error', data.error || 'Error al guardar la clasificación', 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
          }
        } catch (error) {
          console.error('Error:', error);
          ProcessInboxModule.showAlertModal('Error', 'Error de conexión al guardar la clasificación', 'danger');
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalText;
        } finally {
          setTimeout(() => { window.isSubmitting = false; }, 1000);
        }
        return false;
      },

      updateFormValues: function(newValues) {
        const gtdCategorySelect = document.getElementById('gtdCategory');
        if (gtdCategorySelect && newValues.gtd_category) gtdCategorySelect.value = newValues.gtd_category;
        const actionTypeSelect = document.getElementById('actionType');
        if (actionTypeSelect) actionTypeSelect.value = newValues.action_type || '';
        const prioritySelect = document.getElementById('priority');
        if (prioritySelect && newValues.priority) prioritySelect.value = newValues.priority;
        const confidenceRange = document.getElementById('confidenceRange');
        const confidenceValue = document.getElementById('confidenceValue');
        if (confidenceRange && newValues.confidence) {
          confidenceRange.value = newValues.confidence;
          if (confidenceValue) confidenceValue.textContent = newValues.confidence;
        }
      },

      showReclassifyPreview: function(oldValues, newValues) {
        const oldPreview = document.getElementById('oldClassificationPreview');
        const newPreview = document.getElementById('newClassificationPreview');
        if (!oldPreview || !newPreview) return;
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
        window.pendingClassification = { old: oldValues, new: newValues };
        openModal('reclassifyConfirmModal');
      },

      confirmReclassification: function() {
        if (!window.pendingClassification) return;
        closeModal('reclassifyConfirmModal');
        const submitBtn = document.getElementById('saveClassificationBtn');
        if (!submitBtn) return;
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Reclasificando...';
        const form = document.getElementById('classificationForm');
        const formData = new FormData(form);
        formData.append('reclassification', 'true');
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
            ProcessInboxModule.showAlertModal('Reclasificación exitosa', 'El item ha sido reclasificado correctamente.', 'success');
            ProcessInboxModule.updateConsensusDisplay();
            ProcessInboxModule.updateFormValues(data.new_values);
          } else {
            ProcessInboxModule.showAlertModal('Error', data.error || 'Error al reclasificar', 'danger');
          }
        })
        .catch(error => {
          console.error('Error:', error);
          ProcessInboxModule.showAlertModal('Error', 'Error al procesar la reclasificación', 'danger');
        })
        .finally(() => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalText;
          window.pendingClassification = null;
          window.isSubmitting = false;
        });
      },

      loadClassificationHistory: async function() {
        const historyList = document.getElementById('classificationHistoryList');
        if (!historyList) return;
        const itemId = document.querySelector('[data-inbox-item-id]')?.dataset.inboxItemId;
        if (!itemId) {
          historyList.innerHTML = '<div class="alert alert-danger text-center">ID de item no encontrado</div>';
          return;
        }
        historyList.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-warning" role="status"></div><p class="mt-2">Cargando historial...</p></div>';
        try {
          const response = await fetch('/events/inbox/api/classification-history/' + itemId + '/');
          if (!response.ok) throw new Error('HTTP error! status: ' + response.status);
          const data = await response.json();
          if (data.success && data.history && data.history.length > 0) {
            let html = '<div class="timeline">';
            data.history.forEach((item, index) => {
              const date = new Date(item.created_at);
              const formattedDate = date.toLocaleDateString('es-ES', {
                day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
              });
              html += `
                <div class="timeline-item ${index === 0 ? 'latest' : ''}">
                  <div class="timeline-badge ${item.action === 'reclassified' ? 'bg-warning' : 'bg-info'}">
                    <i class="fas ${item.action === 'reclassified' ? 'fa-arrow-repeat' : 'fa-tag'}"></i>
                  </div>
                  <div class="timeline-content card mb-3">
                    <div class="card-body">
                      <div class="d-flex justify-content-between">
                        <h6 class="card-subtitle mb-2 text-muted">
                          <i class="fas fa-user-circle me-1"></i>${item.user || 'Sistema'}
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
                      ${item.notes ? `<p class="mt-2 mb-0 small"><i class="fas fa-comment me-1"></i>${item.notes}</p>` : ''}
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
      },

      updateConsensusDisplay: async function() {
        const itemId = document.querySelector('[data-inbox-item-id]')?.dataset.inboxItemId;
        if (!itemId) return;
        try {
          const response = await fetch('/events/inbox/api/consensus/' + itemId + '/');
          if (!response.ok) return;
          const data = await response.json();
          if (data.success) {
            const consensusCategoryEl = document.querySelector('.consensus-item:first-child .badge');
            if (consensusCategoryEl) {
              consensusCategoryEl.textContent = data.consensus_category ? data.consensus_category.charAt(0).toUpperCase() + data.consensus_category.slice(1) : 'Sin consenso';
            }
            const consensusActionEl = document.querySelector('.consensus-item:nth-child(2) .badge');
            if (consensusActionEl) {
              consensusActionEl.textContent = data.consensus_action ? data.consensus_action.charAt(0).toUpperCase() + data.consensus_action.slice(1) : 'Sin consenso';
            }
            const votesEl = document.querySelector('.consensus-item:last-child .badge');
            if (votesEl) votesEl.textContent = data.votes + ' usuario(s)';
            console.log('Consenso actualizado:', data);
          }
        } catch (error) {
          console.error('Error actualizando consenso:', error);
        }
      }
    };

    // Exponer funciones globales necesarias para el template
    window.selectTask = function(taskId, taskTitle) { ProcessInboxModule.selectTask(taskId, taskTitle); };
    window.confirmTaskLink = function(taskId, taskTitle) { ProcessInboxModule.confirmTaskLink(taskId, taskTitle); };
    window.linkToSelectedProject = function() { ProcessInboxModule.linkToSelectedProject(); };
    window.linkToSelectedEvent = function() { ProcessInboxModule.linkToSelectedEvent(); };
    window.quickReclassify = function(category, action, priority) {
      const form = document.getElementById('classificationForm');
      if (!form) return;
      if (category) document.querySelector('[name="gtd_category"]').value = category;
      if (action) document.querySelector('[name="action_type"]').value = action;
      if (priority) document.querySelector('[name="priority"]').value = priority;
      if (!window.isSubmitting) {
        const event = new Event('submit', { cancelable: true });
        form.dispatchEvent(event);
      }
    };
    window.testModals = function() {
      console.log('=== TEST DE CONFIGURACIÓN ===');
      console.log('projectOption:', document.getElementById('projectOption')?.value);
      console.log('eventOption:', document.getElementById('eventOption')?.value);
      console.log('assigned_to:', document.querySelector('[name="assigned_to"]')?.value);
      ProcessInboxModule.showAlertModal('Test', 'La configuración está funcionando correctamente.', 'success');
    };

    // Módulo de Process Inbox
    if (document.querySelector('.process-inbox-layout')) {
      ProcessInboxModule.init();
    }

    // Animar filas de tabla
    document.querySelectorAll('.admin-inbox-row, .panel-row, .inbox-row, tbody tr:not(.empty-state-cell)').forEach(function(row, index) {
      if (!row.classList.contains('empty-state-cell')) {
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';
        setTimeout(function() {
          row.style.transition = 'all 0.3s ease-out';
          row.style.opacity = '1';
          row.style.transform = 'translateX(0)';
        }, index * 50);
      }
    });

    // Inicializar modales con data-modal
    document.querySelectorAll('[data-modal]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var modalId = this.dataset.modal;
        if (modalId) {
          openModal(modalId);
        }
      });
    });

    // Inicializar toggles de tema en todas las páginas
    document.querySelectorAll('.theme-toggle, .kanban-theme-toggle, .kanban-organized-theme-toggle, #themeToggle, #themeToggleEnhanced, #themeToggleOrganized').forEach(function(btn) {
      btn.addEventListener('click', function() {
        if (window.KanbanModule) {
          window.KanbanModule.toggleTheme();
        } else {
          var currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
          var newTheme = currentTheme === 'dark' ? 'light' : 'dark';
          document.documentElement.setAttribute('data-theme', newTheme);
          localStorage.setItem('kanbanTheme', newTheme);
          var icon = this.querySelector('i');
          if (icon) {
            icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
          }
        }
      });
    });
  });

  // Cleanup on page unload
  window.addEventListener('beforeunload', function() {
    if (ManagementPanelModule.autoRefreshInterval) {
      clearInterval(ManagementPanelModule.autoRefreshInterval);
    }
  });

})();