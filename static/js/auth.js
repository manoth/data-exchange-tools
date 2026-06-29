// ============================================================
// Authentication Module - Data Exchange Tools
// ============================================================

/**
 * Handle login form submission
 */
async function handleLogin(event) {
  event.preventDefault();

  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errorDiv = document.getElementById('login-error');
  const btnLogin = document.getElementById('btn-login');
  const btnText = btnLogin.querySelector('.btn-text');
  const btnLoading = btnLogin.querySelector('.btn-loading');

  // Clear previous errors
  errorDiv.classList.add('hidden');
  errorDiv.textContent = '';

  // Validate
  if (!username || !password) {
    errorDiv.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
      กรุณากรอกชื่อผู้ใช้และรหัสผ่าน
    `;
    errorDiv.classList.remove('hidden');
    return;
  }

  // Show loading state
  btnLogin.disabled = true;
  btnText.classList.add('hidden');
  btnLoading.classList.remove('hidden');

  try {
    const result = await api('/api/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });

    if (result && result.success) {
      // Store auth data
      setToken(result.token);
      setUserData({
        username: result.username || username,
        name: result.name || username,
        position: result.position || '',
        role: result.role || 'user',
        must_change_password: result.must_change_password === true
      });

      showToast('เข้าสู่ระบบสำเร็จ', 'success');
      if (result.role === 'admin') {
        if (result.must_change_password) {
          showPage('admin-password');
        } else if (result.configured === true) {
          showPage('dashboard');
          showSection('upload');
          if (typeof startUpdateAutoCheck === 'function') startUpdateAutoCheck();
        } else {
          showPage('config');
        }
      } else {
        showPage('dashboard');
        showSection('upload');
      }
    } else {
      const msg = result?.message || 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง';
      errorDiv.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
        ${escapeHtml(msg)}
      `;
      errorDiv.classList.remove('hidden');
    }
  } catch (error) {
    errorDiv.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
      เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่อีกครั้ง
    `;
    errorDiv.classList.remove('hidden');
  } finally {
    // Reset loading state
    btnLogin.disabled = false;
    btnText.classList.remove('hidden');
    btnLoading.classList.add('hidden');
  }
}

/**
 * Logout - clear all auth data and navigate to login
 */
function logout() {
  removeToken();
  removeUserData();
  showPage('login');
  showToast('ออกจากระบบสำเร็จ', 'info');
}

function prepareAdminLogin() {
  removeToken();
  removeUserData();
  showPage('login');
  const username = document.getElementById('login-username');
  const password = document.getElementById('login-password');
  if (username) username.value = 'admin';
  if (password) password.focus();
  showToast('กรุณาเข้าสู่ระบบด้วย admin เพื่อจัดการฐานข้อมูล', 'info');
}

function isAdminSessionReady() {
  const userData = getUserData();
  return Boolean(getToken() && userData?.role === 'admin' && userData?.must_change_password !== true);
}

function validateAdminPasswordClient(password, oldPassword) {
  if (password === oldPassword) return 'รหัสผ่านใหม่ต้องไม่ซ้ำกับรหัสผ่านเดิม';
  if (password.length < 8) return 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร';
  if (/\s/.test(password)) return 'รหัสผ่านต้องไม่มีช่องว่าง';
  if (!/[a-z]/.test(password)) return 'ต้องมีตัวพิมพ์เล็กอย่างน้อย 1 ตัว';
  if (!/[A-Z]/.test(password)) return 'ต้องมีตัวพิมพ์ใหญ่อย่างน้อย 1 ตัว';
  if (!/[0-9]/.test(password)) return 'ต้องมีตัวเลขอย่างน้อย 1 ตัว';
  if (!/[^A-Za-z0-9]/.test(password)) return 'ต้องมีอักขระพิเศษอย่างน้อย 1 ตัว';
  if (['admin', 'password', 'administrator'].includes(password.toLowerCase())) return 'รหัสผ่านนี้เดาง่ายเกินไป';
  return '';
}

async function changeAdminPassword(event) {
  event.preventDefault();

  const oldPassword = document.getElementById('admin-old-password').value;
  const newPassword = document.getElementById('admin-new-password').value;
  const confirmPassword = document.getElementById('admin-confirm-password').value;
  const errorDiv = document.getElementById('admin-password-error');

  errorDiv.classList.add('hidden');
  errorDiv.textContent = '';

  if (newPassword !== confirmPassword) {
    errorDiv.textContent = 'ยืนยันรหัสผ่านใหม่ไม่ตรงกัน';
    errorDiv.classList.remove('hidden');
    return;
  }

  const validationError = validateAdminPasswordClient(newPassword, oldPassword);
  if (validationError) {
    errorDiv.textContent = validationError;
    errorDiv.classList.remove('hidden');
    return;
  }

  showLoading();
  try {
    const result = await api('/api/admin/change-password', {
      method: 'POST',
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword
      })
    });
    hideLoading();

    if (result && result.success) {
      if (result.token) {
        setToken(result.token);
      }
      showToast('เปลี่ยนรหัสผ่านสำเร็จ กรุณาตั้งค่าฐานข้อมูล', 'success');
      const userData = getUserData() || {};
      userData.must_change_password = false;
      setUserData(userData);
      showPage('config');
    } else {
      const msg = result?.message || 'ไม่สามารถเปลี่ยนรหัสผ่านได้';
      errorDiv.textContent = msg;
      errorDiv.classList.remove('hidden');
    }
  } catch {
    hideLoading();
    errorDiv.textContent = 'เกิดข้อผิดพลาดในการเปลี่ยนรหัสผ่าน';
    errorDiv.classList.remove('hidden');
  }
}

/**
 * Check if user is authenticated
 * Returns true if token exists
 */
function checkAuth() {
  const token = getToken();
  if (!token) return false;

  // Check token expiry (JWT decode)
  try {
    const parts = token.split('.');
    if (parts.length === 3) {
      const payload = JSON.parse(atob(parts[1]));
      if (payload.exp) {
        const now = Math.floor(Date.now() / 1000);
        if (payload.exp < now) {
          removeToken();
          removeUserData();
          return false;
        }
      }
    }
  } catch {
    // If token can't be decoded, still consider it valid
    // The server will reject it if it's invalid
  }

  return true;
}

/**
 * Toggle password visibility
 */
function togglePassword(btn) {
  const wrapper = btn.closest('.input-wrapper');
  const input = wrapper.querySelector('input');

  if (input.type === 'password') {
    input.type = 'text';
    btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/></svg>`;
  } else {
    input.type = 'password';
    btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/></svg>`;
  }
}
