/*
  Lógica del formulario de reporte IHP-IX (templates/ihpix/report.html).

  Extraída tal cual del <script> inline del template (2026-10) y servida
  como bundle webassets `theme/ihpix-report-js` (depende del kit
  `theme/ihpix-forms-js`, declarado como preload). La configuración que
  antes inyectaba Jinja se lee de:

    <script type="application/json" id="ihpix-report-config">
      {"actionUrl": "...", "editMode": false, "readOnly": false,
       "initialData": {...}, "userId": "...", "keyActivities": {},
       "strings": {clave: texto traducido}}
    </script>

  API pública: window.IhpixReport = { init(config), refresh(), reset() }.
  `init` arranca solo en DOMContentLoaded (tras el kit) y es idempotente;
  `refresh` vuelve a evaluar condicionales, filtros y progreso tras una
  restauración de valores; `reset` equivale a window.ihpixReportReset().
*/
(function (window, document) {
  'use strict';

  var CONFIG = {};
  var S = {};
  var booted = false;
  var refreshFn = null;
  var resetFn = null;

  /* Textos por defecto (inglés); el template los sustituye por la traducción */
  var DEFAULT_STRINGS = {
    dismissNotification: 'Dismiss notification',
    fixHighlighted: 'Please fix the highlighted fields.',
    draftSaved: 'Draft saved.',
    submitted: 'Report submitted successfully!',
    genericError: 'An error occurred. Please try again.',
    networkError: 'Network error. Please check your connection and try again.',
    requiredDone: 'required fields completed',
    allRequiredDone: 'All required fields completed',
    optionalTouched: 'Optional section with answers',
    saving: 'Saving…',
    savedBrowser: 'Saved in this browser',
    savedServer: 'Saved on the server',
    restored: 'We restored your unsaved answers from a previous session.',
    draftDiscarded: 'Draft discarded. You can start a fresh report.',
    reviewComplete: 'Complete',
    reviewMissing: 'Missing',
    reviewOptional: 'Optional',
    reviewWithAnswers: 'with answers',
    reviewNotFilled: 'not filled',
    reviewEdit: 'Edit',
    reviewFix: 'Fix',
    reviewAdd: 'Add',
    reviewAllDone: 'Everything required is answered. You can submit the report.',
    reviewMissingOne: 'One required answer is missing. Fix it and submit.',
    reviewMissingMany: '{n} required answers are missing. Fix them and submit.',
    reviewOf: 'of',
    answerYesNo: 'yes or no'
  };

  function readConfig() {
    var el = document.getElementById('ihpix-report-config');
    if (!el) { return {}; }
    try { return JSON.parse(el.textContent || '{}') || {}; } catch (e) { return {}; }
  }

  /* Igual que el autoescape de Jinja: el texto va dentro de un atributo HTML */
  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&#34;').replace(/'/g, '&#39;');
  }

  function init(config) {
    if (booted) { return api; }
    CONFIG = config || readConfig();
    S = {};
    Object.keys(DEFAULT_STRINGS).forEach(function (k) { S[k] = DEFAULT_STRINGS[k]; });
    Object.keys(CONFIG.strings || {}).forEach(function (k) { S[k] = CONFIG.strings[k]; });

    var form = document.getElementById('ihpix-report-form');
    if (!form) { return api; }           // página sin formulario (p. ej. sin sesión)
    booted = true;

    var form = document.getElementById('ihpix-report-form');
    var submitBtn = document.getElementById('ihpix-report-submit-btn');
    var draftBtn = document.getElementById('ihpix-report-draft-btn');
    var successState = document.getElementById('ihpix-report-success');
    var toastContainer = document.getElementById('ihpix-report-toasts');
    var errorSummary = document.getElementById('ihpix-error-summary');
    var progressFill = document.getElementById('ihpix-progress-fill');
    var progressText = document.getElementById('ihpix-progress-text');
    var progressBar = document.getElementById('ihpix-progressbar');
    var autosaveStatus = document.getElementById('ihpix-autosave-status');
    var backToTop = document.getElementById('ihpix-backtotop');
    var restoreBanner = document.getElementById('ihpix-restore-banner');
    var restoreText = document.getElementById('ihpix-restore-text');
    var restoreDiscard = document.getElementById('ihpix-restore-discard');
    var prefersReducedMotion = !!(window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches);

    /* Modo del formulario (lo fija el controller) */
    var FORM_ACTION_URL = CONFIG.actionUrl || '';
    var EDIT_MODE = !!CONFIG.editMode;
    var READ_ONLY = !!CONFIG.readOnly;
    var INITIAL_DATA = CONFIG.initialData || {};

    /* ── Toasts ─────────────────────────────────────────────────── */
    function showToast(message, type) {
      // Kit compartido si está cargado; si no, el toast local de siempre
      if (window.ihpixToast) { window.ihpixToast(message, type); return; }
      var toast = document.createElement('div');
      toast.className = 'ihpix-report-toast ihpix-report-toast-' + type;
      var icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
      toast.innerHTML = '<i class="fa ' + icon + '" aria-hidden="true"></i><span></span>' +
        '<button class="ihpix-report-toast-close" type="button" ' +
        'aria-label="' + escapeHtml(S.dismissNotification) + '">&times;</button>';
      toast.querySelector('span').textContent = message;
      toast.querySelector('.ihpix-report-toast-close').addEventListener('click', function() {
        removeToast(toast);
      });
      toastContainer.appendChild(toast);
      setTimeout(function() { removeToast(toast); }, 6000);
    }
    /* Disponible para widgets incluidos (p. ej. Sección VII) */
    window.ihpixReportToast = showToast;
    function removeToast(toast) {
      if (!toast.parentNode) return;
      toast.style.animation = 'ihpix-report-slideOut 0.3s ease forwards';
      setTimeout(function() {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300);
    }

    /* ── Conditional reveals ────────────────────────────────────── */
    function evaluateConditionals() {
      var conditionals = form.querySelectorAll('.ihpix-conditional');
      conditionals.forEach(function(el) {
        var name = el.getAttribute('data-conditional-on');
        var showWhen = el.getAttribute('data-show-when');
        var mode = el.getAttribute('data-conditional-mode') || 'equals';
        var inputs = form.querySelectorAll('[name="' + name + '"]');
        var matched = false;
        inputs.forEach(function(inp) {
          if (inp.type === 'radio' || inp.type === 'checkbox') {
            if (inp.checked && inp.value === showWhen) matched = true;
          } else if (mode === 'contains') {
            if (inp.value && inp.value.indexOf(showWhen) !== -1) matched = true;
          } else {
            if (inp.value === showWhen) matched = true;
          }
        });
        // For checkbox groups in 'contains' mode, check any checked
        if (mode === 'contains' && inputs.length && inputs[0].type === 'checkbox') {
          inputs.forEach(function(inp) {
            if (inp.checked && inp.value === showWhen) matched = true;
          });
        }
        el.classList.toggle('show', matched);
      });
    }

    form.addEventListener('change', evaluateConditionals);
    evaluateConditionals();

    /* ── Char counters ──────────────────────────────────────────── */
    function setupCounters() {
      var textareas = form.querySelectorAll('[data-counter]');
      textareas.forEach(function(ta) {
        var counter = document.getElementById(ta.getAttribute('data-counter'));
        if (!counter) return;
        var max = parseInt(ta.getAttribute('maxlength') || '0', 10);
        function update() {
          var len = ta.value.length;
          counter.textContent = len + ' / ' + max;
          counter.classList.toggle('over', max > 0 && len > max * 0.9);
        }
        ta.addEventListener('input', update);
        update();
      });
    }
    setupCounters();

    /* ── PA → Output filter ─────────────────────────────────────── */
    var paSelect = document.getElementById('ihpix-field-priority-area');
    var outputSelect = document.getElementById('ihpix-field-output');
    var originalOutputOptions = outputSelect ? Array.prototype.slice.call(outputSelect.options) : [];
    function filterOutputs() {
      if (!paSelect || !outputSelect) return;
      var pa = paSelect.value;
      outputSelect.innerHTML = '';
      originalOutputOptions.forEach(function(opt) {
        if (!opt.value || opt.getAttribute('data-pa') === pa) {
          outputSelect.appendChild(opt.cloneNode(true));
        }
      });
    }
    if (paSelect) {
      paSelect.addEventListener('change', function () { filterOutputs(); filterKeyActivities(); });
      filterOutputs();
    }

    /* ── Output → Key activity filter ───────────────────────────── */
    var kaSelect = document.getElementById('ihpix-field-key-activity-code');
    var kaNote = document.getElementById('ihpix-key-activity-note');
    var originalKaOptions = kaSelect ? Array.prototype.slice.call(kaSelect.options) : [];
    function filterKeyActivities() {
      if (!kaSelect || !outputSelect) return;
      var out = outputSelect.value;
      var current = kaSelect.value;
      kaSelect.innerHTML = '';
      var shown = 0;
      originalKaOptions.forEach(function (opt) {
        if (!opt.value || opt.getAttribute('data-output') === out) {
          kaSelect.appendChild(opt.cloneNode(true));
          if (opt.value) shown++;
        }
      });
      if (current && kaSelect.querySelector('option[value="' + current.replace(/"/g, '') + '"]')) {
        kaSelect.value = current;
      } else {
        kaSelect.value = '';
      }
      var hasList = shown > 0;
      kaSelect.disabled = !out || !hasList;
      kaSelect.hidden = !!out && !hasList;
      if (kaNote) kaNote.hidden = !out || hasList;
      if (window.IhpixForms && window.IhpixForms.refresh) window.IhpixForms.refresh(kaSelect.parentNode);
    }
    if (outputSelect) {
      outputSelect.addEventListener('change', filterKeyActivities);
      filterKeyActivities();
    }

    /* ── Section nav: estado activo + scroll suave ──────────────── */
    var navLinks = document.querySelectorAll('.ihpix-section-nav a');
    var sectionMap = {};
    navLinks.forEach(function(a) {
      var href = a.getAttribute('href');
      if (href && href.charAt(0) === '#') {
        var id = href.substring(1);
        sectionMap[id] = a;
        a.addEventListener('click', function(e) {
          var target = document.getElementById(id);
          if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
            if (history.replaceState) history.replaceState(null, '', href);
          }
        });
      }
    });
    function updateNav() {
      var scrollPos = window.scrollY + 130;
      var current = null;
      Object.keys(sectionMap).forEach(function(id) {
        var sec = document.getElementById(id);
        if (sec && sec.offsetTop <= scrollPos) current = id;
      });
      navLinks.forEach(function(a) { a.classList.remove('active'); });
      if (current && sectionMap[current]) sectionMap[current].classList.add('active');
    }
    window.addEventListener('scroll', updateNav, { passive: true });
    updateNav();

    /* ── Validation ─────────────────────────────────────────────── */
    function clearFieldErrors() {
      form.querySelectorAll('.ihpix-report-field-error').forEach(function(f) {
        f.classList.remove('ihpix-report-field-error');
        f.setAttribute('aria-invalid', 'false');
        f.removeAttribute('aria-describedby');
      });
      form.querySelectorAll('.ihpix-report-error-text').forEach(function(t) {
        t.style.display = 'none';
      });
    }
    function showFieldError(fieldId, errorId) {
      var field = document.getElementById(fieldId);
      var error = document.getElementById(errorId);
      if (field) {
        field.classList.add('ihpix-report-field-error');
        field.setAttribute('aria-invalid', 'true');
        if (errorId) field.setAttribute('aria-describedby', errorId);
      }
      if (error) error.style.display = 'block';
    }
    function clearFieldError(fieldId, errorId) {
      var field = document.getElementById(fieldId);
      var error = document.getElementById(errorId);
      if (field) {
        field.classList.remove('ihpix-report-field-error');
        field.setAttribute('aria-invalid', 'false');
        field.removeAttribute('aria-describedby');
      }
      if (error) error.style.display = 'none';
    }
    function labelTextFor(fieldId) {
      var l = document.querySelector('label[for="' + fieldId + '"]');
      if (!l) {
        var box = document.getElementById(fieldId);
        if (box) { l = box.querySelector('legend .ihpix-report-label') || box.querySelector('legend'); }
      }
      if (!l) return conflictText('Review and submit');
      var clone = l.cloneNode(true);
      clone.querySelectorAll('.ixf-sr-only, .ihpix-report-help, .kpi-id').forEach(function (n) { n.parentNode.removeChild(n); });
      return clone.textContent.replace(/\*/g, '').replace(/\s+/g, ' ').trim();
    }
    function buildErrorSummary(items) {
      if (!errorSummary) return;
      var ul = errorSummary.querySelector('ul');
      ul.innerHTML = '';
      items.forEach(function(it) {
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.href = '#' + it.fieldId;
        a.textContent = it.label;
        a.addEventListener('click', function(e) {
          e.preventDefault();
          var f = document.getElementById(it.fieldId);
          if (f) {
            f.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'center' });
            var component = window.IhpixForms && window.IhpixForms.get(f);
            var target = (component && component.focusTarget) || f.querySelector('input:not([type="hidden"]), select, textarea, button') || f;
            setTimeout(function() { try { target.focus(); } catch (err) {} }, 350);
          }
        });
        li.appendChild(a);
        ul.appendChild(li);
      });
      errorSummary.classList.add('show');
    }

    /* Errores de validación del servidor → mismos estilos que los locales */
    function highlightServerErrors(errors) {
      clearFieldErrors();
      var failed = [];
      Object.keys(errors).forEach(function(name) {
        var msg = errors[name];
        if (Array.isArray(msg)) msg = msg.join(', ');
        var relation = window.IhpixRelations && window.IhpixRelations.serverError(name, String(msg));
        if (relation) {failed.push(relation); return;}
        var cfg = null;
        REQUIRED_FIELDS.forEach(function(c) { if (c.name === name) cfg = c; });
        var inp = form.querySelector('[name="' + name + '"]');
        var fieldId = cfg ? cfg.fieldId : (inp && inp.id ? inp.id : '');
        if (cfg) {
          showFieldError(cfg.fieldId, cfg.errorId);
        } else if (inp) {
          var box = inp.closest ? inp.closest('.ihpix-report-field') : null;
          (box || inp).classList.add('ihpix-report-field-error');
        }
        var label = fieldId ? labelTextFor(fieldId) : conflictText('Review and submit');
        if (!fieldId) fieldId = 'ihpix-review-summary';
        failed.push({ fieldId: fieldId, label: label + ': ' + msg });
      });
      updateSectionStatus();
      if (failed.length && errorSummary) {
        buildErrorSummary(failed);
        errorSummary.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
      }
    }

    /* ── Reglas adicionales: URL, rango de fechas, jóvenes/mujeres ≤ total ── */
    function fieldValue(name) {
      var inp = form.querySelector('[name="' + name + '"]');
      return inp ? (inp.value || '').trim() : '';
    }
    function ratioOk(part, total) {
      var p = parseInt(fieldValue(part), 10), t = parseInt(fieldValue(total), 10);
      if (isNaN(p) || isNaN(t)) return true;
      return p <= t;
    }
    var EXTRA_RULES = [
      { fieldId: 'ihpix-field-link', errorId: 'ihpix-error-link',
        test: function() { var v = fieldValue('link'); return !v || /^https?:\/\/\S+$/i.test(v); } },
      { fieldId: 'ihpix-field-end-date', errorId: 'ihpix-error-end-date',
        test: function() { var s = fieldValue('start_date'), e = fieldValue('end_date'); return !s || !e || e >= s; } },
      { fieldId: 'ihpix-field-sk-youth', errorId: 'ihpix-error-sk-youth', test: function() { return ratioOk('stakeholders_knowledge_youth', 'stakeholders_knowledge'); } },
      { fieldId: 'ihpix-field-sk-female', errorId: 'ihpix-error-sk-female', test: function() { return ratioOk('stakeholders_knowledge_female', 'stakeholders_knowledge'); } },
      { fieldId: 'ihpix-field-sa-youth', errorId: 'ihpix-error-sa-youth', test: function() { return ratioOk('stakeholders_awareness_youth', 'stakeholders_awareness'); } },
      { fieldId: 'ihpix-field-sa-female', errorId: 'ihpix-error-sa-female', test: function() { return ratioOk('stakeholders_awareness_female', 'stakeholders_awareness'); } }
    ];
    function validateExtras() {
      var failed = [];
      EXTRA_RULES.forEach(function(r) {
        var field = document.getElementById(r.fieldId);
        if (!field || field.disabled) return;
        // Un campo oculto por un gate en "no" no se valida
        if (field.offsetParent === null) { clearFieldError(r.fieldId, r.errorId); return; }
        if (r.test()) {
          clearFieldError(r.fieldId, r.errorId);
        } else {
          showFieldError(r.fieldId, r.errorId);
          failed.push({ fieldId: r.fieldId, label: labelTextFor(r.fieldId) });
        }
      });
      return failed;
    }
    EXTRA_RULES.forEach(function(r) {
      var field = document.getElementById(r.fieldId);
      if (!field) return;
      field.addEventListener('blur', function() { validateExtras(); syncErrorSummary(); });
      field.addEventListener('change', function() { validateExtras(); syncErrorSummary(); });
    });
    (function() {
      var startDate = document.getElementById('ihpix-field-start-date');
      var endDate = document.getElementById('ihpix-field-end-date');
      if (startDate && endDate) {
        var syncMin = function() { endDate.min = startDate.value || ''; validateExtras(); };
        startDate.addEventListener('change', syncMin);
        syncMin();
      }
      ['stakeholders_knowledge', 'stakeholders_awareness'].forEach(function(n) {
        var inp = form.querySelector('[name="' + n + '"]');
        if (inp) inp.addEventListener('change', function() { validateExtras(); syncErrorSummary(); });
      });
    })();

    function validateForm(isDraft) {
      clearFieldErrors();
      var failed = [];
      if (!isDraft) {
        REQUIRED_FIELDS.forEach(function(c) {
          if (!isFieldValid(c)) {
            showFieldError(c.fieldId, c.errorId);
            failed.push({ fieldId: c.fieldId, label: labelTextFor(c.fieldId) });
          }
        });
      } else {
        // Draft: sólo el título es obligatorio
        var title = form.querySelector('[name="title"]');
        if (!title.value.trim()) {
          showFieldError('ihpix-field-title', 'ihpix-error-title');
          failed.push({ fieldId: 'ihpix-field-title', label: labelTextFor('ihpix-field-title') });
        }
      }
      failed = failed.concat(validateExtras());
      if (window.IhpixRelations) failed = failed.concat(window.IhpixRelations.validate());
      updateSectionStatus();
      if (failed.length) {
        buildErrorSummary(failed);
        errorSummary.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
        try { errorSummary.focus(); } catch (err) {}
        return false;
      }
      if (errorSummary) errorSummary.classList.remove('show');
      return true;
    }

    function conflictText(value) {return (CONFIG.relationStrings || {})[value] || value;}
    function showConflict(current) {
      var box = document.getElementById('ihpix-conflict');
      var local = collectFormData();
      box.replaceChildren(); box.hidden = false;
      var heading = document.createElement('h3');
      heading.textContent = conflictText('A newer version was saved. Choose which changes to keep.');
      box.appendChild(heading);
      var choices = [];
      Object.keys(local).forEach(function (field) {
        if (field === 'expected_revision' || field === '_csrf_token' || current[field] === undefined) return;
        var remote = current[field];
        if (Array.isArray(remote) && !Array.isArray(local[field])) remote = JSON.stringify(remote);
        if (JSON.stringify(remote) === JSON.stringify(local[field]) || String(remote) === String(local[field])) return;
        var row = document.createElement('div'), title = document.createElement('strong');
        var input = form.elements[field];
        var label = input && input.id ? form.querySelector('label[for="' + input.id + '"]') : null;
        title.textContent = label ? label.textContent.trim() : field.replace(/_/g, ' '); row.appendChild(title);
        var details = document.createElement('pre');
        details.textContent = conflictText('Your answer') + ': ' + JSON.stringify(local[field]) + '\n' + conflictText('Saved answer') + ': ' + JSON.stringify(remote);
        row.appendChild(details);
        var select = document.createElement('select'); select.setAttribute('aria-label', field);
        [['',conflictText('Choose an answer')],['local',conflictText('Keep my answer')],['server',conflictText('Use saved answer')]].forEach(function (pair) {
          var option = document.createElement('option'); option.value = pair[0]; option.textContent = pair[1]; select.appendChild(option);
        });
        row.appendChild(select); box.appendChild(row); choices.push({field:field, select:select});
      });
      var apply = document.createElement('button'); apply.type = 'button'; apply.className = 'btn btn-primary';
      apply.textContent = conflictText('Apply choices to my draft'); box.appendChild(apply);
      apply.onclick = function () {
        if (choices.some(function (x) {return !x.select.value;})) {showToast(conflictText('Choose an answer for each changed field.'), 'error'); return;}
        var resolved = Object.assign({}, local);
        choices.forEach(function (x) {if (x.select.value === 'server') resolved[x.field] = current[x.field];});
        resolved.expected_revision = current.expected_revision;
        restoreFormData(resolved); refreshDerivedUI(); applyRestoredSelects(resolved);
        box.hidden = true; persistDraft();
        showToast(conflictText('Changes compared. Review your answers and save the draft.'), 'success');
      };
      box.scrollIntoView({block:'center'});
    }

    /* ── Submit ────────────────────────────────────────────────── */
    function submitForm(asDraft, afterSave) {
      if (!validateForm(asDraft)) {
        showToast(S.fixHighlighted, 'error');
        return;
      }
      var btn = asDraft ? draftBtn : submitBtn;
      btn.classList.add('ihpix-report-loading');
      btn.disabled = true;

      if (window.IhpixRelations) window.IhpixRelations.sync();
      var formData = new FormData(form);
      if (asDraft) formData.append('save_as_draft', '1');

      return fetch(FORM_ACTION_URL, {
        method: 'POST',
        body: formData,
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
      .then(function(response) {
        return response.json().then(function(data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function(result) {
        btn.classList.remove('ihpix-report-loading');
        btn.disabled = false;
        if (result.ok && result.data.success) {
          var msg = result.data.message || (asDraft
            ? S.draftSaved
            : S.submitted);
          showToast(msg, 'success');
          // El servidor pasa a ser la fuente de verdad: el borrador local sobra
          clearDraft();
          if (form.elements.expected_revision && result.data.data) form.elements.expected_revision.value = result.data.data.revision;
          if (errorSummary) errorSummary.classList.remove('show');
          if (restoreBanner) restoreBanner.classList.remove('show');
          if (afterSave) { return afterSave(result.data.data); }
          if (asDraft && EDIT_MODE) {
            // Seguimos en el mismo borrador; sólo actualizamos el indicador
            setAutosaveStatus('server');
            return;
          }
          if (result.data.next_url) {
            // Borrador nuevo → su página de edición; envío → "mis reportes"
            window.location.href = result.data.next_url;
            return;
          }
          form.style.display = 'none';
          successState.classList.add('ihpix-report-visible');
          successState.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
          form.reset();
        } else {
          if (result.data.code === 'revision_conflict') showConflict(result.data.current);
          var err = result.data.errors ? S.fixHighlighted : (result.data.error || result.data.message || S.genericError);
          showToast(err, 'error');
          if (result.data.errors) highlightServerErrors(result.data.errors);
        }
      })
      .catch(function() {
        btn.classList.remove('ihpix-report-loading');
        btn.disabled = false;
        showToast(S.networkError, 'error');
      });
    }

    form.addEventListener('submit', function(e) {
      e.preventDefault();
      submitForm(false);
    });
    draftBtn.addEventListener('click', function() { submitForm(true); });
    form.querySelectorAll('[data-ihpix-resource-start]').forEach(function (link) {
      link.addEventListener('click', function (event) {
        event.preventDefault();
        submitForm(true, function (saved) {
          var data = new FormData(); data.append('kind', link.dataset.ihpixResourceStart);
          if (form.elements._csrf_token) data.append('_csrf_token', form.elements._csrf_token.value);
          return fetch('/ihpix/report/' + saved.id + '/resource-start', {method:'POST', body:data})
            .then(function (response) {if (!response.ok) throw new Error('Resource editor unavailable'); return response.json();})
            .then(function (result) {window.location.href = result.url;});
        });
      });
    });


    /* Allow resetting to submit another report */
    window.ihpixReportReset = function() {
      successState.classList.remove('ihpix-report-visible');
      form.style.display = '';
      clearFieldErrors();
      if (errorSummary) errorSummary.classList.remove('show');
      refreshDerivedUI();
      window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
    };

    /* ════════════════════════════════════════════════════════════
       Mejoras de usabilidad: progreso, autoguardado, buscador de
       Member States, validación en vivo y botón "volver arriba".
       ════════════════════════════════════════════════════════════ */

    // Campos obligatorios: alimentan validación, progreso y estado.
    var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    var REQUIRED_FIELDS = [
      { name: 'focal_point_name', fieldId: 'ihpix-field-focal-point',      errorId: 'ihpix-error-focal-point',      section: 'section-1' },
      { name: 'contact_email',    fieldId: 'ihpix-field-contact-email',    errorId: 'ihpix-error-email',            section: 'section-1', email: true },
      { name: 'institution_type', fieldId: 'ihpix-field-institution-type', errorId: 'ihpix-error-institution-type', section: 'section-1' },
      { name: 'institution',      fieldId: 'ihpix-field-institution',      errorId: 'ihpix-error-institution',      section: 'section-1' },
      { name: 'title',            fieldId: 'ihpix-field-title',            errorId: 'ihpix-error-title',            section: 'section-1' },
      { name: 'description',      fieldId: 'ihpix-field-description',      errorId: 'ihpix-error-description',      section: 'section-1' },
      { name: 'outcomes',         fieldId: 'ihpix-field-outcomes',         errorId: 'ihpix-error-outcomes',         section: 'section-1' },
      { name: 'biennium',         fieldId: 'ihpix-field-biennium',         errorId: 'ihpix-error-biennium',         section: 'section-1' },
      { name: 'unesco_secretariat_participation', fieldId: 'ihpix-gate-unesco',     errorId: 'ihpix-error-gate-unesco',     section: 'section-1', radio: true },
      { name: 'has_member_state_support',         fieldId: 'ihpix-gate-ms-support', errorId: 'ihpix-error-gate-ms-support', section: 'section-1', radio: true },
      { name: 'has_flagship',                     fieldId: 'ihpix-gate-flagship',   errorId: 'ihpix-error-gate-flagship',   section: 'section-1', radio: true },
      { name: 'priority_area',    fieldId: 'ihpix-field-priority-area',    errorId: 'ihpix-error-priority-area',    section: 'section-2' },
      { name: 'output',           fieldId: 'ihpix-field-output',           errorId: 'ihpix-error-output',           section: 'section-2' },
      { name: 'has_synergies',    fieldId: 'ihpix-gate-synergies',         errorId: 'ihpix-error-gate-synergies',   section: 'section-3', radio: true },
      { name: 'regions_benefit',  fieldId: 'ihpix-gate-regions',           errorId: 'ihpix-error-gate-regions',     section: 'section-4', radio: true },
      { name: 'kpi_1a_active',    fieldId: 'ihpix-gate-kpi-1a',            errorId: 'ihpix-error-gate-kpi-1a',      section: 'section-5', radio: true },
      { name: 'kpi_1b_active',    fieldId: 'ihpix-gate-kpi-1b',            errorId: 'ihpix-error-gate-kpi-1b',      section: 'section-5', radio: true },
      { name: 'kpi_2_active',     fieldId: 'ihpix-gate-kpi-2',             errorId: 'ihpix-error-gate-kpi-2',       section: 'section-5', radio: true },
      { name: 'kpi_3_active',     fieldId: 'ihpix-gate-kpi-3',             errorId: 'ihpix-error-gate-kpi-3',       section: 'section-5', radio: true },
      { name: 'kpi_4_active',     fieldId: 'ihpix-gate-kpi-4',             errorId: 'ihpix-error-gate-kpi-4',       section: 'section-5', radio: true },
      { name: 'kpi_5_active',     fieldId: 'ihpix-gate-kpi-5',             errorId: 'ihpix-error-gate-kpi-5',       section: 'section-5', radio: true },
      { name: 'kpi_6_active',     fieldId: 'ihpix-gate-kpi-6',             errorId: 'ihpix-error-gate-kpi-6',       section: 'section-5', radio: true },
      { name: 'kpi_8_active',     fieldId: 'ihpix-gate-kpi-8',             errorId: 'ihpix-error-gate-kpi-8',       section: 'section-5', radio: true }
    ].filter(function (c) { return !!document.getElementById(c.fieldId); });

    function isFieldValid(cfg) {
      if (cfg.radio) {
        return !!form.querySelector('[name="' + cfg.name + '"]:checked');
      }
      var inp = form.querySelector('[name="' + cfg.name + '"]');
      if (!inp) return false;
      var val = (inp.value || '').trim();
      if (!val) return false;
      if (cfg.email) return EMAIL_RE.test(val);
      return true;
    }

    /* Member States: ahora es IhpixForms.MultiPicker (kit compartido) */
    var memberPicker = null;

    /* ── Progreso global y estado por sección ───────────────────── */
    var requiredDoneWord = S.requiredDone;
    var allDoneWord = S.allRequiredDone;

    function sectionTouched(sec) {
      var controls = sec.querySelectorAll('input, select, textarea');
      for (var i = 0; i < controls.length; i++) {
        var ctl = controls[i];
        if (ctl.type === 'button' || ctl.type === 'submit' || ctl.type === 'search') continue;
        if (ctl.type === 'hidden') {
          if (ctl.name === 'links_json' && ctl.value && ctl.value !== '[]') return true;
          continue;
        }
        if (ctl.type === 'radio') { if (ctl.checked && ctl.value === 'yes') return true; continue; }
        if (ctl.type === 'checkbox') { if (ctl.checked) return true; continue; }
        if ((ctl.value || '').trim()) return true;
      }
      return false;
    }

    function updateSectionStatus() {
      var bySection = {};
      REQUIRED_FIELDS.forEach(function(c) {
        if (!bySection[c.section]) bySection[c.section] = { total: 0, done: 0 };
        bySection[c.section].total++;
        if (isFieldValid(c)) bySection[c.section].done++;
      });
      Object.keys(sectionMap).forEach(function(id) {
        var link = sectionMap[id];
        var status = link.querySelector('.ihpix-nav-status');
        if (!status) return;
        var sec = document.getElementById(id);
        var hasError = sec && sec.querySelector('.ihpix-report-field-error');
        var info = bySection[id];
        link.classList.remove('is-complete', 'has-error', 'is-touched');
        link.removeAttribute('title');
        if (hasError) {
          link.classList.add('has-error');
          status.innerHTML = '<i class="fa fa-exclamation-circle" aria-hidden="true"></i>';
        } else if (info && info.done === info.total) {
          link.classList.add('is-complete');
          status.innerHTML = '<i class="fa fa-check-circle" aria-hidden="true"></i>';
        } else if (!info && sec && sectionTouched(sec)) {
          // Sección opcional con contenido: marca tenue
          link.classList.add('is-touched');
          link.setAttribute('title', S.optionalTouched);
          status.innerHTML = '<i class="fa fa-check" aria-hidden="true"></i>';
        } else {
          status.innerHTML = '';
        }
      });
    }

    function updateProgress() {
      var done = 0;
      REQUIRED_FIELDS.forEach(function(c) { if (isFieldValid(c)) done++; });
      var total = REQUIRED_FIELDS.length;
      var pct = Math.round(done / total * 100);
      if (progressFill) progressFill.style.width = pct + '%';
      if (progressBar) progressBar.setAttribute('aria-valuenow', String(pct));
      if (progressText) {
        progressText.textContent = (done === total)
          ? allDoneWord
          : (done + ' / ' + total + ' ' + requiredDoneWord);
      }
      updateSectionStatus();
      renderReview();
    }

    /* ── Tabla "Review and submit" ──────────────────────────────── */
    var reviewBody = document.getElementById('ihpix-review-body');
    var reviewSummary = document.getElementById('ihpix-review-summary');
    var actionsStatus = document.getElementById('ihpix-actions-status');
    var SECTION_NAMES = CONFIG.sections || {};
    var ROMANS = { 'section-1': 'I', 'section-2': 'II', 'section-3': 'III', 'section-4': 'IV', 'section-5': 'V', 'section-6': 'VI', 'section-7': 'VII' };
    function renderReview() {
      if (!reviewBody) return;
      var ids = Object.keys(SECTION_NAMES);
      var missingTotal = 0;
      var html = '';
      ids.forEach(function (id) {
        var sec = document.getElementById(id);
        var req = REQUIRED_FIELDS.filter(function (c) { return c.section === id; });
        var done = req.filter(isFieldValid);
        var missing = req.filter(function (c) { return !isFieldValid(c); });
        missingTotal += missing.length;
        var status, cls, action, actionLabel;
        if (req.length && !missing.length) {
          cls = 'is-complete';
          status = '<i class="fa fa-check-circle" aria-hidden="true"></i> ' + escapeHtml(S.reviewComplete);
          actionLabel = S.reviewEdit;
        } else if (missing.length) {
          cls = 'is-missing';
          var links = missing.slice(0, 3).map(function (c) {
            return '<a href="#' + c.fieldId + '" data-ihpix-review-go="' + c.fieldId + '">' + escapeHtml(labelTextFor(c.fieldId)) + '</a>';
          }).join(', ');
          if (missing.length > 3) links += ' +' + (missing.length - 3);
          status = '<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> <span>' + escapeHtml(S.reviewMissing) + ': ' + links + '</span>';
          actionLabel = S.reviewFix;
        } else {
          cls = 'is-optional';
          var touched = sec && sectionTouched(sec);
          status = escapeHtml(S.reviewOptional) + ' \u00b7 ' + escapeHtml(touched ? S.reviewWithAnswers : S.reviewNotFilled);
          actionLabel = touched ? S.reviewEdit : S.reviewAdd;
        }
        html += '<tr class="' + cls + '">' +
          '<td><span class="ihpix-review-roman">' + (ROMANS[id] || '') + '.</span>' + escapeHtml(SECTION_NAMES[id]) + '</td>' +
          '<td><span class="ihpix-review-status ' + cls + '">' + status + '</span></td>' +
          '<td class="ihpix-num">' + (req.length ? done.length + ' ' + escapeHtml(S.reviewOf) + ' ' + req.length : '') + '</td>' +
          '<td><a href="#' + id + '" data-ihpix-review-go="' + id + '">' + escapeHtml(actionLabel) + '</a></td>' +
          '</tr>';
      });
      reviewBody.innerHTML = html;
      reviewBody.querySelectorAll('[data-ihpix-review-go]').forEach(function (a) {
        a.addEventListener('click', function (e) {
          e.preventDefault();
          var target = document.getElementById(a.getAttribute('data-ihpix-review-go'));
          if (!target) return;
          target.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'center' });
          setTimeout(function () {
            var focusable = target.matches('input, select, textarea') ? target : target.querySelector('input, select, textarea');
            try { (focusable || target).focus({ preventScroll: true }); } catch (err) {}
          }, 350);
        });
      });
      if (reviewSummary) {
        reviewSummary.classList.remove('is-ready', 'is-missing');
        if (!missingTotal) {
          reviewSummary.textContent = S.reviewAllDone;
          reviewSummary.classList.add('is-ready');
        } else if (missingTotal === 1) {
          reviewSummary.textContent = S.reviewMissingOne;
          reviewSummary.classList.add('is-missing');
        } else {
          reviewSummary.textContent = S.reviewMissingMany.replace('{n}', String(missingTotal));
          reviewSummary.classList.add('is-missing');
        }
      }
      if (actionsStatus) {
        actionsStatus.textContent = missingTotal
          ? (missingTotal === 1 ? S.reviewMissingOne : S.reviewMissingMany.replace('{n}', String(missingTotal)))
          : S.reviewAllDone;
      }
    }

    /* ── Validación en vivo al salir de cada campo obligatorio ──── */
    // Oculta el resumen de errores cuando ya no queda ningún campo inválido.
    function syncErrorSummary() {
      if (errorSummary) errorSummary.querySelectorAll('a').forEach(function (link) {
        var id = link.getAttribute('href').slice(1);
        if (id.indexOf('ihpix-relation-field-') !== 0) return;
        var field = document.getElementById(id);
        if (!field || !field.classList.contains('ihpix-report-field-error')) link.parentNode.remove();
      });
      if (errorSummary && errorSummary.classList.contains('show') &&
          !form.querySelector('.ihpix-report-field-error')) {
        errorSummary.classList.remove('show');
      }
    }
    form.addEventListener('change', function () {syncErrorSummary(); updateSectionStatus();});
    form.addEventListener('input', function () {syncErrorSummary(); updateSectionStatus();});
    REQUIRED_FIELDS.forEach(function(c) {
      if (c.radio) {
        form.querySelectorAll('[name="' + c.name + '"]').forEach(function (r) {
          r.addEventListener('change', function () {
            clearFieldError(c.fieldId, c.errorId);
            updateSectionStatus();
            syncErrorSummary();
          });
        });
        return;
      }
      var inp = form.querySelector('[name="' + c.name + '"]');
      if (!inp) return;
      inp.addEventListener('blur', function() {
        if (isFieldValid(c)) {
          clearFieldError(c.fieldId, c.errorId);
        } else {
          showFieldError(c.fieldId, c.errorId);
        }
        updateSectionStatus();
        syncErrorSummary();
      });
      inp.addEventListener('input', function() {
        if (inp.classList.contains('ihpix-report-field-error') && isFieldValid(c)) {
          clearFieldError(c.fieldId, c.errorId);
          updateSectionStatus();
          syncErrorSummary();
        }
      });
    });

    /* ── Autoguardado local (sobrevive recargas y cierres) ──────── */
    var USER_ID = CONFIG.userId || '';
    var LEGACY_SAVE_KEY = 'ihpix-report-draft-v1';
    var SAVE_KEY = 'ihpix-report-draft-v3:' + USER_ID + ':' + (CONFIG.reportId || 'new');
    var saveTimer = null;
    var storageOk = (function() {
      try {
        localStorage.setItem('__ihpix_test__', '1');
        localStorage.removeItem('__ihpix_test__');
        return true;
      } catch (e) { return false; }
    })();

    function setAutosaveStatus(state) {
      if (!autosaveStatus) return;
      if (state === 'saving') {
        autosaveStatus.innerHTML = '<i class="fa fa-spinner fa-spin" aria-hidden="true"></i> ' + escapeHtml(S.saving);
      } else if (state === 'saved') {
        autosaveStatus.innerHTML = '<i class="fa fa-check" aria-hidden="true"></i> ' + escapeHtml(S.savedBrowser);
      } else if (state === 'server') {
        autosaveStatus.innerHTML = '<i class="fa fa-cloud" aria-hidden="true"></i> ' + escapeHtml(S.savedServer);
      } else {
        autosaveStatus.innerHTML = '';
      }
    }

    function collectFormData() {
      if (window.IhpixRelations) window.IhpixRelations.sync();
      var data = {};
      form.querySelectorAll('input, select, textarea').forEach(function(el) {
        if (!el.name || el.type === 'file' || el.type === 'submit' || el.type === 'button') return;
        if (el.type === 'radio') {
          if (!Object.prototype.hasOwnProperty.call(data, el.name)) data[el.name] = '';
          if (el.checked) data[el.name] = el.value;
        } else if (el.type === 'checkbox') {
          if (!data[el.name]) data[el.name] = [];
          if (el.checked) data[el.name].push(el.value);
        } else {
          data[el.name] = el.value;
        }
      });
      return data;
    }

    function restoreFormData(data) {
      Object.keys(data).forEach(function(name) {
        var value = data[name];
        var els = form.querySelectorAll('[name="' + name + '"]');
        if (!els.length) return;
        els.forEach(function(el) {
          if (el.type === 'radio') {
            el.checked = (el.value === value);
          } else if (el.type === 'checkbox') {
            el.checked = Array.isArray(value) && value.indexOf(el.value) !== -1;
          } else if (el.id !== 'ihpix-field-output' && el.id !== 'ihpix-field-key-activity-code') {
            // Output y key activity se aplican tras filtrar (ver applyRestoredSelects)
            el.value = (value == null) ? '' : (Array.isArray(value) ? JSON.stringify(value) : value);
          }
        });
      });
    }

    function refreshDerivedUI() {
      evaluateConditionals();
      if (paSelect) filterOutputs();
      if (kaSelect) filterKeyActivities();
      // Sección VII: vuelve a pintar los adjuntos desde el hidden restaurado
      if (window.ihpixLinks) window.ihpixLinks.reload();
      if (window.IhpixRelations) window.IhpixRelations.reload();
      form.querySelectorAll('[data-counter]').forEach(function(ta) {
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      });
      if (memberPicker) memberPicker.refresh();
      // Componentes del kit (combobox, picker, contadores, markdown) releen
      // el valor del control nativo tras una restauración
      if (window.IhpixForms) window.IhpixForms.refresh(form);
      updateProgress();
    }

    function persistDraft() {
      if (!storageOk) return;
      try {
        localStorage.setItem(SAVE_KEY, JSON.stringify({
          savedAt: Date.now(),
          data: collectFormData()
        }));
        setAutosaveStatus('saved');
      } catch (e) {
        setAutosaveStatus('');
      }
    }

    function scheduleAutosave() {
      if (!storageOk) return;
      setAutosaveStatus('saving');
      if (saveTimer) clearTimeout(saveTimer);
      saveTimer = setTimeout(persistDraft, 900);
    }

    function clearDraft() {
      if (saveTimer) clearTimeout(saveTimer);
      if (!storageOk) return;
      try { localStorage.removeItem(SAVE_KEY); } catch (e) {}
      setAutosaveStatus('');
    }

    /* Valores iniciales del servidor (edición) o de la URL (?pa=&output=) */
    function applyInitialData() {
      if (!INITIAL_DATA || !Object.keys(INITIAL_DATA).length) return false;
      restoreFormData(INITIAL_DATA);
      refreshDerivedUI();
      applyRestoredSelects(INITIAL_DATA);
      return true;
    }

    /* Output y key activity dependen de los selects anteriores: se fijan
       después de filtrar y se vuelve a filtrar la key activity. */
    function applyRestoredSelects(data) {
      if (data.output && outputSelect) {
        outputSelect.value = data.output;
        if (kaSelect) filterKeyActivities();
      }
      if (data.key_activity_code && kaSelect) {
        kaSelect.value = data.key_activity_code;
        if (window.IhpixForms && window.IhpixForms.refresh) window.IhpixForms.refresh(kaSelect.parentNode);
      }
    }

    function initAutosave() {
      applyInitialData();
      if (READ_ONLY) { return; }
      if (!storageOk) {
        if (autosaveStatus) autosaveStatus.style.display = 'none';
        applyInitialData();
        return;
      }
      var raw = null;
      try {
        raw = localStorage.getItem(SAVE_KEY);
        // Los borradores v1 (con "No" por defecto en las puertas) se descartan
        try { localStorage.removeItem(LEGACY_SAVE_KEY); localStorage.removeItem(LEGACY_SAVE_KEY + ':' + USER_ID); } catch (e2) {}
      } catch (e) {}
      if (raw) {
        try {
          var parsed = JSON.parse(raw);
          if (parsed && parsed.data && Object.keys(parsed.data).length) {
            restoreFormData(parsed.data);
            refreshDerivedUI();
            applyRestoredSelects(parsed.data);
            if (restoreBanner) {
              if (restoreText && parsed.savedAt) {
                restoreText.textContent =
                  S.restored
                  + ' (' + new Date(parsed.savedAt).toLocaleString() + ')';
              }
              restoreBanner.classList.add('show');
            }
            setAutosaveStatus('saved');
          }
        } catch (e) {}
      }
      // Las respuestas locales y su revisión prevalecen sobre el servidor/perfil.
      // Los listeners se conectan tras restaurar para no reguardar al cargar.
      form.addEventListener('input', scheduleAutosave);
      form.addEventListener('change', scheduleAutosave);
    }

    if (restoreDiscard) {
      restoreDiscard.addEventListener('click', function() {
        form.reset();
        clearFieldErrors();
        if (errorSummary) errorSummary.classList.remove('show');
        if (restoreBanner) restoreBanner.classList.remove('show');
        refreshDerivedUI();
        clearDraft();
        applyInitialData();
        showToast(S.draftDiscarded, 'success');
      });
    }

    /* ── Botón "volver arriba" ──────────────────────────────────── */
    if (backToTop) {
      window.addEventListener('scroll', function() {
        backToTop.classList.toggle('show', window.scrollY > 700);
      }, { passive: true });
      backToTop.addEventListener('click', function() {
        window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
      });
    }

    /* ── El progreso reacciona a cualquier cambio del formulario ── */
    form.addEventListener('input', updateProgress);
    form.addEventListener('change', updateProgress);

    /* ── Arranque ───────────────────────────────────────────────── */
    initAutosave();
    updateProgress();
    if (READ_ONLY) {
      // Pendiente/publicado para su autor: se puede consultar, no editar
      form.querySelectorAll('input, select, textarea, button').forEach(function(el) {
        el.disabled = true;
      });
    }

    refreshFn = refreshDerivedUI;
    resetFn = window.ihpixReportReset;
    return api;
  }

  function refresh() { if (refreshFn) { refreshFn(); } }
  function reset() { if (resetFn) { resetFn(); } }

  var api = { init: init, refresh: refresh, reset: reset };
  window.IhpixReport = api;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(); });
  } else {
    init();
  }
})(window, document);
