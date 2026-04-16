(function () {
  const host = document.getElementById('sidebar-root');

  if (!host) {
    return;
  }

  const currentPage = host.dataset.page || '';
  const links = [
    { id: 'dashboard', label: 'Dashboard', href: 'network-dashboard%20(1).html', icon: 'monitor' },
    { id: 'vlan', label: 'VLAN', href: 'vlan.html', icon: 'vlan' },
    { id: 'alerts', label: 'Alerts', href: 'alerts.html', icon: 'alert' }
  ];

  const icons = {
    vlan: '<path d="M21 5H3a1 1 0 0 0-1 1v3a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1zM21 13H3a1 1 0 0 0-1 1v3a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1z"></path>',
    alert: '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>',
    monitor: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>'
  };

  const renderIcon = (type) =>
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    icons[type] +
    '</svg>';

  host.innerHTML = `
    <aside class="app-sidebar">
      <a class="sidebar-logo" href="network-dashboard%20(1).html" aria-label="Go to dashboard">
        ${renderIcon('vlan')}
      </a>
      <nav class="sidebar-nav" aria-label="Main navigation">
        ${links
          .map(
            (link) => `
              <a class="sidebar-link ${link.id === currentPage ? 'active' : ''}" href="${link.href}">
                ${renderIcon(link.icon)}
                <span>${link.label}</span>
              </a>
            `
          )
          .join('')}
      </nav>
    </aside>
  `;
})();
