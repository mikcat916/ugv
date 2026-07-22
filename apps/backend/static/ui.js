window.DashboardUi = (() => {
  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatDateTime(value) {
    if (!value) return "-";
    return String(value).replace("T", " ");
  }

  function localizeToken(value) {
    const token = String(value || "").toLowerCase();
    return (window.DashboardTokenText || {})[token] || String(value || "-");
  }

  function pillClass(value) {
    const token = String(value || "").toLowerCase();
    if (["critical", "offline", "danger"].includes(token)) return "pill critical";
    if (["warning", "degraded", "medium"].includes(token)) return "pill warning";
    if (["active", "healthy", "online", "good", "low", "positive"].includes(token)) return "pill healthy";
    return "pill";
  }

  return { escapeHtml, formatDateTime, localizeToken, pillClass };
})();
