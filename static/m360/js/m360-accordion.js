/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Vanilla JS components
   File: m360-accordion.js — accordion without Bootstrap
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  document.addEventListener('click', function (event) {
    var trigger = event.target.closest('[data-m360-toggle="collapse"]');
    if (!trigger) return;

    event.preventDefault();
    var targetId = trigger.getAttribute('data-m360-target');
    if (!targetId) return;

    var target = document.querySelector(targetId);
    if (!target) return;

    var expanded = trigger.getAttribute('aria-expanded') === 'true';
    var parent = trigger.closest('.m360-accordion');

    if (parent) {
      parent.querySelectorAll('.m360-accordion-body.m360-open').forEach(function (body) {
        if (body !== target) {
          body.classList.remove('m360-open');
          var otherTrigger = parent.querySelector('[data-m360-target="' + body.id + '"]');
          if (otherTrigger) otherTrigger.setAttribute('aria-expanded', 'false');
        }
      });
    }

    if (expanded) {
      target.classList.remove('m360-open');
      trigger.setAttribute('aria-expanded', 'false');
    } else {
      target.classList.add('m360-open');
      trigger.setAttribute('aria-expanded', 'true');
    }
  });
})();
