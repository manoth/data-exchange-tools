// ============================================================
// Configuration Module - Data Exchange Tools
// ============================================================

/**
 * Initialize config page - populate form if config exists
 */
async function initConfigPage() {
  try {
    const result = await api('/api/config', { method: 'GET' });
    if (result && result.success && result.config) {
      const config = result.config;
      const hostEl = document.getElementById('config-host');
      const portEl = document.getElementById('config-port');
      const dbEl = document.getElementById('config-database');
      const userEl = document.getElementById('config-username');
      const passEl = document.getElementById('config-password');

      if (hostEl && config.host) hostEl.value = config.host;
      if (portEl && config.port) portEl.value = config.port;
      if (dbEl && config.database) dbEl.value = config.database;
      if (userEl && config.username) userEl.value = config.username;
      if (passEl && config.password) passEl.value = config.password;
    }
  } catch (error) {
    console.error('Failed to load config:', error);
  }
}

/**
 * Get form data from config form
 */
function getConfigFormData() {
  return {
    host: document.getElementById('config-host').value.trim(),
    port: parseInt(document.getElementById('config-port').value, 10) || 3306,
    database: document.getElementById('config-database').value.trim(),
    username: document.getElementById('config-username').value.trim(),
    password: document.getElementById('config-password').value
  };
}

/**
 * Validate config form
 */
function validateConfigForm(data) {
  if (!data.host) {
    showToast('กรุณากรอก Host', 'warning');
    return false;
  }
  if (!data.port) {
    showToast('กรุณากรอก Port', 'warning');
    return false;
  }
  if (!data.database) {
    showToast('กรุณากรอกชื่อ Database', 'warning');
    return false;
  }
  if (!data.username) {
    showToast('กรุณากรอก Username', 'warning');
    return false;
  }
  return true;
}

/**
 * Test database connection
 */
async function testConnection() {
  const data = getConfigFormData();
  if (!validateConfigForm(data)) return;

  const statusDiv = document.getElementById('connection-status');
  statusDiv.classList.remove('hidden');
  statusDiv.className = 'connection-status testing';
  statusDiv.innerHTML = `
    <div class="status-content">
      <div class="spinner" style="width:20px;height:20px;"></div>
      <span>กำลังทดสอบการเชื่อมต่อ...</span>
    </div>
  `;

  try {
    const result = await api('/api/config/test', {
      method: 'POST',
      body: JSON.stringify(data)
    });

    if (result && result.success) {
      statusDiv.className = 'connection-status success';
      statusDiv.innerHTML = `
        <div class="status-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
          <span>เชื่อมต่อฐานข้อมูลสำเร็จ</span>
        </div>
      `;
      showToast('เชื่อมต่อฐานข้อมูลสำเร็จ', 'success');
    } else {
      const msg = result?.message || 'ไม่สามารถเชื่อมต่อฐานข้อมูลได้';
      statusDiv.className = 'connection-status error';
      statusDiv.innerHTML = `
        <div class="status-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          <span>${escapeHtml(msg)}</span>
        </div>
      `;
      showToast(msg, 'error');
    }
  } catch (error) {
    statusDiv.className = 'connection-status error';
    statusDiv.innerHTML = `
      <div class="status-content">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        <span>เกิดข้อผิดพลาดในการทดสอบการเชื่อมต่อ</span>
      </div>
    `;
    showToast('เกิดข้อผิดพลาดในการทดสอบการเชื่อมต่อ', 'error');
  }
}

/**
 * Save database configuration
 */
async function saveConfig() {
  const data = getConfigFormData();
  if (!validateConfigForm(data)) return;

  showLoading();

  try {
    const result = await api('/api/config', {
      method: 'POST',
      body: JSON.stringify(data)
    });

    hideLoading();

    if (result && result.success) {
      showToast('บันทึกการตั้งค่าสำเร็จ', 'success');

      // Update connection status display
      const statusDiv = document.getElementById('connection-status');
      statusDiv.classList.remove('hidden');
      statusDiv.className = 'connection-status success';
      statusDiv.innerHTML = `
        <div class="status-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
          <span>บันทึกการตั้งค่าสำเร็จ</span>
        </div>
      `;
      setTimeout(() => {
        showPage('dashboard');
        showSection('upload');
        showToast('ตั้งค่าฐานข้อมูลสำเร็จ', 'success');
      }, 900);
    } else {
      const msg = result?.message || 'ไม่สามารถบันทึกการตั้งค่าได้';
      showToast(msg, 'error');
    }
  } catch (error) {
    hideLoading();
    showToast('เกิดข้อผิดพลาดในการบันทึกการตั้งค่า', 'error');
  }
}

/**
 * Check if database config exists and is valid
 * Returns true if config is set up
 */
async function checkConfigStatus() {
  try {
    const result = await api('/api/config/status', { method: 'GET' });
    return result && result.configured === true;
  } catch {
    return false;
  }
}

/**
 * Shutdown local web service. Admin only.
 */
async function shutdownService() {
  const confirmed = window.confirm('ยืนยันปิด service? ผู้ใช้ทุกคนจะเข้าเว็บไม่ได้จนกว่าจะเปิดโปรแกรมใหม่');
  if (!confirmed) return;

  const statusDiv = document.getElementById('service-status');
  if (statusDiv) {
    statusDiv.className = 'connection-status testing';
    statusDiv.innerHTML = `
      <div class="status-content">
        <div class="spinner" style="width:20px;height:20px;"></div>
        <span>กำลังส่งคำสั่งปิด service...</span>
      </div>
    `;
  }

  try {
    const result = await api('/api/admin/shutdown', { method: 'POST' });
    if (result && result.success) {
      removeToken();
      removeUserData();
      if (statusDiv) {
        statusDiv.className = 'connection-status success';
        statusDiv.innerHTML = `
          <div class="status-content">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            <span>ส่งคำสั่งปิด service แล้ว สามารถปิดหน้าต่างนี้ได้</span>
          </div>
        `;
      }
    } else {
      showToast(result?.message || 'ไม่สามารถปิด service ได้', 'error');
    }
  } catch {
    if (statusDiv) {
      statusDiv.className = 'connection-status success';
      statusDiv.innerHTML = `
        <div class="status-content">
          <span>service ถูกปิดแล้ว</span>
        </div>
      `;
    }
  }
}

/**
 * Check local update manifest. Admin only.
 */
async function checkVersionUpdate() {
  const statusDiv = document.getElementById('version-status');
  const updateBtn = document.getElementById('btn-run-update');
  if (!statusDiv) return;

  statusDiv.className = 'connection-status testing';
  statusDiv.innerHTML = `
    <div class="status-content">
      <div class="spinner" style="width:20px;height:20px;"></div>
      <span>กำลังตรวจสอบ update...</span>
    </div>
  `;
  if (updateBtn) updateBtn.classList.add('hidden');

  const result = await api('/api/version/status', { method: 'GET' });
  if (!result || !result.success) {
    statusDiv.className = 'connection-status error';
    statusDiv.innerHTML = `
      <div class="status-content">
        <span>${escapeHtml(result?.message || 'ไม่สามารถตรวจสอบ update ได้')}</span>
      </div>
    `;
    return;
  }

  const notes = result.notes ? ` (${escapeHtml(result.notes)})` : '';
  if (result.update_available) {
    statusDiv.className = 'connection-status success';
    statusDiv.innerHTML = `
      <div class="status-content">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        <span>มี update: v${escapeHtml(result.latest_version)} | ปัจจุบัน v${escapeHtml(result.current_version)}${notes}</span>
      </div>
    `;
    if (updateBtn) updateBtn.classList.remove('hidden');
  } else {
    statusDiv.className = 'connection-status';
    statusDiv.innerHTML = `
      <div class="status-content">
        <span>เวอร์ชันปัจจุบัน v${escapeHtml(result.current_version)} | ${escapeHtml(result.message || 'ยังไม่มี update')}</span>
      </div>
    `;
  }
}

/**
 * Run detected update script. Admin only.
 */
async function runUpdateScript() {
  const confirmed = window.confirm('ยืนยันเริ่ม update script? ระบบอาจต้องเปิดโปรแกรมใหม่หลังอัปเดต');
  if (!confirmed) return;

  const statusDiv = document.getElementById('version-status');
  const updateBtn = document.getElementById('btn-run-update');
  if (updateBtn) updateBtn.disabled = true;
  if (statusDiv) {
    statusDiv.className = 'connection-status testing';
    statusDiv.innerHTML = `
      <div class="status-content">
        <div class="spinner" style="width:20px;height:20px;"></div>
        <span>กำลังเริ่ม update script...</span>
      </div>
    `;
  }

  const result = await api('/api/admin/update', { method: 'POST' });
  if (updateBtn) updateBtn.disabled = false;

  if (result && result.success) {
    if (statusDiv) {
      statusDiv.className = 'connection-status success';
      statusDiv.innerHTML = `
        <div class="status-content">
          <span>${escapeHtml(result.message)}</span>
        </div>
      `;
    }
    showToast('เริ่ม update แล้ว', 'success');
  } else {
    const msg = result?.message || 'ไม่สามารถเริ่ม update ได้';
    if (statusDiv) {
      statusDiv.className = 'connection-status error';
      statusDiv.innerHTML = `
        <div class="status-content">
          <span>${escapeHtml(msg)}</span>
        </div>
      `;
    }
    showToast(msg, 'error');
  }
}
