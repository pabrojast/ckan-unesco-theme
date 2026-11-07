(function () {
  'use strict';
  var back = document.querySelector('[data-ihpix-back]');
  if (!back) return;
  // Solo reutilizamos el historial cuando venimos de otra página de IHP IX.
  // Los accesos directos conservan el enlace jerárquico generado en servidor.
  var previous;
  try { previous = new URL(document.referrer); } catch (error) { return; }
  var current = new URL(window.location.href);
  if (previous.origin !== current.origin || previous.pathname === current.pathname ||
      !/^(?:\/[a-z]{2}(?:[-_][A-Za-z]{2})?)?\/(?:ihpix(?:\/|$)|ckan-admin\/ihpix(?:\/|$)|(?:user|group|organization)\/[^/]+\/ihpix(?:\/|$))/.test(previous.pathname)) return;
  back.href = previous.href;
  back.removeAttribute('data-ihpix-progress-parent');
  back.addEventListener('click', function (event) {
    if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey ||
        event.shiftKey || event.altKey || window.history.length <= 1) return;
    event.preventDefault();
    window.history.back();
  });
}());
