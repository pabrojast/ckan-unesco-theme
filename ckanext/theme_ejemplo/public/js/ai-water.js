/*
 * AI for Water Management (páginas del grupo con diseño propio).
 * La cabecera del sitio se oculta al bajar por la página y vuelve a
 * aparecer arriba del todo, al acercar el ratón al borde superior o al
 * entrar en ella con el teclado. El menú de la iniciativa (.aiw-subnav)
 * queda fijo arriba mientras tanto (ver ai-water.css).
 */
(function () {
  'use strict';
  function init() {
    var body = document.body;
    var header = document.querySelector('header.masthead');
    if (!body || !header || !document.querySelector('.aiw')) { return; }

    body.classList.add('aiw-autohide');
    var root = document.documentElement;
    var hovering = false;
    var ticking = false;

    function setHeight() {
      root.style.setProperty('--aiw-header-h', header.offsetHeight + 'px');
    }
    function update() {
      ticking = false;
      var atTop = window.scrollY <= 10;
      body.classList.toggle('aiw-header-hidden', !atTop && !hovering);
    }
    function requestUpdate() {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    }
    function show() { hovering = true; update(); }
    function hide() { hovering = false; update(); }

    // Franja invisible en el borde superior: al acercar el ratón aparece la cabecera
    var zone = document.createElement('div');
    zone.className = 'aiw-reveal-zone';
    zone.setAttribute('aria-hidden', 'true');
    body.appendChild(zone);
    zone.addEventListener('mouseenter', show);
    header.addEventListener('mouseenter', show);
    header.addEventListener('mouseleave', hide);
    // Teclado: al entrar en la cabecera con Tab se muestra; al salir se oculta
    header.addEventListener('focusin', show);
    header.addEventListener('focusout', function (e) {
      if (!header.contains(e.relatedTarget)) { hide(); }
    });

    window.addEventListener('scroll', requestUpdate, { passive: true });
    window.addEventListener('resize', function () { setHeight(); requestUpdate(); });
    // La altura cambia si se abre el menú móvil de la cabecera
    if (window.ResizeObserver) { new ResizeObserver(setHeight).observe(header); }
    setHeight();
    update();
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
