/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Vanilla JS components
   File: m360-popover.js — popovers without Bootstrap
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const TOGGLE_ATTR = 'data-m360-toggle';
  const POPOVER_TYPE = 'popover';
  const POPOVER_CLASS = 'm360-popover';
  const OPEN_CLASS = 'm360-popover-open';

  function closeAll(except) {
    document.querySelectorAll('.' + POPOVER_CLASS + '.' + OPEN_CLASS).forEach(function (el) {
      if (el !== except) el.classList.remove(OPEN_CLASS);
    });
  }

  document.addEventListener('click', function (event) {
    const trigger = event.target.closest('[' + TOGGLE_ATTR + '="' + POPOVER_TYPE + '"]');
    if (!trigger) {
      const popover = event.target.closest('.' + POPOVER_CLASS);
      if (!popover) closeAll();
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    let popover = trigger.querySelector('.' + POPOVER_CLASS);
    if (!popover) {
      const content = trigger.getAttribute('data-m360-popover-content') || trigger.getAttribute('title') || '';
      popover = document.createElement('div');
      popover.className = POPOVER_CLASS;
      popover.innerHTML = '<div class="m360-popover-body">' + content + '</div>';
      trigger.appendChild(popover);
    }

    const isOpen = popover.classList.contains(OPEN_CLASS);
    closeAll(popover);
    if (!isOpen) popover.classList.add(OPEN_CLASS);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') closeAll();
  });
})();
