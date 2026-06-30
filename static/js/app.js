// ============================================================
// Main Application Module - Data Exchange Tools
// ============================================================

let updateCheckTimer = null;
let isRouting = false;

const routeByPage = {
  login: '/login',
  'admin-password': '/change-admin-password',
  config: '/config',
  service: '/service'
};

const routeBySection = {
  upload: '/upload',
  history: '/history',
  settings: '/settings',
  manual: '/manual'
};

function normalizeRoute(path = window.location.pathname) {
  const cleanPath = path.replace(/\/+$/, '') || '/';
  const allowedRoutes = new Set([
    '/',
    ...Object.values(routeByPage),
    ...Object.values(routeBySection)
  ]);
  return allowedRoutes.has(cleanPath) ? cleanPath : '/upload';
}

function setRoute(path, replace = false) {
  const route = normalizeRoute(path);
  if (window.location.pathname === route) return;
  const method = replace ? 'replaceState' : 'pushState';
  window.history[method]({}, '', route);
}

function getRequestedRoute() {
  const route = normalizeRoute();
  return route === '/' ? '/upload' : route;
}

function rememberRouteForAfterLogin(route = getRequestedRoute()) {
  if (route !== '/login' && route !== '/change-admin-password') {
    sessionStorage.setItem('dex_pending_route', route);
  }
}

function consumePendingRoute() {
  const route = sessionStorage.getItem('dex_pending_route') || getRequestedRoute();
  sessionStorage.removeItem('dex_pending_route');
  return route;
}

function rememberReturnRoute(targetRoute) {
  const currentRoute = getRequestedRoute();
  const blockedRoutes = new Set(['/', '/login', '/change-admin-password', targetRoute]);

  if (!blockedRoutes.has(currentRoute)) {
    sessionStorage.setItem('dex_return_route', currentRoute);
  }
}

function consumeReturnRoute() {
  const route = normalizeRoute(sessionStorage.getItem('dex_return_route') || '/upload');
  sessionStorage.removeItem('dex_return_route');

  if (route === '/login' || route === '/change-admin-password') {
    return '/upload';
  }

  return route;
}

function routeToCurrentPath(replace = false) {
  navigateToRoute(getRequestedRoute(), replace);
}

/**
 * Show a page (login, config, dashboard)
 */
function showPage(pageName, updateRoute = true) {
  if ((pageName === 'config' || pageName === 'service') && !isAdminSessionReady()) {
    rememberRouteForAfterLogin(routeByPage[pageName] || '/upload');
    prepareAdminLogin();
    return;
  }

  if (!isRouting && updateRoute && (pageName === 'config' || pageName === 'service')) {
    rememberReturnRoute(routeByPage[pageName]);
  }

  const pages = document.querySelectorAll('.page');
  pages.forEach(page => {
    page.classList.add('hidden');
  });

  const targetPage = document.getElementById(`page-${pageName}`);
  if (targetPage) {
    targetPage.classList.remove('hidden');
  }

  if (!isRouting && updateRoute && routeByPage[pageName]) {
    setRoute(routeByPage[pageName]);
  }

  // Page-specific initialization
  if (pageName === 'dashboard') {
    initDashboard();
  } else if (pageName === 'config') {
    initConfigPage();
  }
}

function goToUploadPage(updateRoute = true) {
  showPage('dashboard', false);
  showSection('upload', updateRoute);
}

function returnFromConfig() {
  if (checkAuth() && getUserData()) {
    navigateToRoute(consumeReturnRoute(), true);
  } else {
    showPage('login');
  }
}

/**
 * Show a dashboard section (upload, history, settings)
 */
function showSection(sectionName, updateRoute = true) {
  if (sectionName === 'settings' && !isAdminSessionReady()) {
    showSection('upload', updateRoute);
    showToast('เมนูตั้งค่าจัดการได้เฉพาะ admin', 'warning');
    return;
  }

  showPage('dashboard', false);

  const sections = document.querySelectorAll('.section');
  sections.forEach(section => {
    section.classList.remove('active');
  });

  const targetSection = document.getElementById(`section-${sectionName}`);
  if (targetSection) {
    targetSection.classList.add('active');
  }

  // Update sidebar active state
  const sidebarItems = document.querySelectorAll('.sidebar-item');
  sidebarItems.forEach(item => {
    item.classList.remove('active');
    if (item.dataset.section === sectionName) {
      item.classList.add('active');
    }
  });

  if (!isRouting && updateRoute && routeBySection[sectionName]) {
    setRoute(routeBySection[sectionName]);
  }

  // Section-specific initialization
  if (sectionName === 'settings') {
    loadSettingsStatus();
  } else if (sectionName === 'history') {
    loadHistory();
  } else if (sectionName === 'manual') {
    loadManualContent();
  }
}

async function navigateToRoute(route, replace = false) {
  const targetRoute = normalizeRoute(route);
  isRouting = true;

  try {
    if (!checkAuth()) {
      rememberRouteForAfterLogin(targetRoute);
      showPage('login', false);
      setRoute('/login', replace);
      return;
    }

    const userData = getUserData();
    if (userData?.role === 'admin' && userData.must_change_password) {
      showPage('admin-password', false);
      setRoute('/change-admin-password', replace);
      return;
    }

    if (userData?.role === 'admin' && targetRoute !== '/config') {
      const configured = await checkConfigStatus();
      if (!configured) {
        showPage('config', false);
        setRoute('/config', replace);
        return;
      }
    }

    if ((targetRoute === '/config' || targetRoute === '/service' || targetRoute === '/settings') && !isAdminSessionReady()) {
      showSection('upload', false);
      setRoute('/upload', replace);
      showToast('เมนูนี้จัดการได้เฉพาะ admin', 'warning');
      return;
    }

    if (targetRoute === '/config') {
      showPage('config', false);
      setRoute('/config', replace);
      return;
    }

    if (targetRoute === '/service') {
      showPage('service', false);
      setRoute('/service', replace);
      return;
    }

    const sectionByRoute = {
      '/upload': 'upload',
      '/history': 'history',
      '/settings': 'settings',
      '/manual': 'manual'
    };

    const section = sectionByRoute[targetRoute] || 'upload';
    showSection(section, false);
    setRoute(routeBySection[section] || '/upload', replace);
  } finally {
    isRouting = false;
  }
}

/**
 * Toggle sidebar collapsed state
 */
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.querySelector('.main-content');

  if (sidebar) {
    sidebar.classList.toggle('collapsed');
  }
  if (mainContent) {
    mainContent.classList.toggle('sidebar-collapsed');
  }
}

/**
 * Initialize dashboard
 */
function initDashboard() {
  // Set user info in navbar
  const userData = getUserData();
  if (userData) {
    const nameEl = document.getElementById('nav-username');
    const posEl = document.getElementById('nav-position');
    if (nameEl) nameEl.textContent = userData.name || userData.username || '-';
    if (posEl) posEl.textContent = userData.position || '';
  }

  applyRoleVisibility();

  // Initialize upload zone
  initUpload();
}

function applyRoleVisibility() {
  const isAdmin = isAdminSessionReady();
  document.querySelectorAll('.admin-only').forEach(el => {
    el.classList.toggle('hidden', !isAdmin);
  });

  if (!isAdmin && document.getElementById('section-settings')?.classList.contains('active')) {
    showSection('upload');
  }
}

async function loadManualContent() {
  const container = document.getElementById('manual-content');
  if (!container || container.dataset.loaded === 'true') return;

  try {
    const response = await fetch('/static/manual_fragment.html', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    container.innerHTML = await response.text();
    container.dataset.loaded = 'true';
  } catch (error) {
    container.innerHTML = `
      <div class="empty-state">
        <p>ไม่สามารถโหลดคู่มือการใช้งานได้</p>
        <p class="text-secondary">${escapeHtml(error.message || 'ไม่ทราบสาเหตุ')}</p>
      </div>
    `;
  }
}

function startUpdateAutoCheck() {
  if (!isAdminSessionReady() || typeof checkVersionUpdate !== 'function') return;
  if (updateCheckTimer) return;

  checkVersionUpdate(false, true);
  updateCheckTimer = window.setInterval(() => {
    if (!isAdminSessionReady()) {
      window.clearInterval(updateCheckTimer);
      updateCheckTimer = null;
      return;
    }
    checkVersionUpdate(false, true);
  }, 10 * 60 * 1000);
}

/**
 * Load settings page status
 */
async function loadSettingsStatus() {
  const statusDiv = document.getElementById('settings-db-status');
  if (!statusDiv) return;

  statusDiv.innerHTML = `
    <div class="status-content">
      <div class="spinner" style="width:20px;height:20px;"></div>
      <span>กำลังตรวจสอบสถานะ...</span>
    </div>
  `;

  const configured = await checkConfigStatus();

  if (configured) {
    statusDiv.className = 'connection-status success';
    statusDiv.innerHTML = `
      <div class="status-content">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        <span>เชื่อมต่อฐานข้อมูลแล้ว</span>
      </div>
    `;
  } else {
    statusDiv.className = 'connection-status error';
    statusDiv.innerHTML = `
      <div class="status-content">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
        <span>ยังไม่ได้ตั้งค่าฐานข้อมูล</span>
      </div>
    `;
  }

  if (typeof checkVersionUpdate === 'function' && isAdminSessionReady()) {
    checkVersionUpdate(true, false);
  }
}

/**
 * Application startup
 */
document.addEventListener('DOMContentLoaded', async function () {
  localStorage.removeItem('dex_token');
  localStorage.removeItem('dex_user');

  const requestedRoute = getRequestedRoute();

  // Check authentication first
  if (checkAuth()) {
    const userData = getUserData();
    if (userData?.role === 'admin') {
      if (userData.must_change_password) {
        showPage('admin-password', false);
        setRoute('/change-admin-password', true);
      } else {
        const configured = await checkConfigStatus();
        if (configured) {
          await navigateToRoute(requestedRoute, true);
          startUpdateAutoCheck();
        } else {
          showPage('config', false);
          setRoute('/config', true);
        }
      }
    } else {
      await navigateToRoute(requestedRoute, true);
    }
  } else {
    rememberRouteForAfterLogin(requestedRoute);
    showPage('login', false);
    setRoute('/login', true);
  }

  window.addEventListener('popstate', () => {
    routeToCurrentPath(true);
  });

  // Handle responsive sidebar close on mobile when clicking outside
  document.addEventListener('click', function (e) {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.querySelector('.sidebar-toggle');

    if (window.innerWidth <= 768 && sidebar && !sidebar.classList.contains('collapsed')) {
      if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
        sidebar.classList.add('collapsed');
        const mainContent = document.querySelector('.main-content');
        if (mainContent) mainContent.classList.add('sidebar-collapsed');
      }
    }
  });

  // Handle window resize
  window.addEventListener('resize', function () {
    const sidebar = document.getElementById('sidebar');
    if (window.innerWidth <= 768 && sidebar) {
      sidebar.classList.add('collapsed');
    }
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', function (e) {
    // Escape to close loading overlay
    if (e.key === 'Escape') {
      hideLoading();
    }
  });
});
