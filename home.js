// Homepage behavior: sections fade/lift into view as they're scrolled to,
// a thin progress bar tracks how far down the page you are, and the side
// rail nav highlights whichever section is currently in view.
// All three degrade safely — see the html.js-ready gate in style.css,
// and the rail/bar simply do nothing if their elements aren't found.

(function () {
  var sections = document.querySelectorAll(".section");
  if ("IntersectionObserver" in window && sections.length) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    sections.forEach(function (s) { io.observe(s); });
  } else {
    // No IntersectionObserver support: just show everything.
    sections.forEach(function (s) { s.classList.add("in-view"); });
  }

  var bar = document.getElementById("scroll-progress");
  if (bar) {
    var update = function () {
      var doc = document.documentElement;
      var scrollTop = doc.scrollTop || document.body.scrollTop;
      var scrollable = (doc.scrollHeight || document.body.scrollHeight) - doc.clientHeight;
      var pct = scrollable > 0 ? (scrollTop / scrollable) * 100 : 0;
      bar.style.width = pct + "%";
    };
    document.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
  }

  var railLinks = document.querySelectorAll(".section-rail a");
  if ("IntersectionObserver" in window && railLinks.length && sections.length) {
    var linksById = {};
    railLinks.forEach(function (a) {
      var id = a.getAttribute("href").slice(1);
      linksById[id] = a;
    });

    var spy = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          var link = linksById[entry.target.id];
          if (!link) return;
          if (entry.isIntersecting) {
            railLinks.forEach(function (a) { a.classList.remove("is-active"); });
            link.classList.add("is-active");
          }
        });
      },
      { rootMargin: "-45% 0px -45% 0px", threshold: 0 }
    );
    sections.forEach(function (s) { spy.observe(s); });
  }
})();
