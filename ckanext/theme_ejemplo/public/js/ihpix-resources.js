/* Altas de datasets y eventos en el mismo paso del reporte, sin redirecciones. */
(function () {
  'use strict';
  var messages = document.getElementById('ihpix-resource-strings');
  if (!messages) return;
  var S = JSON.parse(messages.textContent);
  function requestId() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (letter) {
      var n = Math.floor(Math.random() * 16);
      return (letter === 'x' ? n : (n & 3 | 8)).toString(16);
    });
  }
  document.querySelectorAll('.ihpix-resource-modal').forEach(function (modal) {
    var kind = modal.dataset.resourceKind;
    var form = modal.querySelector('form');
    var busy = false;
    var submit = form && form.querySelector('[type=submit]');
    var submitLabel = submit && submit.textContent;
    var success = modal.querySelector('[data-resource-success]');
    var errorBox = modal.querySelector('[data-resource-error]');
    function sources() {
      var selected = form.elements.source_kind.value;
      form.querySelectorAll('[data-resource-source]').forEach(function (panel) { panel.hidden = panel.dataset.resourceSource !== selected; });
    }
    function setBusy(value) {
      busy = value;
      modal.setAttribute('aria-busy', String(value));
      modal.toggleAttribute('data-static', value);
      modal.querySelectorAll('[data-ihpix-modal-close]').forEach(function (button) { button.disabled = value; });
      submit.disabled = value;
      submit.textContent = value ? S.saving : submitLabel;
      form.inert = value;
    }
    function errors(values) {
      form.querySelectorAll('[data-error-for]').forEach(function (box) { box.textContent = ''; });
      form.querySelectorAll('[aria-invalid]').forEach(function (field) { field.removeAttribute('aria-invalid'); });
      var general = [], first = null;
      Object.keys(values).forEach(function (name) {
        var box = Array.from(form.querySelectorAll('[data-error-for]')).find(function (el) { return el.dataset.errorFor === name; });
        var message = Array.isArray(values[name]) ? values[name].join(', ') : String(values[name]);
        if (box) box.textContent = message;
        else general.push(message);
        var field = name === 'source' ? (form.elements.source_kind.value === 'file' ? form.elements.file : form.elements.source_url) : form.elements[name];
        if (field && field.setAttribute) {
          field.setAttribute('aria-invalid', 'true');
          if (!first) first = field;
        }
      });
      errorBox.textContent = general.length ? general.join(' ') : S.fix;
      errorBox.hidden = !Object.keys(values).length;
      if (first) {
        var component = window.IhpixForms.get(first);
        (component && component.focusTarget || first).focus();
      }
    }
    function validate() {
      var result = {};
      form.querySelectorAll('[required]').forEach(function (field) {
        if (!field.value.trim()) result[field.name] = S.missing;
        else if (field.type === 'email' && !field.validity.valid) result[field.name] = S.email;
      });
      var source = form.elements.source_kind.value;
      if (source === 'file' && !form.elements.file.files.length) result.source = S.file;
      if (source === 'url' && !/^https?:\/\/\S+$/i.test(form.elements.source_url.value)) result.source = S.url;
      if (kind === 'event') {
        if (form.elements.end_date.value && form.elements.end_date.value < form.elements.start_date.value) result.end_date = S.date;
        if (form.elements.registration_url.value && !/^https?:\/\/\S+$/i.test(form.elements.registration_url.value)) result.registration_url = S.url;
      }
      errors(result);
      return !Object.keys(result).length;
    }
    document.querySelectorAll('[data-ihpix-resource-open="' + kind + '"]').forEach(function (button) {
      button.addEventListener('click', function () {
        if (busy) return;
        if (form) {
          var output = document.getElementById('ihpix-field-output');
          form.elements.output_code.value = output ? output.value : '';
          var organization = document.getElementById('ihpix-institution-org');
          if (!form.elements.organization.value && organization && Array.from(form.elements.organization.options).some(function (option) { return option.value === organization.value; })) form.elements.organization.value = organization.value;
          success.hidden = true;
          errors({});
        }
        window.IhpixForms.Modal.open(modal);
      });
    });
    if (!form) return;
    form.elements.request_id.value = requestId();
    form.querySelectorAll('[name=source_kind]').forEach(function (radio) { radio.addEventListener('change', sources); });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (busy || !validate()) return;
      var body = new FormData(form);
      if (form.elements.source_kind.value !== 'file') body.delete('file');
      setBusy(true);
      window.IhpixForms.upload(modal.dataset.postUrl, body, {onProgress:function (percent) {
        var progress = form.querySelector('.ixf-progress');
        var bar = form.querySelector('.ixf-progress-bar');
        if (progress) progress.setAttribute('aria-valuenow', String(percent));
        if (bar) bar.style.width = percent + '%';
      }}).then(function (response) {
        if (!response.ok || !response.data.success) {
          setBusy(false);
          errors(response.data.errors || {general:response.data.error || S.network});
          return;
        }
        window.ihpixLinks.add(response.data.link);
        success.textContent = S.created;
        success.hidden = false;
        window.ihpixToast(S.created, 'success');
        setTimeout(function () {
          setBusy(false);
          window.IhpixForms.Modal.close(modal, 'done');
          form.reset();
          form.elements.request_id.value = requestId();
          sources();
          window.IhpixForms.refresh(form);
        }, 900);
      }).catch(function () { setBusy(false); errors({general:S.network}); });
    });
  });
})();
