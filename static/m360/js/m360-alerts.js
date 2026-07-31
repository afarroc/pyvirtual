/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Vanilla JS components
   File: m360-alerts.js — alert dismiss without Bootstrap
   Replaces: data-bs-dismiss="alert"
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const DISMISS_ATTR = 'data-m360-dismiss';
  const ALERT_SELECTOR = '.alert';

  document.addEventListener('click', function (event) {
    const trigger = event.target.closest('[' + DISMISS_ATTR + '="alert"]');
    if (!trigger) return;

    const alert = trigger.closest(ALERT_SELECTOR);
    if (!alert) return;

    event.preventDefault();
    alert.style.transition = 'opacity 0.5s ease';
    alert.style.opacity = '0';
    setTimeout(function () { alert.remove(); }, 500);
  });

  document.addEventListener('DOMContentLoaded', function () {
    var persistent = '.alert:not(.alert-persistent)';
    document.querySelectorAll(persistent).forEach(function (alert) {
      setTimeout(function () {
        if (alert.parentNode) {
          alert.style.transition = 'opacity 0.5s ease';
          alert.style.opacity = '0';
          setTimeout(function () { alert.remove(); }, 500);
        }
      }, 5000);
    });
  });
})();
