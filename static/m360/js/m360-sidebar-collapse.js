/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Sidebar collapse without Bootstrap
   File: m360-sidebar-collapse.js — open/close sidebar submenus
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var TOGGLE_ATTR = 'data-m360-toggle';
  var COLLAPSE_VALUE = 'collapse';
  var TARGET_ATTR = 'data-m360-target';
  var PARENT_ATTR = 'data-m360-parent';
  var OPEN_CLASS = 'm360-open';

  function closeTarget(trigger, target) {
    target.classList.remove(OPEN_CLASS);
    trigger.setAttribute('aria-expanded', 'false');
  }

  function closeChildren(target) {
    target.querySelectorAll(':scope > .m360-sidebar-nav-item > .m360-sidebar-nav-link[' + TOGGLE_ATTR + '="' + COLLAPSE_VALUE + '"]').forEach(function (childTrigger) {
      var childTarget = document.querySelector(childTrigger.getAttribute(TARGET_ATTR));
      if (childTarget) closeTarget(childTrigger, childTarget);
    });
  }

  document.addEventListener('click', function (event) {
    var trigger = event.target.closest('[' + TOGGLE_ATTR + '="' + COLLAPSE_VALUE + '"]');
    if (!trigger) return;

    if (!trigger.closest('.m360-sidebar-nav') && !trigger.closest('.sidebar-nav')) return;

    event.preventDefault();

    var targetId = trigger.getAttribute(TARGET_ATTR);
    if (!targetId) return;
    var target = document.querySelector(targetId);
    if (!target) return;

    var isExpanded = trigger.getAttribute('aria-expanded') === 'true';

    var parentSelector = trigger.getAttribute(PARENT_ATTR);
    if (parentSelector) {
      var parent = document.querySelector(parentSelector);
      if (parent) {
        parent.querySelectorAll(':scope > .m360-sidebar-nav-item > .m360-sidebar-nav-link[' + TOGGLE_ATTR + '="' + COLLAPSE_VALUE + '"], :scope > .nav-item > .nav-link[' + TOGGLE_ATTR + '="' + COLLAPSE_VALUE + '"]').forEach(function (siblingTrigger) {
          if (siblingTrigger !== trigger) {
            var siblingTarget = document.querySelector(siblingTrigger.getAttribute(TARGET_ATTR));
            if (siblingTarget) {
              closeTarget(siblingTrigger, siblingTarget);
              closeChildren(siblingTarget);
            }
          }
        });
      }
    }

    if (isExpanded) {
      closeTarget(trigger, target);
      closeChildren(target);
    } else {
      target.classList.add(OPEN_CLASS);
      trigger.setAttribute('aria-expanded', 'true');
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      document.querySelectorAll('.m360-sidebar-nav .m360-sidebar-nav-link[' + TOGGLE_ATTR + '="' + COLLAPSE_VALUE + '"][aria-expanded="true"], .sidebar-nav .nav-link[' + TOGGLE_ATTR + '="' + COLLAPSE_VALUE + '"][aria-expanded="true"]').forEach(function (openTrigger) {
        var target = document.querySelector(openTrigger.getAttribute(TARGET_ATTR));
        if (target) {
          closeTarget(openTrigger, target);
          closeChildren(target);
        }
      });
    }
  });
})();