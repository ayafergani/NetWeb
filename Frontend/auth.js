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
  }

  function clearSession() {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem('userRole');
    localStorage.removeItem('userName');
    localStorage.removeItem('userId');
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

  window.NetGuardAuth = {
    ROLES,
    PAGE_ACCESS,
    getSession,
    setSession,
    clearSession,
    getRole,
    isAuthenticated,
    canAccessPage,
    getAllowedPages,
    getDefaultPage,
    redirectToDefault,
    requirePageAccess
  };
})();
