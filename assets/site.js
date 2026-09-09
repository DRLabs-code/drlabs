/* DRLabs theme + auth + language. Load after DOM. */
(function () {
  const THEME_KEY = "drlabs-theme";
  const LANG_KEY = "drlabs-lang";
  const USERS_KEY = "drlabs-users-v1";
  const SESSION_KEY = "drlabs-session-v1";
  const LANGS = ["zh", "en", "ja", "ko", "fr", "es", "ru"];
  const LANG_LABEL = {
    zh: "中文",
    en: "English",
    ja: "日本語",
    ko: "한국어",
    fr: "Français",
    es: "Español",
    ru: "Русский",
  };
  const LANG_HTML = { zh: "zh-CN", en: "en", ja: "ja", ko: "ko", fr: "fr", es: "es", ru: "ru" };

  const I18N = {
    zh: {
      "nav.home": "首页",
      "nav.research": "研究报告",
      "nav.about": "关于",
      "nav.login": "登录/注册",
      "nav.logout": "退出",
      "theme.toLight": "切换到浅色",
      "theme.toDark": "切换到深色",
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
      "theme.toLight": "Switch to light",
      "theme.toDark": "Switch to dark",
      "auth.invalidPhone": "Enter a valid phone number",
      "auth.shortPassword": "Password must be at least 6 characters",
      "auth.exists": "This phone number is already registered",
      "auth.missing": "Account not found",
      "auth.badPassword": "Incorrect password",
      "auth.registered": "Registered and signed in",
      "auth.phonePh": "Phone number",
      "auth.passwordPh": "At least 6 characters",
    },
    ja: {
      "nav.home": "ホーム",
      "nav.research": "リサーチ",
      "nav.about": "概要",
      "nav.login": "ログイン / 登録",
      "nav.logout": "ログアウト",
      "theme.toLight": "ライトに切り替え",
      "theme.toDark": "ダークに切り替え",
      "auth.invalidPhone": "有効な電話番号を入力してください",
      "auth.shortPassword": "パスワードは6文字以上",
      "auth.exists": "この電話番号は登録済みです",
      "auth.missing": "アカウントが見つかりません",
      "auth.badPassword": "パスワードが違います",
      "auth.registered": "登録してログインしました",
      "auth.phonePh": "電話番号",
      "auth.passwordPh": "6文字以上",
    },
    ko: {
      "nav.home": "홈",
      "nav.research": "리서치",
      "nav.about": "소개",
      "nav.login": "로그인 / 가입",
      "nav.logout": "로그아웃",
      "theme.toLight": "라이트로 전환",
      "theme.toDark": "다크로 전환",
      "auth.invalidPhone": "유효한 전화번호를 입력하세요",
      "auth.shortPassword": "비밀번호는 6자 이상",
      "auth.exists": "이미 등록된 번호입니다",
      "auth.missing": "계정을 찾을 수 없습니다",
      "auth.badPassword": "비밀번호가 올바르지 않습니다",
      "auth.registered": "가입되어 로그인되었습니다",
      "auth.phonePh": "전화번호",
      "auth.passwordPh": "6자 이상",
    },
    fr: {
      "nav.home": "Accueil",
      "nav.research": "Recherche",
      "nav.about": "À propos",
      "nav.login": "Connexion / Inscription",
      "nav.logout": "Déconnexion",
      "theme.toLight": "Passer au clair",
      "theme.toDark": "Passer au sombre",
      "auth.invalidPhone": "Entrez un numéro valide",
      "auth.shortPassword": "Mot de passe : 6 caractères min.",
      "auth.exists": "Ce numéro est déjà inscrit",
      "auth.missing": "Compte introuvable",
      "auth.badPassword": "Mot de passe incorrect",
      "auth.registered": "Inscrit et connecté",
      "auth.phonePh": "Téléphone",
      "auth.passwordPh": "Au moins 6 caractères",
    },
    es: {
      "nav.home": "Inicio",
      "nav.research": "Investigación",
      "nav.about": "Acerca de",
      "nav.login": "Entrar / Registrarse",
      "nav.logout": "Salir",
      "theme.toLight": "Cambiar a claro",
      "theme.toDark": "Cambiar a oscuro",
      "auth.invalidPhone": "Introduce un teléfono válido",
      "auth.shortPassword": "La contraseña debe tener 6+ caracteres",
      "auth.exists": "Este teléfono ya está registrado",
      "auth.missing": "Cuenta no encontrada",
      "auth.badPassword": "Contraseña incorrecta",
      "auth.registered": "Registrado e iniciado",
      "auth.phonePh": "Teléfono",
      "auth.passwordPh": "Al menos 6 caracteres",
    },
    ru: {
      "nav.home": "Главная",
      "nav.research": "Исследования",
      "nav.about": "О нас",
      "nav.login": "Вход / Регистрация",
      "nav.logout": "Выйти",
      "theme.toLight": "Включить светлую",
      "theme.toDark": "Включить тёмную",
      "auth.invalidPhone": "Введите корректный телефон",
      "auth.shortPassword": "Пароль не короче 6 символов",
      "auth.exists": "Этот номер уже зарегистрирован",
      "auth.missing": "Аккаунт не найден",
      "auth.badPassword": "Неверный пароль",
      "auth.registered": "Регистрация выполнена, вы вошли",
      "auth.phonePh": "Телефон",
      "auth.passwordPh": "Не менее 6 символов",
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
    if (LANGS.indexOf(saved) !== -1) return saved;
    const nav = (navigator.language || "zh").toLowerCase();
    if (nav.startsWith("zh")) return "zh";
    if (nav.startsWith("ja")) return "ja";
    if (nav.startsWith("ko")) return "ko";
    if (nav.startsWith("fr")) return "fr";
    if (nav.startsWith("es")) return "es";
    if (nav.startsWith("ru")) return "ru";
    return "en";
  }
  function lang() {
    return document.documentElement.getAttribute("data-lang") || "zh";
  }
  function t(key) {
    const pack = I18N[lang()] || I18N.zh;
    return pack[key] || I18N.en[key] || I18N.zh[key] || key;
  }

  function applyTheme() {
    const resolved = resolveTheme(localStorage.getItem(THEME_KEY) || "auto");
    document.documentElement.setAttribute("data-theme", resolved);
    const el = document.getElementById("themeToggle");
    if (el) {
      el.setAttribute("aria-label", resolved === "dark" ? t("theme.toLight") : t("theme.toDark"));
      el.setAttribute("title", resolved === "dark" ? t("theme.toLight") : t("theme.toDark"));
      var sun = el.querySelector(".sun");
      var moon = el.querySelector(".moon");
      if (sun) sun.hidden = resolved !== "light";
      if (moon) moon.hidden = resolved !== "dark";
    }
  }
  window.cycleTheme = function () {
    const resolved = resolveTheme(localStorage.getItem(THEME_KEY) || "auto");
    localStorage.setItem(THEME_KEY, resolved === "dark" ? "light" : "dark");
    applyTheme();
  };

  function applyTitle() {
    const current = lang();
    const titled = document.documentElement.getAttribute("data-title-" + current);
    if (titled) document.title = titled;
  }

  function paintLangMenu(current) {
    const menu = document.getElementById("langMenu");
    if (!menu) return;
    menu.querySelectorAll("[data-set-lang]").forEach(function (btn) {
      btn.setAttribute("aria-current", btn.getAttribute("data-set-lang") === current ? "true" : "false");
    });
  }

  function applyLang() {
    const current = detectLang();
    localStorage.setItem(LANG_KEY, current);
    document.documentElement.setAttribute("data-lang", current);
    document.documentElement.setAttribute("lang", LANG_HTML[current] || "en");
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      const key = el.getAttribute("data-i18n");
      if (key) el.textContent = t(key);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) {
      const key = el.getAttribute("data-i18n-placeholder");
      if (key) el.setAttribute("placeholder", t(key));
    });
    const langBtn = document.getElementById("langLabel");
    if (langBtn) langBtn.textContent = LANG_LABEL[current] || current;
    paintLangMenu(current);
    applyTitle();
    applyTheme();
    paintNav();
  }
  window.setLang = function (next) {
    if (LANGS.indexOf(next) === -1) return;
    localStorage.setItem(LANG_KEY, next);
    const menu = document.getElementById("langMenu");
    if (menu) menu.hidden = true;
    const langBtn = document.getElementById("langLabel");
    if (langBtn) langBtn.setAttribute("aria-expanded", "false");
    applyLang();
  };
  window.toggleLangMenu = function () {
    const menu = document.getElementById("langMenu");
    const langBtn = document.getElementById("langLabel");
    if (!menu) return;
    menu.hidden = !menu.hidden;
    if (langBtn) langBtn.setAttribute("aria-expanded", menu.hidden ? "false" : "true");
  };
  window.cycleLang = function () {
    const i = LANGS.indexOf(detectLang());
    window.setLang(LANGS[(i + 1) % LANGS.length]);
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

  window.DRI18N = { t: t, applyLang: applyLang, setLang: window.setLang };

  document.addEventListener("DOMContentLoaded", function () {
    applyLang();
    if (window.requireAuthForArticle) requireAuthForArticle();
    document.querySelectorAll("[data-set-lang]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        window.setLang(btn.getAttribute("data-set-lang"));
      });
    });
    document.addEventListener("click", function (e) {
      const wrap = document.querySelector(".lang-wrap");
      const menu = document.getElementById("langMenu");
      if (!wrap || !menu || menu.hidden) return;
      if (!wrap.contains(e.target)) {
        menu.hidden = true;
        const langBtn = document.getElementById("langLabel");
        if (langBtn) langBtn.setAttribute("aria-expanded", "false");
      }
    });
    var bar = document.querySelector("[data-filter-bar]");
    if (bar) {
      bar.addEventListener("click", function (event) {
        var btn = event.target.closest("[data-filter-topic]");
        if (!btn) return;
        var topic = btn.getAttribute("data-filter-topic") || "all";
        bar.querySelectorAll("[data-filter-topic]").forEach(function (el) {
          el.setAttribute("aria-pressed", el === btn ? "true" : "false");
        });
        var visible = 0;
        document.querySelectorAll("[data-topics]").forEach(function (el) {
          var topics = (el.getAttribute("data-topics") || "").split(/\s+/);
          var show = topic === "all" || topics.indexOf(topic) !== -1;
          el.hidden = !show;
          if (show) visible += 1;
        });
        var empty = document.getElementById("filterEmpty");
        if (empty) empty.hidden = visible > 0;
      });
    }
  });
  setInterval(function () {
    if ((localStorage.getItem(THEME_KEY) || "auto") === "auto") applyTheme();
  }, 60 * 1000);
})();
