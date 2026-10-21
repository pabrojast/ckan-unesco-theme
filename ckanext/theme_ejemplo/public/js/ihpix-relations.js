/* Controles repetibles. El JSON oculto es compartido con restauración/importación. */
(function () {
  'use strict';
  var config = JSON.parse(document.getElementById('ihpix-report-config').textContent);
  var form = document.getElementById('ihpix-report-form');
  var ready = false;
  var groups = {};
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
  function select(parent, label, options, value) {
    var wrap = element('label', t(label), parent);
    var node = element('select', '', wrap);
    node.className = 'ihpix-report-select';
    node.setAttribute('aria-label', t(label));
    element('option', '—', node).value = '';
    options.forEach(function (pair) { element('option', pair[1], node).value = pair[0]; });
    node.value = value || '';
    return node;
  }
  function remove(parent, row, sync) {
    var button = element('button', t('Remove'), parent);
    button.type = 'button'; button.className = 'btn';
    button.onclick = function () { row.remove(); sync(); form.dispatchEvent(new Event('input', {bubbles:true})); };
  }
  function association(name, data) {
    var parent = form.querySelector('[data-relation-rows="' + name + '"]');
    var row = element('fieldset', '', parent);
    row.className = 'ihpix-relation-row';
    var paOptions = Array.from(form.elements.priority_area.options).filter(function (x) { return x.value; }).map(function (x) { return [x.value, x.textContent]; });
    var pa = select(row, 'Priority Area', paOptions, data.priority_area);
    var outputBox = element('div', '', row), keyBox = element('div', '', row);
    var output, key;
    function keys(value) {
      keyBox.replaceChildren();
      key = select(keyBox, 'Key activity', (config.keyActivities[output.value] || []).map(function (x) { return [x.code, x.code + ' · ' + x.title]; }), value);
      key.onchange = sync;
    }
    function outputs(value, keyValue) {
      outputBox.replaceChildren();
      var opts = Object.keys(config.keyActivities).filter(function (x) {return 'PA' + x.split('.')[0] === pa.value;}).map(function (x) {return [x, x];});
      output = select(outputBox, 'Output', opts, value);
      keys(keyValue);
      output.onchange = function () { keys(''); sync(); };
    }
    outputs(data.output, data.key_activity_code);
    pa.onchange = function () { outputs('', ''); sync(); };
    row.getValue = function () { return {priority_area:pa.value, output:output.value, key_activity_code:key.value}; };
    remove(row, row, sync);
  }
  function supporter(data) {
    var row = element('fieldset', '', form.querySelector('[data-supporter-rows]'));
    row.className = 'ihpix-relation-row';
    var country = select(row, 'Supporting country', config.countries.filter(function (x) {return x.iso2;}).map(function (x) {return [x.iso2, x['country_title_' + config.language] || x.country_title_en];}), data.country);
    var choices = [];
    [['financial','Financial'], ['in_kind','In-kind'], ['hosting','Hosting']].forEach(function (item) {
      var label = element('label', '', row), input = element('input', '', label);
      input.type = 'checkbox'; input.value = item[0]; input.checked = (data.types || []).includes(item[0]);
      label.appendChild(document.createTextNode(' ' + t(item[1]) + ' '));
      input.onchange = sync; choices.push(input);
    });
    country.onchange = sync;
    row.getValue = function () {return {country:country.value, types:choices.filter(function (x) {return x.checked;}).map(function (x) {return x.value;})};};
    remove(row, row, sync);
  }
  function primary() {
    return {priority_area:form.elements.priority_area.value, output:form.elements.output.value,
            key_activity_code:form.elements.key_activity_code.value};
  }
  function sync() {
    if (!ready) return;
    Object.keys(groups).forEach(function (name) {
      var values = Array.from(groups[name].children).map(function (x) {return x.getValue();});
      if (name === 'contributions_json' && form.elements.output.value) values.unshift(primary());
      write(name, values);
    });
    var holder = form.querySelector('[data-supporter-rows]');
    if (holder) write('supporters_json', Array.from(holder.children).map(function (x) {return x.getValue();}));
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
    metadata();
    var legacy = form.querySelector('[data-legacy-supporter]');
    if (legacy) legacy.hidden = !form.elements.supporting_member_state.value;
    if (config.readOnly) form.querySelectorAll('.ihpix-relation-row input, .ihpix-relation-row select, .ihpix-relation-row button, [data-partner-organizations] select, [data-relation-add], [data-supporter-add]').forEach(function (x) {x.disabled = true;});
  }
  form.querySelectorAll('[data-relation-add]').forEach(function (button) {
    button.onclick = function () {association(button.dataset.relationAdd, {}); sync();};
  });
  var addSupporter = form.querySelector('[data-supporter-add]');
  if (addSupporter) addSupporter.onclick = function () {supporter({}); sync();};
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
  window.IhpixRelations = {reload:reload, sync:sync};
}());
