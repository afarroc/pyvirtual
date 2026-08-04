
    (function() {
      'use strict';

      const Utils = {
        getElement: function(selector) {
          return document.querySelector(selector);
        },
        getElements: function(selector) {
          return document.querySelectorAll(selector);
        },
        toggleClass: function(el, className) {
          el.classList.toggle(className);
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
        },

        initDropdowns: function() {
          const qaToggle = Utils.getElement('#quickActionsToggle');
          const qaMenu = Utils.getElement('#quickActionsMenu');
          if (qaToggle && qaMenu) {
            qaToggle.addEventListener('click', (e) => {
              e.stopPropagation();
              DropdownManager.toggle(qaToggle, qaMenu);
            });
          }

          const notifToggle = Utils.getElement('#notificationsToggle');
          const notifMenu = Utils.getElement('#notificationsMenu');
          if (notifToggle && notifMenu) {
            notifToggle.addEventListener('click', (e) => {
              e.stopPropagation();
              DropdownManager.toggle(notifToggle, notifMenu);
            });
          }

          const msgToggle = Utils.getElement('#messagesToggle');
          const msgMenu = Utils.getElement('#messagesMenu');
          if (msgToggle && msgMenu) {
            msgToggle.addEventListener('click', (e) => {
              e.stopPropagation();
              DropdownManager.toggle(msgToggle, msgMenu);
            });
          }

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

          document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
              e.preventDefault();
              this.searchInput.focus();
              this.searchInput.select();
            }
          });

          this.searchInput.addEventListener('input', () => {
            if (this.searchInput.value.length > 0) {
              this.searchBar.classList.add('has-value');
            } else {
              this.searchBar.classList.remove('has-value');
            }
          });

          if (this.searchClear) {
            this.searchClear.addEventListener('click', () => {
              this.searchInput.value = '';
              this.searchBar.classList.remove('has-value');
              this.searchInput.focus();
            });
          }
        },

        initNotifications: function() {
          const markBtn = Utils.getElement('#markAllRead');
          if (markBtn) {
            markBtn.addEventListener('click', () => {
              const items = Utils.getElements('.notif-item.unread');
              items.forEach(item => item.classList.remove('unread'));
              const badge = Utils.getElement('#notifBadge');
              if (badge) badge.textContent = '0';
            });
          }

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
                  const remaining = Utils.getElements('.notif-item:not(.unread)').length;
                  const unread = Utils.getElements('.notif-item.unread').length;
                  badge.textContent = unread + remaining;
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
                if (count > 0) badge.textContent = count - 1;
                if (badge.textContent === '0') badge.style.display = 'none';
              }
            });
          });
        }
      };

      // ==========================================
      // SIDEBAR MODULE
      // ==========================================
      const SidebarModule = {
        init: function() {
          this.sidebar = Utils.getElement('#mainSidebar');
          this.menuToggle = Utils.getElement('#menuToggle');

          this.initToggle();
          this.initNavigation();
          this.initUpgrade();
          this.initTooltips();
        },

        initToggle: function() {
          if (!this.menuToggle || !this.sidebar) return;

          this.menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            Utils.toggleClass(this.sidebar, 'open');
          });

          document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
              const isInside = this.sidebar.contains(e.target) || this.menuToggle.contains(e.target);
              if (!isInside) {
                this.sidebar.classList.remove('open');
              }
            }
          });

          window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
              this.sidebar.classList.remove('open');
            }
          });
        },

        initNavigation: function() {
          const links = Utils.getElements('.sidebar-nav a');
          links.forEach(link => {
            link.addEventListener('click', (e) => {
              const li = link.closest('li');
              if (li) {
                const allLis = link.closest('ul').querySelectorAll('li');
                allLis.forEach(l => l.classList.remove('active'));
                li.classList.add('active');

                if (window.innerWidth <= 768) {
                  this.sidebar.classList.remove('open');
                }
              }
            });
          });

          this.initSidebarDropdowns();
        },

        initSidebarDropdowns: function() {
          const toggles = Utils.getElements('.sidebar-nav-item.has-dropdown > .sidebar-nav-link.dropdown-toggle');
          toggles.forEach(toggle => {
            toggle.addEventListener('click', function(e) {
              e.preventDefault();
              e.stopPropagation();
              const li = this.closest('li.sidebar-nav-item');
              if (!li) return;
              const isOpen = li.classList.contains('open');
              const parentUl = li.closest('ul');
              if (parentUl) {
                parentUl.querySelectorAll(':scope > .sidebar-nav-item.has-dropdown.open').forEach(openLi => {
                  if (openLi !== li) openLi.classList.remove('open');
                });
              }
              if (isOpen) {
                li.classList.remove('open');
                this.setAttribute('aria-expanded', 'false');
              } else {
                li.classList.add('open');
                this.setAttribute('aria-expanded', 'true');
              }
            });
          });
        },

        initTooltips: function() {
          const tooltipLinks = Utils.getElements('[data-tooltip]');
          tooltipLinks.forEach(link => {
            link.addEventListener('mouseenter', function() {
              this.setAttribute('data-tooltip-active', 'true');
            });
            link.addEventListener('mouseleave', function() {
              this.removeAttribute('data-tooltip-active');
            });
          });
        },

        initUpgrade: function() {
          const upgradeBtn = Utils.getElement('#upgradeBtn');
          if (upgradeBtn) {
            upgradeBtn.addEventListener('click', () => {
              alert('🚀 Upgrade to Pro - All features unlocked!');
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
          this.initTimeline();
          this.initDateRange();
          this.initNewProject();
        },

        initStats: function() {
          const statValues = Utils.getElements('.stat-value');
          statValues.forEach(el => {
            const originalText = el.textContent;
            const isCurrency = originalText.includes('$');
            const isNumber = !isCurrency && !isNaN(parseFloat(originalText));

            if (isCurrency) {
              const num = parseFloat(originalText.replace(/[$,K]/g, ''));
              this.animateCounter(el, 0, num * 1000, 1500, (val) => {
                if (val >= 1000) {
                  return '$' + (val / 1000).toFixed(1) + 'K';
                }
                return '$' + val.toFixed(0);
              });
            } else if (isNumber) {
              const num = parseInt(originalText.replace(/,/g, ''));
              this.animateCounter(el, 0, num, 1500);
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
              periodBtns.forEach(b => b.classList.remove('active'));
              btn.classList.add('active');

              const bars = Utils.getElements('.bar');
              bars.forEach((bar, i) => {
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
              const rows = Array.from(tbody.querySelectorAll('tr'));

              rows.sort((a, b) => {
                let aVal = a.querySelector(`td:${header.cellIndex + 1}`)?.textContent.trim() || '';
                let bVal = b.querySelector(`td:${header.cellIndex + 1}`)?.textContent.trim() || '';

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

        initTimeline: function() {
          const viewBtn = Utils.getElement('#timelineView');
          if (viewBtn) {
            viewBtn.addEventListener('click', () => {
              const items = Utils.getElements('.timeline-item');
              items.forEach((item, i) => {
                setTimeout(() => {
                  item.style.transition = 'all 0.3s ease';
                  item.style.opacity = item.style.opacity === '0' ? '1' : '0';
                  item.style.transform = item.style.transform === 'translateX(20px)' ? 'translateX(0)' : 'translateX(20px)';
                }, i * 80);
              });
            });
          }
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

        initNewProject: function() {
          const btn = Utils.getElement('#newProjectBtn');
          if (btn) {
            btn.addEventListener('click', () => {
              const modal = document.createElement('div');
              modal.style.cssText = `
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 999;
                animation: fadeIn 0.3s ease;
              `;
              modal.innerHTML = `
                <div style="
                  background: white;
                  padding: 2rem;
                  border-radius: 16px;
                  max-width: 400px;
                  width: 90%;
                  box-shadow: 0 24px 64px rgba(0,0,0,0.2);
                  animation: slideUp 0.3s ease;
                ">
                  <h3 style="margin-bottom:0.5rem;">New Project</h3>
                  <p style="color:var(--text-muted);font-size:0.875rem;margin-bottom:1.5rem;">Create a new project to get started</p>
                  <div style="display:flex;flex-direction:column;gap:0.75rem;">
                    <input type="text" placeholder="Project name" style="padding:0.6rem 1rem;border:1px solid var(--border);border-radius:8px;font-family:inherit;font-size:0.875rem;">
                    <textarea placeholder="Description" rows="3" style="padding:0.6rem 1rem;border:1px solid var(--border);border-radius:8px;font-family:inherit;font-size:0.875rem;resize:vertical;"></textarea>
                    <div style="display:flex;gap:0.5rem;justify-content:flex-end;margin-top:0.5rem;">
                      <button class="btn btn-ghost" id="modalCancel">Cancel</button>
                      <button class="btn btn-primary" id="modalCreate">Create Project</button>
                    </div>
                  </div>
                </div>
                <style>
                  @keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
                  @keyframes slideUp { from { transform:translateY(20px); opacity:0; } to { transform:translateY(0); opacity:1; } }
                </style>
              `;
              document.body.appendChild(modal);

              const cancel = modal.querySelector('#modalCancel');
              const create = modal.querySelector('#modalCreate');

              const closeModal = () => {
                modal.style.opacity = '0';
                modal.style.transition = 'opacity 0.3s ease';
                setTimeout(() => modal.remove(), 300);
              };

              cancel.addEventListener('click', closeModal);
              create.addEventListener('click', () => {
                alert('🚀 Project created successfully!');
                closeModal();
              });
              modal.addEventListener('click', (e) => {
                if (e.target === modal) closeModal();
              });
            });
          }
        }
      };

      document.addEventListener('DOMContentLoaded', function() {
        DropdownManager.init();
        HeaderModule.init();
        SidebarModule.init();
        DashboardModule.init();
      });

    })();
  