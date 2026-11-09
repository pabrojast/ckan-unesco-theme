/*
 * AI for Water Management (páginas del grupo con diseño propio, y páginas de
 * iniciativa que usan la misma plantilla).
 * Las franjas de IHP-WINS (barra de la cuenta, cabecera del sitio y migas)
 * están plegadas por defecto desde el primer pintado (ver ai-water.css); solo
 * queda arriba el menú de la iniciativa (.aiw-subnav). El botón "IHP-WINS
 * menu", a la derecha de ese menú, las despliega o las pliega. No aparecen al
 * pasar el ratón.
 */
(function () {
  'use strict';
  function init() {
    var body = document.body;
    var header = document.querySelector('header.masthead');
    var subnav = document.querySelector('.aiw-subnav');
    var bar = subnav && subnav.querySelector('.aiw-wrap');
    if (!body || !header || !bar) { return; }

    var root = document.documentElement;
    var account = document.querySelector('.account-masthead');
    var toolbar = document.querySelector('.aiw .toolbar');
    var crumbs = toolbar && toolbar.closest('.container');
    var folded = [account, header, crumbs].filter(Boolean);
    // Elemento de referencia para que el contenido no salte (justo después del menú)
    var anchor = subnav.nextElementSibling || subnav;
    if (!header.id) { header.id = 'aiw-site-header'; }

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'aiw-ribbon-toggle';
    button.setAttribute('aria-controls', header.id);
    button.innerHTML = '<span>IHP-WINS<span class="aiw-ribbon-toggle-more"> menu</span></span>' +
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
    bar.appendChild(button);
    // En el móvil el menú se desliza en horizontal: que se vea la pestaña actual
    var list = bar.querySelector('ul');
    var current = list && list.querySelector('[aria-current="page"]');
    if (current && list.scrollWidth > list.clientWidth) {
      list.scrollLeft = Math.max(0, current.offsetLeft - list.offsetLeft - 16);
    }

    function setHeights() {
      root.style.setProperty('--aiw-header-h', header.offsetHeight + 'px');
      root.style.setProperty('--aiw-acct-h', (account ? account.offsetHeight : 0) + 'px');
    }
    function setOpen(open) {
      // Arriba del todo, las franjas empujan el contenido al desplegarse. Más
      // abajo, el contenido no debe saltar: se compensa el desplazamiento.
      var scrolled = window.scrollY > 4;
      var before = anchor.getBoundingClientRect().top;
      if (scrolled) { body.classList.add('aiw-ribbons-instant'); }
      body.classList.toggle('aiw-ribbons-open', open);
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
      // Plegadas, no reciben el foco ni las leen los lectores de pantalla
      folded.forEach(function (el) { el.inert = !open; });
      if (scrolled) {
        // 'instant': el sitio usa scroll-behavior: smooth
        window.scrollBy({ top: anchor.getBoundingClientRect().top - before, left: 0, behavior: 'instant' });
        window.requestAnimationFrame(function () { body.classList.remove('aiw-ribbons-instant'); });
      }
    }
    setOpen(false);
    button.addEventListener('click', function () {
      setOpen(!body.classList.contains('aiw-ribbons-open'));
    });

    window.addEventListener('resize', setHeights);
    // Las alturas cambian si se abre el menú móvil de la cabecera
    if (window.ResizeObserver) {
      var ro = new ResizeObserver(setHeights);
      ro.observe(header);
      if (account) { ro.observe(account); }
    }
    setHeights();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

/*
 * Filtros por tipo en la lista de socios (Partners & people). Sin JavaScript
 * los botones quedan ocultos y se ve la lista completa.
 */
(function () {
  'use strict';
  function init() {
    document.querySelectorAll('.aiw-filters[data-aiw-filter-target]').forEach(function (bar) {
      var list = document.getElementById(bar.getAttribute('data-aiw-filter-target'));
      if (!list) { return; }
      var items = list.querySelectorAll('[data-type]');
      var buttons = bar.querySelectorAll('button[data-filter]');
      var count = bar.querySelector('.aiw-filter-count');
      function apply(filter) {
        var shown = 0;
        items.forEach(function (el) {
          var visible = filter === 'all' || el.getAttribute('data-type') === filter;
          el.hidden = !visible;
          if (visible) { shown += 1; }
        });
        buttons.forEach(function (b) {
          b.setAttribute('aria-pressed', b.getAttribute('data-filter') === filter ? 'true' : 'false');
        });
        if (count) { count.textContent = shown + (shown === 1 ? ' institution' : ' institutions'); }
      }
      buttons.forEach(function (b) {
        b.addEventListener('click', function () { apply(b.getAttribute('data-filter')); });
      });
      bar.hidden = false;
      apply('all');
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

/*
 * Menú "Add" del menú de la iniciativa (<details>, ver snippets/add_menu.html):
 * se cierra al pulsar fuera o con Escape. Sin JavaScript funciona igual.
 */
(function () {
  'use strict';
  function init() {
    var menus = document.querySelectorAll('details.aiw-add');
    if (!menus.length) { return; }
    document.addEventListener('click', function (e) {
      menus.forEach(function (d) { if (d.open && !d.contains(e.target)) { d.open = false; } });
    });
    menus.forEach(function (d) {
      d.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && d.open) { d.open = false; d.querySelector('summary').focus(); }
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
