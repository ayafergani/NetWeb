(function () {
  const root = document.getElementById('topbar-root');

  if (!root) {
    return;
  }

  const titleText = root.dataset.title || 'Dashboard';
  const subtitleText = root.dataset.subtitle || '';
  const notificationCount = Number(root.dataset.notifications || 3);

  // ========== RÉCUPÉRATION DE LA SESSION UTILISATEUR ==========
  function getSessionUser() {
    try {
      if (window.NetGuardAuth && typeof window.NetGuardAuth.getSession === 'function') {
        const s = window.NetGuardAuth.getSession();
        if (s) {
          // Enrichir avec email depuis localStorage si absent dans la session
          if (!s.email) s.email = localStorage.getItem('userEmail') || '';
          return s;
        }
      }
      const raw = localStorage.getItem('netguardSession');
      if (raw) {
        const s = JSON.parse(raw);
        if (!s.email) s.email = localStorage.getItem('userEmail') || '';
        return s;
      }
    } catch (e) {
      console.warn('Impossible de lire la session :', e);
    }
    return null;
  }

  const ROLE_LABELS = {
    'admin':          'Administrateur Système',
    'network_admin':  'Administrateur Réseau',
    'security_admin': 'Analyste Sécurité (SOC)',
    'auditor':        'Auditeur Externe',
    'ADMIN':          'Administrateur Système',
    'NETWORK_ADMIN':  'Administrateur Réseau',
    'SECURITY_ADMIN': 'Analyste Sécurité (SOC)',
    'AUDITOR':        'Auditeur Externe',
  };

  function getRoleLabel(role) {
    if (!role) return 'Inconnu';
    return ROLE_LABELS[role] || role;
  }

  function getRoleColor(role) {
    const r = (role || '').toLowerCase();
    if (r.includes('network'))  return '#0ea5e9';
    if (r.includes('security')) return '#f59e0b';
    if (r.includes('audit'))    return '#22c55e';
    if (r.includes('admin'))    return '#6366f1';
    return '#64748b';
  }

  function getInitials(username) {
    if (username) return username.slice(0, 2).toUpperCase();
    return '??';
  }

  root.innerHTML = `
    <header class="topbar">
      <div class="topbar-section">
        <div class="topbar-title" id="topbar-title"></div>
        <div class="topbar-subtitle" id="topbar-subtitle"></div>
      </div>

      <div class="topbar-actions">
        <label class="topbar-search">
          <span class="sr-only">Rechercher</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
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

        <button type="button" id="topbar-theme-toggle" class="icon-button theme-toggle" aria-label="Changer le theme">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path>
          </svg>
        </button>

        <div class="user-dropdown">
          <button type="button" id="topbar-user-button" class="icon-button user-avatar-btn" aria-label="Compte utilisateur">
            <span id="topbar-user-initials" class="user-initials-badge">?</span>
          </button>
          <div id="topbar-user-menu" class="user-menu" hidden>
            <div id="topbar-menu-user-info" class="user-menu-info">
              <div id="topbar-menu-avatar" class="user-menu-avatar">?</div>
              <div class="user-menu-details">
                <span id="topbar-menu-username" class="user-menu-name">Chargement...</span>
                <span id="topbar-menu-role" class="user-menu-role">...</span>
              </div>
            </div>
            <div class="user-menu-divider"></div>
            <button type="button" class="user-menu-item" id="topbar-menu-profile">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              Mon profil
            </button>
            <button type="button" class="user-menu-item user-menu-item--danger" id="topbar-menu-logout">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
              Déconnexion
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- ===================== MODAL PROFIL ===================== -->
    <div id="topbar-profile-modal" class="ng-profile-overlay" role="dialog" aria-modal="true" aria-labelledby="ng-profile-title">
      <div class="ng-profile-card">

        <button type="button" id="profile-modal-close" class="ng-profile-close" aria-label="Fermer">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>

        <div class="ng-profile-header">
          <div class="ng-profile-header-bg" id="ng-header-bg"></div>
          <div class="ng-profile-avatar-wrap">
            <div class="ng-profile-avatar" id="ng-profile-avatar">??</div>
            <div class="ng-profile-status-dot" title="En ligne"></div>
          </div>
          <div class="ng-profile-header-info">
            <h2 class="ng-profile-name" id="ng-profile-title">Chargement…</h2>
            <span class="ng-profile-badge" id="ng-profile-badge">…</span>
          </div>
        </div>

        <div class="ng-profile-body">

          <div class="ng-info-row">
            <div class="ng-info-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="ng-info-content">
              <span class="ng-info-label">Nom d'utilisateur</span>
              <span class="ng-info-value" id="ng-profile-username">—</span>
            </div>
          </div>

          <div class="ng-info-row">
            <div class="ng-info-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                <polyline points="22,6 12,13 2,6"/>
              </svg>
            </div>
            <div class="ng-info-content">
              <span class="ng-info-label">Adresse e-mail</span>
              <span class="ng-info-value" id="ng-profile-email">—</span>
            </div>
          </div>

          <div class="ng-info-row">
            <div class="ng-info-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </div>
            <div class="ng-info-content">
              <span class="ng-info-label">Rôle et permissions</span>
              <span class="ng-info-value" id="ng-profile-role">—</span>
            </div>
          </div>

          <div class="ng-info-row">
            <div class="ng-info-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="ng-info-content">
              <span class="ng-info-label">Session démarrée</span>
              <span class="ng-info-value" id="ng-profile-session">—</span>
            </div>
          </div>

        </div>

        <div class="ng-profile-footer">
          <button type="button" id="profile-modal-logout" class="ng-btn-logout">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Déconnexion
          </button>
          <button type="button" id="profile-modal-close-btn" class="ng-btn-close">Fermer</button>
        </div>

      </div>
    </div>
  `;

  const titleEl      = document.getElementById('topbar-title');
  const subtitleEl   = document.getElementById('topbar-subtitle');
  const countEl      = document.getElementById('topbar-notif-count');
  const themeToggle  = document.getElementById('topbar-theme-toggle');
  const userButton   = document.getElementById('topbar-user-button');
  const userMenu     = document.getElementById('topbar-user-menu');
  const logoutBtn    = document.getElementById('topbar-menu-logout');
  const profileBtn   = document.getElementById('topbar-menu-profile');
  const profileModal = document.getElementById('topbar-profile-modal');

  // ========== AVATAR + DROPDOWN ==========
  function initUserAvatar() {
    var user      = getSessionUser();
    var initials  = getInitials(user ? user.username : null);
    var roleColor = getRoleColor(user ? user.role : null);

    var initialsEl = document.getElementById('topbar-user-initials');
    if (initialsEl) {
      initialsEl.textContent = initials;
      initialsEl.style.background = 'linear-gradient(135deg, ' + roleColor + ', ' + roleColor + 'cc)';
    }

    var menuUsernameEl = document.getElementById('topbar-menu-username');
    var menuRoleEl     = document.getElementById('topbar-menu-role');
    var menuAvatarEl   = document.getElementById('topbar-menu-avatar');
    if (menuUsernameEl) menuUsernameEl.textContent = (user && user.username) || 'Utilisateur';
    if (menuRoleEl)     menuRoleEl.textContent     = getRoleLabel(user ? user.role : null);
    if (menuAvatarEl) {
      menuAvatarEl.textContent = initials;
      menuAvatarEl.style.background = 'linear-gradient(135deg, ' + roleColor + ', ' + roleColor + 'cc)';
    }
  }

  // ========== REMPLIR LE MODAL PROFIL ==========
  function fillProfileModal() {
    var user      = getSessionUser();
    var initials  = getInitials(user ? user.username : null);
    var roleColor = getRoleColor(user ? user.role : null);

    // Fond coloré de l'en-tête
    var headerBg = document.getElementById('ng-header-bg');
    if (headerBg) {
      headerBg.style.background = 'linear-gradient(135deg, ' + roleColor + '28 0%, ' + roleColor + '08 100%)';
    }

    // Avatar avec initiales et ombre colorée
    var avatar = document.getElementById('ng-profile-avatar');
    if (avatar) {
      avatar.textContent     = initials;
      avatar.style.background  = 'linear-gradient(135deg, ' + roleColor + ' 0%, ' + roleColor + 'bb 100%)';
      avatar.style.boxShadow   = '0 8px 28px ' + roleColor + '55';
    }

    // Nom = username depuis la BDD
    var nameEl = document.getElementById('ng-profile-title');
    if (nameEl) nameEl.textContent = (user && user.username) || 'Utilisateur';

    // Badge rôle coloré
    var badgeEl = document.getElementById('ng-profile-badge');
    if (badgeEl) {
      badgeEl.textContent       = getRoleLabel(user ? user.role : null);
      badgeEl.style.background  = roleColor + '18';
      badgeEl.style.color       = roleColor;
      badgeEl.style.borderColor = roleColor + '50';
    }

    // Champs détaillés — toutes les données viennent de la session (BDD via /login)
    var usernameEl = document.getElementById('ng-profile-username');
    var emailEl    = document.getElementById('ng-profile-email');
    var roleEl     = document.getElementById('ng-profile-role');
    var sessionEl  = document.getElementById('ng-profile-session');

    if (usernameEl) usernameEl.textContent = (user && user.username) || '—';
    if (emailEl)    emailEl.textContent    = (user && user.email)    || 'Non renseigné';
    if (roleEl)     roleEl.textContent     = getRoleLabel(user ? user.role : null);

    if (sessionEl) {
      var loginTime = localStorage.getItem('netguard_login_time');
      if (!loginTime) {
        loginTime = Date.now().toString();
        localStorage.setItem('netguard_login_time', loginTime);
      }
      var d = new Date(Number(loginTime));
      sessionEl.textContent = d.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
    }
  }

  function openProfileModal() {
    fillProfileModal();
    profileModal.classList.add('ng-profile-overlay--visible');
    closeUserMenu();
    setTimeout(function() {
      var closeBtn = document.getElementById('profile-modal-close');
      if (closeBtn) closeBtn.focus();
    }, 120);
  }

  function closeProfileModal() {
    profileModal.classList.remove('ng-profile-overlay--visible');
  }

  function doLogout() {
    if (window.NetGuardAuth && typeof window.NetGuardAuth.clearSession === 'function') {
      window.NetGuardAuth.clearSession();
    }
    localStorage.removeItem('netguard_login_time');
    window.location.href = 'login.html';
  }

  function updateNotificationCount(count) {
    var value = Number(count) || 0;
    countEl.textContent = value > 99 ? '99+' : value;
    countEl.style.display = value > 0 ? 'flex' : 'none';
  }

  function setTheme(isDark) {
    document.documentElement.classList.toggle('dark-mode', isDark);
    document.body.classList.toggle('dark-mode', isDark);
    document.documentElement.classList.toggle('dark', isDark);
    document.body.classList.toggle('dark', isDark);

    if (themeToggle) {
      themeToggle.classList.toggle('toggle-active', isDark);
      themeToggle.setAttribute('aria-pressed', String(isDark));
      var svg = themeToggle.querySelector('svg');
      if (svg) {
        svg.innerHTML = isDark
          ? '<path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>'
          : '<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path>';
      }
    }
    localStorage.setItem('netguard-theme', isDark ? 'dark' : 'light');
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark: isDark } }));
  }

  function toggleTheme() {
    var isDark = document.documentElement.classList.contains('dark-mode') || document.body.classList.contains('dark-mode');
    setTheme(!isDark);
  }

  function initTheme() {
    var savedTheme = localStorage.getItem('netguard-theme');
    var shouldBeDark = savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches);
    setTheme(shouldBeDark);
  }

  function closeUserMenu() { userMenu.hidden = true; }
  function toggleUserMenu() { userMenu.hidden = !userMenu.hidden; }

  // ========== INIT ==========
  titleEl.textContent    = titleText;
  subtitleEl.textContent = subtitleText;
  subtitleEl.style.display = subtitleText ? 'block' : 'none';
  updateNotificationCount(notificationCount);
  initTheme();
  initUserAvatar();

  // ========== ÉVÉNEMENTS ==========
  window.addEventListener('storage', function (e) {
    if (e.key === 'netguard-theme') setTheme(e.newValue === 'dark');
  });

  if (themeToggle) themeToggle.addEventListener('click', toggleTheme);

  userButton.addEventListener('click', function (e) {
    e.stopPropagation();
    toggleUserMenu();
  });

  profileBtn.addEventListener('click', openProfileModal);
  logoutBtn.addEventListener('click', doLogout);

  document.getElementById('profile-modal-logout').addEventListener('click', doLogout);
  document.getElementById('profile-modal-close').addEventListener('click', closeProfileModal);
  document.getElementById('profile-modal-close-btn').addEventListener('click', closeProfileModal);

  profileModal.addEventListener('click', function (e) {
    if (e.target === profileModal) closeProfileModal();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeProfileModal(); closeUserMenu(); }
  });

  document.addEventListener('click', function (e) {
    if (userMenu && !userMenu.contains(e.target) && e.target !== userButton) closeUserMenu();
  });

  // ========== API PUBLIQUE ==========
  window.setPageTitle = function (title, subtitle) {
    titleEl.textContent    = title || 'Dashboard';
    subtitleEl.textContent = subtitle || '';
    subtitleEl.style.display = subtitle ? 'block' : 'none';
  };
  window.setNotificationCount = function (count) { updateNotificationCount(count); };
  window.toggleTheme  = toggleTheme;
  window.setTheme     = setTheme;
  window.openProfileModal = openProfileModal;
})();