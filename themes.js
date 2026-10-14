// Theme picker — press T anywhere on the site (or use the palette button in
// the header, or the "Theme" link in the footer) to flip through the themes.
//
// Closely modeled on the theme picker on omarchy.org: a carousel of
// screenshot cards, ← / → (or swipe) to browse, Enter to apply, Esc to
// close, and a split-wipe transition as the new theme lands. The choice is
// remembered, follows you to every page, and syncs across open tabs.
//
// The <head> of every page carries a tiny boot script that sets
// <html data-theme="…" data-scheme="…"> before first paint; this file does
// everything else. Palettes live in themes.css; preview screenshots live in
// assets/themes/ (regenerate them with tools/theme-previews.py).

(function () {
  "use strict";

  var THEMES = [
    { id: "original", name: "Original", light: true },
    { id: "catppuccin", name: "Catppuccin" },
    { id: "catppuccin-latte", name: "Catppuccin Latte", light: true },
    { id: "ethereal", name: "Ethereal" },
    { id: "everforest", name: "Everforest" },
    { id: "flexoki-light", name: "Flexoki Light", light: true },
    { id: "gruvbox", name: "Gruvbox" },
    { id: "hackerman", name: "Hackerman" },
    { id: "kanagawa", name: "Kanagawa" },
    { id: "last-horizon", name: "Last Horizon" },
    { id: "lumon", name: "Lumon" },
    { id: "lupine", name: "Lupine", light: true },
    { id: "matte-black", name: "Matte Black" },
    { id: "miasma", name: "Miasma" },
    { id: "nord", name: "Nord" },
    { id: "osaka-jade", name: "Osaka Jade" },
    { id: "retro-82", name: "Retro 82" },
    { id: "ristretto", name: "Ristretto" },
    { id: "rose-pine", name: "Rosé Pine", light: true },
    { id: "solitude", name: "Solitude" },
    { id: "tokyo-night", name: "Tokyo Night" },
    { id: "vantablack", name: "Vantablack" },
    { id: "white", name: "White", light: true }
  ];

  // First-time visitors get the theme that matches their OS appearance;
  // once they pick one, their pick wins everywhere.
  var DEFAULT_LIGHT = "original";
  var DEFAULT_DARK = "tokyo-night";

  var STORE_KEY = "ak-site-theme";    // the visitor's pick (absent = follow the OS)
  var SCHEME_KEY = "ak-site-scheme";  // "light" | "dark", read by the head boot script
  var HINT_KEY = "ak-theme-hint-seen";
  var HINT_DELAY = 1600;
  var SWIPE_PX = 44;

  var root = document.documentElement;
  var me = document.currentScript;
  // themes.js lives at the site root, so its own URL locates the assets
  // from any page depth (/, /blog/, /blog/posts/).
  var BASE = new URL(".", (me && me.src) || location.href).href;

  var mqDark = matchMedia("(prefers-color-scheme: dark)");
  var mqMobile = matchMedia("(max-width: 639px)");
  var mqReduce = matchMedia("(prefers-reduced-motion: reduce)");

  var ICONS = {
    palette: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M2 12C2 6.71457 6.51697 2.5 12 2.5C17.483 2.5 22 6.71457 22 12C22 13.8878 21.4937 15.1519 20.4345 15.8123C19.4491 16.4266 18.2002 16.3605 17.1496 16.2236C16.7813 16.1757 16.397 16.1121 16.0307 16.0515C15.8617 16.0235 15.6965 15.9962 15.5384 15.9713C15.0184 15.8895 14.5499 15.8295 14.1335 15.8234C13.298 15.8112 12.8925 16.0091 12.671 16.4526C12.539 16.7171 12.5395 17.0363 12.6858 17.4705C12.8149 17.8538 13.0214 18.2277 13.2435 18.63C13.2828 18.7012 13.3226 18.7734 13.3626 18.8465C13.4857 19.0721 13.6169 19.3217 13.7077 19.5624C13.7926 19.7875 13.8875 20.117 13.8161 20.466C13.7303 20.8858 13.4434 21.1713 13.0891 21.3241C12.7768 21.4588 12.3992 21.5 12 21.5C6.51697 21.5 2 17.2854 2 12ZM10.25 6.25C9.42157 6.25 8.75 6.92157 8.75 7.75C8.75 8.57843 9.42157 9.25 10.25 9.25C11.0784 9.25 11.75 8.57843 11.75 7.75C11.75 6.92157 11.0784 6.25 10.25 6.25ZM7.25 10.5C6.42157 10.5 5.75 11.1716 5.75 12C5.75 12.8284 6.42157 13.5 7.25 13.5C8.07843 13.5 8.75 12.8284 8.75 12C8.75 11.1716 8.07843 10.5 7.25 10.5ZM15.25 7.75C14.4216 7.75 13.75 8.42157 13.75 9.25C13.75 10.0784 14.4216 10.75 15.25 10.75C16.0784 10.75 16.75 10.0784 16.75 9.25C16.75 8.42157 16.0784 7.75 15.25 7.75Z"/></svg>',
    brush: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M19.25 13.75V2.75H11.5L10 4.75L8.5 2.75H4.75V13.75H9.75L9.42705 18.7557C9.33117 20.2419 10.5107 21.5 12 21.5C13.4893 21.5 14.6688 20.2419 14.5729 18.7557L14.25 13.75H19.25Z" stroke="currentColor" stroke-width="1.5"/><path d="M4.75 10.25H19.25" stroke="currentColor" stroke-width="1.5"/></svg>',
    left: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M14.5 18.25L8.25 12L14.5 5.75" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/></svg>',
    right: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9.5 18.25L15.75 12L9.5 5.75" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/></svg>',
    close: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6.25 6.25L17.75 17.75M17.75 6.25L6.25 17.75" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/></svg>'
  };

  // "AK" set in Fraunces Bold (the site's display face), as outlines, so the
  // favicon can be re-inked in every palette.
  var MONOGRAM = "M5 -8.9H13.6L13.6 -7.6H4.9ZM6.7 -0.5Q6.7 -0.3 6.6 -0.1Q6.4 0 6.1 0H0.8Q0.5 0 0.3 -0.1Q0.1 -0.3 0.1 -0.5Q0.1 -0.7 0.2 -0.9Q0.3 -1 0.5 -1.1L1 -1.3Q1.5 -1.5 2 -2Q2.4 -2.6 2.7 -3.7L7.4 -19.1Q7.6 -19.8 7.5 -20.3Q7.4 -20.7 6.8 -20.9Q6.5 -21.1 6.4 -21.2Q6.2 -21.4 6.2 -21.6Q6.2 -21.8 6.4 -22Q6.6 -22.1 6.9 -22.1H15.1Q15.5 -22.1 15.6 -22Q15.8 -21.8 15.8 -21.6Q15.8 -21.4 15.7 -21.2Q15.5 -21.1 15.2 -20.9Q14.9 -20.8 14.8 -20.6Q14.7 -20.4 14.9 -19.8L20.4 -2.6Q20.6 -2 20.8 -1.6Q21.1 -1.3 21.5 -1.2Q21.8 -1 21.9 -0.9Q22.1 -0.8 22.1 -0.5Q22.1 -0.3 21.9 -0.1Q21.7 0 21.3 0H13.5Q13.2 0 13 -0.1Q12.8 -0.3 12.8 -0.5Q12.8 -0.8 12.9 -0.9Q13.1 -1 13.3 -1.1L14 -1.3Q14.4 -1.4 14.4 -1.7Q14.5 -1.9 14.3 -2.5L8.8 -19.9L9.3 -20.6L4.3 -3.9Q4 -3.2 4.1 -2.7Q4.3 -2.2 4.7 -1.8Q5.1 -1.5 5.7 -1.2L6.3 -1.1Q6.5 -1 6.6 -0.9Q6.7 -0.7 6.7 -0.5Z M29.7 -8.6 38.1 -17.2Q39 -18 39.2 -18.8Q39.5 -19.5 39.2 -20Q39 -20.6 38.2 -20.8L37.6 -21Q37.4 -21.1 37.2 -21.2Q37.1 -21.4 37.1 -21.6Q37.1 -21.8 37.3 -22Q37.5 -22.1 37.8 -22.1H44.7Q45.1 -22.1 45.2 -22Q45.4 -21.8 45.4 -21.6Q45.4 -21.4 45.3 -21.2Q45.1 -21.1 44.7 -21Q44.4 -20.8 44 -20.6Q43.7 -20.4 43.2 -20Q42.6 -19.6 41.8 -18.9Q41.1 -18.2 39.9 -17.1L30.2 -7.5ZM32.9 -11.4 37.3 -15.3 44.5 -2.5Q44.9 -1.8 45.2 -1.5Q45.5 -1.3 45.9 -1.2Q46.2 -1.1 46.3 -0.9Q46.5 -0.7 46.5 -0.5Q46.5 -0.3 46.3 -0.1Q46.1 0 45.7 0H37.3Q36.9 0 36.8 -0.1Q36.6 -0.3 36.6 -0.6Q36.6 -0.8 36.7 -0.9Q36.8 -1.1 37 -1.1L37.8 -1.3Q38.1 -1.3 38.1 -1.6Q38.1 -1.8 37.8 -2.4ZM31.2 -2.1Q31.2 -1.8 31.3 -1.6Q31.5 -1.4 31.8 -1.3L32.7 -1.1Q33 -1 33.1 -0.9Q33.2 -0.8 33.2 -0.5Q33.2 -0.3 33 -0.1Q32.8 0 32.5 0H23.8Q23.5 0 23.3 -0.1Q23.1 -0.3 23.1 -0.5Q23.1 -1 23.6 -1.1L24.5 -1.3Q24.9 -1.4 25.1 -1.6Q25.3 -1.8 25.3 -2.1V-20.1Q25.3 -20.3 25.1 -20.5Q24.9 -20.7 24.5 -20.8L23.6 -21Q23.1 -21.1 23.1 -21.6Q23.1 -21.8 23.3 -22Q23.5 -22.1 23.8 -22.1H32.6Q33 -22.1 33.1 -22Q33.3 -21.8 33.3 -21.6Q33.3 -21.1 32.8 -21L31.9 -20.8Q31.5 -20.7 31.3 -20.5Q31.2 -20.3 31.2 -20.1Z";

  // ------------------------------------------------------------------
  // Theme state
  // ------------------------------------------------------------------

  function find(id) {
    for (var i = 0; i < THEMES.length; i++) if (THEMES[i].id === id) return i;
    return -1;
  }
  function osDefault() { return mqDark.matches ? DEFAULT_DARK : DEFAULT_LIGHT; }
  function storedTheme() {
    try {
      var t = localStorage.getItem(STORE_KEY);
      return find(t) >= 0 ? t : null;
    } catch (e) { return null; }
  }
  function currentTheme() {
    var t = root.getAttribute("data-theme");
    return find(t) >= 0 ? t : osDefault();
  }
  function previewSrc(id) {
    return BASE + "assets/themes/" + id + (mqMobile.matches ? "-m" : "") + ".webp";
  }
  function token(name) {
    return getComputedStyle(document.body || root).getPropertyValue(name).trim();
  }

  function syncChrome() {
    var id = currentTheme();
    var theme = THEMES[find(id)];

    // Footer label(s): "Theme: Tokyo Night".
    var labels = document.querySelectorAll("[data-theme-name]");
    for (var i = 0; i < labels.length; i++) labels[i].textContent = theme.name;

    // Browser UI color (mobile address bar, PWA title bar).
    var bg = token("--bg-base");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "theme-color";
      document.head.appendChild(meta);
    }
    if (bg) meta.setAttribute("content", bg);

    // Favicon: the original PNG for Original, the AK monogram re-inked in
    // the palette's background + brand color for everything else.
    var href, type;
    if (id === "original") {
      href = BASE + "favicon.png";
      type = "image/png";
    } else {
      var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">' +
        '<rect width="64" height="64" rx="13" fill="' + token("--t-bg") + '"/>' +
        '<path transform="translate(8.72 43.56)" fill="' + token("--t-brand") + '" d="' + MONOGRAM + '"/></svg>';
      href = "data:image/svg+xml," + encodeURIComponent(svg);
      type = "image/svg+xml";
    }
    var old = document.querySelectorAll('link[rel~="icon"]');
    for (var j = 0; j < old.length; j++) old[j].parentNode.removeChild(old[j]);
    var link = document.createElement("link");
    link.rel = "icon";
    link.type = type;
    link.href = href;
    document.head.appendChild(link);
  }

  function setTheme(id, persist) {
    if (find(id) < 0) return;
    root.classList.add("tp-no-transitions");
    root.setAttribute("data-theme", id);
    root.setAttribute("data-scheme", THEMES[find(id)].light ? "light" : "dark");
    if (persist) {
      try {
        localStorage.setItem(STORE_KEY, id);
        localStorage.setItem(SCHEME_KEY, THEMES[find(id)].light ? "light" : "dark");
      } catch (e) {}
    }
    syncChrome();
    window.dispatchEvent(new CustomEvent("site-theme-change", { detail: { theme: id } }));
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { root.classList.remove("tp-no-transitions"); });
    });
  }

  // Apply with the split wipe when the browser supports View Transitions
  // (and the visitor hasn't asked for reduced motion); otherwise instantly.
  function applyTheme(id, after) {
    var swap = function () { setTheme(id, true); if (after) after(); };
    if (typeof document.startViewTransition !== "function" || mqReduce.matches) {
      swap();
      return;
    }
    root.classList.add("theme-wipe-frosted");
    var cleanup = function () { root.classList.remove("theme-wipe-frosted"); };
    try {
      var vt = document.startViewTransition(swap);
      vt.finished.then(cleanup, cleanup);
    } catch (e) {
      swap();
      cleanup();
    }
  }

  // ------------------------------------------------------------------
  // Picker
  // ------------------------------------------------------------------

  var picker = null; // { backdrop, dialog, stage, spacer, nameBtn, nameText, live, slots }
  var index = 0;
  var lastFocus = null;
  var lastFocusVisible = false;
  var swipe = { id: -1, from: 0, moved: 0 };
  var wheel = { acc: 0, last: 0, timer: 0 };
  var preloaded = {};

  function preloadAround(center, radius) {
    var n = THEMES.length;
    for (var o = -radius; o <= radius; o++) {
      var src = previewSrc(THEMES[(center + o + n) % n].id);
      if (preloaded[src]) continue;
      preloaded[src] = true;
      var img = new Image();
      img.decoding = "async";
      try { img.fetchPriority = "low"; } catch (e) {}
      img.src = src;
    }
  }

  function el(tag, cls, html) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html) node.innerHTML = html;
    return node;
  }

  function buildPicker() {
    var backdrop = el("div", "tp-backdrop");
    backdrop.setAttribute("aria-hidden", "true");

    var dialog = el("div", "tp-dialog");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", "Theme picker");
    dialog.tabIndex = -1;

    var dismiss = el("div", "tp-dismiss");
    dismiss.setAttribute("aria-hidden", "true");
    dismiss.addEventListener("click", closePicker);

    var stage = el("div", "tp-stage");
    var spacer = el("div", "tp-spacer");
    stage.appendChild(spacer);

    var nameBtn = el("button", "tp-name");
    nameBtn.type = "button";
    var nameText = el("span");
    nameBtn.appendChild(nameText);
    nameBtn.addEventListener("click", commit);

    var prev = el("button", "tp-arrow tp-prev", ICONS.left);
    prev.type = "button";
    prev.setAttribute("aria-label", "Previous theme");
    prev.addEventListener("click", function (e) { e.stopPropagation(); move(-1); });

    var next = el("button", "tp-arrow tp-next", ICONS.right);
    next.type = "button";
    next.setAttribute("aria-label", "Next theme");
    next.addEventListener("click", function (e) { e.stopPropagation(); move(1); });

    var live = el("div", "tp-sr");
    live.setAttribute("aria-live", "polite");

    dialog.appendChild(dismiss);
    dialog.appendChild(stage);
    dialog.appendChild(nameBtn);
    dialog.appendChild(prev);
    dialog.appendChild(next);
    dialog.appendChild(live);

    // Touch: swipe left / right to browse.
    dialog.addEventListener("pointerdown", function (e) {
      if (e.pointerType === "touch") swipe = { id: e.pointerId, from: e.clientX, moved: 0 };
    });
    dialog.addEventListener("pointermove", function (e) {
      if (e.pointerId === swipe.id) swipe.moved = e.clientX - swipe.from;
    });
    dialog.addEventListener("pointerup", function (e) {
      if (e.pointerId !== swipe.id) return;
      swipe.id = -1;
      if (Math.abs(swipe.moved) > SWIPE_PX) move(swipe.moved < 0 ? 1 : -1);
    });
    dialog.addEventListener("pointercancel", function () { swipe.id = -1; swipe.moved = 0; });
    // A swipe that ends on a card must not also "click" it.
    dialog.addEventListener("click", function (e) {
      if (Math.abs(swipe.moved) <= SWIPE_PX) return;
      swipe.moved = 0;
      e.preventDefault();
      e.stopPropagation();
    }, true);

    // Mouse wheel / trackpad: browse, and keep the page behind still.
    dialog.addEventListener("wheel", function (e) {
      e.preventDefault();
      var d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
      if (e.deltaMode === 1) d *= 16;
      clearTimeout(wheel.timer);
      wheel.timer = setTimeout(function () { wheel.acc = 0; }, 180);
      wheel.acc += d;
      var now = Date.now();
      if (Math.abs(wheel.acc) >= 60 && now - wheel.last > 240) {
        move(wheel.acc > 0 ? 1 : -1);
        wheel.acc = 0;
        wheel.last = now;
      }
    }, { passive: false });

    return {
      backdrop: backdrop, dialog: dialog, stage: stage, spacer: spacer,
      nameBtn: nameBtn, nameText: nameText, prev: prev, next: next, live: live,
      slots: {}
    };
  }

  function makeSlot(theme) {
    var slot = el("div", "tp-slot");
    var card = el("button", "tp-card");
    card.type = "button";
    card.tabIndex = -1;
    var frame = el("div", "tp-frame");
    var inner = el("div", "tp-inner");
    var img = el("img");
    img.alt = theme.name + " theme preview";
    img.width = 1600;
    img.height = 900;
    img.decoding = "async";
    img.draggable = false;
    img.src = previewSrc(theme.id);
    img.addEventListener("error", function () {
      if (img.dataset.retried) return;
      img.dataset.retried = "1";
      setTimeout(function () { img.src = previewSrc(theme.id) + "?retry"; }, 1000);
    });
    inner.appendChild(img);
    frame.appendChild(inner);
    card.appendChild(frame);
    slot.appendChild(card);
    card.addEventListener("click", function () {
      var offset = Number(card.getAttribute("data-offset")) || 0;
      if (offset === 0) commit();
      else move(offset);
    });
    slot._frame = frame;
    slot._card = card;
    return slot;
  }

  function render() {
    var n = THEMES.length;
    var visible = {};
    for (var o = -2; o <= 2; o++) visible[THEMES[(index + o + n) % n].id] = o;

    var slots = picker.slots;
    Object.keys(slots).forEach(function (id) {
      if (!(id in visible)) {
        slots[id].parentNode.removeChild(slots[id]);
        delete slots[id];
      }
    });

    Object.keys(visible).forEach(function (id) {
      var o = visible[id];
      var s = Math.abs(o);
      var theme = THEMES[find(id)];
      var slot = slots[id];
      if (!slot) {
        // New cards appear in place; only cards already on stage slide.
        slot = slots[id] = makeSlot(theme);
        slot.style.transition = "none";
        picker.stage.insertBefore(slot, picker.spacer);
        requestAnimationFrame(function () {
          requestAnimationFrame(function () { slot.style.transition = ""; });
        });
      }
      var shift = o === 0 ? 0 : (o < 0 ? -1 : 1) * (6 + s * 12);
      slot.style.transform = "translateX(" + shift + "%) scale(" + (s === 0 ? 1 : 0.88) + ")";
      slot.style.zIndex = String(10 - s);
      slot.setAttribute("aria-hidden", o === 0 ? "false" : "true");
      slot._card.setAttribute("data-offset", String(o));
      slot._card.setAttribute("aria-label", (o === 0 ? "Use " : "Show ") + theme.name);
      slot._frame.classList.toggle("is-active", o === 0);
    });

    var t = THEMES[index];
    picker.nameText.textContent = t.name;
    picker.nameText.setAttribute("data-theme", t.id);
    picker.nameText.classList.toggle("is-light", !!t.light);
    picker.nameBtn.setAttribute("aria-label", "Use " + t.name);
    picker.live.textContent = t.name + ", theme " + (index + 1) + " of " + n +
      (t.id === currentTheme() ? " (current)" : "") + ". Enter to apply.";
    preloadAround(index, 3);
  }

  function move(delta) {
    if (!picker) return;
    var n = THEMES.length;
    index = ((index + delta) % n + n) % n;
    render();
  }

  function commit() {
    if (!picker) return;
    var id = THEMES[index].id;
    if (id === currentTheme()) { closePicker(); return; }
    applyTheme(id, closePicker);
  }

  function setExpanded(open) {
    var triggers = document.querySelectorAll("[data-theme-picker]");
    for (var i = 0; i < triggers.length; i++) triggers[i].setAttribute("aria-expanded", open ? "true" : "false");
  }

  function openPicker() {
    if (picker) return;
    hideNotice(true);
    index = Math.max(0, find(currentTheme()));
    lastFocus = document.activeElement;
    try { lastFocusVisible = !!(lastFocus && lastFocus.matches(":focus-visible")); } catch (e) { lastFocusVisible = false; }
    picker = buildPicker();
    document.body.appendChild(picker.backdrop);
    document.body.appendChild(picker.dialog);
    render();
    picker.dialog.focus({ preventScroll: true });
    document.addEventListener("keydown", onPickerKey, true);
    setExpanded(true);
  }

  function closePicker() {
    if (!picker) return;
    document.removeEventListener("keydown", onPickerKey, true);
    picker.backdrop.parentNode.removeChild(picker.backdrop);
    picker.dialog.parentNode.removeChild(picker.dialog);
    picker = null;
    setExpanded(false);
    if (lastFocus && typeof lastFocus.focus === "function" && document.contains(lastFocus)) {
      try { lastFocus.focus({ preventScroll: true, focusVisible: lastFocusVisible }); } catch (e) {}
    }
  }

  function onPickerKey(e) {
    if (!picker) return;
    var k = e.key;
    if (k === "ArrowLeft" || k === "Left") { e.preventDefault(); move(-1); }
    else if (k === "ArrowRight" || k === "Right") { e.preventDefault(); move(1); }
    else if (k === "Enter" && (e.target === picker.dialog || e.target === picker.nameBtn)) { e.preventDefault(); commit(); }
    else if (k === "Escape" || k === "Esc") { e.preventDefault(); e.stopPropagation(); closePicker(); }
    else if (k === "Tab") {
      // Keep focus inside the dialog: ‹  name  ›
      var order = [picker.prev, picker.nameBtn, picker.next];
      var at = order.indexOf(document.activeElement);
      var to = at < 0 ? (e.shiftKey ? 2 : 0) : (at + (e.shiftKey ? -1 : 1) + order.length) % order.length;
      e.preventDefault();
      order[to].focus();
    }
  }

  function isTyping(target) {
    if (!target || !target.tagName) return false;
    var tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
  }

  // T toggles the picker anywhere (except while typing in a field).
  // Ctrl/Cmd+T belongs to the browser (new tab), so T is unmodified, as on
  // omarchy.org — which also honours Super + Ctrl + Shift + Space.
  window.addEventListener("keydown", function (e) {
    var isT = (e.key === "t" || e.key === "T") && !e.metaKey && !e.ctrlKey && !e.altKey && !isTyping(e.target);
    var isChord = e.code === "Space" && e.metaKey && e.ctrlKey && e.shiftKey;
    if (!isT && !isChord) return;
    if (e.repeat) return;
    e.preventDefault();
    if (picker) closePicker();
    else openPicker();
  });

  document.addEventListener("click", function (e) {
    var trigger = e.target.closest && e.target.closest("[data-theme-picker]");
    if (!trigger) return;
    e.preventDefault();
    openPicker();
  });

  // Warm the cache for the cards nearest the current theme when the
  // visitor looks like they're about to open the picker.
  function warm() { preloadAround(Math.max(0, find(currentTheme())), 2); }
  document.addEventListener("pointerover", function (e) {
    if (e.target.closest && e.target.closest("[data-theme-picker]")) warm();
  }, { passive: true });
  document.addEventListener("focusin", function (e) {
    if (e.target.closest && e.target.closest("[data-theme-picker]")) warm();
  });

  // ------------------------------------------------------------------
  // First-visit notice
  // ------------------------------------------------------------------

  var notice = null;

  function hintSeen() {
    try { return localStorage.getItem(HINT_KEY) === "true"; } catch (e) { return true; }
  }
  function markHintSeen() {
    try { localStorage.setItem(HINT_KEY, "true"); } catch (e) {}
  }

  function showNotice() {
    if (notice || picker || hintSeen()) return;
    var header = document.querySelector(".site-header");
    var top = header ? Math.round(header.getBoundingClientRect().bottom) + 14 : 88;

    notice = el("div", "tp-notice");
    notice.setAttribute("role", "status");
    notice.style.setProperty("--tp-notice-top", Math.max(top, 16) + "px");

    var box = el("div", "tp-notice-box");
    var main = el("button", "tp-notice-main");
    main.type = "button";
    main.innerHTML = ICONS.brush.replace("<svg ", '<svg class="tp-notice-icon" ') +
      '<span><span class="tp-notice-title">Change the theme</span>' +
      '<span class="tp-notice-text">Press T, or tap here. Pick any of ' + THEMES.length +
      ' palettes and every page follows along.</span></span>';
    main.addEventListener("click", openPicker);

    var close = el("button", "tp-notice-close", ICONS.close);
    close.type = "button";
    close.setAttribute("aria-label", "Dismiss");
    close.addEventListener("click", function () { hideNotice(true); });

    box.appendChild(main);
    box.appendChild(close);
    notice.appendChild(box);
    document.body.appendChild(notice);
  }

  function hideNotice(remember) {
    if (remember) markHintSeen();
    if (notice && notice.parentNode) notice.parentNode.removeChild(notice);
    notice = null;
  }

  // ------------------------------------------------------------------
  // Boot
  // ------------------------------------------------------------------

  // Settle anything the head boot script couldn't: a saved theme that no
  // longer exists, or a scheme that doesn't match the theme.
  (function () {
    var saved = null;
    try { saved = localStorage.getItem(STORE_KEY); } catch (e) {}
    if (saved !== null && find(saved) < 0) {
      try { localStorage.removeItem(STORE_KEY); localStorage.removeItem(SCHEME_KEY); } catch (e) {}
    }
    var id = currentTheme();
    var scheme = THEMES[find(id)].light ? "light" : "dark";
    if (root.getAttribute("data-theme") !== id || root.getAttribute("data-scheme") !== scheme) {
      setTheme(id, false);
    } else {
      syncChrome();
    }
    if (storedTheme()) {
      try { localStorage.setItem(SCHEME_KEY, scheme); } catch (e) {}
    }
  })();

  // Follow the OS light/dark switch until the visitor makes a choice.
  var onOsChange = function () { if (!storedTheme()) setTheme(osDefault(), false); };
  if (mqDark.addEventListener) mqDark.addEventListener("change", onOsChange);
  else if (mqDark.addListener) mqDark.addListener(onOsChange);

  // Change it in one tab, every open tab follows.
  window.addEventListener("storage", function (e) {
    if (e.key !== STORE_KEY) return;
    setTheme(find(e.newValue) >= 0 ? e.newValue : osDefault(), false);
    if (picker) { index = Math.max(0, find(currentTheme())); render(); }
  });

  // Swap card art if the viewport crosses the phone breakpoint mid-pick.
  var onMobileChange = function () {
    if (!picker) return;
    Object.keys(picker.slots).forEach(function (id) {
      var img = picker.slots[id].querySelector("img");
      if (img) img.src = previewSrc(id);
    });
  };
  if (mqMobile.addEventListener) mqMobile.addEventListener("change", onMobileChange);

  if (!hintSeen()) setTimeout(showNotice, HINT_DELAY);

  var idle = window.requestIdleCallback || function (fn) { return setTimeout(fn, 1500); };
  idle(function () { preloadAround(Math.max(0, find(currentTheme())), 1); });

  // A tiny public handle, handy from the console: siteTheme.set("nord").
  window.siteTheme = {
    list: THEMES.map(function (t) { return t.id; }),
    get: currentTheme,
    set: function (id) { if (find(id) >= 0) applyTheme(id); },
    open: openPicker,
    close: closePicker
  };
})();
