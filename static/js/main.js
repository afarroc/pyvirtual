/**
 * Management360 - Dashboard JavaScript
 * Funcionalidades: Header dropdowns, Sidebar con anidamiento multinivel,
 * Dashboard stats, tabs, charts y modales
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

  // ==========================================
  // INIT
  // ==========================================
  document.addEventListener('DOMContentLoaded', function() {
    DropdownManager.init();
    HeaderModule.init();
    SidebarModule.init();
    DashboardModule.init();
  });

})();