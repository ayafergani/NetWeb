(function () {
  const STORAGE_KEY = 'netguardSession';
  const ROLES = {
    ADMIN: 'ADMIN',
    NETWORK_ADMIN: 'NETWORK_ADMIN',
    SECURITY_ADMIN: 'SECURITY_ADMIN',
    AUDITOR: 'AUDITOR'
  };

  const PAGE_ACCESS = {
    dashboard: [ROLES.ADMIN, ROLES.NETWORK_ADMIN, ROLES.SECURITY_ADMIN, ROLES.AUDITOR],
    vlan: [ROLES.ADMIN, ROLES.NETWORK_ADMIN],
    interfaces: [ROLES.ADMIN, ROLES.NETWORK_ADMIN],
    alerts: [ROLES.ADMIN, ROLES.SECURITY_ADMIN, ROLES.AUDITOR],
    traffic: [ROLES.ADMIN, ROLES.SECURITY_ADMIN, ROLES.AUDITOR],
    configuration: [ROLES.ADMIN, ROLES.SECURITY_ADMIN],
    users: [ROLES.ADMIN],
    logs: [ROLES.ADMIN, ROLES.AUDITOR]
  };

  const DEFAULT_PAGE_BY_ROLE = {
    [ROLES.ADMIN]: 'network-dashboard%20(1).html',
    [ROLES.NETWORK_ADMIN]: 'network-dashboard%20(1).html',
    [ROLES.SECURITY_ADMIN]: 'network-dashboard%20(1).html',
    [ROLES.AUDITOR]: 'network-dashboard%20(1).html'
  };

  // Base de données des utilisateurs avec emails
  const USERS_DB = {
    admin: { 
      password: '123', 
      role: ROLES.ADMIN, 
      name: 'Super Admin', 
      email: 'benainimeroua@gmail.com' 
    },
    net: { 
      password: '123', 
      role: ROLES.NETWORK_ADMIN, 
      name: 'Ingénieur Réseau', 
      email: 'net@netguard.com' 
    },
    sec: { 
      password: '123', 
      role: ROLES.SECURITY_ADMIN, 
      name: 'Analyste SOC', 
      email: 'sec@netguard.com' 
    },
    audit: { 
      password: '123', 
      role: ROLES.AUDITOR, 
      name: 'Auditeur Externe', 
      email: 'audit@netguard.com' 
    }
  };

  function getSession() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  function setSession(session) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    localStorage.setItem('userRole', session.role);
    localStorage.setItem('userName', session.name);
    localStorage.setItem('userId', session.username);
    if (session.email) {
      localStorage.setItem('userEmail', session.email);
    }
  }

  function clearSession() {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem('userRole');
    localStorage.removeItem('userName');
    localStorage.removeItem('userId');
    localStorage.removeItem('userEmail');
  }

  function getRole() {
    const session = getSession();
    return session ? session.role : null;
  }

  function isAuthenticated() {
    return Boolean(getSession());
  }

  function canAccessPage(pageId, role) {
    const resolvedRole = role || getRole();
    const allowedRoles = PAGE_ACCESS[pageId] || [];
    return allowedRoles.includes(resolvedRole);
  }

  function getAllowedPages(role) {
    const resolvedRole = role || getRole();
    return Object.keys(PAGE_ACCESS).filter((pageId) => canAccessPage(pageId, resolvedRole));
  }

  function getDefaultPage(role) {
    return DEFAULT_PAGE_BY_ROLE[role] || 'login.html';
  }

  function redirectToDefault(role) {
    window.location.replace(getDefaultPage(role || getRole()));
  }

  function requirePageAccess(pageId) {
    const session = getSession();

    if (!session) {
      window.location.replace('login.html');
      return false;
    }

    if (!canAccessPage(pageId, session.role)) {
      redirectToDefault(session.role);
      return false;
    }

    return true;
  }

  // Fonction pour authentifier un utilisateur
  function authenticate(username, password) {
    const user = USERS_DB[username.toLowerCase()];
    if (user && user.password === password) {
      return {
        success: true,
        user: {
          username: username.toLowerCase(),
          name: user.name,
          role: user.role,
          email: user.email
        }
      };
    }
    return { success: false, error: 'Identifiant ou mot de passe incorrect' };
  }

  // Fonction pour trouver un utilisateur par email
  function findUserByEmail(email) {
    const normalizedEmail = email.toLowerCase().trim();
    for (const [username, userData] of Object.entries(USERS_DB)) {
      if (userData.email && userData.email.toLowerCase() === normalizedEmail) {
        return {
          username: username,
          ...userData
        };
      }
    }
    return null;
  }

  // Fonction pour réinitialiser le mot de passe
  function resetPassword(email) {
    const user = findUserByEmail(email);
    if (!user) {
      return { success: false, error: 'Aucun compte trouvé avec cet email' };
    }
    
    // Générer un nouveau mot de passe aléatoire
    const tempPassword = Math.random().toString(36).slice(-8);
    USERS_DB[user.username].password = tempPassword;
    
    return { 
      success: true, 
      message: 'Nouveau mot de passe généré',
      username: user.username,
      newPassword: tempPassword,
      email: email
    };
  }

  // Fonction pour obtenir les infos d'un utilisateur
  function getUserInfo(username) {
    const user = USERS_DB[username.toLowerCase()];
    if (user) {
      return {
        username: username.toLowerCase(),
        name: user.name,
        role: user.role,
        email: user.email
      };
    }
    return null;
  }

  // Exporter les fonctions et objets
  window.NetGuardAuth = {
    ROLES,
    PAGE_ACCESS,
    USERS_DB,
    getSession,
    setSession,
    clearSession,
    getRole,
    isAuthenticated,
    canAccessPage,
    getAllowedPages,
    getDefaultPage,
    redirectToDefault,
    requirePageAccess,
    authenticate,
    findUserByEmail,
    resetPassword,
    getUserInfo
  };
})();
