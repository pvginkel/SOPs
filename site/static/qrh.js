/* Homelab QRH: checklist ticks, search, copy buttons, day/night. No dependencies, works from file://. */
(function () {
  "use strict";

  var root = document.body.dataset.root || "";
  var store = {
    get: function (k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
    drop: function (k) { try { localStorage.removeItem(k); } catch (e) {} }
  };

  /* --- Day / night --------------------------------------------------------------------- */

  var themeButton = document.getElementById("theme");
  function showTheme() {
    themeButton.textContent = document.documentElement.dataset.theme === "day" ? "☀ Day" : "☾ Night";
  }
  themeButton.addEventListener("click", function () {
    var next = document.documentElement.dataset.theme === "day" ? "night" : "day";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("qrh:theme", next); } catch (e) {}
    showTheme();
  });
  showTheme();

  /* --- Index toggle on small screens --------------------------------------------------- */

  var navToggle = document.querySelector(".navtoggle");
  navToggle.addEventListener("click", function () {
    var open = document.body.classList.toggle("nav-open");
    navToggle.setAttribute("aria-expanded", String(open));
  });

  /* --- Checklist: ticks survive a reload for a day, then the card starts clean --------- */

  var ticks = Array.prototype.slice.call(document.querySelectorAll("li.step .tick"));
  var progress = document.querySelector(".progress");
  if (ticks.length && progress) {
    var key = "qrh:steps:" + location.pathname;
    var DAY = 24 * 60 * 60 * 1000;
    var saved = store.get(key);
    if (saved && Date.now() - saved.at < DAY) {
      saved.done.forEach(function (i) { if (ticks[i]) ticks[i].checked = true; });
    }

    var count = progress.querySelector(".count");
    var bar = document.createElement("span");
    bar.className = "bar";
    bar.appendChild(document.createElement("span"));
    count.after(bar);

    var update = function (persist) {
      var done = [];
      ticks.forEach(function (t, i) {
        t.closest("li.step").classList.toggle("done", t.checked);
        if (t.checked) done.push(i);
      });
      var complete = done.length === ticks.length;
      count.textContent = complete ? "Checklist complete" : done.length + " / " + ticks.length + " done";
      bar.firstChild.style.width = (100 * done.length / ticks.length) + "%";
      progress.classList.toggle("complete", complete);
      if (persist) {
        if (done.length) store.set(key, { at: Date.now(), done: done });
        else store.drop(key);
      }
    };

    ticks.forEach(function (t) { t.addEventListener("change", function () { update(true); }); });
    progress.querySelector(".reset").addEventListener("click", function () {
      ticks.forEach(function (t) { t.checked = false; });
      update(true);
    });
    progress.hidden = false;
    update(false);
  }

  /* --- Copy buttons on code blocks ----------------------------------------------------- */

  document.querySelectorAll("pre > code").forEach(function (code) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy";
    button.textContent = "Copy";
    button.addEventListener("click", function () {
      var done = function () {
        button.textContent = "Copied";
        button.classList.add("done");
        setTimeout(function () { button.textContent = "Copy"; button.classList.remove("done"); }, 1500);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(code.textContent).then(done);
      } else {
        var range = document.createRange();
        range.selectNodeContents(code);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        if (document.execCommand("copy")) done();
        sel.removeAllRanges();
      }
    });
    code.parentNode.appendChild(button);
  });

  /* --- Search: the index is a script, not JSON, so file:// can load it ---------------- */

  var input = document.getElementById("q");
  var results = document.getElementById("results");
  var loading = null;
  var active = -1;

  function loadIndex() {
    if (!loading) {
      loading = new Promise(function (resolve, reject) {
        var s = document.createElement("script");
        s.src = root + "search-index.js";
        s.onload = function () { resolve(window.QRH_INDEX || []); };
        s.onerror = reject;
        document.head.appendChild(s);
      });
    }
    return loading;
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }

  function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

  function snippet(text, terms) {
    var lower = text.toLowerCase();
    var at = lower.indexOf(terms[0]);
    var start = Math.max(0, at - 60);
    var cut = (start > 0 ? "…" : "") + text.slice(start, start + 180) + (start + 180 < text.length ? "…" : "");
    var re = new RegExp("(" + terms.map(escapeRe).join("|") + ")", "gi");
    return escapeHtml(cut).replace(re, "<mark>$1</mark>");
  }

  function search(index, query) {
    var terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) return [];
    var hits = [];
    index.forEach(function (e) {
      var title = e.t.toLowerCase(), head = e.h.toLowerCase(), text = e.x.toLowerCase();
      var score = 0;
      for (var i = 0; i < terms.length; i++) {
        var t = terms[i];
        var inTitle = title.indexOf(t) >= 0, inHead = head.indexOf(t) >= 0, inText = text.indexOf(t) >= 0;
        if (!inTitle && !inHead && !inText) return;
        score += (inTitle ? 8 : 0) + (inHead ? 5 : 0) + Math.min(text.split(t).length - 1, 5);
      }
      if (e.k !== "runbook") score += 3;
      hits.push({ e: e, score: score });
    });
    hits.sort(function (a, b) { return b.score - a.score; });
    return hits.slice(0, 20).map(function (h) { return h.e; });
  }

  function render(hits, query) {
    var terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    active = -1;
    if (!hits.length) {
      results.innerHTML = '<li class="r-none">Nothing matches.</li>';
    } else {
      results.innerHTML = hits.map(function (e) {
        var where = e.h ? '<span class="r-head"> › ' + escapeHtml(e.h) + "</span>" : "";
        var code = e.c ? escapeHtml(e.c) + " · " : "";
        return '<li class="k-' + e.k + '"><a href="' + root + e.u + '">' +
          '<span class="r-title">' + code + escapeHtml(e.t) + "</span>" + where +
          '<span class="r-snip">' + snippet(e.x || e.h, terms) + "</span></a></li>";
      }).join("");
    }
    results.hidden = false;
  }

  function move(delta) {
    var links = results.querySelectorAll("a");
    if (!links.length) return;
    if (active >= 0) links[active].classList.remove("active");
    active = (active + delta + links.length) % links.length;
    links[active].classList.add("active");
    links[active].scrollIntoView({ block: "nearest" });
  }

  input.addEventListener("focus", loadIndex);
  input.addEventListener("input", function () {
    var query = input.value.trim();
    if (!query) { results.hidden = true; return; }
    loadIndex().then(function (index) {
      if (input.value.trim() === query) render(search(index, query), query);
    }, function () {
      results.innerHTML = '<li class="r-none">The search index did not load.</li>';
      results.hidden = false;
    });
  });
  input.addEventListener("keydown", function (ev) {
    if (ev.key === "ArrowDown") { ev.preventDefault(); move(1); }
    else if (ev.key === "ArrowUp") { ev.preventDefault(); move(-1); }
    else if (ev.key === "Enter") {
      var links = results.querySelectorAll("a");
      var pick = links[active >= 0 ? active : 0];
      if (pick) { ev.preventDefault(); location.href = pick.href; }
    } else if (ev.key === "Escape") { results.hidden = true; input.blur(); }
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "/" && document.activeElement !== input && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
      ev.preventDefault();
      input.focus();
    }
  });
  document.addEventListener("click", function (ev) {
    if (!ev.target.closest(".search")) results.hidden = true;
  });
})();
