/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Vanilla JS components
   File: m360-nav.js — mobile nav toggle without Bootstrap
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  document.addEventListener('click', function (event) {
    var toggle = event.target.closest('[data-nav-toggle]');
    if (!toggle) return;

    event.preventDefault();
    var nav = toggle.closest('[data-nav-menu]');
    if (!nav) return;

    var isOpen = nav.classList.contains('is-open');
    var expanded = toggle.getAttribute('aria-expanded') === 'true';

    if (isOpen) {
      nav.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    } else {
      nav.classList.add('is-open');
      toggle.setAttribute('aria-expanded', 'true');
    }
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
})();
