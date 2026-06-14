(function initSidebar() {
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("sidebar-toggle");
  if (!sidebar || !toggle) return;

  const storageKey = "ccn-sidebar-collapsed";

  function setCollapsed(collapsed) {
    sidebar.classList.toggle("collapsed", collapsed);
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.setAttribute("aria-label", collapsed ? "Open menu" : "Close menu");
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    try {
      localStorage.setItem(storageKey, collapsed ? "1" : "0");
    } catch (_error) {
      /* ignore storage errors */
    }
  }

  let collapsed = true;
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved === "0") collapsed = false;
    else if (saved === "1") collapsed = true;
  } catch (_error) {
    collapsed = true;
  }

  setCollapsed(collapsed);

  toggle.addEventListener("click", () => {
    setCollapsed(!sidebar.classList.contains("collapsed"));
  });
})();
