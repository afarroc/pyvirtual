/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Vanilla JS components
   File: m360-tabs.js — tab navigation without Bootstrap
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  function updateTabContext(trigger) {
    var titleEl = document.getElementById('tab-page-title');
    var breadcrumbEl = document.getElementById('tab-breadcrumb-current');
    if (!titleEl || !breadcrumbEl) return;

    var tabTitle = trigger.getAttribute('data-tab-title');
    var tabBreadcrumb = trigger.getAttribute('data-tab-breadcrumb');
    if (tabTitle) titleEl.textContent = tabTitle;
    if (tabBreadcrumb) breadcrumbEl.textContent = tabBreadcrumb;
  }

  function bindTabs() {
    document.querySelectorAll('button[data-m360-toggle="tab"]').forEach(function (tabEl) {
      tabEl.addEventListener('click', function (event) {
        var targetId = tabEl.getAttribute('data-m360-target');
        if (!targetId) return;

        event.preventDefault();
        var tabPane = document.querySelector(targetId);
        if (!tabPane) return;

        var tabList = tabEl.closest('[role="tablist"], .m360-tabs, .m360-mode-tabs');
        if (tabList) {
          tabList.querySelectorAll('[data-m360-toggle="tab"]').forEach(function (btn) {
            btn.classList.remove('m360-active');
            btn.setAttribute('aria-selected', 'false');
          });
        }

        tabEl.classList.add('m360-active');
        tabEl.setAttribute('aria-selected', 'true');

    var activePanes = (tabPane.closest('.m360-tab-content, main, .m360-page') || document).querySelectorAll('.m360-tab-pane');
    activePanes.forEach(function (pane) {
      pane.classList.remove('m360-active');
    });

        tabPane.classList.add('m360-active');
        updateTabContext(tabEl);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindTabs);
  } else {
    bindTabs();
  }
})();
