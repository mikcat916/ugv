window.DashboardApi = (() => {
  async function apiFetch(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });

    if (response.status === 401) {
      window.location.href = "/login";
      throw new Error("登录状态已失效，请重新登录。");
    }

    const isJson = response.headers.get("content-type")?.includes("application/json");
    const payload = isJson ? await response.json() : null;

    if (!response.ok) {
      throw new Error(payload?.detail || `请求失败：${response.status}`);
    }

    return payload;
  }

  return { apiFetch };
})();
