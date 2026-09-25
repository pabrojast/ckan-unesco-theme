/* ==========================================================================
   IhpixForms — kit de formularios IHP-IX (vanilla JS, sin jQuery)

   Componentes opt-in por atributos data-*:
     textarea[data-ihpix-markdown]      → MarkdownEditor (barra + preview)
     select[data-ihpix-combobox]        → Combobox local con búsqueda
     input[data-ihpix-combobox=remote]  → Combobox remoto (data-source-url)
     [data-ihpix-multipicker]           → MultiPicker (checkboxes + chips)
     textarea[data-ihpix-counter]       → CharCounter (requiere maxlength)
     [data-ihpix-upload]                → FileUpload (progreso, tamaño, tipo)
     [data-ihpix-confirm]               → ConfirmDialog (form o botón)
     [data-ihpix-modal-open="#id"]      → abre un .ixf-modal

   Principio: nunca se quita el control nativo; se oculta y se sincroniza,
   así los scripts existentes (autosave, restauración, errores) que buscan
   por name/id siguen funcionando. Los componentes disparan eventos
   `input`/`change` nativos con bubbles para que los escuchen los forms.

   Cadenas: <script type="application/json" id="ihpix-forms-i18n"> con
   {strings: {...}, previewUrl: '...', csrf: '...'} (ver snippets/forms_assets.html).
   ========================================================================== */
(function (window, document) {
  'use strict';
  if (window.IhpixForms) { return; }

  var CONFIG = { strings: {}, previewUrl: '', csrf: '' };
  var registry = new WeakMap();
  var instances = [];

  function loadConfig() {
    var el = document.getElementById('ihpix-forms-i18n');
    if (!el) { return; }
    try {
      var parsed = JSON.parse(el.textContent || '{}');
      CONFIG.strings = parsed.strings || {};
      CONFIG.previewUrl = parsed.previewUrl || CONFIG.previewUrl;
      CONFIG.csrf = parsed.csrf || CONFIG.csrf;
    } catch (e) { /* sin cadenas: se usan los fallbacks en inglés */ }
  }

  function t(key, fallback, params) {
    var s = CONFIG.strings[key] || fallback || key;
    if (params) {
      Object.keys(params).forEach(function (k) { s = s.replace(new RegExp('\\{' + k + '\\}', 'g'), params[k]); });
    }
    return s;
  }

  /* ── Utilidades ───────────────────────────────────────────────────── */
  var uidCounter = 0;
  function uid(prefix) { uidCounter += 1; return (prefix || 'ixf') + '-' + Date.now().toString(36) + '-' + uidCounter; }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) { n.className = cls; }
    if (text != null) { n.textContent = text; }
    return n;
  }

  function normalize(str) {
    return String(str || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function fire(target, type) {
    target.dispatchEvent(new Event(type, { bubbles: true }));
  }

  function csrfToken() {
    var meta = document.querySelector('meta[name="_csrf_token"]');
    if (meta && meta.content) { return meta.content; }
    var input = document.querySelector('input[name="_csrf_token"]');
    if (input && input.value) { return input.value; }
    return CONFIG.csrf || '';
  }

  function postForm(url, formData, options) {
    options = options || {};
    var fd = formData || new FormData();
    if (!(fd instanceof FormData)) {
      var converted = new FormData();
      Object.keys(fd).forEach(function (k) { converted.append(k, fd[k]); });
      fd = converted;
    }
    var token = csrfToken();
    if (token && !fd.has('_csrf_token')) { fd.append('_csrf_token', token); }
    return fetch(url, {
      method: options.method || 'POST',
      body: fd,
      credentials: 'same-origin',
      headers: Object.assign({ 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' }, options.headers || {})
    }).then(function (response) {
      return response.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = { success: false, error: text }; }
        return { ok: response.ok, status: response.status, data: data };
      });
    });
  }

  function upload(url, formData, options) {
    options = options || {};
    var token = csrfToken();
    if (token && !formData.has('_csrf_token')) { formData.append('_csrf_token', token); }
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', url, true);
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.withCredentials = true;
      if (xhr.upload && options.onProgress) {
        xhr.upload.addEventListener('progress', function (e) {
          if (e.lengthComputable) { options.onProgress(Math.round(e.loaded / e.total * 100), e); }
        });
      }
      xhr.onload = function () {
        var data = null;
        try { data = xhr.responseText ? JSON.parse(xhr.responseText) : null; } catch (e) { data = { success: false, error: xhr.responseText }; }
        resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, data: data });
      };
      xhr.onerror = function () { reject(new Error('network')); };
      xhr.onabort = function () { reject(new Error('abort')); };
      xhr.send(formData);
      if (options.onStart) { options.onStart(xhr); }
    });
  }

  function formatErrors(errorDict) {
    if (!errorDict) { return ''; }
    if (typeof errorDict === 'string') { return errorDict; }
    return Object.keys(errorDict).map(function (k) {
      var v = errorDict[k];
      if (Array.isArray(v)) { v = v.join(', '); }
      return (k === '__all__' ? '' : k + ': ') + v;
    }).join('; ');
  }

  function markInvalid(control, invalid, message) {
    if (!control) { return; }
    if (invalid) { control.setAttribute('aria-invalid', 'true'); } else { control.removeAttribute('aria-invalid'); }
    var inst = registry.get(control);
    if (inst && typeof inst.setInvalid === 'function') { inst.setInvalid(invalid); }
    var errorId = control.getAttribute('data-error-target') || (control.id ? control.id + '-error' : '');
    var errorEl = errorId ? document.getElementById(errorId) : null;
    if (errorEl) {
      if (message) { errorEl.textContent = message; }
      errorEl.classList.toggle('is-visible', !!invalid);
    }
  }

  function applyFieldErrors(form, errors) {
    var first = null;
    Object.keys(errors || {}).forEach(function (name) {
      var control = form.querySelector('[name="' + name + '"]') || form.querySelector('#' + name);
      if (!control) { return; }
      var msg = errors[name];
      if (Array.isArray(msg)) { msg = msg.join(', '); }
      markInvalid(control, true, msg);
      if (!first) { first = control; }
    });
    if (first) {
      var inst = registry.get(first);
      var focusable = (inst && inst.focusTarget) || first;
      try { focusable.focus({ preventScroll: false }); } catch (e) { /* noop */ }
    }
    return first;
  }

  function clearFieldErrors(form) {
    form.querySelectorAll('[aria-invalid="true"]').forEach(function (c) { markInvalid(c, false); });
  }

  /* ── Toast ────────────────────────────────────────────────────────── */
  var Toast = (function () {
    var container = null;
    function ensure() {
      if (container && document.body.contains(container)) { return container; }
      container = el('div', 'ixf-toasts');
      container.id = 'ixf-toasts';
      container.setAttribute('role', 'status');
      container.setAttribute('aria-live', 'polite');
      document.body.appendChild(container);
      return container;
    }
    function remove(toast) {
      if (!toast || !toast.parentNode) { return; }
      toast.classList.add('is-leaving');
      setTimeout(function () { if (toast.parentNode) { toast.parentNode.removeChild(toast); } }, 220);
    }
    function show(message, type, options) {
      options = options || {};
      type = type || 'info';
      var box = ensure();
      var toast = el('div', 'ixf-toast is-' + type);
      if (type === 'error') { toast.setAttribute('role', 'alert'); }
      var icon = el('i', 'fa ' + ({ success: 'fa-check-circle', error: 'fa-exclamation-circle', warning: 'fa-exclamation-triangle' }[type] || 'fa-info-circle'));
      icon.setAttribute('aria-hidden', 'true');
      var body = el('div', 'ixf-toast-body', message);
      var close = el('button', 'ixf-toast-close', '×');
      close.type = 'button';
      close.setAttribute('aria-label', t('dismiss', 'Dismiss notification'));
      close.addEventListener('click', function () { remove(toast); });
      toast.appendChild(icon); toast.appendChild(body); toast.appendChild(close);
      box.appendChild(toast);
      var timeout = options.timeout != null ? options.timeout : (type === 'error' ? 9000 : 6000);
      var timer = timeout > 0 ? setTimeout(function () { remove(toast); }, timeout) : null;
      toast.addEventListener('mouseenter', function () { if (timer) { clearTimeout(timer); timer = null; } });
      toast.addEventListener('mouseleave', function () { if (!timer && timeout > 0) { timer = setTimeout(function () { remove(toast); }, 2500); } });
      return toast;
    }
    function clear() { if (container) { Array.prototype.slice.call(container.children).forEach(remove); } }
    return { show: show, clear: clear, remove: remove };
  })();

  /* ── Modal (focus trap, Esc, backdrop) ────────────────────────────── */
  var Modal = (function () {
    var stack = [];
    var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type=hidden]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    function focusables(dialog) {
      return Array.prototype.slice.call(dialog.querySelectorAll(FOCUSABLE)).filter(function (n) {
        return n.offsetParent !== null || n === document.activeElement;
      });
    }

    function onKeydown(e) {
      var top = stack[stack.length - 1];
      if (!top) { return; }
      if (e.key === 'Escape' && !top.el.hasAttribute('data-static')) {
        e.preventDefault();
        close(top.el, 'escape');
        return;
      }
      if (e.key === 'Tab') {
        var items = focusables(top.el.querySelector('.ixf-modal-dialog') || top.el);
        if (!items.length) { e.preventDefault(); return; }
        var first = items[0], last = items[items.length - 1];
        if (e.shiftKey && (document.activeElement === first || !top.el.contains(document.activeElement))) {
          e.preventDefault(); last.focus();
        } else if (!e.shiftKey && (document.activeElement === last || !top.el.contains(document.activeElement))) {
          e.preventDefault(); first.focus();
        }
      }
    }

    function open(modalEl, options) {
      if (typeof modalEl === 'string') { modalEl = document.querySelector(modalEl); }
      if (!modalEl) { return null; }
      options = options || {};
      var entry = { el: modalEl, opener: document.activeElement, onClose: options.onClose };
      if (!modalEl.querySelector('.ixf-modal-backdrop')) {
        var backdrop = el('div', 'ixf-modal-backdrop');
        modalEl.insertBefore(backdrop, modalEl.firstChild);
      }
      modalEl.hidden = false;
      modalEl.classList.add('is-open');
      document.body.classList.add('ixf-modal-open');
      if (!stack.length) { document.addEventListener('keydown', onKeydown, true); }
      stack.push(entry);
      if (!modalEl.__ixfBound) {
        modalEl.__ixfBound = true;
        modalEl.addEventListener('click', function (e) {
          if (e.target.classList.contains('ixf-modal-backdrop') && !modalEl.hasAttribute('data-static')) { close(modalEl, 'backdrop'); }
          if (e.target.closest('[data-ihpix-modal-close]')) { e.preventDefault(); close(modalEl, 'button'); }
        });
      }
      var dialog = modalEl.querySelector('.ixf-modal-dialog') || modalEl;
      var target = modalEl.querySelector('[data-autofocus]') || focusables(dialog)[0] || dialog;
      if (target === dialog && !dialog.hasAttribute('tabindex')) { dialog.setAttribute('tabindex', '-1'); }
      setTimeout(function () { try { target.focus(); } catch (e) { /* noop */ } }, 10);
      init(modalEl);
      return modalEl;
    }

    function close(modalEl, reason) {
      if (typeof modalEl === 'string') { modalEl = document.querySelector(modalEl); }
      if (!modalEl) { return; }
      var idx = -1;
      for (var i = stack.length - 1; i >= 0; i--) { if (stack[i].el === modalEl) { idx = i; break; } }
      if (idx === -1) { return; }
      var entry = stack.splice(idx, 1)[0];
      modalEl.classList.remove('is-open');
      modalEl.hidden = true;
      if (!stack.length) {
        document.body.classList.remove('ixf-modal-open');
        document.removeEventListener('keydown', onKeydown, true);
      }
      if (entry.opener && typeof entry.opener.focus === 'function') { try { entry.opener.focus(); } catch (e) { /* noop */ } }
      if (typeof entry.onClose === 'function') { entry.onClose(reason); }
      modalEl.dispatchEvent(new CustomEvent('ihpix:modal-close', { detail: { reason: reason } }));
    }

    function build(options) {
      var wrapper = el('div', 'ixf-modal');
      wrapper.hidden = true;
      wrapper.setAttribute('role', 'dialog');
      wrapper.setAttribute('aria-modal', 'true');
      var titleId = uid('ixf-modal-title');
      wrapper.setAttribute('aria-labelledby', titleId);
      var dialog = el('div', 'ixf-modal-dialog' + (options.size ? ' is-' + options.size : ''));
      var header = el('div', 'ixf-modal-header');
      var title = el('h2', 'ixf-modal-title', options.title || '');
      title.id = titleId;
      var closeBtn = el('button', 'ixf-modal-close', '×');
      closeBtn.type = 'button';
      closeBtn.setAttribute('aria-label', t('close', 'Close'));
      closeBtn.setAttribute('data-ihpix-modal-close', '');
      header.appendChild(title); header.appendChild(closeBtn);
      var body = el('div', 'ixf-modal-body');
      if (options.bodyNode) { body.appendChild(options.bodyNode); } else if (options.message) { body.textContent = options.message; }
      var footer = el('div', 'ixf-modal-footer');
      dialog.appendChild(header); dialog.appendChild(body); dialog.appendChild(footer);
      wrapper.appendChild(dialog);
      document.body.appendChild(wrapper);
      return { el: wrapper, body: body, footer: footer, title: title };
    }

    return { open: open, close: close, build: build };
  })();

  /* ── ConfirmDialog ────────────────────────────────────────────────── */
  function confirmDialog(options) {
    options = options || {};
    return new Promise(function (resolve) {
      var m = Modal.build({ title: options.title || t('confirmTitle', 'Please confirm'), message: options.message || '', size: 'narrow' });
      var cancel = el('button', 'ixf-btn ixf-btn-ghost', options.cancelLabel || t('cancel', 'Cancel'));
      cancel.type = 'button';
      var ok = el('button', 'ixf-btn ' + (options.danger ? 'ixf-btn-danger' : 'ixf-btn-primary'), options.confirmLabel || t('confirm', 'Confirm'));
      ok.type = 'button';
      if (options.danger) { cancel.setAttribute('data-autofocus', ''); } else { ok.setAttribute('data-autofocus', ''); }
      var done = false;
      function finish(value) {
        if (done) { return; }
        done = true;
        Modal.close(m.el, value ? 'confirm' : 'cancel');
        setTimeout(function () { if (m.el.parentNode) { m.el.parentNode.removeChild(m.el); } }, 250);
        resolve(value);
      }
      cancel.addEventListener('click', function () { finish(false); });
      ok.addEventListener('click', function () { finish(true); });
      m.footer.appendChild(cancel); m.footer.appendChild(ok);
      Modal.open(m.el, { onClose: function (reason) { if (reason !== 'confirm') { finish(false); } } });
    });
  }

  function bindConfirm(target) {
    if (target.__ixfConfirm) { return; }
    target.__ixfConfirm = true;
    var message = target.getAttribute('data-ihpix-confirm') || '';
    var danger = target.hasAttribute('data-ihpix-confirm-danger');
    var title = target.getAttribute('data-ihpix-confirm-title') || '';
    var label = target.getAttribute('data-ihpix-confirm-label') || '';
    // El fallback inline (onsubmit/onclick="return confirm(...)") se retira: ya hay diálogo accesible
    if (target.tagName === 'FORM') {
      target.removeAttribute('onsubmit');
      target.addEventListener('submit', function (e) {
        if (target.__ixfConfirmed) { target.__ixfConfirmed = false; return; }
        e.preventDefault();
        confirmDialog({ message: message, danger: danger, title: title, confirmLabel: label }).then(function (yes) {
          if (!yes) { return; }
          target.__ixfConfirmed = true;
          if (typeof target.requestSubmit === 'function') { target.requestSubmit(); } else { target.submit(); }
        });
      });
    } else {
      target.removeAttribute('onclick');
      target.addEventListener('click', function (e) {
        if (target.__ixfConfirmed) { target.__ixfConfirmed = false; return; }
        e.preventDefault();
        confirmDialog({ message: message, danger: danger, title: title, confirmLabel: label }).then(function (yes) {
          if (!yes) { return; }
          target.__ixfConfirmed = true;
          target.click();
        });
      });
    }
  }

  /* ── CharCounter ──────────────────────────────────────────────────── */
  function CharCounter(textarea) {
    var max = parseInt(textarea.getAttribute('maxlength'), 10);
    if (!max) { return null; }
    var counter = el('span', 'ixf-counter');
    counter.id = textarea.id ? textarea.id + '-counter' : uid('ixf-counter');
    counter.setAttribute('aria-live', 'polite');
    var host = textarea.closest('.ixf-md') || textarea;
    host.parentNode.insertBefore(counter, host.nextSibling);
    var described = (textarea.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
    described.push(counter.id);
    textarea.setAttribute('aria-describedby', described.join(' '));
    var lastAnnounced = 0;
    function update() {
      var n = textarea.value.length;
      var ratio = n / max;
      counter.classList.toggle('is-warn', ratio >= 0.9 && n < max);
      counter.classList.toggle('is-full', n >= max);
      var text = t('charsOf', '{n} / {max}', { n: n, max: max });
      // Solo se anuncia en umbrales para no saturar al lector de pantalla
      var threshold = ratio >= 1 ? 100 : ratio >= 0.95 ? 95 : ratio >= 0.8 ? 80 : 0;
      if (threshold !== lastAnnounced) { counter.setAttribute('aria-live', threshold ? 'polite' : 'off'); lastAnnounced = threshold; }
      counter.textContent = text;
    }
    textarea.addEventListener('input', update);
    update();
    var api = { refresh: update, el: counter };
    registry.set(textarea, api);
    return api;
  }

  /* ── MarkdownEditor ───────────────────────────────────────────────── */
  function MarkdownEditor(textarea) {
    if (textarea.disabled || textarea.readOnly) { return null; }
    var wrap = el('div', 'ixf-md');
    textarea.parentNode.insertBefore(wrap, textarea);
    var bar = el('div', 'ixf-md-bar');
    bar.setAttribute('role', 'toolbar');
    bar.setAttribute('aria-label', t('formatting', 'Text formatting'));
    var textId = textarea.id || (textarea.id = uid('ixf-md-text'));
    var previewId = textId + '-preview';
    var preview = el('div', 'ixf-md-preview ixf-md-body');
    preview.id = previewId;
    preview.hidden = true;
    preview.setAttribute('aria-live', 'polite');
    preview.setAttribute('tabindex', '0');

    var actions = [
      { key: 'bold', icon: 'fa-bold', label: t('bold', 'Bold'), shortcut: 'b', run: function () { wrapSelection('**', '**', t('boldText', 'bold text')); } },
      { key: 'italic', icon: 'fa-italic', label: t('italic', 'Italic'), shortcut: 'i', run: function () { wrapSelection('_', '_', t('italicText', 'italic text')); } },
      { key: 'heading', icon: 'fa-header', label: t('heading', 'Heading'), run: function () { prefixLines('### '); } },
      { sep: true },
      { key: 'ul', icon: 'fa-list-ul', label: t('bulletList', 'Bullet list'), run: function () { prefixLines('- '); } },
      { key: 'ol', icon: 'fa-list-ol', label: t('numberedList', 'Numbered list'), run: function () { prefixLines('1. ', true); } },
      { key: 'link', icon: 'fa-link', label: t('link', 'Link'), shortcut: 'k', run: function () { insertLink(); } }
    ];

    var buttons = [];
    actions.forEach(function (a) {
      if (a.sep) { bar.appendChild(el('span', 'ixf-md-sep')); return; }
      var b = el('button');
      b.type = 'button';
      b.setAttribute('aria-label', a.label);
      b.title = a.label + (a.shortcut ? ' (Ctrl+' + a.shortcut.toUpperCase() + ')' : '');
      b.setAttribute('tabindex', buttons.length ? '-1' : '0');
      var ic = el('i', 'fa ' + a.icon); ic.setAttribute('aria-hidden', 'true');
      b.appendChild(ic);
      b.addEventListener('click', function () { showWrite(); a.run(); textarea.focus(); });
      bar.appendChild(b);
      buttons.push(b);
    });

    // Tabs Write / Preview
    var tabs = el('div', 'ixf-md-tabs');
    tabs.setAttribute('role', 'tablist');
    var writeTab = el('button', null, t('write', 'Write'));
    var previewTab = el('button', null, t('preview', 'Preview'));
    [writeTab, previewTab].forEach(function (tb, i) {
      tb.type = 'button';
      tb.setAttribute('role', 'tab');
      tb.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
      tb.setAttribute('tabindex', i === 0 ? '0' : '-1');
      tabs.appendChild(tb);
    });
    writeTab.setAttribute('aria-controls', textId);
    previewTab.setAttribute('aria-controls', previewId);
    bar.appendChild(tabs);

    // Roving tabindex en la barra
    bar.addEventListener('keydown', function (e) {
      var group = e.target.closest('[role=tablist]') ? [writeTab, previewTab] : buttons;
      var i = group.indexOf(e.target);
      if (i === -1) { return; }
      var next = null;
      if (e.key === 'ArrowRight') { next = group[(i + 1) % group.length]; }
      if (e.key === 'ArrowLeft') { next = group[(i - 1 + group.length) % group.length]; }
      if (e.key === 'Home') { next = group[0]; }
      if (e.key === 'End') { next = group[group.length - 1]; }
      if (next) { e.preventDefault(); group.forEach(function (b) { b.setAttribute('tabindex', '-1'); }); next.setAttribute('tabindex', '0'); next.focus(); if (group[0] === writeTab) { next.click(); } }
    });

    var foot = el('div', 'ixf-md-foot');
    var hint = el('span', null, t('markdownHint', 'Markdown supported: **bold**, _italic_, - lists, [link](https://…)'));
    foot.appendChild(hint);

    textarea.classList.add('ixf-md-textarea');
    textarea.setAttribute('role', 'tabpanel');
    wrap.appendChild(bar);
    wrap.appendChild(textarea);
    wrap.appendChild(preview);
    wrap.appendChild(foot);

    var previewTimer = null, previewSeq = 0;
    function showWrite() {
      preview.hidden = true; textarea.hidden = false;
      writeTab.setAttribute('aria-selected', 'true'); previewTab.setAttribute('aria-selected', 'false');
    }
    function showPreview() {
      textarea.hidden = true; preview.hidden = false;
      writeTab.setAttribute('aria-selected', 'false'); previewTab.setAttribute('aria-selected', 'true');
      renderPreview();
    }
    function fallbackPreview(text) {
      preview.innerHTML = text.trim() ? escapeHtml(text).replace(/\n/g, '<br>') : '<p class="ixf-md-empty">' + escapeHtml(t('previewEmpty', 'Nothing to preview yet.')) + '</p>';
    }
    function renderPreview() {
      var text = textarea.value;
      var url = textarea.getAttribute('data-preview-url') || CONFIG.previewUrl;
      if (!text.trim()) { fallbackPreview(text); return; }
      if (!url) { fallbackPreview(text); return; }
      var seq = ++previewSeq;
      preview.classList.add('is-loading');
      preview.setAttribute('aria-busy', 'true');
      var fd = new FormData(); fd.append('text', text);
      postForm(url, fd).then(function (res) {
        if (seq !== previewSeq) { return; }
        if (res.ok && res.data && res.data.success && typeof res.data.html === 'string') {
          preview.innerHTML = res.data.html || '<p class="ixf-md-empty">' + escapeHtml(t('previewEmpty', 'Nothing to preview yet.')) + '</p>';
        } else { fallbackPreview(text); }
      }).catch(function () { if (seq === previewSeq) { fallbackPreview(text); } })
        .then(function () { preview.classList.remove('is-loading'); preview.removeAttribute('aria-busy'); });
    }
    writeTab.addEventListener('click', function () { showWrite(); textarea.focus(); });
    previewTab.addEventListener('click', showPreview);
    preview.addEventListener('keydown', function (e) { if (e.key === 'Escape') { showWrite(); textarea.focus(); } });
    textarea.addEventListener('input', function () {
      if (!preview.hidden) { clearTimeout(previewTimer); previewTimer = setTimeout(renderPreview, 400); }
    });

    function replaceSelection(text, selStart, selEnd) {
      var start = textarea.selectionStart, end = textarea.selectionEnd;
      if (typeof textarea.setRangeText === 'function') {
        textarea.setRangeText(text, start, end, 'preserve');
      } else {
        var v = textarea.value; textarea.value = v.slice(0, start) + text + v.slice(end);
      }
      textarea.setSelectionRange(start + selStart, start + selEnd);
      fire(textarea, 'input');
    }
    function wrapSelection(before, after, placeholder) {
      var start = textarea.selectionStart, end = textarea.selectionEnd;
      var selected = textarea.value.slice(start, end) || placeholder;
      replaceSelection(before + selected + after, before.length, before.length + selected.length);
    }
    function prefixLines(prefix, numbered) {
      var start = textarea.selectionStart, end = textarea.selectionEnd, value = textarea.value;
      var lineStart = value.lastIndexOf('\n', start - 1) + 1;
      var lineEnd = value.indexOf('\n', end); if (lineEnd === -1) { lineEnd = value.length; }
      var block = value.slice(lineStart, lineEnd);
      var lines = block.split('\n').map(function (line, i) {
        var p = numbered ? (i + 1) + '. ' : prefix;
        return line.replace(/^(\s*)(?:[-*+]\s+|\d+\.\s+|#{1,6}\s+)?/, '$1' + p);
      });
      var out = lines.join('\n');
      textarea.setSelectionRange(lineStart, lineEnd);
      replaceSelection(out, 0, out.length);
    }
    function insertLink() {
      var start = textarea.selectionStart, end = textarea.selectionEnd;
      var selected = textarea.value.slice(start, end);
      var isUrl = /^https?:\/\//i.test(selected);
      var label = isUrl ? t('linkText', 'link text') : (selected || t('linkText', 'link text'));
      var url = isUrl ? selected : 'https://';
      var md = '[' + label + '](' + url + ')';
      var selFrom = isUrl ? 1 : label.length + 3;
      var selTo = isUrl ? 1 + label.length : label.length + 3 + url.length;
      replaceSelection(md, selFrom, selTo);
    }
    textarea.addEventListener('keydown', function (e) {
      if (!(e.ctrlKey || e.metaKey) || e.altKey) { return; }
      var key = e.key.toLowerCase();
      var action = actions.filter(function (a) { return a.shortcut === key; })[0];
      if (action) { e.preventDefault(); action.run(); }
    });

    var api = { refresh: function () { if (!preview.hidden) { renderPreview(); } }, el: wrap, focusTarget: textarea, setInvalid: function (v) { wrap.classList.toggle('has-error', !!v); } };
    registry.set(textarea, api);
    return api;
  }

  /* ── Combobox ─────────────────────────────────────────────────────── */
  function Combobox(control) {
    var remote = control.tagName === 'INPUT';
    var select = remote ? null : control;
    var wrap = el('div', 'ixf-combobox');
    var input, hiddenValue;
    var listId = uid('ixf-listbox');
    var list = el('ul', 'ixf-listbox');
    list.id = listId;
    list.setAttribute('role', 'listbox');
    list.hidden = true;
    var toggle = el('button', 'ixf-combobox-toggle');
    toggle.type = 'button';
    toggle.setAttribute('aria-label', t('showOptions', 'Show options'));
    toggle.setAttribute('tabindex', '-1');
    var caret = el('i', 'fa fa-chevron-down'); caret.setAttribute('aria-hidden', 'true'); toggle.appendChild(caret);
    var clear = el('button', 'ixf-combobox-clear', '×');
    clear.type = 'button';
    clear.setAttribute('aria-label', t('clearSelection', 'Clear selection'));

    if (remote) {
      input = control;
      input.parentNode.insertBefore(wrap, input);
      wrap.appendChild(input);
    } else {
      input = el('input', (select.className || '').replace(/\bihpix-report-select\b/, 'ihpix-report-input'));
      input.type = 'text';
      input.autocomplete = 'off';
      input.id = (select.id || uid('ixf-cb')) + '-combobox';
      select.parentNode.insertBefore(wrap, select);
      wrap.appendChild(input);
      wrap.appendChild(select);
      select.classList.add('ixf-visually-hidden');
      select.setAttribute('tabindex', '-1');
      select.setAttribute('aria-hidden', 'true');
      // Reasignar la etiqueta visible al input
      if (select.id) {
        document.querySelectorAll('label[for="' + select.id + '"]').forEach(function (l) { l.setAttribute('for', input.id); });
      }
      var describedBy = select.getAttribute('aria-describedby');
      if (describedBy) { input.setAttribute('aria-describedby', describedBy); }
      if (select.required) { input.setAttribute('aria-required', 'true'); }
      if (select.disabled) { input.disabled = true; }
    }
    input.classList.add('ixf-combobox-input');
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-controls', listId);
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-haspopup', 'listbox');
    if (!input.placeholder) { input.placeholder = t('typeToSearch', 'Type to search…'); }
    wrap.appendChild(clear);
    wrap.appendChild(toggle);
    wrap.appendChild(list);

    var options = [];      // {value, label, search, extra}
    var filtered = [];
    var activeIndex = -1;
    var open = false;
    var MAX_ROWS = parseInt(control.getAttribute('data-max-rows'), 10) || 60;
    var minChars = parseInt(control.getAttribute('data-min-chars'), 10) || 0;
    var sourceUrl = control.getAttribute('data-source-url') || '';
    var valueKey = control.getAttribute('data-value-key') || 'name';
    var labelKeys = (control.getAttribute('data-label-keys') || 'fullname,name,title').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    var remoteTimer = null, remoteSeq = 0;
    var status = el('span', 'ixf-sr-only');
    status.setAttribute('aria-live', 'polite');
    wrap.appendChild(status);

    function readOptions() {
      options = [];
      if (!select) { return; }
      Array.prototype.forEach.call(select.options, function (o) {
        if (!o.value && !o.hasAttribute('data-keep-empty')) { return; }
        options.push({ value: o.value, label: o.textContent.trim(), search: normalize(o.textContent + ' ' + (o.getAttribute('data-search') || '') + ' ' + o.value), extra: o.getAttribute('data-search') || '' });
      });
    }

    function currentLabel() {
      if (!select) { return input.value; }
      var o = select.options[select.selectedIndex];
      return (o && o.value) ? o.textContent.trim() : '';
    }

    function syncFromSelect() {
      if (!select) { wrap.classList.toggle('has-value', !!input.value); return; }
      input.value = currentLabel();
      wrap.classList.toggle('has-value', !!select.value);
    }

    function render(items, note) {
      list.innerHTML = '';
      filtered = items;
      activeIndex = -1;
      if (!items.length && !note) {
        var empty = el('li', 'ixf-option is-note', t('noResults', 'No results'));
        empty.setAttribute('role', 'presentation');
        list.appendChild(empty);
      }
      items.forEach(function (item, i) {
        var li = el('li', 'ixf-option');
        li.id = listId + '-opt-' + i;
        li.setAttribute('role', 'option');
        var selected = select ? (select.value === item.value && !!item.value) : (input.value === item.value);
        li.setAttribute('aria-selected', selected ? 'true' : 'false');
        var main = el('span', null, item.label);
        li.appendChild(main);
        if (item.extra) { li.appendChild(el('small', null, item.extra)); }
        li.addEventListener('mousedown', function (e) { e.preventDefault(); });
        li.addEventListener('click', function () { choose(i); });
        list.appendChild(li);
      });
      if (note) {
        var n = el('li', 'ixf-option is-note', note);
        n.setAttribute('role', 'presentation');
        list.appendChild(n);
      }
      status.textContent = items.length ? t('resultsCount', '{n} results', { n: items.length }) : t('noResults', 'No results');
    }

    function filterLocal(query) {
      var q = normalize(query);
      var items = !q ? options.slice() : options.filter(function (o) { return o.search.indexOf(q) !== -1; });
      if (q) {
        // Coincidencias al inicio primero
        items.sort(function (a, b) {
          var as = normalize(a.label).indexOf(q) === 0 ? 0 : 1, bs = normalize(b.label).indexOf(q) === 0 ? 0 : 1;
          return as - bs;
        });
      }
      var more = items.length - MAX_ROWS;
      render(items.slice(0, MAX_ROWS), more > 0 ? t('moreResults', '{n} more, keep typing to narrow down', { n: more }) : '');
    }

    function fetchRemote(query) {
      var seq = ++remoteSeq;
      var url = sourceUrl + encodeURIComponent(query);
      fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (seq !== remoteSeq) { return; }
          var rows = Array.isArray(data) ? data : (data && (data.result || data.results || data.ResultSet && data.ResultSet.Result)) || [];
          var items = rows.map(function (row) {
            var label = '';
            for (var i = 0; i < labelKeys.length; i++) { if (row[labelKeys[i]]) { label = row[labelKeys[i]]; break; } }
            var value = row[valueKey] != null ? String(row[valueKey]) : label;
            return { value: value, label: label || value, extra: (label && value !== label) ? value : '', search: '' };
          });
          render(items.slice(0, MAX_ROWS));
          show();
        }).catch(function () { if (seq === remoteSeq) { render([]); } });
    }

    function show() {
      if (open) { return; }
      open = true; list.hidden = false; input.setAttribute('aria-expanded', 'true');
    }
    function hide() {
      if (!open) { return; }
      open = false; list.hidden = true; input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant');
      activeIndex = -1;
    }
    function search(query) {
      if (remote) {
        if (query.length < Math.max(minChars, 1)) { hide(); return; }
        clearTimeout(remoteTimer);
        remoteTimer = setTimeout(function () { fetchRemote(query); }, 250);
      } else {
        filterLocal(query);
        show();
      }
    }
    function setActive(i) {
      var items = list.querySelectorAll('[role=option]');
      if (!items.length) { return; }
      if (i < 0) { i = items.length - 1; }
      if (i >= items.length) { i = 0; }
      items.forEach(function (n) { n.classList.remove('is-active'); });
      activeIndex = i;
      items[i].classList.add('is-active');
      input.setAttribute('aria-activedescendant', items[i].id);
      if (typeof items[i].scrollIntoView === 'function') { items[i].scrollIntoView({ block: 'nearest' }); }
    }
    function choose(i) {
      var item = filtered[i];
      if (!item) { return; }
      if (select) {
        select.value = item.value;
        input.value = item.label;
        fire(select, 'change');
        fire(select, 'input');
      } else {
        input.value = item.value;
        input.setAttribute('data-selected-label', item.label);
        fire(input, 'change');
      }
      wrap.classList.add('has-value');
      hide();
    }
    function clearValue() {
      if (select) { select.value = ''; fire(select, 'change'); fire(select, 'input'); }
      input.value = '';
      wrap.classList.remove('has-value');
      input.focus();
    }

    input.addEventListener('input', function () {
      if (select && select.value && normalize(input.value) !== normalize(currentLabel())) {
        select.value = ''; fire(select, 'change'); wrap.classList.remove('has-value');
      }
      search(input.value);
    });
    input.addEventListener('focus', function () { if (!remote) { filterLocal(''); } });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); if (!open) { search(remote ? input.value : ''); } setActive(activeIndex + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); if (open) { setActive(activeIndex - 1); } }
      else if (e.key === 'Home' && open) { e.preventDefault(); setActive(0); }
      else if (e.key === 'End' && open) { e.preventDefault(); setActive(filtered.length - 1); }
      else if (e.key === 'Enter') { if (open && activeIndex >= 0) { e.preventDefault(); choose(activeIndex); } else if (open) { e.preventDefault(); hide(); } }
      else if (e.key === 'Escape') { if (open) { e.preventDefault(); hide(); syncFromSelect(); } }
      else if (e.key === 'Tab') { hide(); if (select) { syncFromSelect(); } }
    });
    input.addEventListener('blur', function () { setTimeout(function () { if (!wrap.contains(document.activeElement)) { hide(); if (select) { syncFromSelect(); } } }, 120); });
    toggle.addEventListener('click', function () { if (open) { hide(); } else { input.focus(); search(remote ? input.value : ''); } });
    clear.addEventListener('click', clearValue);

    if (select) {
      // Reflejar aria-invalid / disabled del select nativo
      var mo = new MutationObserver(function () {
        if (select.getAttribute('aria-invalid') === 'true') { input.setAttribute('aria-invalid', 'true'); } else { input.removeAttribute('aria-invalid'); }
        input.disabled = select.disabled;
      });
      mo.observe(select, { attributes: true, attributeFilter: ['aria-invalid', 'disabled', 'class'] });
      readOptions();
      syncFromSelect();
    } else {
      wrap.classList.toggle('has-value', !!input.value);
    }

    var api = {
      refresh: function () { readOptions(); syncFromSelect(); },
      setValue: function (v) { if (select) { select.value = v; syncFromSelect(); } else { input.value = v; } },
      el: wrap,
      input: input,
      focusTarget: input,
      setInvalid: function (v) { if (v) { input.setAttribute('aria-invalid', 'true'); } else { input.removeAttribute('aria-invalid'); } }
    };
    registry.set(control, api);
    registry.set(input, api);
    return api;
  }

  /* ── MultiPicker ──────────────────────────────────────────────────── */
  function MultiPicker(container) {
    var mode = container.getAttribute('data-value-mode') || 'checkboxes';
    var hiddenSel = container.getAttribute('data-input');
    var hidden = mode === 'json' && hiddenSel ? document.querySelector(hiddenSel) : null;
    var list = container.querySelector('.ixf-mp-list') || container.querySelector('[data-mp-list]');
    if (!list) {
      // Envolver los labels sueltos del contenedor
      list = el('div', 'ixf-mp-list');
      Array.prototype.slice.call(container.querySelectorAll('label')).forEach(function (l) { list.appendChild(l); });
      container.appendChild(list);
    }
    list.classList.add('ixf-mp-list');
    list.setAttribute('role', 'group');
    container.classList.add('ixf-mp');
    var labels = Array.prototype.slice.call(list.querySelectorAll('label'));
    var name = container.getAttribute('data-label') || '';
    if (name) { list.setAttribute('aria-label', name); }

    var searchWrap = el('div', 'ixf-mp-search');
    var icon = el('i', 'fa fa-search'); icon.setAttribute('aria-hidden', 'true');
    var searchInput = el('input');
    searchInput.type = 'search';
    searchInput.autocomplete = 'off';
    searchInput.placeholder = container.getAttribute('data-placeholder') || t('searchList', 'Search…');
    searchInput.setAttribute('aria-label', (name ? name + ': ' : '') + t('searchList', 'Search…'));
    searchWrap.appendChild(icon); searchWrap.appendChild(searchInput);
    var chips = el('div', 'ixf-mp-chips');
    var empty = el('div', 'ixf-mp-empty', t('noMatches', 'No matches for your search.'));
    var footer = el('div', 'ixf-mp-footer');
    var count = el('span'); count.setAttribute('aria-live', 'polite');
    var clearBtn = el('button', null, t('clearAll', 'Clear all')); clearBtn.type = 'button';
    footer.appendChild(count); footer.appendChild(clearBtn);
    container.insertBefore(chips, list);
    container.insertBefore(searchWrap, chips);
    container.appendChild(empty);
    container.appendChild(footer);

    function inputs() { return labels.map(function (l) { return l.querySelector('input[type=checkbox]'); }).filter(Boolean); }
    function labelText(l) { var s = l.querySelector('span, .label-text'); return (s ? s.textContent : l.textContent).trim(); }
    function values() { return inputs().filter(function (i) { return i.checked; }).map(function (i) { return i.getAttribute('data-value') || i.value; }); }

    function syncHidden() {
      if (!hidden) { return; }
      var v = values();
      hidden.value = v.length ? JSON.stringify(v) : '';
      fire(hidden, 'change');
    }
    function render() {
      chips.innerHTML = '';
      var n = 0;
      labels.forEach(function (l) {
        var input = l.querySelector('input[type=checkbox]');
        if (!input || !input.checked) { return; }
        n++;
        var chip = el('span', 'ixf-chip');
        chip.appendChild(el('span', null, labelText(l)));
        var btn = el('button', null, '×');
        btn.type = 'button';
        btn.setAttribute('aria-label', t('remove', 'Remove') + ' ' + labelText(l));
        btn.addEventListener('click', function () { input.checked = false; fire(input, 'change'); render(); syncHidden(); });
        chip.appendChild(btn);
        chips.appendChild(chip);
      });
      count.textContent = t('selectedCount', '{n} selected', { n: n });
      clearBtn.disabled = n === 0;
    }
    function filter() {
      var q = normalize(searchInput.value);
      var visible = 0;
      labels.forEach(function (l) {
        var hay = normalize(labelText(l) + ' ' + (l.getAttribute('data-search') || '') + ' ' + ((l.querySelector('input') || {}).value || ''));
        var match = !q || hay.indexOf(q) !== -1;
        l.hidden = !match;
        if (match) { visible++; }
      });
      empty.classList.toggle('is-visible', visible === 0);
    }
    searchInput.addEventListener('input', filter);
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') {
        var first = labels.filter(function (l) { return !l.hidden; })[0];
        if (first) { e.preventDefault(); first.querySelector('input').focus(); }
      }
      if (e.key === 'Escape' && searchInput.value) { e.preventDefault(); searchInput.value = ''; filter(); }
    });
    list.addEventListener('change', function () { render(); syncHidden(); });
    clearBtn.addEventListener('click', function () {
      var doClear = function () { inputs().forEach(function (i) { i.checked = false; }); render(); syncHidden(); fire(list, 'change'); };
      if (values().length > 5) { confirmDialog({ message: t('clearAllConfirm', 'Clear all selected items?'), danger: true }).then(function (yes) { if (yes) { doClear(); } }); }
      else { doClear(); }
    });

    // Modo json: precargar desde el hidden si ya tiene valor
    if (hidden && hidden.value) {
      try {
        var pre = JSON.parse(hidden.value);
        if (Array.isArray(pre)) { inputs().forEach(function (i) { i.checked = pre.indexOf(i.getAttribute('data-value') || i.value) !== -1; }); }
      } catch (e) { /* valor no JSON: se ignora */ }
    }
    render();
    filter();
    var api = { refresh: function () { render(); }, getValues: values, clear: function () { inputs().forEach(function (i) { i.checked = false; }); render(); syncHidden(); }, el: container, focusTarget: searchInput };
    registry.set(container, api);
    return api;
  }

  /* ── FileUpload ───────────────────────────────────────────────────── */
  function FileUpload(container) {
    var input = container.querySelector('input[type=file]');
    if (!input) { return null; }
    container.classList.add('ixf-upload');
    input.classList.add('ixf-visually-hidden');
    input.setAttribute('tabindex', '-1');
    var maxMb = parseFloat(container.getAttribute('data-max-mb')) || 0;
    var accept = (container.getAttribute('data-accept') || input.getAttribute('accept') || '').split(',').map(function (s) { return s.trim().toLowerCase(); }).filter(Boolean);
    if (accept.length && !input.getAttribute('accept')) { input.setAttribute('accept', accept.join(',')); }
    var zone = el('button', 'ixf-upload-zone');
    zone.type = 'button';
    var zi = el('i', 'fa fa-cloud-upload'); zi.setAttribute('aria-hidden', 'true');
    var zt = el('span'); zt.innerHTML = escapeHtml(t('dropOr', 'Drag a file here or')) + ' <strong>' + escapeHtml(t('chooseFile', 'choose a file')) + '</strong>';
    var hintParts = [];
    if (accept.length) { hintParts.push(accept.join(', ')); }
    if (maxMb) { hintParts.push(t('maxSize', 'max. {max} MB', { max: maxMb })); }
    var zh = el('span', 'ixf-upload-hint', hintParts.join(' · '));
    zone.appendChild(zi); zone.appendChild(zt); if (hintParts.length) { zone.appendChild(zh); }
    var fileRow = el('div', 'ixf-upload-file');
    var fi = el('i', 'fa fa-file-o'); fi.setAttribute('aria-hidden', 'true');
    var fname = el('span', 'ixf-upload-name');
    var fsize = el('span', 'ixf-upload-size');
    var frm = el('button', 'ixf-upload-remove', '×'); frm.type = 'button'; frm.setAttribute('aria-label', t('removeFile', 'Remove file'));
    fileRow.appendChild(fi); fileRow.appendChild(fname); fileRow.appendChild(fsize); fileRow.appendChild(frm);
    var progress = el('div', 'ixf-progress');
    progress.setAttribute('role', 'progressbar');
    progress.setAttribute('aria-valuemin', '0'); progress.setAttribute('aria-valuemax', '100'); progress.setAttribute('aria-valuenow', '0');
    var bar = el('div', 'ixf-progress-bar');
    progress.appendChild(bar);
    var error = el('div', 'ixf-upload-error');
    error.setAttribute('role', 'alert');
    container.appendChild(zone); container.appendChild(fileRow); container.appendChild(progress); container.appendChild(error);

    function fmtSize(bytes) {
      if (bytes < 1024) { return bytes + ' B'; }
      if (bytes < 1024 * 1024) { return (bytes / 1024).toFixed(0) + ' KB'; }
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
    function setError(msg) {
      error.textContent = msg || '';
      container.classList.toggle('has-error', !!msg);
    }
    function validate(file) {
      if (!file) { return ''; }
      if (maxMb && file.size > maxMb * 1024 * 1024) { return t('fileTooLarge', 'The file is too large (max. {max} MB).', { max: maxMb }); }
      if (accept.length) {
        var ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
        var okExt = accept.some(function (a) { return a === ext || (a.indexOf('/') !== -1 && (a === file.type || (a.endsWith('/*') && file.type.indexOf(a.slice(0, -1)) === 0))); });
        if (!okExt) { return t('fileTypeNotAllowed', 'This file type is not allowed.'); }
      }
      return '';
    }
    function setFile(file) {
      var problem = validate(file);
      if (problem) { input.value = ''; container.classList.remove('has-file'); setError(problem); fire(input, 'change'); return; }
      setError('');
      if (file) {
        fname.textContent = file.name; fsize.textContent = fmtSize(file.size);
        container.classList.add('has-file');
      } else { container.classList.remove('has-file'); }
    }
    zone.addEventListener('click', function () { input.click(); });
    input.addEventListener('change', function () { setFile(input.files && input.files[0]); });
    frm.addEventListener('click', function () { input.value = ''; setFile(null); fire(input, 'change'); zone.focus(); });
    ['dragenter', 'dragover'].forEach(function (evt) { container.addEventListener(evt, function (e) { e.preventDefault(); container.classList.add('is-dragover'); }); });
    ['dragleave', 'drop'].forEach(function (evt) { container.addEventListener(evt, function (e) { e.preventDefault(); container.classList.remove('is-dragover'); }); });
    container.addEventListener('drop', function (e) {
      var files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length) {
        try { input.files = files; } catch (err) { /* navegadores antiguos */ }
        setFile(files[0]);
        fire(input, 'change');
      }
    });
    var api = {
      refresh: function () { setFile(input.files && input.files[0]); },
      file: function () { return input.files && input.files[0]; },
      setProgress: function (pct) { container.classList.toggle('is-uploading', pct != null && pct < 100); bar.style.width = (pct || 0) + '%'; progress.setAttribute('aria-valuenow', String(pct || 0)); },
      setError: setError,
      reset: function () { input.value = ''; setFile(null); api.setProgress(null); },
      el: container,
      focusTarget: zone
    };
    registry.set(container, api);
    registry.set(input, api);
    return api;
  }

  /* ── Inicialización ───────────────────────────────────────────────── */
  // La marca de "ya inicializado" es por componente: un textarea puede llevar
  // a la vez data-ihpix-markdown y data-ihpix-counter (editor + contador).
  function each(root, selector, fn, key) {
    var mark = 'data-ihpix-ready' + (key ? '-' + key : '');
    var nodes = Array.prototype.slice.call(root.querySelectorAll(selector));
    if (root !== document && root.matches && root.matches(selector)) { nodes.unshift(root); }
    nodes.forEach(function (n) {
      if (n.hasAttribute(mark)) { return; }
      n.setAttribute(mark, '');
      n.setAttribute('data-ihpix-ready', '');
      var inst = fn(n);
      if (inst) { instances.push({ root: n, api: inst }); }
    });
  }

  function init(root) {
    root = root || document;
    loadConfig();
    each(root, 'textarea[data-ihpix-markdown]', MarkdownEditor, 'md');
    each(root, 'textarea[data-ihpix-counter], input[data-ihpix-counter]', CharCounter, 'counter');
    each(root, 'select[data-ihpix-combobox], input[data-ihpix-combobox]', Combobox, 'combobox');
    each(root, '[data-ihpix-multipicker]', MultiPicker, 'mp');
    each(root, '[data-ihpix-upload]', FileUpload, 'upload');
    each(root, '[data-ihpix-confirm]', function (n) { bindConfirm(n); return null; }, 'confirm');
    each(root, '[data-ihpix-modal-open]', function (n) {
      n.addEventListener('click', function (e) { e.preventDefault(); Modal.open(n.getAttribute('data-ihpix-modal-open')); });
      return null;
    }, 'modal');
  }

  function refresh(root) {
    root = root || document;
    instances.forEach(function (entry) {
      if (root === document || root.contains(entry.root)) {
        if (entry.api && typeof entry.api.refresh === 'function') { entry.api.refresh(); }
      }
    });
  }

  function get(node) { return registry.get(node) || null; }

  window.IhpixForms = {
    init: init,
    refresh: refresh,
    get: get,
    t: t,
    csrfToken: csrfToken,
    postForm: postForm,
    upload: upload,
    formatErrors: formatErrors,
    applyFieldErrors: applyFieldErrors,
    clearFieldErrors: clearFieldErrors,
    markInvalid: markInvalid,
    Toast: Toast,
    Modal: Modal,
    confirm: confirmDialog,
    components: { MarkdownEditor: MarkdownEditor, Combobox: Combobox, MultiPicker: MultiPicker, CharCounter: CharCounter, FileUpload: FileUpload },
    config: CONFIG
  };
  window.ihpixToast = function (message, type, options) { return Toast.show(message, type, options); };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(document); });
  } else {
    init(document);
  }
})(window, document);
