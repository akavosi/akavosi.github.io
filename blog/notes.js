// Notes (blog) shared behavior: auto-generated table of contents,
// and copy-to-clipboard for the "cite this note" box.
// Reads only what's already on the page — adds no content of its own.

(function () {
  function slugify(text) {
    return text
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "-")
      .slice(0, 60);
  }

  function buildTOC() {
    var body = document.querySelector(".post-article-body");
    var tocList = document.getElementById("note-toc-list");
    var tocWrap = document.getElementById("note-toc");
    if (!body || !tocList || !tocWrap) return;

    var headings = body.querySelectorAll("h2, h3");
    if (headings.length < 2) {
      tocWrap.style.display = "none";
      return;
    }

    var used = {};
    headings.forEach(function (h) {
      var base = slugify(h.textContent) || "section";
      var id = base;
      var n = 1;
      while (used[id]) { id = base + "-" + (++n); }
      used[id] = true;
      h.id = id;

      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = "#" + id;
      a.textContent = h.textContent;
      if (h.tagName === "H3") a.classList.add("toc-h3");
      li.appendChild(a);
      tocList.appendChild(li);
    });
  }

  function wireCiteCopy() {
    var btn = document.querySelector(".note-cite-copy");
    var pre = document.querySelector(".note-cite-box pre");
    if (!btn || !pre) return;
    btn.addEventListener("click", function () {
      var text = pre.textContent.trim();
      var done = function () {
        var original = btn.textContent;
        btn.textContent = "Copied";
        setTimeout(function () { btn.textContent = original; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(done);
      } else {
        done();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      buildTOC();
      wireCiteCopy();
    });
  } else {
    buildTOC();
    wireCiteCopy();
  }
})();
