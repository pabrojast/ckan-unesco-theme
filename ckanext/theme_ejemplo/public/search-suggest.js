/*
 * Sugerencias mientras se escribe para los buscadores del portal.
 *
 * Se activa en cualquier <input name="q"> que tenga el atributo
 * data-suggest-scope o esté dentro de un elemento que lo tenga. El scope
 * (all | dataset | organization | group | initiative | memberstate) decide
 * qué fuentes consulta GET /api/theme/suggest (MyLogica.search_suggest).
 *
 * Sin JS, o si el endpoint falla, el formulario sigue funcionando igual:
 * Enter sin sugerencia seleccionada envía la búsqueda normal.
 */
(function () {
  'use strict';

  var script = document.currentScript;
  if (!script || !window.fetch) { return; }

  var ENDPOINT = script.getAttribute('data-suggest-url') || '/api/theme/suggest';
  var LABEL_ALL = script.getAttribute('data-label-all') || 'See all results for';
  var LABEL_EMPTY = script.getAttribute('data-label-empty') || 'No suggestions found';
  var LABEL_LIST = script.getAttribute('data-label-list') || 'Search suggestions';
  var MIN_CHARS = 2;
  var DEBOUNCE_MS = 200;
  var uid = 0;

  // Mismo plegado que search.normalize_text en el servidor, pero conservando
  // la posición de cada carácter para poder resaltar sobre el texto original.
  function fold(ch) {
    return ch.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  function highlight(container, text, tokens) {
    var folded = '';
    var map = [];
    for (var i = 0; i < text.length; i++) {
      var f = fold(text[i]);
      for (var k = 0; k < f.length; k++) { folded += f[k]; map.push(i); }
    }
    var marks = new Array(text.length);
    tokens.forEach(function (token) {
      if (!token) { return; }
      var from = 0;
      var at;
      while ((at = folded.indexOf(token, from)) !== -1) {
        for (var j = at; j < at + token.length; j++) { marks[map[j]] = true; }
        from = at + token.length;
      }
    });
    var pos = 0;
    while (pos < text.length) {
      var marked = !!marks[pos];
      var end = pos;
      while (end < text.length && !!marks[end] === marked) { end++; }
      var chunk = text.slice(pos, end);
      if (marked) {
        var mark = document.createElement('mark');
        mark.textContent = chunk;
        container.appendChild(mark);
      } else {
        container.appendChild(document.createTextNode(chunk));
      }
      pos = end;
    }
  }

  function tokenize(query) {
    return fold(query).replace(/[^\p{L}\p{N}]+/gu, ' ').trim().split(' ').filter(Boolean);
  }

  function attach(input, scope) {
    var form = input.form;
    var id = 'search-suggest-' + (++uid);
    var wrap = input.parentNode;
    var anchor = wrap;
    if (wrap.classList.contains('input-group')) {
      // Dentro de un .input-group el panel sería el último hijo y Bootstrap
      // le quitaría las esquinas redondeadas al botón: se ancla justo después.
      anchor = document.createElement('div');
      wrap.parentNode.insertBefore(anchor, wrap.nextSibling);
    }
    anchor.classList.add('search-suggest-anchor');

    var panel = document.createElement('div');
    panel.className = 'search-suggest-panel';
    panel.hidden = true;
    var list = document.createElement('ul');
    list.id = id;
    list.className = 'search-suggest-list';
    list.setAttribute('role', 'listbox');
    list.setAttribute('aria-label', LABEL_LIST);
    panel.appendChild(list);
    var status = document.createElement('div');
    status.className = 'search-suggest-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    panel.appendChild(status);
    anchor.appendChild(panel);

    input.setAttribute('autocomplete', 'off');
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-controls', id);

    var options = [];
    var active = -1;
    var timer = null;
    var controller = null;
    var lastQuery = null;

    function close() {
      panel.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      active = -1;
    }

    function open() {
      panel.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    function setActive(index) {
      if (active >= 0 && options[active]) {
        options[active].classList.remove('is-active');
        options[active].setAttribute('aria-selected', 'false');
      }
      active = index;
      if (active >= 0 && options[active]) {
        options[active].classList.add('is-active');
        options[active].setAttribute('aria-selected', 'true');
        input.setAttribute('aria-activedescendant', options[active].id);
        options[active].scrollIntoView({ block: 'nearest' });
      } else {
        input.removeAttribute('aria-activedescendant');
      }
    }

    function addOption(parent, href, build) {
      var li = document.createElement('li');
      li.id = id + '-opt-' + options.length;
      li.className = 'search-suggest-option';
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', 'false');
      var link = document.createElement('a');
      link.href = href;
      link.tabIndex = -1;
      li.appendChild(link);
      build(link);
      var index = options.length;
      li.addEventListener('mousemove', function () {
        if (active !== index) { setActive(index); }
      });
      parent.appendChild(li);
      options.push(li);
    }

    function render(data, query) {
      list.textContent = '';
      options = [];
      active = -1;
      var tokens = tokenize(query);
      var groups = data.groups || [];

      groups.forEach(function (group) {
        if (groups.length > 1 || scope === 'all') {
          var heading = document.createElement('li');
          heading.className = 'search-suggest-heading';
          heading.setAttribute('role', 'presentation');
          heading.textContent = group.label;
          list.appendChild(heading);
        }
        group.items.forEach(function (item) {
          addOption(list, item.url, function (link) {
            var title = document.createElement('span');
            title.className = 'search-suggest-title';
            highlight(title, item.title || '', tokens);
            link.appendChild(title);
            if (item.subtitle) {
              var sub = document.createElement('span');
              sub.className = 'search-suggest-subtitle';
              sub.textContent = item.subtitle;
              link.appendChild(sub);
            }
          });
        });
      });

      status.textContent = groups.length ? '' : LABEL_EMPTY;

      // Pie: la búsqueda completa de siempre, por si nada de lo sugerido sirve.
      if (form) {
        addOption(list, '#', function (link) {
          link.parentNode.classList.add('search-suggest-all');
          link.appendChild(document.createTextNode(LABEL_ALL + ' '));
          var strong = document.createElement('strong');
          strong.textContent = '\u201c' + query + '\u201d';
          link.appendChild(strong);
          link.addEventListener('click', function (event) {
            event.preventDefault();
            close();
            if (form.requestSubmit) { form.requestSubmit(); } else { form.submit(); }
          });
        });
      }
      open();
    }

    function request() {
      var query = input.value.trim();
      if (query.length < MIN_CHARS) {
        lastQuery = null;
        if (controller) { controller.abort(); }
        close();
        return;
      }
      if (query === lastQuery) {
        if (panel.hidden && list.childNodes.length) { open(); }
        return;
      }
      lastQuery = query;
      // Descarta la respuesta anterior: puede llegar después que la nueva.
      if (controller) { controller.abort(); }
      controller = window.AbortController ? new AbortController() : null;
      var url = ENDPOINT + (ENDPOINT.indexOf('?') === -1 ? '?' : '&') +
        'scope=' + encodeURIComponent(scope) + '&q=' + encodeURIComponent(query);
      fetch(url, {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' },
        signal: controller ? controller.signal : undefined
      }).then(function (response) {
        if (!response.ok) { throw new Error('HTTP ' + response.status); }
        return response.json();
      }).then(function (data) {
        if (input.value.trim() !== query) { return; }
        render(data, query);
      }).catch(function (error) {
        if (error && error.name === 'AbortError') { return; }
        lastQuery = null;
        close();
      });
    }

    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(request, DEBOUNCE_MS);
    });

    input.addEventListener('focus', function () {
      if (input.value.trim().length >= MIN_CHARS) { request(); }
    });

    input.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        if (!panel.hidden) { event.preventDefault(); close(); }
        return;
      }
      if (panel.hidden || !options.length) { return; }
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActive(active + 1 >= options.length ? 0 : active + 1);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActive(active <= 0 ? options.length - 1 : active - 1);
      } else if (event.key === 'Enter' && active >= 0) {
        // Sin opción activa no se intercepta: Enter envía el formulario.
        event.preventDefault();
        options[active].querySelector('a').click();
      }
    });

    document.addEventListener('click', function (event) {
      if (!wrap.contains(event.target) && !panel.contains(event.target)) { close(); }
    });
  }

  function init() {
    var inputs = document.querySelectorAll(
      'input[name="q"][data-suggest-scope], [data-suggest-scope] input[name="q"]');
    Array.prototype.forEach.call(inputs, function (input) {
      if (input.getAttribute('data-suggest-ready')) { return; }
      input.setAttribute('data-suggest-ready', '1');
      var holder = input.closest('[data-suggest-scope]');
      attach(input, holder.getAttribute('data-suggest-scope') || 'all');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
