/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Mobile navbar collapse
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  function initNav() {
    var toggles = document.querySelectorAll('[data-nav-toggle]');
    toggles.forEach(function (toggle) {
      if (toggle.dataset.m360NavInit) return;
      toggle.dataset.m360NavInit = 'true';

      toggle.addEventListener('click', function (event) {
        event.preventDefault();
        var nav = toggle.closest('[data-nav-menu]');
        if (!nav) return;

        var isOpen = nav.classList.contains('is-open');

        if (isOpen) {
          nav.classList.remove('is-open');
          toggle.setAttribute('aria-expanded', 'false');
        } else {
          nav.classList.add('is-open');
          toggle.setAttribute('aria-expanded', 'true');
        }
      });
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        document.querySelectorAll('[data-nav-menu].is-open').forEach(function (nav) {
          nav.classList.remove('is-open');
          var toggle = nav.querySelector('[data-nav-toggle]');
          if (toggle) toggle.setAttribute('aria-expanded', 'false');
        });
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNav);
  } else {
    initNav();
  }
})();
