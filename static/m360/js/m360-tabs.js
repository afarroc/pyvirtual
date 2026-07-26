/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Vanilla JS components
   File: m360-tabs.js — tab navigation without Bootstrap
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  document.addEventListener('click', function (event) {
    var trigger = event.target.closest('[data-m360-toggle="tab"]');
    if (!trigger) return;

    event.preventDefault();
    var tabId = trigger.getAttribute('data-m360-target');
    if (!tabId) return;

    var tabPane = document.querySelector(tabId);
    if (!tabPane) return;

    var tabList = trigger.closest('[role="tablist"], .m360-tabs, .m360-mode-tabs');
    if (tabList) {
      tabList.querySelectorAll('[data-m360-toggle="tab"]').forEach(function (btn) {
        btn.classList.remove('m360-active');
        btn.setAttribute('aria-selected', 'false');
      });
    }

    trigger.classList.add('m360-active');
    trigger.setAttribute('aria-selected', 'true');

    var activePanes = tabPane.closest('.m360-tab-content, main, .m360-page')?.querySelectorAll('.m360-tab-pane') || document.querySelectorAll('.m360-tab-pane');
    activePanes.forEach(function (pane) {
      pane.classList.remove('m360-active');
    });

    tabPane.classList.add('m360-active');
  });
})();
