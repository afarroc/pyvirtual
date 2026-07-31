/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Sidebar responsive toggle + collapse + focus trap
   File: m360-sidebar-toggle.js — mobile/desktop sidebar state management
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var TOGGLE_ATTR = 'data-m360-toggle';
  var SIDEBAR_VALUE = 'sidebar';
  var TARGET_ATTR = 'data-m360-target';
  var OPEN_CLASS = 'sidebar-open';
  var OVERLAY_ATTR = 'data-m360-sidebar-overlay';
  var COLLAPSED_CLASS = 'is-collapsed';
  var STORAGE_KEY = 'm360-sidebar-collapsed';

  function openSidebar(sidebar, overlay, root) {
    if (root) root.classList.add(OPEN_CLASS);
    if (sidebar) sidebar.classList.add('m360-open');
    if (overlay) overlay.classList.add('is-open');
  }

  function closeSidebar(sidebar, overlay, root) {
    if (root) root.classList.remove(OPEN_CLASS);
    if (sidebar) sidebar.classList.remove('m360-open');
    if (overlay) overlay.classList.remove('is-open');
  }

  function getRoot() {
    return document.querySelector('.m360-root');
  }

  function getOverlay(sidebar) {
    var selector = sidebar.getAttribute(OVERLAY_ATTR);
    if (!selector) return document.querySelector('.m360-sidebar-overlay');
    return document.querySelector(selector);
  }

  /* --------------------------------------------------------------------------
     Collapse / expand desktop sidebar
     -------------------------------------------------------------------------- */
  function toggleCollapsed(sidebar) {
    if (!sidebar) return;
    var isCollapsed = sidebar.classList.contains(COLLAPSED_CLASS);
    if (isCollapsed) {
      sidebar.classList.remove(COLLAPSED_CLASS);
      localStorage.removeItem(STORAGE_KEY);
    } else {
      sidebar.classList.add(COLLAPSED_CLASS);
      localStorage.setItem(STORAGE_KEY, 'true');
    }
  }

  function restoreCollapsedState(sidebar) {
    if (!sidebar) return;
    var stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'true') {
      sidebar.classList.add(COLLAPSED_CLASS);
    }
  }

  document.addEventListener('click', function (event) {
    var collapseTrigger = event.target.closest('[' + TOGGLE_ATTR + '="sidebar-collapse"]');
    if (collapseTrigger) {
      var sidebar = collapseTrigger.closest('.m360-root') ? collapseTrigger.closest('.m360-root').querySelector('#sidebar') : document.querySelector('#sidebar');
      toggleCollapsed(sidebar);
      return;
    }

    var trigger = event.target.closest('[' + TOGGLE_ATTR + '="' + SIDEBAR_VALUE + '"]');
    if (!trigger) return;

    var targetId = trigger.getAttribute(TARGET_ATTR);
    if (!targetId) return;
    var sidebar = document.querySelector(targetId);
    if (!sidebar) return;

    var overlay = getOverlay(sidebar);
    var root = getRoot();
    var isExpanded = trigger.getAttribute('aria-expanded') === 'true';

    if (isExpanded) {
      closeSidebar(sidebar, overlay, root);
      trigger.setAttribute('aria-expanded', 'false');
    } else {
      openSidebar(sidebar, overlay, root);
      trigger.setAttribute('aria-expanded', 'true');
    }
  });

  /* --------------------------------------------------------------------------
     Overlay click closes sidebar
     -------------------------------------------------------------------------- */
  document.addEventListener('click', function (event) {
    var sidebar = document.querySelector('.m360-page-layout > #sidebar.m360-open');
    if (!sidebar) return;

    var overlay = getOverlay(sidebar);
    if (!overlay) return;

    if (event.target === overlay) {
      var trigger = document.querySelector('[' + TOGGLE_ATTR + '="' + SIDEBAR_VALUE + '"][aria-expanded="true"]');
      closeSidebar(sidebar, overlay, getRoot());
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
    }
  });

  /* --------------------------------------------------------------------------
     Keyboard: Escape closes sidebar / submenus
     -------------------------------------------------------------------------- */
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;

    // Close mobile sidebar first
    var sidebar = document.querySelector('.m360-page-layout > #sidebar.m360-open');
    if (sidebar) {
      var trigger = document.querySelector('[' + TOGGLE_ATTR + '="' + SIDEBAR_VALUE + '"][aria-expanded="true"]');
      var overlay = getOverlay(sidebar);
      closeSidebar(sidebar, overlay, getRoot());
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
      if (trigger) trigger.focus();
      return;
    }

    // Close open submenus
    document.querySelectorAll('.m360-sidebar-nav .m360-sidebar-nav-link[' + TOGGLE_ATTR + '="collapse"][aria-expanded="true"], .sidebar-nav .nav-link[' + TOGGLE_ATTR + '="collapse"][aria-expanded="true"]').forEach(function (openTrigger) {
      var target = document.querySelector(openTrigger.getAttribute(TARGET_ATTR));
      if (target) {
        target.classList.remove('m360-open');
        openTrigger.setAttribute('aria-expanded', 'false');
      }
    });
  });

  /* --------------------------------------------------------------------------
     Focus trap for mobile overlay
     -------------------------------------------------------------------------- */
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Tab') return;

    var sidebar = document.querySelector('.m360-page-layout > #sidebar.m360-open');
    if (!sidebar) return;

    var focusable = sidebar.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])');
    if (!focusable.length) return;

    var first = focusable[0];
    var last = focusable[focusable.length - 1];

    if (event.shiftKey) {
      if (document.activeElement === first) {
        event.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  /* --------------------------------------------------------------------------
     Init: restore collapsed state on load
     -------------------------------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', function () {
    var sidebar = document.querySelector('#sidebar');
    restoreCollapsedState(sidebar);
  });
})();
