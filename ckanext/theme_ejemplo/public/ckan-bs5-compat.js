(function (window) {
  "use strict";

  var $ = window.jQuery;
  var bootstrap = window.bootstrap;

  if (!$) {
    return;
  }

  function setControlText($element, text) {
    if ($element.is("input")) {
      $element.val(text);
      return;
    }

    $element.html(text);
  }

  function bridgePlugin(name, Constructor) {
    if (!Constructor || $.fn[name]) {
      return;
    }

    $.fn[name] = function (action) {
      var args = Array.prototype.slice.call(arguments, 1);

      return this.each(function () {
        var instance = Constructor.getOrCreateInstance(this);

        if (!action) {
          return;
        }

        if (typeof action === "string" && typeof instance[action] === "function") {
          instance[action].apply(instance, args);
        }
      });
    };
  }

  if (!$.fn.button) {
    $.fn.button = function (action) {
      return this.each(function () {
        var $element = $(this);
        var loadingText = $element.attr("data-loading-text") || $element.data("loading-text") || "Loading...";
        var resetText = $element.data("reset-text");

        if (resetText === undefined) {
          resetText = $element.is("input") ? $element.val() : $element.html();
          $element.data("reset-text", resetText);
        }

        if (action === "loading") {
          setControlText($element, loadingText);
          $element.addClass("disabled").attr("aria-disabled", "true").prop("disabled", true);
          return;
        }

        if (action === "reset") {
          setControlText($element, resetText);
          $element.removeClass("disabled").removeAttr("aria-disabled").prop("disabled", false);
          return;
        }

        if (bootstrap && bootstrap.Button) {
          bootstrap.Button.getOrCreateInstance(this);
        }
      });
    };
  }

  bridgePlugin("modal", bootstrap && bootstrap.Modal);
  bridgePlugin("popover", bootstrap && bootstrap.Popover);
  bridgePlugin("tooltip", bootstrap && bootstrap.Tooltip);
  bridgePlugin("dropdown", bootstrap && bootstrap.Dropdown);
  bridgePlugin("collapse", bootstrap && bootstrap.Collapse);
  bridgePlugin("tab", bootstrap && bootstrap.Tab);
})(window);
