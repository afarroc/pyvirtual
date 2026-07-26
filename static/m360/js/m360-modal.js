/* ═══════════════════════════════════════════════════════════════════════════════
   M360 Design System — Vanilla JS components
   File: m360-modal.js — modal dialogs without Bootstrap
   ═══════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const OPEN_ATTR = 'data-m360-open';
  const CLOSE_ATTR = 'data-m360-close';
  const MODAL_CLASS = 'm360-modal';
  const ACTIVE_CLASS = 'm360-active';

  function openModal(modal) {
    if (!modal || modal.classList.contains(ACTIVE_CLASS)) return;
    modal.classList.add(ACTIVE_CLASS);
    const firstInput = modal.querySelector('input, select, textarea');
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 50);
    }
    document.body.style.overflow = 'hidden';
  }

  function closeModal(modal) {
    if (!modal || !modal.classList.contains(ACTIVE_CLASS)) return;
    modal.classList.remove(ACTIVE_CLASS);
    document.body.style.overflow = '';
  }

  function getTargetModal(trigger) {
    const targetId = trigger.getAttribute(OPEN_ATTR);
    if (!targetId) return null;
    return document.getElementById(targetId);
  }

  document.addEventListener('click', function (event) {
    const trigger = event.target.closest('[' + OPEN_ATTR + ']');
    if (trigger) {
      event.preventDefault();
      const modal = getTargetModal(trigger);
      if (modal) openModal(modal);
      return;
    }

    const closeTrigger = event.target.closest('[' + CLOSE_ATTR + ']');
    if (closeTrigger) {
      event.preventDefault();
      const modal = closeTrigger.closest('.' + MODAL_CLASS);
      if (modal) closeModal(modal);
      return;
    }

    const backdrop = event.target.closest('.' + MODAL_CLASS);
    if (backdrop && event.target === backdrop) {
      closeModal(backdrop);
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    const openModals = document.querySelectorAll('.' + MODAL_CLASS + '.' + ACTIVE_CLASS);
    if (openModals.length === 0) return;
    const last = openModals[openModals.length - 1];
    closeModal(last);
  });

  window.m360Modal = {
    open: openModal,
    close: closeModal
  };
})();
