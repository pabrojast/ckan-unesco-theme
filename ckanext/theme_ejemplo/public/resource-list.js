/* Lista pública: la agrupación y los filtros se resuelven siempre en servidor. */
(function () {
  'use strict';
  var section = document.getElementById('dataset-resources');
  if (!section || section.dataset.initialized) return;
  section.dataset.initialized = 'true';
  section.addEventListener('click', function (event) {
    var button = event.target.closest('.resource-read-more');
    if (!button) return;
    var wrapper = button.closest('.description-wrapper');
    var expanded = button.getAttribute('aria-expanded') === 'true';
    wrapper.querySelector('.description-full').hidden = expanded;
    wrapper.querySelector('.description.excerpt').hidden = !expanded;
    button.setAttribute('aria-expanded', String(!expanded));
    button.textContent = expanded ? button.dataset.labelMore : button.dataset.labelLess;
  });
  var search = document.getElementById('resources-search');
  if (!search) return;
  var format = document.getElementById('resources-format-filter');
  var allFiles = document.getElementById('resources-all-files');
  var list = document.getElementById('resources-list');
  var status = document.getElementById('resources-status');
  var pagination = document.getElementById('resources-pagination-links');
  var labels = JSON.parse(document.getElementById('resources-labels').textContent);
  var perPage = Number(section.dataset.perPage);
  var controller, timer, sequence = 0;

  function renderPages(total, current) {
    pagination.replaceChildren();
    var last = Math.ceil(total / perPage);
    if (last <= 1) return;
    function add(text, page, disabled, active) {
      var li = document.createElement('li');
      var button = document.createElement('button');
      button.type = 'button'; button.textContent = text; button.disabled = disabled;
      button.dataset.page = page;
      button.setAttribute('aria-label', /^\d+$/.test(String(text)) ? labels.page + ' ' + page : text);
      if (active) button.setAttribute('aria-current', 'page');
      li.appendChild(button); pagination.appendChild(li);
    }
    add(labels.previous, current - 1, current === 1, false);
    var previous = 0;
    for (var page = 1; page <= last; page++) {
      if (page !== 1 && page !== last && Math.abs(page - current) > 1) continue;
      if (previous && page - previous > 1) {
        var gap = document.createElement('li'); gap.textContent = '…'; pagination.appendChild(gap);
      }
      add(String(page), page, false, page === current); previous = page;
    }
    add(labels.next, current + 1, current === last, false);
  }
  function load(page) {
    if (controller) controller.abort();
    controller = new AbortController();
    var requestId = ++sequence;
    list.classList.add('is-loading'); list.setAttribute('aria-busy', 'true');
    var params = new URLSearchParams({page: page, limit: perPage, q: search.value.trim(),
      format: format.value, mode: allFiles && allFiles.checked ? 'all' : 'grouped'});
    fetch(section.dataset.url + '?' + params.toString(), {signal: controller.signal})
      .then(function (response) { if (!response.ok) throw new Error('HTTP ' + response.status); return response.json(); })
      .then(function (data) {
        if (requestId !== sequence) return;
        list.innerHTML = data.html;
        status.textContent = labels.results + ': ' + data.total; status.hidden = false;
        renderPages(data.total, data.page);
      })
      .catch(function (error) {
        if (error.name !== 'AbortError' && requestId === sequence) {
          status.textContent = labels.error; status.hidden = false;
        }
      })
      .finally(function () {
        if (requestId === sequence) { list.classList.remove('is-loading'); list.removeAttribute('aria-busy'); }
      });
  }
  search.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { load(1); }, 300); });
  format.addEventListener('change', function () { clearTimeout(timer); load(1); });
  if (allFiles) allFiles.addEventListener('change', function () { clearTimeout(timer); load(1); });
  pagination.addEventListener('click', function (event) {
    var button = event.target.closest('button[data-page]');
    if (button && !button.disabled) load(Number(button.dataset.page));
  });
  renderPages(Number(section.dataset.total), 1);
})();
