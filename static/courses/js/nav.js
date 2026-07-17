(function () {
  "use strict";

  const toggle = document.querySelector('[data-nav-toggle]');
  const menu = document.querySelector('[data-nav-menu]');
  if (!toggle || !menu) return;

  const closeMenu = function () {
    menu.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
  };

  toggle.addEventListener('click', function () {
    const isOpen = menu.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });

  document.addEventListener('click', function (event) {
    if (!menu.contains(event.target) && !toggle.contains(event.target)) {
      closeMenu();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      closeMenu();
    }
  });

  const dropdowns = menu.querySelectorAll('.nav__dropdown');
  dropdowns.forEach(function (dropdown) {
    const trigger = dropdown.closest('li');
    if (!trigger) return;

    const triggerLink = trigger.querySelector(':scope > .nav__link');
    if (!triggerLink) return;

    triggerLink.addEventListener('click', function (event) {
      if (window.innerWidth <= 768) {
        event.preventDefault();
        const isOpen = dropdown.classList.toggle('is-open');
        dropdowns.forEach(function (other) {
          if (other !== dropdown) {
            other.classList.remove('is-open');
          }
        });
      }
    });
  });

  menu.addEventListener('click', function (event) {
    if (event.target.closest('.nav__dropdown')) {
      return;
    }
    dropdowns.forEach(function (dropdown) {
      dropdown.classList.remove('is-open');
    });
  });
})();

