(function () {
  "use strict";

  const grid = document.getElementById('grid');
  const typeFilter = document.getElementById('typeFilter');
  const ocrFilter = document.getElementById('ocrFilter');
  const pdfaFilter = document.getElementById('pdfaFilter');
  const searchInput = document.getElementById('search');
  const resetButton = document.getElementById('resetFilters');

  if (!grid) return;

  const getCardData = function (card) {
    return {
      type: (card.getAttribute('data-type') || '').toLowerCase(),
      ocr: (card.getAttribute('data-ocr') || '').toLowerCase(),
      pdfa: (card.getAttribute('data-pdfa') || '').toLowerCase(),
      title: (card.querySelector('.m360-text-lg')?.textContent || '').toLowerCase(),
      id: (card.querySelector('.m360-text-muted')?.textContent || '').toLowerCase(),
    };
  };

  const matchesCard = function (card) {
    const data = getCardData(card);
    const searchTerm = (searchInput?.value || '').trim().toLowerCase();

    const matchesType = !typeFilter?.value || data.type === typeFilter.value.toLowerCase();
    const matchesOcr = !ocrFilter?.value || data.ocr === ocrFilter.value.toLowerCase();
    const matchesPdfa = !pdfaFilter?.value || data.pdfa === pdfaFilter.value.toLowerCase();
    const matchesSearch = !searchTerm || data.title.includes(searchTerm) || data.id.includes(searchTerm);

    return matchesType && matchesOcr && matchesPdfa && matchesSearch;
  };

  const applyFilters = function () {
    const cards = grid.querySelectorAll('.m360-card');
    cards.forEach(function (card) {
      const visible = matchesCard(card);
      card.style.display = visible ? '' : 'none';
    });
  };

  const resetFilters = function () {
    if (typeFilter) typeFilter.value = '';
    if (ocrFilter) ocrFilter.value = '';
    if (pdfaFilter) pdfaFilter.value = '';
    if (searchInput) searchInput.value = '';
    applyFilters();
  };

  if (typeFilter) typeFilter.addEventListener('change', applyFilters);
  if (ocrFilter) ocrFilter.addEventListener('change', applyFilters);
  if (pdfaFilter) pdfaFilter.addEventListener('change', applyFilters);
  if (searchInput) searchInput.addEventListener('input', applyFilters);
  if (resetButton) resetButton.addEventListener('click', resetFilters);
})();
