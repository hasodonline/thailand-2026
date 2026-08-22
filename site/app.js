/* ============================================================
   תאילנד 2026 — ספר הטיול · behaviour
   Four small things, no dependencies:
     1. the sticky day strip tracks what you're reading
     2. gallery photos open in a lightbox
     3. Google map iframes load only when scrolled near —
        six eager iframes would cost six map loads per visit
        against a 300/day cap, and stall the first paint
     4. a light/dark override that survives reloads
   ============================================================ */
(function () {
  'use strict';

  /* ---- 1. day strip ------------------------------------- */
  var nav = document.querySelector('.daynav');
  if (nav) {
    var links = [].slice.call(nav.querySelectorAll('a[href^="#"]'));
    var targets = links
      .map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); })
      .filter(Boolean);

    var mark = function (id) {
      links.forEach(function (a) {
        var on = a.getAttribute('href') === '#' + id;
        a.classList.toggle('on', on);
        if (on && nav.querySelector('.track')) {
          var t = nav.querySelector('.track');
          var want = a.offsetLeft - (t.clientWidth - a.clientWidth) / 2;
          if (Math.abs(t.scrollLeft - want) > 40) t.scrollTo({ left: want, behavior: 'smooth' });
        }
      });
    };

    if ('IntersectionObserver' in window && targets.length) {
      var seen = {};
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { seen[e.target.id] = e.isIntersecting ? e.intersectionRatio : 0; });
        var best = null, score = 0;
        Object.keys(seen).forEach(function (id) { if (seen[id] > score) { score = seen[id]; best = id; } });
        if (best) mark(best);
      }, { rootMargin: '-70px 0px -55% 0px', threshold: [0, .1, .5, 1] });
      targets.forEach(function (t) { io.observe(t); });
    }
  }

  /* ---- 2. lightbox -------------------------------------- */
  var lb = document.querySelector('dialog.lb');
  if (lb && typeof lb.showModal === 'function') {
    var lbImg = lb.querySelector('img'), lbCap = lb.querySelector('.cap');
    document.addEventListener('click', function (ev) {
      var btn = ev.target.closest ? ev.target.closest('.gallery button, figure.zoom') : null;
      if (btn) {
        var img = btn.querySelector('img');
        if (!img) return;
        lbImg.src = img.currentSrc || img.src;
        lbImg.alt = img.alt || '';
        var cap = btn.querySelector('.cap, figcaption');
        lbCap.textContent = cap ? cap.textContent : (img.alt || '');
        lb.showModal();
        return;
      }
      if (ev.target === lb || (ev.target.closest && ev.target.closest('.x'))) lb.close();
    });
    lb.addEventListener('close', function () { lbImg.removeAttribute('src'); });
  }

  /* ---- 3. lazy maps ------------------------------------- */
  var frames = [].slice.call(document.querySelectorAll('iframe[data-src]'));
  if (frames.length) {
    var load = function (f) {
      if (f.dataset.src) { f.src = f.dataset.src; delete f.dataset.src; }
    };
    if ('IntersectionObserver' in window) {
      var mio = new IntersectionObserver(function (entries, obs) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { load(e.target); obs.unobserve(e.target); }
        });
      }, { rootMargin: '400px 0px' });
      frames.forEach(function (f) { mio.observe(f); });
    } else {
      frames.forEach(load);
    }
    // paper needs the real thing, not a placeholder
    window.addEventListener('beforeprint', function () { frames.forEach(load); });
  }

  /* ---- 4. theme ----------------------------------------- */
  var btn = document.querySelector('.themetoggle');
  if (btn) {
    var apply = function (v) {
      if (v) document.documentElement.setAttribute('data-theme', v);
      else document.documentElement.removeAttribute('data-theme');
      btn.textContent = v === 'dark' ? '☀️' : v === 'light' ? '🌙' : '◐';
      btn.setAttribute('aria-label', 'החלפת ערכת צבעים');
    };
    var saved = null;
    try { saved = localStorage.getItem('th26-theme'); } catch (e) {}
    apply(saved);
    btn.addEventListener('click', function () {
      var cur = document.documentElement.getAttribute('data-theme');
      var next = cur === 'dark' ? 'light' : cur === 'light' ? null : 'dark';
      apply(next);
      try {
        if (next) localStorage.setItem('th26-theme', next);
        else localStorage.removeItem('th26-theme');
      } catch (e) {}
    });
  }
})();
