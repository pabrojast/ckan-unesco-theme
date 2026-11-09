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
    savedServer: 'Saved to your account',
    autosaveTitle: 'Saved in this browser. Add an activity title to save to your account.',
    autosaveLocal: 'Saved in this browser. Waiting to sync with your account.',
    autosaveInvalid: 'Saved in this browser. Some answers need correction before saving to your account.',
    autosaveUnsafe: 'Changes are not saved yet. Keep this page open and retry.',
    autosaveConflict: 'Another editor saved changes. Compare the versions before continuing.',
    autosaveManual: 'Changes are saved in this browser. Save explicitly to update this report.',
    continueUploads: 'Continue to uploads',
    continueReview: 'Continue to review',
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
    var currentStep = 1;
    var completed = false;

    /* Los tres pasos comparten un formulario: ocultar un paso no borra sus respuestas. */
    var wizard = document.querySelector('.ihpix-wizard');
    var stepPanels = form.querySelectorAll('[data-ihpix-step]');
    var previousStep = form.querySelector('[data-ihpix-step-previous]');
    var nextStep = form.querySelector('[data-ihpix-step-next]');
    function showStep(step, moveFocus, updateHash) {
      currentStep = Math.max(1, Math.min(3, Number(step) || 1));
      stepPanels.forEach(function (panel) { panel.hidden = Number(panel.dataset.ihpixStep) !== currentStep; });
      if (wizard) wizard.querySelectorAll('button').forEach(function (button) {
        if (Number(button.dataset.ihpixStepGo) === currentStep) button.setAttribute('aria-current', 'step');
        else button.removeAttribute('aria-current');
      });
      document.querySelector('.ihpix-report-layout').classList.toggle('is-later-step', currentStep > 1);
      previousStep.hidden = currentStep === 1;
      nextStep.hidden = currentStep === 3;
      nextStep.textContent = currentStep === 1 ? S.continueUploads : S.continueReview;
      submitBtn.hidden = currentStep !== 3 || READ_ONLY;
      updateProgress();
      if (updateHash) history.replaceState(null, '', '#section-' + (currentStep === 1 ? '1' : currentStep === 2 ? '7' : 'review'));
      if (moveFocus) {
        var panel = form.querySelector('[data-ihpix-step="' + currentStep + '"]');
        panel.focus({preventScroll:true});
        wizard.scrollIntoView({behavior:prefersReducedMotion ? 'auto' : 'smooth', block:'start'});
      }
    }
    function revealStep(target) {
      var panel = target.closest('[data-ihpix-step]');
      if (panel) showStep(panel.dataset.ihpixStep, false, false);
    }
    function stepFromHash() {
      var target = document.getElementById(window.location.hash.slice(1));
      if (target) revealStep(target);
    }
    if (wizard) wizard.querySelectorAll('button').forEach(function (button) {
      button.addEventListener('click', function () { showStep(button.dataset.ihpixStepGo, true, true); persistDraft(); });
    });
    previousStep.addEventListener('click', function () { showStep(currentStep - 1, true, true); persistDraft(); });
    nextStep.addEventListener('click', function () { showStep(currentStep + 1, true, true); persistDraft(); });
    window.addEventListener('hashchange', stepFromHash);

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
            revealStep(target);
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
        if (sec && sec.offsetParent !== null && sec.offsetTop <= scrollPos) current = id;
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
            revealStep(f);
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
        if (field.closest('.ihpix-conditional:not(.show)')) { clearFieldError(r.fieldId, r.errorId); return; }
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
        var resolved = collectFormData();
        choices.forEach(function (x) {if (x.select.value === 'server') resolved[x.field] = current[x.field];});
        resolved.expected_revision = current.expected_revision;
        restoreFormData(resolved); refreshDerivedUI(); applyRestoredSelects(resolved);
        box.hidden = true; conflictPaused = false; persistDraft(); queueServer();
        showToast(conflictText('Changes compared. Review your answers and save the draft.'), 'success');
      };
      box.scrollIntoView({block:'center'});
    }

    /* ── Submit ────────────────────────────────────────────────── */
    function submitForm(asDraft, afterSave) {
      if (READ_ONLY || manualSaving || conflictPaused) return;
      if (!validateForm(asDraft)) { showToast(S.fixHighlighted, 'error'); return; }
      manualSaving = true;
      clearTimeout(saveTimer); clearTimeout(serverTimer);
      var btn = asDraft ? draftBtn : submitBtn;
      btn.classList.add('ihpix-report-loading');
      form.inert = true;
      return (AUTO_URL ? saveToServer() : Promise.resolve(true)).then(function (saved) {
        if (!saved) {
          if (lastSaveError && lastSaveError.errors) highlightServerErrors(lastSaveError.errors);
          showToast(conflictPaused ? S.autosaveConflict : ((lastSaveError && lastSaveError.error) || S.networkError), 'error');
          return;
        }
        if (asDraft && AUTO_URL) {
          showToast(S.draftSaved, 'success');
          if (afterSave) return afterSave(saved);
          return;
        }
        if (window.IhpixRelations) window.IhpixRelations.sync();
        var data = new FormData(form);
        if (asDraft) data.append('save_as_draft', '1');
        return fetch(FORM_ACTION_URL, {method:'POST', body:data, credentials:'same-origin',
          headers:{'X-Requested-With':'XMLHttpRequest'}})
          .then(function (response) { return response.json().then(function (body) { return {ok:response.ok, data:body}; }); })
          .then(function (result) {
            if (!result.ok || !result.data.success) {
              if (result.data.code === 'revision_conflict') { conflictPaused = true; showConflict(result.data.current); setAutosaveStatus('conflict'); }
              if (result.data.errors) highlightServerErrors(result.data.errors);
              showToast(result.data.error || S.genericError, 'error');
              return;
            }
            form.elements.expected_revision.value = result.data.data.revision;
            serverSnapshot = fingerprint(collectFormData());
            INITIAL_DATA = collectFormData();
            clearDraft();
            if (restoreBanner) restoreBanner.classList.remove('show');
            if (errorSummary) errorSummary.classList.remove('show');
            if (asDraft) {
              adoptReport(result.data.data.id, result.data.next_url);
              setAutosaveStatus('server');
              if (afterSave) return afterSave(result.data.data);
              return;
            }
            completed = true;
            showToast(S.submitted, 'success');
            if (result.data.next_url) window.location.href = result.data.next_url;
          });
      }).catch(function () { showToast(S.networkError, 'error'); })
        .then(function () {
          btn.classList.remove('ihpix-report-loading');
          form.inert = false;
          manualSaving = false;
        });
    }

    form.addEventListener('submit', function(e) {
      e.preventDefault();
      if (currentStep < 3) showStep(currentStep + 1, true, true);
      else submitForm(false);
    });
    draftBtn.addEventListener('click', function() { submitForm(true); });
    /* Allow resetting to submit another report */
    window.ihpixReportReset = function() {
      window.location.href = CONFIG.newReportUrl || '/ihpix/report';
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
          revealStep(target);
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

    /* ── Borrador local y sincronización serializada con la cuenta ── */
    var USER_ID = CONFIG.userId || '';
    var REPORT_ID = CONFIG.reportId || '';
    var AUTO_URL = CONFIG.autosaveUrl || '';
    var SAVE_KEY = 'ihpix-report-draft-v3:' + USER_ID + ':' + (REPORT_ID || 'new');
    var clientDraftId = makeDraftId();
    var saveTimer = null, serverTimer = null, serverPending = null;
    var serverSnapshot = null, navigationSnapshot = null, lastSavedData = null;
    var manualSaving = false, conflictPaused = false, lastSaveError = null;
    var storageOk = true, lastSavedAt = null;
    var retrySave = document.getElementById('ihpix-autosave-retry');

    function makeDraftId() {
      if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (letter) {
        var random = Math.floor(Math.random() * 16);
        return (letter === 'x' ? random : (random & 3 | 8)).toString(16);
      });
    }
    function fingerprint(data) {
      var clean = {};
      Object.keys(data).sort().forEach(function (key) {
        if (key !== '_csrf_token' && key !== 'expected_revision') clean[key] = data[key];
      });
      return JSON.stringify(clean);
    }
    function setAutosaveStatus(state) {
      var text = '', icon = 'check';
      if (state === 'saving') { text = S.saving; icon = 'spinner fa-spin'; }
      else if (state === 'server') { text = S.savedServer + (lastSavedAt ? ' · ' + lastSavedAt.toLocaleTimeString() : ''); icon = 'cloud'; }
      else if (state === 'title') text = S.autosaveTitle;
      else if (state === 'local') text = S.autosaveLocal;
      else if (state === 'invalid') text = S.autosaveInvalid;
      else if (state === 'unsafe') { text = S.autosaveUnsafe; icon = 'exclamation-triangle'; }
      else if (state === 'conflict') { text = S.autosaveConflict; icon = 'exclamation-triangle'; }
      else if (state === 'saved') text = AUTO_URL ? S.savedBrowser : S.autosaveManual;
      document.querySelectorAll('[data-ihpix-autosave-status]').forEach(function (el) {
        el.dataset.saveState = state;
        el.innerHTML = text ? '<i class="fa fa-' + icon + '" aria-hidden="true"></i> ' + escapeHtml(text) : '';
      });
      if (retrySave) retrySave.hidden = !AUTO_URL || ['local', 'invalid', 'unsafe'].indexOf(state) < 0;
    }

    function collectFormData() {
      if (window.IhpixRelations) window.IhpixRelations.sync();
      var data = {};
      form.querySelectorAll('input, select, textarea').forEach(function(el) {
        if (!el.name || el.name === '_csrf_token' || el.type === 'file' || el.type === 'submit' || el.type === 'button') return;
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
        if (name === '_csrf_token') return;
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
      if (READ_ONLY) return false;
      var data = collectFormData();
      try {
        localStorage.setItem(SAVE_KEY, JSON.stringify({savedAt:Date.now(), data:data,
          clientDraftId:clientDraftId, reportId:REPORT_ID, serverSnapshot:serverSnapshot, step:currentStep}));
        storageOk = true;
        navigationSnapshot = fingerprint(data);
        return true;
      } catch (error) { storageOk = false; return false; }
    }
    function clearDraft() {
      clearTimeout(saveTimer); clearTimeout(serverTimer);
      try { localStorage.removeItem(SAVE_KEY); } catch (error) {}
      setAutosaveStatus('');
    }
    function adoptReport(id, editUrl) {
      if (!id) return;
      var oldKey = SAVE_KEY;
      REPORT_ID = CONFIG.reportId = id;
      EDIT_MODE = true;
      FORM_ACTION_URL = editUrl || FORM_ACTION_URL;
      SAVE_KEY = 'ihpix-report-draft-v3:' + USER_ID + ':' + id;
      if (editUrl && window.history.replaceState) window.history.replaceState(null, '', editUrl + window.location.hash);
      if (persistDraft() && oldKey !== SAVE_KEY) {
        try { localStorage.removeItem(oldKey); } catch (error) {}
      }
    }
    function queueServer(delay) {
      clearTimeout(serverTimer);
      if (!AUTO_URL || READ_ONLY || manualSaving || conflictPaused) return;
      serverTimer = setTimeout(function () { saveToServer(); }, delay == null ? 1600 : delay);
    }
    function saveToServer() {
      clearTimeout(serverTimer);
      if (!AUTO_URL || READ_ONLY || conflictPaused) return Promise.resolve(null);
      // Todo guardado, incluso el manual, espera el acuse anterior y vuelve a leer la respuesta actual.
      if (serverPending) return serverPending.then(function (saved) { return saved ? saveToServer() : null; });
      var payload = collectFormData(), snapshot = fingerprint(payload);
      persistDraft();
      if (!(payload.title || '').trim()) {
        setAutosaveStatus(storageOk ? 'title' : 'unsafe');
        return Promise.resolve(null);
      }
      if (REPORT_ID && snapshot === serverSnapshot) {
        setAutosaveStatus('server');
        return Promise.resolve(lastSavedData || {id:REPORT_ID, revision:form.elements.expected_revision.value});
      }
      var data = new FormData(form);
      data.append('client_draft_id', clientDraftId);
      if (REPORT_ID) data.append('id', REPORT_ID);
      setAutosaveStatus('saving');
      lastSaveError = null;
      if (restoreDiscard) restoreDiscard.disabled = true;
      serverPending = fetch(AUTO_URL, {method:'POST', body:data, credentials:'same-origin',
        headers:{'X-Requested-With':'XMLHttpRequest', 'Accept':'application/json'}})
        .then(function (response) { return response.json().then(function (body) { return {ok:response.ok, status:response.status, data:body}; }); })
        .then(function (result) {
          if (!result.ok || !result.data.success) {
            lastSaveError = result.data;
            if (result.data.code === 'revision_conflict') {
              adoptReport(result.data.report_id, result.data.edit_url);
              conflictPaused = true;
              showConflict(result.data.current);
              setAutosaveStatus('conflict');
            } else {
              persistDraft();
              setAutosaveStatus(storageOk ? (result.status === 400 ? 'invalid' : 'local') : 'unsafe');
            }
            return null;
          }
          var saved = result.data.data;
          form.elements.expected_revision.value = saved.revision;
          serverSnapshot = snapshot;
          INITIAL_DATA = Object.assign({}, payload, {expected_revision:saved.revision});
          lastSavedData = saved;
          lastSavedAt = new Date();
          adoptReport(saved.id, result.data.next_url);
          if (restoreBanner) restoreBanner.classList.remove('show');
          setAutosaveStatus(fingerprint(collectFormData()) === snapshot ? 'server' : (storageOk ? 'local' : 'unsafe'));
          return saved;
        }).catch(function () {
          persistDraft();
          setAutosaveStatus(storageOk ? 'local' : 'unsafe');
          return null;
        }).then(function (saved) {
          serverPending = null;
          if (restoreDiscard) restoreDiscard.disabled = false;
          if (saved && fingerprint(collectFormData()) !== serverSnapshot) queueServer(100);
          return saved;
        });
      return serverPending;
    }
    function scheduleAutosave() {
      if (READ_ONLY) return;
      clearTimeout(saveTimer);
      saveTimer = setTimeout(function () {
        persistDraft();
        if (!serverPending && !conflictPaused) {
          setAutosaveStatus(fingerprint(collectFormData()) === serverSnapshot ? 'server' :
            (!storageOk ? 'unsafe' : (!AUTO_URL ? 'saved' : (fieldValue('title') ? 'local' : 'title'))));
        }
      }, 300);
      queueServer();
    }
    document.querySelectorAll('#ihpix-my-drafts, .ix-navigation a').forEach(function (link) {
      link.addEventListener('click', function (event) {
        var snapshot = fingerprint(collectFormData());
        if (READ_ONLY || snapshot === navigationSnapshot || snapshot === serverSnapshot) return;
        if (!persistDraft()) {
          event.preventDefault(); event.stopImmediatePropagation();
          window.alert(S.draftNavigationError);
        }
      }, true);
    });
    window.addEventListener('pagehide', function () { if (!READ_ONLY && !completed) persistDraft(); });
    window.addEventListener('beforeunload', function (event) {
      if (READ_ONLY || completed || fingerprint(collectFormData()) === serverSnapshot || persistDraft()) return;
      event.preventDefault(); event.returnValue = '';
    });
    window.addEventListener('online', function () { queueServer(0); });
    if (retrySave) retrySave.addEventListener('click', function () {
      saveToServer().then(function () { if (lastSaveError && lastSaveError.errors) highlightServerErrors(lastSaveError.errors); });
    });

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
      serverSnapshot = REPORT_ID ? fingerprint(collectFormData()) : null;
      if (READ_ONLY) return;
      var raw = null;
      try { raw = localStorage.getItem(SAVE_KEY); } catch (error) { storageOk = false; }
      if (raw) {
        try {
          var parsed = JSON.parse(raw);
          if (parsed && parsed.data) {
            if (parsed.clientDraftId) clientDraftId = parsed.clientDraftId;
            // Si todo quedó confirmado, preferimos la versión actual del servidor (puede venir de otra pestaña).
            if (!parsed.serverSnapshot || fingerprint(parsed.data) !== parsed.serverSnapshot) {
              restoreFormData(parsed.data); refreshDerivedUI(); applyRestoredSelects(parsed.data);
            }
            if (!window.location.hash && parsed.step) currentStep = parsed.step;
            if (restoreBanner && fingerprint(collectFormData()) !== serverSnapshot) {
              restoreText.textContent = S.restored + (parsed.savedAt ? ' (' + new Date(parsed.savedAt).toLocaleString() + ')' : '');
              restoreBanner.classList.add('show');
            }
            if (fingerprint(collectFormData()) !== serverSnapshot) scheduleAutosave();
          }
        } catch (error) {}
      }
      form.addEventListener('input', scheduleAutosave);
      form.addEventListener('change', scheduleAutosave);
      if (REPORT_ID && fingerprint(collectFormData()) === serverSnapshot) setAutosaveStatus('server');
    }
    if (restoreDiscard) restoreDiscard.addEventListener('click', function () {
      if (serverPending) return;
      if (REPORT_ID) { clearDraft(); completed = true; window.location.reload(); return; }
      clearDraft(); form.reset(); clearFieldErrors();
      if (errorSummary) errorSummary.classList.remove('show');
      if (restoreBanner) restoreBanner.classList.remove('show');
      applyInitialData(); refreshDerivedUI();
      navigationSnapshot = fingerprint(collectFormData());
      setAutosaveStatus(REPORT_ID ? 'server' : '');
    });

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
    navigationSnapshot = fingerprint(collectFormData());
    updateProgress();
    document.querySelector('.ihpix-report-page').classList.add('is-wizard-ready');
    wizard.hidden = false;
    showStep(currentStep, false, false);
    stepFromHash();
    if (READ_ONLY) {
      // Pendiente/publicado para su autor: se puede consultar, no editar
      form.querySelectorAll('input, select, textarea, button').forEach(function(el) {
        if (!el.matches('[data-ihpix-step-next], [data-ihpix-step-previous]')) el.disabled = true;
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
