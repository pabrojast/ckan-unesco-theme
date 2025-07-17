// Bootstrap 5 Initialization Module
// Inicialización de componentes Bootstrap 5 para CKAN

(function (ckan, jQuery) {
  'use strict';

  // Inicializar tooltips de Bootstrap 5
  function initTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }

  // Inicializar popovers de Bootstrap 5
  function initPopovers() {
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
      return new bootstrap.Popover(popoverTriggerEl);
    });
  }

  // Inicializar cuando el DOM esté listo
  jQuery(document).ready(function() {
    initTooltips();
    initPopovers();
  });

  // Exponer funciones para uso en módulos
  ckan.bootstrap5 = {
    initTooltips: initTooltips,
    initPopovers: initPopovers
  };

})(this.ckan, this.jQuery);
