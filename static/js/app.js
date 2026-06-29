// ============================================================
// Main Application Module - Data Exchange Tools
// ============================================================

/**
 * Show a page (login, config, dashboard)
 */
function showPage(pageName) {
  if ((pageName === 'config' || pageName === 'service') && !isAdminSessionReady()) {
    prepareAdminLogin();
    return;
  }

  const pages = document.querySelectorAll('.page');
  pages.forEach(page => {
    page.classList.add('hidden');
  });

  const targetPage = document.getElementById(`page-${pageName}`);
  if (targetPage) {
    targetPage.classList.remove('hidden');
  }

  // Page-specific initialization
  if (pageName === 'dashboard') {
    initDashboard();
  } else if (pageName === 'config') {
    initConfigPage();
  }
}

function goToUploadPage() {
  showPage('dashboard');
  showSection('upload');
}

function returnFromConfig() {
  if (checkAuth() && getUserData()) {
    goToUploadPage();
  } else {
    showPage('login');
  }
}

/**
 * Show a dashboard section (upload, history, settings)
 */
function showSection(sectionName) {
  if (sectionName === 'settings' && !isAdminSessionReady()) {
    showSection('upload');
    showToast('เมนูตั้งค่าจัดการได้เฉพาะ admin', 'warning');
    return;
  }

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

  // Section-specific initialization
  if (sectionName === 'settings') {
    loadSettingsStatus();
  } else if (sectionName === 'history') {
    loadHistory();
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
    checkVersionUpdate();
  }
}

/**
 * Application startup
 */
document.addEventListener('DOMContentLoaded', async function () {
  localStorage.removeItem('dex_token');
  localStorage.removeItem('dex_user');

  // Check authentication first
  if (checkAuth()) {
    const userData = getUserData();
    if (userData?.role === 'admin') {
      if (userData.must_change_password) {
        showPage('admin-password');
      } else {
        const configured = await checkConfigStatus();
        if (configured) {
          goToUploadPage();
        } else {
          showPage('config');
        }
      }
    } else {
      goToUploadPage();
    }
  } else {
    showPage('login');
  }

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
