// Shared behavior for every page under /blog — the notes index (search,
// filter, archive stats, surprise-me) and every individual post (theme
// toggle, broken-image fallback). Each block checks for its own elements
// first and quietly does nothing on pages that don't have them.

// Human-readable labels for the tag slugs used in data-tags across posts.
// Kept as an explicit map (rather than read off on-page pills) because the
// compact Archive rows that drive search/filter no longer render pills.
var NOTE_TAG_LABELS = {
  "markov-decision-processes": "Markov Decision Processes",
  "combinatorial-optimization": "Combinatorial Optimization",
  "approximation-guarantees": "Approximation Guarantees",
  "integer-programming": "Integer Programming",
  "companion": "Companion",
  "interactive": "Interactive",
  "simulated-annealing": "Simulated Annealing",
  "metaheuristics": "Metaheuristics",
  "ant-colony-optimization": "Ant Colony Optimization",
  "genetic-algorithms": "Genetic Algorithms",
  "average-reward": "Average Reward",
  "seminar": "Seminar"
};

// Archive: search, tag filtering, live stats, and "random note". Scoped to
// the Archive section specifically — Featured/Recent/Series/Interactive
// above it are curated by hand, not filtered; the Archive is the complete,
// searchable record, which is what "search notes" should mean.
(function () {
  var rows = Array.prototype.slice.call(document.querySelectorAll(".archive-row"));
  if (!rows.length) return;

  var yearGroups = Array.prototype.slice.call(document.querySelectorAll(".archive-year-group"));
  var tagFilterEl = document.getElementById("notes-tag-filter");
  var searchInput = document.getElementById("notes-search-input");
  var emptyState = document.getElementById("notes-empty");
  var activeTags = {};
  var searchQuery = "";

  // Live stats, computed from the actual archive/series markup rather than
  // hand-typed numbers that can drift out of sync with the real content.
  var statNotes = document.getElementById("stat-notes");
  var statSeries = document.getElementById("stat-series");
  var statInteractive = document.getElementById("stat-interactive");
  if (statNotes) statNotes.textContent = String(rows.length);
  if (statSeries) statSeries.textContent = String(document.querySelectorAll(".series-block").length);
  if (statInteractive) {
    var interactiveCount = rows.filter(function (li) {
      var slugs = (li.getAttribute("data-tags") || "").split(",");
      return slugs.indexOf("interactive") !== -1;
    }).length;
    statInteractive.textContent = String(interactiveCount);
  }

  if (tagFilterEl) {
    var usedSlugs = {};
    rows.forEach(function (li) {
      (li.getAttribute("data-tags") || "").split(",").filter(Boolean).forEach(function (slug) {
        usedSlugs[slug] = true;
      });
    });

    var allPill = document.createElement("button");
    allPill.type = "button";
    allPill.className = "filter-pill is-active";
    allPill.textContent = "All";
    allPill.addEventListener("click", function () {
      activeTags = {};
      if (searchInput) searchInput.value = "";
      searchQuery = "";
      render();
    });
    tagFilterEl.appendChild(allPill);

    Object.keys(usedSlugs).sort(function (a, b) {
      var la = NOTE_TAG_LABELS[a] || a, lb = NOTE_TAG_LABELS[b] || b;
      return la.localeCompare(lb);
    }).forEach(function (slug) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "filter-pill";
      btn.textContent = NOTE_TAG_LABELS[slug] || slug;
      btn.dataset.tag = slug;
      btn.addEventListener("click", function () { toggleTag(slug); });
      tagFilterEl.appendChild(btn);
    });
  }

  function toggleTag(slug) {
    if (activeTags[slug]) delete activeTags[slug];
    else activeTags[slug] = true;
    render();
  }

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      searchQuery = searchInput.value.trim().toLowerCase();
      render();
    });
    // Cmd/Ctrl+K focuses search from anywhere on the page.
    document.addEventListener("keydown", function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
      if (e.key === "Escape" && document.activeElement === searchInput) {
        searchInput.value = "";
        searchQuery = "";
        render();
        searchInput.blur();
      }
    });
  }

  var resetBtn = document.getElementById("notes-empty-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      activeTags = {};
      searchQuery = "";
      if (searchInput) searchInput.value = "";
      render();
    });
  }

  function render() {
    var activeList = Object.keys(activeTags);
    var visibleCount = 0;

    rows.forEach(function (li) {
      var slugs = (li.getAttribute("data-tags") || "").split(",");
      var tagMatch = activeList.length === 0 || activeList.some(function (t) { return slugs.indexOf(t) !== -1; });
      var text = li.textContent.toLowerCase();
      var searchMatch = !searchQuery || text.indexOf(searchQuery) !== -1;
      var visible = tagMatch && searchMatch;
      li.hidden = !visible;
      if (visible) visibleCount += 1;
    });

    yearGroups.forEach(function (group) {
      var visibleRows = group.querySelectorAll(".archive-row:not([hidden])");
      group.hidden = visibleRows.length === 0;
    });

    if (tagFilterEl) {
      var pills = tagFilterEl.querySelectorAll(".filter-pill");
      pills.forEach(function (btn) {
        if (!btn.dataset.tag) { btn.classList.toggle("is-active", activeList.length === 0); return; }
        btn.classList.toggle("is-active", !!activeTags[btn.dataset.tag]);
      });
    }

    if (emptyState) emptyState.hidden = visibleCount !== 0;
  }

  // Surprise me: jump to a random primary note, skipping interactive
  // companions (those are meant to be read after their main note).
  var surpriseBtn = document.getElementById("surprise-btn");
  if (surpriseBtn) {
    var primaryUrls = rows.filter(function (li) {
      var slugs = (li.getAttribute("data-tags") || "").split(",");
      return slugs.indexOf("interactive") === -1 && slugs.indexOf("companion") === -1;
    }).map(function (li) {
      return li.querySelector("a").getAttribute("href");
    });
    surpriseBtn.addEventListener("click", function () {
      var others = primaryUrls.filter(function (u) { return u.indexOf(window.location.pathname.split("/").pop()) === -1; });
      var pool = others.length ? others : primaryUrls;
      var pick = pool[Math.floor(Math.random() * pool.length)];
      window.location.href = pick;
    });
  }
})();

// Broken images degrade to a quiet on-brand placeholder instead of a raw
// broken-image icon. See .img-fallback in style.css.
(function () {
  var imgs = document.querySelectorAll("img");
  for (var i = 0; i < imgs.length; i++) {
    imgs[i].addEventListener("error", (function (img) {
      return function () {
        var container = img.closest(".post-figure, .post-hero-art, .card-thumb, .featured-note-media, .series-thumb");
        if (container) {
          container.classList.add("img-fallback");
        } else {
          img.classList.add("img-fallback-inline");
        }
      };
    })(imgs[i]));
  }
})();
