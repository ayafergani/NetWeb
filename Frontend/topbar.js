(function () {
  const root = document.getElementById('topbar-root');

  if (!root) {
    return;
  }

  const titleText = root.dataset.title || 'Dashboard';
  const subtitleText = root.dataset.subtitle || '';
  const notificationCount = Number(root.dataset.notifications || 3);

  root.innerHTML = `
    <header class="topbar">
      <div class="topbar-section">
        <div class="topbar-title" id="topbar-title"></div>
        <div class="topbar-subtitle" id="topbar-subtitle"></div>
      </div>

      <div class="topbar-actions">
        <label class="topbar-search">
          <span class="sr-only">Rechercher</span>
          <input id="topbar-search-input" class="search-input" type="search" placeholder="Rechercher..." autocomplete="off" />
        </label>

        <div class="notif-wrapper">
          <button type="button" id="topbar-notif-button" class="icon-button" aria-label="Notifications">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0 1 18 14.158V11a6 6 0 0 0-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 1 1-6 0v-1m6 0H9" />
            </svg>
          </button>
          <span id="topbar-notif-count" class="notif-count"></span>
        </div>

        <button type="button" id="topbar-theme-toggle" class="icon-button theme-toggle" aria-label="Changer le thème">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path>
          </svg>
        </button>

        <div class="user-dropdown">
          <button type="button" id="topbar-user-button" class="icon-button" aria-label="Compte utilisateur">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
          </button>
          <div id="topbar-user-menu" class="user-menu" hidden>
            <button type="button" class="user-menu-item" id="topbar-menu-profile">Mon profil</button>
            <button type="button" class="user-menu-item" id="topbar-menu-logout">Déconnexion</button>
          </div>
        </div>
      </div>
    </header>
  `;

  const titleEl = document.getElementById('topbar-title');
  const subtitleEl = document.getElementById('topbar-subtitle');
  const countEl = document.getElementById('topbar-notif-count');
  const themeToggle = document.getElementById('topbar-theme-toggle');
  const userButton = document.getElementById('topbar-user-button');
  const userMenu = document.getElementById('topbar-user-menu');
  const logoutBtn = document.getElementById('topbar-menu-logout');

  function updateTitle(title, subtitle) {
    titleEl.textContent = title || 'Dashboard';
    subtitleEl.textContent = subtitle || '';
    subtitleEl.style.display = subtitle ? 'block' : 'none';
  }

  function updateNotificationCount(count) {
    const value = Number(count) || 0;
    countEl.textContent = value > 99 ? '99+' : value;
    countEl.style.display = value > 0 ? 'flex' : 'none';
  }

  // ========== GESTION DU DARK MODE UNIFIÉE ==========
  function setTheme(isDark) {
    const htmlElement = document.documentElement;
    const bodyElement = document.body;

    htmlElement.classList.toggle('dark-mode', isDark);
    bodyElement.classList.toggle('dark-mode', isDark);
    htmlElement.classList.toggle('dark', isDark);
    bodyElement.classList.toggle('dark', isDark);
    htmlElement.classList.toggle('dark-theme', false);
    bodyElement.classList.toggle('dark-theme', false);
    
    // Mettre à jour l'icône du toggle
    if (themeToggle) {
      themeToggle.classList.toggle('toggle-active', isDark);
      themeToggle.setAttribute('aria-pressed', String(isDark));
      themeToggle.title = isDark ? 'Activer le thème clair' : 'Activer le thème sombre';
      
      // Changer l'icône (lune -> soleil)
      const svg = themeToggle.querySelector('svg');
      if (svg) {
        if (isDark) {
          svg.innerHTML = '<path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>';
        } else {
          svg.innerHTML = '<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path>';
        }
      }
    }
    
    // Sauvegarder dans localStorage
    localStorage.setItem('netguard-theme', isDark ? 'dark' : 'light');
    
    // Déclencher un événement personnalisé pour informer les autres composants
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark } }));
  }

  function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark-mode') || document.body.classList.contains('dark-mode');
    setTheme(!isDark);
  }

  // Initialiser le thème au chargement
  function initTheme() {
    const savedTheme = localStorage.getItem('netguard-theme');
    const shouldBeDark = savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches);
    setTheme(shouldBeDark);
  }

  function closeUserMenu() {
    userMenu.hidden = true;
  }

  function toggleUserMenu() {
    userMenu.hidden = !userMenu.hidden;
  }

  titleEl.textContent = titleText;
  subtitleEl.textContent = subtitleText;
  subtitleEl.style.display = subtitleText ? 'block' : 'none';
  updateNotificationCount(notificationCount);

  // Initialiser le thème
  initTheme();

  window.addEventListener('storage', function(event) {
    if (event.key === 'netguard-theme') {
      setTheme(event.newValue === 'dark');
    }
  });

  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }
  userButton.addEventListener('click', function (event) {
    event.stopPropagation();
    toggleUserMenu();
  });

  logoutBtn.addEventListener('click', function () {
    if (window.NetGuardAuth && typeof window.NetGuardAuth.clearSession === 'function') {
      window.NetGuardAuth.clearSession();
    }
    window.location.href = 'netguard_login_v2.html';
  });

  document.addEventListener('click', function (event) {
    if (userMenu && !userMenu.contains(event.target) && event.target !== userButton) {
      closeUserMenu();
    }
  });

  window.setPageTitle = function (title, subtitle) {
    updateTitle(title, subtitle || '');
  };

  window.setNotificationCount = function (count) {
    updateNotificationCount(count);
  };

  window.toggleTheme = toggleTheme;
  window.setTheme = setTheme;
})();