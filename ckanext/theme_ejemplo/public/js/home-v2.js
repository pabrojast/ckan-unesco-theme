/* IHP-WINS home page v2 (redesign) - added by Jorgen Van Der Biest.
   Behaviour for templates/home/home_v2.html: hero video pause, the About
   panel in the hero, the header top bar, explore-data tabs and the sticky
   section bar.
   Without JavaScript the page still works: the About panel is open, both
   data panels show, and the section links are normal anchors. */
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

  /* ── About IHP-WINS: a panel in the hero, collapsed by default. The title
     block and the "About IHP-WINS" button open and close it; the title moves
     up because the hero body sits at the bottom of the hero. ── */
  var hero = document.getElementById('hv2-top');
  var aboutBtn = document.getElementById('hv2-about-btn');
  var aboutPanel = document.getElementById('IHPWINS');
  function setAbout(open) {
    if (!hero || !aboutPanel) { return; }
    hero.classList.toggle('hv2-about-open', open);
    aboutPanel.setAttribute('aria-hidden', open ? 'false' : 'true');
    if ('inert' in aboutPanel) { aboutPanel.inert = !open; }
    if (aboutBtn) {
      aboutBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      var label = aboutBtn.querySelector('.hv2-about-label');
      if (label) { label.textContent = aboutBtn.getAttribute(open ? 'data-label-close' : 'data-label-open'); }
    }
  }
  function aboutIsOpen() { return !!hero && hero.classList.contains('hv2-about-open'); }
  if (hero && aboutPanel) {
    setAbout(false);
    hero.addEventListener('click', function (e) {
      if (!e.target.closest) { return; }
      var trigger = e.target.closest('[data-hv2-about-toggle], #hv2-about-btn');
      if (!trigger || e.target.closest('a')) { return; }
      setAbout(!aboutIsOpen());
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && aboutIsOpen()) {
        setAbout(false);
        if (aboutBtn) { aboutBtn.focus(); }
      }
    });
    if (location.hash === '#IHPWINS') { setAbout(true); }
  }

  /* In-page links (#datasets, ...): smooth scroll, offset by the sticky bar
     through scroll-margin-top in the CSS. Links to #IHPWINS open the About
     panel and scroll back to the top of the hero. */
  root.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a[href^="#"]') : null;
    if (!a || !root.contains(a)) { return; }
    var id = a.getAttribute('href').slice(1);
    if (id === 'IHPWINS' && hero && aboutPanel) {
      e.preventDefault();
      setAbout(true);
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
      if (history.replaceState) { history.replaceState(null, '', '#IHPWINS'); }
      return;
    }
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

  /* ── Header top bar: home-v2.css folds it away on screens with a mouse.
     It unfolds when the mouse reaches the top edge of the page (or keyboard
     focus enters it) and stays open while the mouse is anywhere in the header,
     so it does not fold away on the way down to the menu. ── */
  var header = document.querySelector('header.masthead');
  var topBar = header && header.querySelector('.masthead-top-bar');
  if (topBar) {
    var topBarOpen = false;
    var setTopBar = function (open) {
      if (open !== topBarOpen) { topBarOpen = open; document.body.classList.toggle('hv2-topbar-open', open); }
    };
    header.addEventListener('mousemove', function (e) { if (e.clientY <= 20) { setTopBar(true); } });
    topBar.addEventListener('focusin', function () { setTopBar(true); });
    header.addEventListener('mouseleave', function () {
      if (!topBar.contains(document.activeElement)) { setTopBar(false); }
    });
    topBar.addEventListener('focusout', function (e) {
      if (!topBar.contains(e.relatedTarget) && !header.matches(':hover')) { setTopBar(false); }
    });
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
        var a = byId[en.target.id === 'hv2-top' ? 'IHPWINS' : en.target.id];
        if (a) { a.classList.add('is-on'); a.setAttribute('aria-current', 'location'); }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    Object.keys(byId).forEach(function (id) {
      // The About panel lives in the hero: watch the hero for it
      var el = document.getElementById(id === 'IHPWINS' ? 'hv2-top' : id);
      if (el) { io.observe(el); }
    });
  }
})();
