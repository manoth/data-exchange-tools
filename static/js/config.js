// ============================================================
// Configuration Module - Data Exchange Tools
// ============================================================

const configTestState = {
  passed: false,
  fingerprint: ''
};

function getConfigFingerprint(data = getConfigFormData()) {
  return JSON.stringify(data);
}

function setConfigTestPassed(data) {
  configTestState.passed = true;
  configTestState.fingerprint = getConfigFingerprint(data);
  updateSaveConfigButton();
}

function resetConfigTestState(message = '') {
  configTestState.passed = false;
  configTestState.fingerprint = '';
  updateSaveConfigButton();
  if (message) {
    const statusDiv = document.getElementById('connection-status');
    if (statusDiv) {
      statusDiv.classList.remove('hidden');
      statusDiv.className = 'connection-status warning';
      statusDiv.innerHTML = `
        <div class="status-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
          <span>${escapeHtml(message)}</span>
        </div>
      `;
    }
  }
}

function isConfigTestValid(data = getConfigFormData()) {
  return configTestState.passed && configTestState.fingerprint === getConfigFingerprint(data);
}

function updateSaveConfigButton() {
  const saveBtn = document.getElementById('btn-save-config');
  if (!saveBtn) return;
  const valid = isConfigTestValid();
  saveBtn.classList.toggle('btn-needs-test', !valid);
  saveBtn.title = valid ? '' : 'ต้องทดสอบการเชื่อมต่อให้สำเร็จก่อนบันทึก';
}

function bindConfigInputWatchers() {
  document.querySelectorAll('#config-form input').forEach((input) => {
    if (input.dataset.configWatchBound === 'true') return;
    input.dataset.configWatchBound = 'true';
    input.addEventListener('input', () => {
      if (configTestState.passed) {
        resetConfigTestState('มีการแก้ไขข้อมูลการเชื่อมต่อ กรุณาทดสอบอีกครั้งก่อนบันทึก');
      } else {
        updateSaveConfigButton();
      }
    });
  });
}

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
  } finally {
    bindConfigInputWatchers();
    resetConfigTestState();
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
      setConfigTestPassed(data);
      statusDiv.className = 'connection-status success';
      statusDiv.innerHTML = `
        <div class="status-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
          <span>เชื่อมต่อฐานข้อมูลสำเร็จ</span>
        </div>
      `;
      showToast('เชื่อมต่อฐานข้อมูลสำเร็จ', 'success');
      showSweetAlert({
        type: 'success',
        title: 'ทดสอบสำเร็จ',
        message: 'เชื่อมต่อฐานข้อมูลสำเร็จ สามารถบันทึกการตั้งค่าได้แล้ว',
        confirmText: 'ตกลง'
      });
    } else {
      const msg = result?.message || 'ไม่สามารถเชื่อมต่อฐานข้อมูลได้';
      resetConfigTestState();
      statusDiv.className = 'connection-status error';
      statusDiv.innerHTML = `
        <div class="status-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          <span>${escapeHtml(msg)}</span>
        </div>
      `;
      showToast(msg, 'error');
      showSweetAlert({
        type: 'error',
        title: 'ทดสอบไม่สำเร็จ',
        message: msg,
        confirmText: 'ตรวจสอบอีกครั้ง'
      });
    }
  } catch (error) {
    resetConfigTestState();
    statusDiv.className = 'connection-status error';
    statusDiv.innerHTML = `
      <div class="status-content">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        <span>เกิดข้อผิดพลาดในการทดสอบการเชื่อมต่อ</span>
      </div>
    `;
    showToast('เกิดข้อผิดพลาดในการทดสอบการเชื่อมต่อ', 'error');
    showSweetAlert({
      type: 'error',
      title: 'ทดสอบไม่สำเร็จ',
      message: 'เกิดข้อผิดพลาดในการทดสอบการเชื่อมต่อ กรุณาตรวจสอบข้อมูลและเครือข่าย',
      confirmText: 'ตกลง'
    });
  }
}

/**
 * Save database configuration
 */
async function saveConfig() {
  const data = getConfigFormData();
  if (!validateConfigForm(data)) return;
  if (!isConfigTestValid(data)) {
    const message = configTestState.passed
      ? 'ข้อมูลการเชื่อมต่อถูกแก้ไขหลังทดสอบ กรุณาทดสอบการเชื่อมต่อใหม่ก่อนบันทึก'
      : 'กรุณากดทดสอบการเชื่อมต่อให้สำเร็จก่อนบันทึกการตั้งค่า';
    resetConfigTestState(message);
    showSweetAlert({
      type: 'warning',
      title: 'ยังบันทึกไม่ได้',
      message,
      confirmText: 'รับทราบ'
    });
    showToast(message, 'warning');
    return;
  }

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
        navigateToRoute('/upload', true);
        if (typeof startUpdateAutoCheck === 'function') startUpdateAutoCheck();
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
 * Check online/local update manifest. Admin only.
 */
async function checkVersionUpdate(force = true, silent = false) {
  const statusDiv = document.getElementById('version-status');
  const updateBtn = document.getElementById('btn-run-update');
  const updateBtnLabel = document.getElementById('btn-run-update-label');
  if (!statusDiv && silent) return;

  if (statusDiv) {
    statusDiv.className = 'connection-status testing';
    statusDiv.innerHTML = `
      <div class="status-content">
        <div class="spinner" style="width:20px;height:20px;"></div>
        <span>กำลังตรวจสอบ update...</span>
      </div>
    `;
  }
  if (updateBtn) updateBtn.classList.add('hidden');

  const query = force ? '?force=true' : '';
  const result = await api(`/api/version/status${query}`, { method: 'GET' });
  if (!result || !result.success) {
    if (statusDiv) {
      statusDiv.className = 'connection-status error';
      statusDiv.innerHTML = `
        <div class="status-content">
          <span>${escapeHtml(result?.message || 'ไม่สามารถตรวจสอบ update ได้')}</span>
        </div>
      `;
    }
    return;
  }

  const notes = result.notes ? ` (${escapeHtml(result.notes)})` : '';
  if (result.update_available) {
    if (statusDiv) {
      statusDiv.className = 'connection-status success';
      statusDiv.innerHTML = `
        <div class="status-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m17 8-5-5-5 5"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/></svg>
          <span>พบเวอร์ชันใหม่ v${escapeHtml(result.latest_version)} (เวอร์ชันปัจจุบัน v${escapeHtml(result.current_version)})${notes}</span>
        </div>
        <div class="status-subtext">พร้อมดาวน์โหลดและติดตั้งอัปเดต</div>
      `;
    }
    if (updateBtnLabel) {
      updateBtnLabel.textContent = `อัปเดตเป็น v${result.latest_version}`;
    }
    if (updateBtn) updateBtn.classList.remove('hidden');
    if (silent) showToast(`มี update v${result.latest_version}`, 'info');
  } else {
    if (statusDiv) {
      statusDiv.className = 'connection-status success';
      statusDiv.innerHTML = `
        <div class="status-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
          <span>เวอร์ชัน v${escapeHtml(result.current_version)} เป็นเวอร์ชันล่าสุดแล้ว</span>
        </div>
        <div class="status-subtext">ระบบจะตรวจสอบเวอร์ชันใหม่อีกครั้งโดยอัตโนมัติทุก 10 นาที</div>
      `;
    }
  }
}

/**
 * Run detected update script. Admin only.
 */
async function runUpdateScript() {
  const confirmed = window.confirm('ยืนยันเริ่ม online update? ถ้าเป็น update หน้าเว็บ ระบบจะ refresh หน้าให้เอง');
  if (!confirmed) return;

  const statusDiv = document.getElementById('version-status');
  const updateBtn = document.getElementById('btn-run-update');
  if (updateBtn) updateBtn.disabled = true;
  if (statusDiv) {
    statusDiv.className = 'connection-status testing';
    statusDiv.innerHTML = `
      <div class="status-content">
        <div class="spinner" style="width:20px;height:20px;"></div>
        <span>กำลังเริ่ม online update...</span>
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
    showToast(result.reload_required ? 'อัปเดตหน้าเว็บแล้ว กำลัง refresh...' : 'เริ่ม update แล้ว', 'success');
    if (result.reload_required) {
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    }
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
