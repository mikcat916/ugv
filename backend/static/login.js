const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const loginConfig = window.APP_CONFIG || {};
const loginSubmitButton = loginForm?.querySelector('button[type="submit"]');
const authModeButtons = document.querySelectorAll("[data-auth-mode]");
const registerOnlyFields = document.querySelectorAll(".register-only");

let authMode = "login";

function setLoginSubmitting(submitting) {
  if (!loginSubmitButton) return;
  loginSubmitButton.disabled = submitting;
  if (submitting) {
    loginSubmitButton.textContent = authMode === "register" ? "注册中…" : "登录中…";
    return;
  }
  loginSubmitButton.textContent = authMode === "register" ? "注册并进入" : "登录";
}

function applyAuthMode(nextMode) {
  const registerAllowed = Boolean(loginConfig.allowSelfRegister);
  authMode = nextMode === "register" && registerAllowed ? "register" : "login";
  authModeButtons.forEach((button) => {
    const active = button.dataset.authMode === authMode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  registerOnlyFields.forEach((field) => {
    field.hidden = authMode !== "register";
  });
  loginError.textContent = "";
  setLoginSubmitting(false);
}

authModeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    applyAuthMode(button.dataset.authMode);
  });
});

loginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.textContent = "";

  if (!loginConfig.mysqlReady) {
    loginError.textContent = authMode === "register" ? "MySQL 当前不可用，暂时无法注册。" : "MySQL 当前不可用，暂时无法登录。";
    return;
  }

  const payload = Object.fromEntries(new FormData(loginForm).entries());
  payload.username = String(payload.username || "").trim();
  payload.password = String(payload.password || "").trim();
  payload.displayName = String(payload.displayName || "").trim();
  payload.loginToken = String(loginConfig.loginToken || "");

  if (!payload.username) {
    loginError.textContent = "请输入用户名。";
    return;
  }

  if (!payload.password) {
    loginError.textContent = "请输入密码。";
    return;
  }

  if (authMode === "register" && payload.password.length < 6) {
    loginError.textContent = "密码长度至少为 6 位。";
    return;
  }

  try {
    setLoginSubmitting(true);
    const response = await fetch(authMode === "register" ? "/auth/register" : "/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-Login-Token": payload.loginToken,
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || (authMode === "register" ? "注册失败" : "登录失败"));
    }
    window.location.href = data.redirect || "/overview";
  } catch (error) {
    loginError.textContent = error.message;
  } finally {
    setLoginSubmitting(false);
  }
});

if (!loginConfig.allowSelfRegister) {
  authModeButtons.forEach((button) => {
    if (button.dataset.authMode === "register") {
      button.hidden = true;
    }
  });
}

applyAuthMode("login");
