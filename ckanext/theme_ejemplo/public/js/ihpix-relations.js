/* Controles repetibles. El JSON oculto es compartido con restauración/importación. */
(function () {
  'use strict';
  var config = JSON.parse(document.getElementById('ihpix-report-config').textContent);
  var form = document.getElementById('ihpix-report-form');
  var ready = false;
  var groups = {};
  var sequence = 0;
  var titles = {contributions_json: 'Additional contribution {n}', synergies_json: 'Synergy {n}', supporters_json: 'Supporting country {n}'};
  // Se conserva el catálogo completo antes de que el selector principal lo filtre.
  var outputOptions = Array.from(form.elements.output.options).filter(function (x) {return x.value;}).map(function (x) {return [x.value, x.textContent];});
  function t(value) {return (config.relationStrings || {})[value] || value;}
  function element(tag, text, parent) {
    var node = document.createElement(tag);
    if (text) node.textContent = text;
    if (parent) parent.appendChild(node);
    return node;
  }
  function read(name) {
    try { return JSON.parse(form.elements[name].value || '[]'); } catch (_) { return []; }
  }
  function write(name, value) {
    form.elements[name].value = JSON.stringify(value);
  }
  function select(parent, label, options, value, placeholder) {
    var wrap = element('label', t(label), parent);
    var node = element('select', '', wrap);
    node.id = 'ihpix-relation-field-' + (++sequence);
    wrap.htmlFor = node.id;
    node.className = 'ihpix-report-select';
    node.setAttribute('aria-label', t(label));
    element('option', t(placeholder || 'Select an option'), node).value = '';
    options.forEach(function (pair) { element('option', pair[1], node).value = pair[0]; });
    node.value = value || '';
    return node;
  }
  function remove(parent, row, sync) {
    var actions = element('div', '', parent);
    actions.className = 'ihpix-relation-actions';
    var button = element('button', '', actions);
    button.type = 'button'; button.className = 'ihpix-report-btn is-remove';
    var icon = element('i', '', button); icon.className = 'fa fa-trash'; icon.setAttribute('aria-hidden', 'true');
    element('span', t('Remove'), button);
    button.onclick = function () {
      var holder = row.parentNode;
      var next = row.nextElementSibling || row.previousElementSibling;
      row.remove(); sync(); changed();
      var target = next ? next.querySelector('select') : form.querySelector(holder.hasAttribute('data-supporter-rows') ? '[data-supporter-add]' : '[data-relation-add="' + holder.dataset.relationRows + '"]');
      if (target) target.focus();
    };
  }
  function changed() {form.dispatchEvent(new Event('input', {bubbles:true}));}
  function numberedRow(parent, name) {
    var row = element('fieldset', '', parent);
    row.className = 'ihpix-relation-row'; row.dataset.relationName = name;
    element('legend', '', row).className = 'ihpix-relation-title';
    row.addEventListener('change', function () {
      row.querySelectorAll('.ihpix-report-field-error').forEach(function (node) {node.classList.remove('ihpix-report-field-error'); node.removeAttribute('aria-invalid'); node.removeAttribute('aria-describedby');});
      row.querySelectorAll('[data-relation-error]').forEach(function (node) {node.remove();});
    });
    return row;
  }
  function renumber(holder, name) {
    Array.from(holder.children).forEach(function (row, i) {
      row.querySelector('legend').textContent = t(titles[name]).replace('{n}', i + 1);
      row.querySelector('button').setAttribute('aria-label', t('Remove') + ': ' + row.querySelector('legend').textContent);
    });
  }
  function association(name, data) {
    var parent = form.querySelector('[data-relation-rows="' + name + '"]');
    var row = numberedRow(parent, name);
    var paOptions = Array.from(form.elements.priority_area.options).filter(function (x) { return x.value; }).map(function (x) { return [x.value, x.textContent]; });
    var pa = select(row, 'Priority Area', paOptions, data.priority_area, 'Select a priority area');
    var outputBox = element('div', '', row), keyBox = element('div', '', row);
    var output, key;
    function keys(value) {
      keyBox.replaceChildren();
      key = select(keyBox, 'Key activity (optional)', (config.keyActivities[output.value] || []).map(function (x) { return [x.code, x.code + ' · ' + x.title]; }), value, output.value ? 'Select a key activity' : 'Select an output first');
      key.disabled = !output.value || !!config.readOnly;
      key.onchange = sync;
    }
    function outputs(value, keyValue) {
      outputBox.replaceChildren();
      var opts = outputOptions.filter(function (x) {return 'PA' + x[0].split('.')[0] === pa.value;});
      output = select(outputBox, 'Output', opts, value, pa.value ? 'Select an output' : 'Select a priority area first');
      output.disabled = !pa.value || !!config.readOnly;
      keys(keyValue);
      output.onchange = function () { keys(''); sync(); };
    }
    outputs(data.output, data.key_activity_code);
    pa.onchange = function () { outputs('', ''); sync(); };
    row.getValue = function () { return {priority_area:pa.value, output:output.value, key_activity_code:key.value}; };
    remove(row, row, sync);
    return row;
  }
  function supporter(data) {
    var row = numberedRow(form.querySelector('[data-supporter-rows]'), 'supporters_json');
    var country = select(row, 'Supporting country', config.countries.filter(function (x) {return x.iso2;}).map(function (x) {return [x.iso2, x['country_title_' + config.language] || x.country_title_en];}), data.country, 'Select a country');
    var choices = [];
    var roles = element('div', '', row); roles.className = 'ihpix-relation-roles';
    element('p', t('Type of support (select all that apply)'), roles);
    [['financial','Financial'], ['in_kind','In-kind'], ['hosting','Hosting']].forEach(function (item) {
      var label = element('label', '', roles), input = element('input', '', label);
      input.type = 'checkbox'; input.value = item[0]; input.checked = (data.types || []).includes(item[0]);
      label.appendChild(document.createTextNode(' ' + t(item[1]) + ' '));
      input.onchange = sync; choices.push(input);
    });
    country.onchange = sync;
    row.getValue = function () {return {country:country.value, types:choices.filter(function (x) {return x.checked;}).map(function (x) {return x.value;})};};
    remove(row, row, sync);
    return row;
  }
  function primary() {
    return {priority_area:form.elements.priority_area.value, output:form.elements.output.value,
            key_activity_code:form.elements.key_activity_code.value};
  }
  function sync() {
    if (!ready) return;
    Object.keys(groups).forEach(function (name) {
      var values = Array.from(groups[name].children).map(function (x) {return x.getValue();});
      renumber(groups[name], name);
      if (name === 'contributions_json' && (form.elements.output.value || values.length)) values.unshift(primary());
      if (name === 'synergies_json' && form.elements.has_synergies.value !== 'yes') values = [];
      write(name, values);
    });
    var holder = form.querySelector('[data-supporter-rows]');
    if (holder) {
      renumber(holder, 'supporters_json');
      write('supporters_json', form.elements.has_member_state_support.value === 'yes' ? Array.from(holder.children).map(function (x) {return x.getValue();}) : []);
    }
  }
  function reload() {
    ['contributions_json','synergies_json'].forEach(function (name) {
      groups[name] = form.querySelector('[data-relation-rows="' + name + '"]');
      groups[name].replaceChildren();
      var items = read(name);
      if (name === 'contributions_json') items = items.slice(1);
      items.forEach(function (item) {association(name, item);});
    });
    var holder = form.querySelector('[data-supporter-rows]');
    if (holder) {holder.replaceChildren(); read('supporters_json').forEach(supporter);}
    var partners = form.querySelector('[data-partner-organizations]');
    partners.replaceChildren();
    var picker = select(partners, 'Partner organizations on IHP-WINS', config.organizations.map(function (x) {return [x.id,x.title];}), '');
    picker.multiple = true; picker.size = 5;
    Array.from(picker.options).forEach(function (x) {x.selected = read('partner_org_ids').includes(x.value);});
    picker.onchange = function () {write('partner_org_ids', Array.from(picker.selectedOptions).map(function (x) {return x.value;}).filter(Boolean));};
    ready = true;
    Object.keys(groups).forEach(function (name) {renumber(groups[name], name);});
    if (holder) renumber(holder, 'supporters_json');
    metadata();
    var legacy = form.querySelector('[data-legacy-supporter]');
    if (legacy) legacy.hidden = !form.elements.supporting_member_state.value;
    if (config.readOnly) form.querySelectorAll('.ihpix-relation-row input, .ihpix-relation-row select, .ihpix-relation-row button, [data-partner-organizations] select, [data-relation-add], [data-supporter-add]').forEach(function (x) {x.disabled = true;});
  }
  form.querySelectorAll('[data-relation-add]').forEach(function (button) {
    button.onclick = function () {var row = association(button.dataset.relationAdd, {}); sync(); changed(); row.querySelector('select').focus();};
  });
  var addSupporter = form.querySelector('[data-supporter-add]');
  if (addSupporter) addSupporter.onclick = function () {var row = supporter({}); sync(); changed(); row.querySelector('select').focus();};
  var institution = form.elements.institution_org_id;
  institution.onchange = function () {
    var org = config.organizations.find(function (x) {return x.id === institution.value;});
    if (org) form.elements.institution.value = org.title;
  };
  function metadata() {
    var select = form.elements.country, value = select.value.toLowerCase();
    var title = select.selectedOptions[0] ? select.selectedOptions[0].textContent.trim().toLowerCase() : '';
    var row = config.countries.find(function (country) {return ['iso2','iso3','country_title_en','country_title_es','country_title_fr','country_title_ar'].some(function (key) {var name=(country[key]||'').toLowerCase();return name && (name===title || name===value || name.replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')===value);});});
    var hint = document.getElementById('ihpix-country-metadata');
    if (hint) hint.textContent = row ? ' · '+(row.electoral_group||'')+' · '+(row.regional_group||[]).join(' / ') : '';
  }
  form.elements.country.addEventListener('change', metadata);
  function rowProblem(row) {
    var value = row.getValue(), selects = row.querySelectorAll('select');
    if (row.dataset.relationName === 'supporters_json') {
      if (!value.country) return [selects[0], 'Choose a supporting country.'];
      if (!value.types.length) return [row.querySelector('input'), 'Choose at least one type of support.'];
    } else {
      if (!value.priority_area) return [selects[0], 'Choose a priority area.'];
      if (!value.output) return [selects[1], 'Choose an output for this priority area.'];
    }
    return null;
  }
  function markError(row, field, message) {
    if (!field.id) field.id = 'ihpix-relation-field-' + (++sequence);
    var id = field.id + '-error', hint = document.getElementById(id);
    if (!hint) {hint = element('p', '', row); hint.id = id; hint.dataset.relationError = '';}
    hint.className = 'ihpix-report-error-text'; hint.style.display = 'block'; hint.textContent = message;
    field.classList.add('ihpix-report-field-error'); field.setAttribute('aria-invalid', 'true'); field.setAttribute('aria-describedby', id);
    return {fieldId: field.id, label: row.querySelector('legend').textContent + ': ' + message};
  }
  function validate() {
    var failed = [];
    form.querySelectorAll('.ihpix-relation-row').forEach(function (row) {
      if (row.offsetParent === null) return;
      var problem = rowProblem(row);
      if (problem) failed.push(markError(row, problem[0], t(problem[1])));
    });
    return failed;
  }
  function serverError(name, message) {
    var parts = name.split('.'), holder = groups[parts[0]];
    if (parts[0] === 'supporters_json') holder = form.querySelector('[data-supporter-rows]');
    if (!holder) return null;
    var index = Number(parts[1]) - (parts[0] === 'contributions_json' ? 2 : 1);
    var row = holder.children[index];
    if (!row) return {fieldId: parts[0] === 'contributions_json' ? 'ihpix-field-output' : (parts[0] === 'synergies_json' ? 'ihpix-field-synergies' : 'ihpix-gate-ms-support'), label: t('Please review the selected entries.')};
    var problem = rowProblem(row);
    var messages = {
      'Select an Output belonging to its Priority Area': 'Choose an output for this priority area.',
      'Key activity does not belong to this Output': 'Choose a key activity from the selected output.',
      'Select a UNESCO country': 'Choose a supporting country.',
      'Select financial, in-kind or hosting support': 'Choose at least one type of support.'
    };
    var position = message.indexOf('Key activity') === 0 ? 2 : (parts[0] === 'supporters_json' ? 0 : 1);
    var field = problem ? problem[0] : row.querySelectorAll('select')[position];
    return markError(row, field, t(problem ? problem[1] : (messages[message] || 'Please review the selected entries.')));
  }
  window.IhpixRelations = {reload:reload, sync:sync, validate:validate, serverError:serverError};
}());
