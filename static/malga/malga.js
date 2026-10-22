// MaLGa academic page - shared script. No dependencies, no network access, no HTML injection.
// Source of truth: Malga-Vision/malga-academic-page-template (static/malga/).
(function () {
  "use strict";

  // Copy buttons: <button data-copy="element-id">.
  document.querySelectorAll("button[data-copy]").forEach(function (button) {
    var label = button.querySelector("[data-label]") || button;
    var original = label.textContent;
    button.addEventListener("click", function () {
      var source = document.getElementById(button.getAttribute("data-copy"));
      if (!source || !navigator.clipboard) return;
      navigator.clipboard.writeText(source.textContent.trim()).then(function () {
        button.setAttribute("data-copied", "true");
        label.textContent = "Copied";
        setTimeout(function () {
          button.removeAttribute("data-copied");
          label.textContent = original;
        }, 2000);
      });
    });
  });

  // Highlight the header link of the section being read.
  var links = Array.prototype.slice.call(document.querySelectorAll(".site-nav a[href^='#']"));
  if (!links.length || !("IntersectionObserver" in window)) return;
  var byId = {};
  links.forEach(function (link) { byId[link.getAttribute("href").slice(1)] = link; });
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      links.forEach(function (link) { link.removeAttribute("aria-current"); });
      byId[entry.target.id].setAttribute("aria-current", "true");
    });
  }, { rootMargin: "-30% 0px -60% 0px" });
  Object.keys(byId).forEach(function (id) {
    var section = document.getElementById(id);
    if (section) observer.observe(section);
  });
})();
