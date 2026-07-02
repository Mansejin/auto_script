(function () {
  const STORAGE = "mansejin-theme";

  function getTheme() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE, theme);
    } catch (_) {}
    syncInputs(theme);
  }

  function syncInputs(theme) {
    const dark = theme === "dark";
    document.querySelectorAll(".theme-switch-input").forEach((input) => {
      input.checked = dark;
    });
  }

  function init() {
    const lang = document.documentElement.lang.startsWith("en") ? "en" : "ko";
    const label = lang === "en" ? "Dark mode" : "다크 모드";

    document.querySelectorAll(".theme-switch-input").forEach((input) => {
      input.setAttribute("aria-label", label);
      syncInputs(getTheme());
      input.addEventListener("change", () => {
        apply(input.checked ? "dark" : "light");
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
