/* IHP-WINS home page v2 (redesign) - added by Jorgen Van Der Biest.
   Behaviour for templates/home/home_v2.html: hero video pause, explore-data
   tabs, the spotlight slide deck, and the sticky section bar.
   Without JavaScript the page still works: both data panels show, the first
   slide shows, and the section links are normal anchors. */
(function () {
  'use strict';

  var root = document.getElementById('hv2');
  if (!root) { return; }
  root.classList.add('hv2-js');

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function scrollToId(id) {
    var el = document.getElementById(id);
    if (!el) { return false; }
    el.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    if (history.replaceState) { history.replaceState(null, '', '#' + id); }
    return true;
  }

  /* In-page links (#IHPWINS, #datasets, ...): smooth scroll, offset by the
     sticky bar through scroll-margin-top in the CSS. */
  root.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a[href^="#"]') : null;
    if (!a || !root.contains(a)) { return; }
    var id = a.getAttribute('href').slice(1);
    if (id && scrollToId(id)) { e.preventDefault(); }
  });

  /* ── Hero video: muted autoplay, pause button, reduced motion ── */
  var video = document.getElementById('hv2-video');
  var vbtn = document.getElementById('hv2-vbtn');
  function setVideoButton(paused) {
    if (!vbtn) { return; }
    vbtn.setAttribute('aria-label', vbtn.getAttribute(paused ? 'data-label-play' : 'data-label-pause'));
    var icon = vbtn.querySelector('.fa');
    if (icon) { icon.className = 'fa ' + (paused ? 'fa-play' : 'fa-pause'); }
  }
  if (video) {
    video.muted = true;
    if (reduceMotion) {
      video.removeAttribute('autoplay');
      video.pause();
      setVideoButton(true);
    } else {
      var p = video.play();
      if (p && p.catch) { p.catch(function () { setVideoButton(true); }); }
    }
    if (vbtn) {
      vbtn.addEventListener('click', function () {
        if (video.paused) {
          var q = video.play();
          if (q && q.catch) { q.catch(function () {}); }
          setVideoButton(false);
        } else {
          video.pause();
          setVideoButton(true);
        }
      });
    }
  }

  /* ── Explore data tabs ── */
  var tabsBox = root.querySelector('[data-hv2-tabs]');
  if (tabsBox) {
    var tabs = tabsBox.querySelectorAll('[data-hv2-tab]');
    var selectTab = function (name, focus) {
      Array.prototype.forEach.call(tabs, function (t) {
        var on = t.getAttribute('data-hv2-tab') === name;
        t.classList.toggle('is-on', on);
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.setAttribute('tabindex', on ? '0' : '-1');
        if (on && focus) { t.focus(); }
      });
      Array.prototype.forEach.call(tabsBox.querySelectorAll('[data-hv2-panel]'), function (p) {
        p.hidden = p.getAttribute('data-hv2-panel') !== name;
      });
      Array.prototype.forEach.call(tabsBox.querySelectorAll('[data-hv2-panel-img]'), function (img) {
        img.hidden = img.getAttribute('data-hv2-panel-img') !== name;
      });
    };
    Array.prototype.forEach.call(tabs, function (t, i) {
      t.addEventListener('click', function () { selectTab(t.getAttribute('data-hv2-tab')); });
      t.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          var next = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
          selectTab(next.getAttribute('data-hv2-tab'), true);
          e.preventDefault();
        }
      });
    });
    selectTab('recent');
  }

  /* ── Spotlight slide deck ── */
  var deck = root.querySelector('[data-hv2-deck]');
  if (deck) {
    var slides = deck.querySelectorAll('[data-hv2-slide]');
    var tabBtns = deck.querySelectorAll('[data-hv2-goto]');
    var toggle = deck.querySelector('[data-hv2-toggle]');
    var current = 0;
    var userPaused = reduceMotion;
    var hovering = false;

    var show = function (i) {
      current = (i + slides.length) % slides.length;
      Array.prototype.forEach.call(slides, function (s, k) {
        s.classList.toggle('is-on', k === current);
        s.setAttribute('aria-hidden', k === current ? 'false' : 'true');
      });
      Array.prototype.forEach.call(tabBtns, function (b, k) {
        b.classList.toggle('is-on', k === current);
        b.setAttribute('aria-selected', k === current ? 'true' : 'false');
        // restart the progress bar
        var bar = b.querySelector('.hv2-prog');
        if (bar && k === current) { bar.style.animation = 'none'; void bar.offsetWidth; bar.style.animation = ''; }
      });
    };
    var refreshPaused = function () {
      deck.classList.toggle('is-paused', userPaused || hovering);
      if (toggle) {
        toggle.setAttribute('aria-label', toggle.getAttribute(userPaused ? 'data-label-play' : 'data-label-pause'));
        var icon = toggle.querySelector('.fa');
        if (icon) { icon.className = 'fa ' + (userPaused ? 'fa-play' : 'fa-pause'); }
      }
    };

    // The progress bar's CSS animation drives the timing: when it ends, advance.
    deck.addEventListener('animationend', function (e) {
      if (e.animationName === 'hv2-fill') { show(current + 1); }
    });
    Array.prototype.forEach.call(tabBtns, function (b) {
      b.addEventListener('click', function () { show(parseInt(b.getAttribute('data-hv2-goto'), 10) || 0); });
    });
    var prev = deck.querySelector('[data-hv2-prev]');
    var next = deck.querySelector('[data-hv2-next]');
    if (prev) { prev.addEventListener('click', function () { show(current - 1); }); }
    if (next) { next.addEventListener('click', function () { show(current + 1); }); }
    if (toggle) { toggle.addEventListener('click', function () { userPaused = !userPaused; refreshPaused(); }); }
    deck.addEventListener('mouseenter', function () { hovering = true; refreshPaused(); });
    deck.addEventListener('mouseleave', function () { hovering = false; refreshPaused(); });
    deck.addEventListener('focusin', function () { hovering = true; refreshPaused(); });
    deck.addEventListener('focusout', function () { hovering = false; refreshPaused(); });
    show(0);
    refreshPaused();
  }

  /* ── Sticky section bar: underline the section in view ── */
  var navLinks = root.querySelectorAll('.hv2-snav');
  if ('IntersectionObserver' in window && navLinks.length) {
    var byId = {};
    Array.prototype.forEach.call(navLinks, function (a) { byId[a.getAttribute('href').slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) { return; }
        Array.prototype.forEach.call(navLinks, function (a) { a.classList.remove('is-on'); a.removeAttribute('aria-current'); });
        var a = byId[en.target.id];
        if (a) { a.classList.add('is-on'); a.setAttribute('aria-current', 'location'); }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    Object.keys(byId).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) { io.observe(el); }
    });
  }
})();
