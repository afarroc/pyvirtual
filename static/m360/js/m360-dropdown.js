/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Vanilla JS components
   File: m360-dropdown.js — dropdown menus without Bootstrap
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const TOGGLE_ATTR = 'data-m360-toggle';
  const DROPDOWN_CLASS = 'm360-dropdown';
  const MENU_CLASS = 'm360-dropdown-menu';
  const OPEN_CLASS = 'm360-open';

  function closeAll(except) {
    document.querySelectorAll('.' + DROPDOWN_CLASS + '.' + OPEN_CLASS).forEach(function (el) {
      if (el !== except) el.classList.remove(OPEN_CLASS);
    });
  }

  document.addEventListener('click', function (event) {
    const toggle = event.target.closest('[' + TOGGLE_ATTR + '="dropdown"]');
    if (toggle) {
      event.preventDefault();
      event.stopPropagation();
      const dropdown = toggle.closest('.' + DROPDOWN_CLASS);
      if (!dropdown) return;
      const isOpen = dropdown.classList.contains(OPEN_CLASS);
      closeAll(dropdown);
      if (!isOpen) dropdown.classList.add(OPEN_CLASS);
      return;
    }

    if (event.target.closest('.' + MENU_CLASS)) {
      return;
    }

    closeAll();
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') closeAll();
  });
})();
