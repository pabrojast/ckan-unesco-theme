/**
 * Tracking Display - Renders dataset view counts and resource download badges.
 * Reads tracking data from a JSON script tag injected by package/base.html.
 */
(function () {
  'use strict';

  var dataEl = document.getElementById('tracking-data');
  if (!dataEl) return;

  var data;
  try {
    data = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }
  if (!data || !data.total) return;

  function formatNumber(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
  }

  // --- Dataset page: insert tracking bar after dataset heading ---
  var heading = document.querySelector('.page-heading, h1.heading');
  // Prefer inserting after the dataset-badges div if present
  var badges = document.querySelector('.dataset-badges');
  var insertTarget = badges || heading;

  if (insertTarget) {
    var bar = document.createElement('div');
    bar.className = 'tracking-stats-bar';
    bar.innerHTML =
      '<span class="tracking-stat tracking-views">' +
        '<i class="fa fa-eye"></i> ' +
        '<strong>' + formatNumber(data.total) + '</strong> ' +
        (data.total === 1 ? 'view' : 'views') +
      '</span>';

    // Sum resource downloads
    var totalDownloads = 0;
    if (data.resources) {
      for (var rid in data.resources) {
        if (data.resources.hasOwnProperty(rid)) {
          totalDownloads += data.resources[rid];
        }
      }
    }
    if (totalDownloads > 0) {
      bar.innerHTML +=
        '<span class="tracking-stat tracking-downloads">' +
          '<i class="fa fa-download"></i> ' +
          '<strong>' + formatNumber(totalDownloads) + '</strong> ' +
          (totalDownloads === 1 ? 'download' : 'downloads') +
        '</span>';
    }

    // Insert after badges or after heading
    if (insertTarget.nextSibling) {
      insertTarget.parentNode.insertBefore(bar, insertTarget.nextSibling);
    } else {
      insertTarget.parentNode.appendChild(bar);
    }
  }

  // --- Resource items: add download badges (only if not already present from template) ---
  if (data.resources) {
    var resourceItems = document.querySelectorAll('.resource-item');
    for (var i = 0; i < resourceItems.length; i++) {
      var item = resourceItems[i];
      // Skip if badge already rendered server-side
      if (item.querySelector('.resource-downloads-badge')) continue;

      var link = item.querySelector('a.heading[href*="/resource/"]');
      if (!link) continue;

      var href = link.getAttribute('href') || '';
      var match = href.match(/\/resource\/([a-f0-9-]+)/);
      if (!match) continue;

      var resourceId = match[1];
      var downloads = data.resources[resourceId];
      if (downloads && downloads > 0) {
        var badge = document.createElement('span');
        badge.className = 'resource-downloads-badge';
        badge.innerHTML =
          '<i class="fa fa-download"></i> ' + formatNumber(downloads);
        badge.title = downloads + (downloads === 1 ? ' download' : ' downloads');

        var btnGroup = item.querySelector('.btn-group');
        if (btnGroup) {
          btnGroup.parentNode.insertBefore(badge, btnGroup);
        } else {
          item.appendChild(badge);
        }
      }
    }
  }
})();
