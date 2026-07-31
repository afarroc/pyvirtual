/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Vanilla JS components
   File: m360-back-to-top.js — back to top behavior without Bootstrap
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var selector = '.back-to-top';
  var button = document.querySelector(selector);
  if (!button) return;

  var toggleVisibility = function () {
    button.style.display = window.pageYOffset > 100 ? 'flex' : 'none';
  };

  button.addEventListener('click', function (event) {
    event.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  window.addEventListener('scroll', toggleVisibility, { passive: true });
  toggleVisibility();
})();
