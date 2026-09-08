/* DRLabs theme + auth + language. Load after DOM. */
(function () {
  const THEME_KEY = "drlabs-theme";
  const LANG_KEY = "drlabs-lang";
  const USERS_KEY = "drlabs-users-v1";
  const SESSION_KEY = "drlabs-session-v1";

  const I18N = {
    zh: {
      "nav.home": "首页",
      "nav.research": "研究报告",
      "nav.about": "关于",
      "nav.login": "登录/注册",
      "nav.logout": "退出",
      "theme.auto": "皮肤:自动",
      "theme.light": "皮肤:白天",
      "theme.dark": "皮肤:黑夜",
      "lang.label": "中文 · EN",
      "footer": "内容仅供研究参考，不构成投资建议。加密资产风险极高，投资请理性。",
      "gate.title": "登录后阅读完整研报",
      "gate.body": "未登录不展示正文，避免只看到图片预览。",
      "gate.hint": "注册只需手机号 + 密码（无短信费用）。",
      "gate.cta": "去登录 / 注册",
      "auth.invalidPhone": "请输入有效手机号",
      "auth.shortPassword": "密码至少 6 位",
      "auth.exists": "该手机号已注册",
      "auth.missing": "账号不存在",
      "auth.badPassword": "密码错误",
      "auth.registered": "注册成功，已登录",
      "auth.phonePh": "11 位手机号",
      "auth.passwordPh": "至少 6 位",
    },
    en: {
      "nav.home": "Home",
      "nav.research": "Research",
      "nav.about": "About",
      "nav.login": "Log in / Sign up",
      "nav.logout": "Log out",
      "theme.auto": "Theme: Auto",
      "theme.light": "Theme: Light",
      "theme.dark": "Theme: Dark",
      "lang.label": "中 · English",
      "footer": "For research only. Not investment advice. Crypto can result in partial or total loss.",
      "gate.title": "Log in to read the full report",
      "gate.body": "The body is hidden until you log in, so the charts are not shown as a free preview.",
      "gate.hint": "Sign up with phone number + password. No SMS fee.",
      "gate.cta": "Log in / Sign up",
      "auth.invalidPhone": "Enter a valid phone number",
      "auth.shortPassword": "Password must be at least 6 characters",
      "auth.exists": "This phone number is already registered",
      "auth.missing": "Account not found",
      "auth.badPassword": "Incorrect password",
      "auth.registered": "Registered and signed in",
      "auth.phonePh": "Phone number",
      "auth.passwordPh": "At least 6 characters",
    },
  };

  function hourTheme() {
    const h = new Date().getHours();
    return h >= 6 && h < 18 ? "light" : "dark";
  }
  function resolveTheme(mode) {
    if (mode === "light" || mode === "dark") return mode;
    return hourTheme();
  }
  function detectLang() {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved === "zh" || saved === "en") return saved;
    const nav = (navigator.language || "zh").toLowerCase();
    return nav.startsWith("zh") ? "zh" : "en";
  }
  function lang() {
    return document.documentElement.getAttribute("data-lang") || "zh";
  }
  function t(key) {
    const pack = I18N[lang()] || I18N.zh;
    return pack[key] || I18N.zh[key] || key;
  }

  function applyTheme() {
    const mode = localStorage.getItem(THEME_KEY) || "auto";
    document.documentElement.setAttribute("data-theme", resolveTheme(mode));
    const el = document.getElementById("themeLabel");
    if (el) {
      el.textContent =
        mode === "auto" ? t("theme.auto") : mode === "light" ? t("theme.light") : t("theme.dark");
    }
  }
  window.cycleTheme = function () {
    const order = ["auto", "light", "dark"];
    const cur = localStorage.getItem(THEME_KEY) || "auto";
    localStorage.setItem(THEME_KEY, order[(order.indexOf(cur) + 1) % order.length]);
    applyTheme();
  };

  function applyTitle() {
    const current = lang();
    const zh = document.documentElement.getAttribute("data-title-zh");
    const en = document.documentElement.getAttribute("data-title-en");
    if (current === "en" && en) document.title = en;
    else if (zh) document.title = zh;
  }

  function applyLang() {
    const current = detectLang();
    localStorage.setItem(LANG_KEY, current);
    document.documentElement.setAttribute("data-lang", current);
    document.documentElement.setAttribute("lang", current === "zh" ? "zh-CN" : "en");
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      const key = el.getAttribute("data-i18n");
      if (key) el.textContent = t(key);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) {
      const key = el.getAttribute("data-i18n-placeholder");
      if (key) el.setAttribute("placeholder", t(key));
    });
    const langBtn = document.getElementById("langLabel");
    if (langBtn) {
      langBtn.textContent = t("lang.label");
      langBtn.setAttribute("aria-pressed", current === "en" ? "true" : "false");
    }
    applyTitle();
    applyTheme();
    paintNav();
  }
  window.cycleLang = function () {
    localStorage.setItem(LANG_KEY, detectLang() === "zh" ? "en" : "zh");
    applyLang();
  };

  function loadUsers() {
    try {
      return JSON.parse(localStorage.getItem(USERS_KEY) || "[]");
    } catch (e) {
      return [];
    }
  }
  function saveUsers(u) {
    localStorage.setItem(USERS_KEY, JSON.stringify(u));
  }
  async function hashPw(pw, salt) {
    const data = new TextEncoder().encode(salt + "::" + pw);
    const buf = await crypto.subtle.digest("SHA-256", data);
    return Array.from(new Uint8Array(buf))
      .map(function (b) {
        return b.toString(16).padStart(2, "0");
      })
      .join("");
  }
  function validPhone(p) {
    return /^1[3-9]\d{9}$/.test(p) || /^\+?\d{8,15}$/.test(p);
  }
  window.DRAuth = {
    me: function () {
      try {
        return JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null");
      } catch (e) {
        return null;
      }
    },
    logout: function () {
      sessionStorage.removeItem(SESSION_KEY);
      location.reload();
    },
    register: async function (phone, password) {
      phone = (phone || "").trim();
      password = password || "";
      if (!validPhone(phone)) throw new Error(t("auth.invalidPhone"));
      if (password.length < 6) throw new Error(t("auth.shortPassword"));
      const users = loadUsers();
      if (users.some(function (u) { return u.phone === phone; })) throw new Error(t("auth.exists"));
      const salt = crypto.randomUUID();
      const password_hash = await hashPw(password, salt);
      users.push({ phone: phone, salt: salt, password_hash: password_hash, created_at: new Date().toISOString() });
      saveUsers(users);
      sessionStorage.setItem(SESSION_KEY, JSON.stringify({ phone: phone }));
      return true;
    },
    login: async function (phone, password) {
      phone = (phone || "").trim();
      password = password || "";
      const u = loadUsers().find(function (x) { return x.phone === phone; });
      if (!u) throw new Error(t("auth.missing"));
      const h = await hashPw(password, u.salt);
      if (h !== u.password_hash) throw new Error(t("auth.badPassword"));
      sessionStorage.setItem(SESSION_KEY, JSON.stringify({ phone: phone }));
      return true;
    },
    exportUsers: function () {
      const blob = new Blob([localStorage.getItem(USERS_KEY) || "[]"], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "drlabs-users.json";
      a.click();
    },
  };

  function paintNav() {
    const slot = document.getElementById("authSlot");
    if (!slot) return;
    const me = window.DRAuth.me();
    if (me) {
      slot.innerHTML =
        '<span class="muted">' +
        me.phone +
        '</span> <a href="#" id="logoutBtn">' +
        t("nav.logout") +
        "</a>";
      const b = document.getElementById("logoutBtn");
      if (b)
        b.onclick = function (e) {
          e.preventDefault();
          DRAuth.logout();
        };
    } else {
      slot.innerHTML = '<a href="' + slot.getAttribute("data-login") + '">' + t("nav.login") + "</a>";
    }
  }
  window.requireAuthForArticle = function () {
    const art = document.getElementById("article");
    const gate = document.getElementById("loginNeeded");
    if (!art) return;
    if (DRAuth.me()) {
      art.dataset.locked = "0";
      if (gate) gate.style.display = "none";
    } else {
      art.dataset.locked = "1";
      if (gate) gate.style.display = "block";
    }
  };

  window.doRegister = async function () {
    const msg = document.getElementById("msg");
    if (!msg) return;
    msg.className = "err";
    msg.textContent = "";
    try {
      await DRAuth.register(document.getElementById("phone").value, document.getElementById("password").value);
      msg.className = "ok";
      msg.textContent = t("auth.registered");
      location.href = "research/";
    } catch (e) {
      msg.textContent = e.message || String(e);
    }
  };
  window.doLogin = async function () {
    const msg = document.getElementById("msg");
    if (!msg) return;
    msg.className = "err";
    msg.textContent = "";
    try {
      await DRAuth.login(document.getElementById("phone").value, document.getElementById("password").value);
      location.href = "research/";
    } catch (e) {
      msg.textContent = e.message || String(e);
    }
  };

  window.DRI18N = { t: t, applyLang: applyLang };

  document.addEventListener("DOMContentLoaded", function () {
    applyLang();
    if (window.requireAuthForArticle) requireAuthForArticle();
  });
  setInterval(function () {
    if ((localStorage.getItem(THEME_KEY) || "auto") === "auto") applyTheme();
  }, 60 * 1000);
})();
