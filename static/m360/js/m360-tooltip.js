/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Vanilla JS components
   File: m360-tooltip.js — tooltips without Bootstrap
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const TOGGLE_ATTR = 'data-m360-toggle';
  const TOOLTIP_TYPE = 'tooltip';

  document.addEventListener('mouseover', function (event) {
    const trigger = event.target.closest('[' + TOGGLE_ATTR + '="' + TOOLTIP_TYPE + '"]');
    if (!trigger) return;

    const title = trigger.getAttribute('data-m360-tooltip-title') || trigger.getAttribute('title') || '';
    if (!title) return;

    let tooltip = trigger.querySelector('.m360-tooltip');
    if (!tooltip) {
      tooltip = document.createElement('div');
      tooltip.className = 'm360-tooltip';
      tooltip.setAttribute('role', 'tooltip');
      trigger.appendChild(tooltip);
    }

    tooltip.textContent = title;
    trigger.classList.add('m360-tooltip-open');
    trigger.setAttribute('aria-describedby', 'm360-tooltip-' + Math.random().toString(36).slice(2));
  });

  document.addEventListener('mouseout', function (event) {
    const trigger = event.target.closest('[' + TOGGLE_ATTR + '="' + TOOLTIP_TYPE + '"]');
    if (!trigger) return;

    const tooltip = trigger.querySelector('.m360-tooltip');
    if (tooltip) {
      tooltip.remove();
    }
    trigger.classList.remove('m360-tooltip-open');
    trigger.removeAttribute('aria-describedby');
  });
})();
