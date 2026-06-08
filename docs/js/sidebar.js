(function initSidebar() {
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("sidebar-toggle");
  if (!sidebar || !toggle) return;

  const storageKey = "ccn-sidebar-collapsed";

  function setCollapsed(collapsed) {
    sidebar.classList.toggle("collapsed", collapsed);
    toggle.setAttribute("aria-expanded", String(!collapsed));
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    try {
      localStorage.setItem(storageKey, collapsed ? "1" : "0");
    } catch (_error) {
      /* ignore storage errors */
    }
  }

  let collapsed = false;
  try {
    collapsed = localStorage.getItem(storageKey) === "1";
  } catch (_error) {
    collapsed = window.matchMedia("(max-width: 700px)").matches;
  }

  if (window.matchMedia("(max-width: 700px)").matches && localStorage.getItem(storageKey) === null) {
    collapsed = true;
  }

  setCollapsed(collapsed);

  toggle.addEventListener("click", () => {
    setCollapsed(!sidebar.classList.contains("collapsed"));
  });
})();
