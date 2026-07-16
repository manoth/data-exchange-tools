// PERSON death-status audit against API Center.
let deathAuditFilter = 'all';
let deathAuditPage = 1;
let deathAuditPageSize = 20;
let deathAuditPollTimer = null;
let deathAuditSearchTimer = null;
let deathAuditSortColumn = '';
let deathAuditSortDirection = 'asc';

function initDeathAudit() {
  loadDeathAuditResults();
}

function setDeathAuditView(state = {}) {
  const hasStarted = state.status && state.status !== 'idle';
  const emptyState = document.getElementById('death-audit-empty');
  const results = document.getElementById('death-audit-results');
  const runButton = document.getElementById('death-audit-run');
  emptyState?.classList.toggle('hidden', hasStarted);
  results?.classList.toggle('hidden', !hasStarted);
  runButton?.classList.toggle('hidden', !hasStarted);
}

async function startDeathAudit() {
  const button = document.getElementById('death-audit-run');
  if (button) button.disabled = true;
  setDeathAuditView({ status: 'starting' });
  showDeathAuditLoading('กำลังเตรียมข้อมูล PERSON จาก HIS...');
  const result = await api('/api/death-audit/start', { method: 'POST' });
  if (result?.success) {
    showToast('เริ่มตรวจสอบข้อมูลแล้ว', 'success');
    deathAuditPage = 1;
    loadDeathAuditResults();
  } else if (button) {
    button.disabled = false;
    hideDeathAuditLoading();
  }
}

async function loadDeathAuditResults() {
  const search = document.getElementById('death-audit-search')?.value || '';
  const query = new URLSearchParams({
    result_filter: deathAuditFilter, search,
    page: String(deathAuditPage), page_size: String(deathAuditPageSize),
    sort_by: deathAuditSortColumn, sort_direction: deathAuditSortDirection
  });
  const result = await api(`/api/death-audit/results?${query}`);
  if (!result?.success) {
    hideDeathAuditLoading();
    return;
  }

  setDeathAuditView(result.state || {});
  updateDeathAuditSummary(result);
  renderDeathAuditRows(result.rows || []);
  renderDeathAuditPagination(result.filtered_count || 0);
  updateDeathAuditSortHeaders();

  clearTimeout(deathAuditPollTimer);
  if (['starting', 'running'].includes(result.state?.status)) {
    showDeathAuditLoading(deathAuditProgressText(result.state));
    deathAuditPollTimer = setTimeout(loadDeathAuditResults, 1200);
  } else {
    hideDeathAuditLoading();
    if (result.state?.status === 'error') {
      showSweetAlert({
        type: 'error',
        title: 'ตรวจสอบข้อมูลไม่สำเร็จ',
        message: result.state.message || 'ไม่สามารถเชื่อมต่อ HIS หรือ API Center ได้'
      });
    }
  }
}

function deathAuditProgressText(state = {}) {
  if (!state.total) return state.message || 'กำลังอ่านข้อมูล PERSON จาก HIS...';
  return `กำลังเทียบข้อมูลการเสียชีวิต ${formatNumber(state.processed || 0)} / ${formatNumber(state.total)} คน`;
}

function showDeathAuditLoading(message) {
  showLoading();
  const text = document.querySelector('#loading-overlay .loading-content p');
  if (text) text.textContent = message || 'กำลังตรวจสอบข้อมูล...';
}

function hideDeathAuditLoading() {
  hideLoading();
  const text = document.querySelector('#loading-overlay .loading-content p');
  if (text) text.textContent = 'กำลังดำเนินการ...';
}

function updateDeathAuditSummary(result) {
  const counts = result.counts || {};
  document.getElementById('death-count-all').textContent = formatNumber(counts.all || 0);
  document.getElementById('death-count-alive').textContent = formatNumber(counts.alive || 0);
  document.getElementById('death-count-deceased').textContent = formatNumber(counts.deceased || 0);

  const state = result.state || {};
  const notice = document.getElementById('death-audit-notice');
  const runButton = document.getElementById('death-audit-run');
  if (runButton) runButton.disabled = ['starting', 'running'].includes(state.status);
  if (notice) {
    notice.classList.toggle('hidden', !['starting', 'running', 'error'].includes(state.status));
    notice.className = `connection-status ${state.status === 'error' ? 'error' : 'checking'}${notice.classList.contains('hidden') ? ' hidden' : ''}`;
    notice.textContent = state.status === 'error'
      ? `ตรวจสอบไม่สำเร็จ: ${state.message || 'ไม่สามารถเชื่อมต่อ API Center'}`
      : `กำลังตรวจสอบ ${formatNumber(state.processed || 0)} / ${formatNumber(state.total || 0)} รายการ`;
  }
  const info = document.getElementById('death-audit-info');
  if (info) info.textContent = `ทั้งหมด ${formatNumber(counts.all || 0)} คน | แสดงผลหลังกรอง ${formatNumber(result.filtered_count || 0)} คน`;
}

function renderDeathAuditRows(rows) {
  const body = document.getElementById('death-audit-tbody');
  if (!body) return;
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="8"><div class="empty-state"><p>ไม่พบข้อมูลตามเงื่อนไข</p></div></td></tr>';
    return;
  }
  body.innerHTML = rows.map(row => `
    <tr>
      <td class="center-cell">${escapeHtml(row.PERSON_CID || '-')}</td>
      <td class="center-cell">${escapeHtml(row.PID || '-')}</td>
      <td>${escapeHtml(row.FULL_NAME || '-')}</td>
      <td class="center-cell">${escapeHtml(formatSex(row.SEX))}</td>
      <td class="center-cell">${escapeHtml(row.BIRTH || '-')}</td>
      <td class="center-cell">${escapeHtml(row.AGE ?? '-')}</td>
      <td class="center-cell"><span class="audit-pill audit-pill-alive">${escapeHtml(row.HIS_STATUS || '-')}</span></td>
      <td class="center-cell"><span class="audit-pill ${row.CENTRAL_STATUS === 'พบว่าเสียชีวิตแล้ว' ? 'audit-pill-deceased' : 'audit-pill-clear'}">${escapeHtml(row.CENTRAL_STATUS || '-')}</span></td>
    </tr>`).join('');
}

function setDeathAuditFilter(filter) {
  deathAuditFilter = filter;
  deathAuditPage = 1;
  document.querySelectorAll('[data-audit-filter]').forEach(card => card.classList.toggle('active', card.dataset.auditFilter === filter));
  loadDeathAuditResults();
}

function queueDeathAuditSearch() {
  clearTimeout(deathAuditSearchTimer);
  deathAuditSearchTimer = setTimeout(() => { deathAuditPage = 1; loadDeathAuditResults(); }, 300);
}

function changeDeathAuditPageSize(value) {
  deathAuditPageSize = Number(value) || 20;
  deathAuditPage = 1;
  loadDeathAuditResults();
}

function setDeathAuditSort(column) {
  if (deathAuditSortColumn === column) {
    deathAuditSortDirection = deathAuditSortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    deathAuditSortColumn = column;
    deathAuditSortDirection = 'asc';
  }
  deathAuditPage = 1;
  updateDeathAuditSortHeaders();
  loadDeathAuditResults();
}

function updateDeathAuditSortHeaders() {
  document.querySelectorAll('[data-audit-sort]').forEach(header => {
    const active = header.dataset.auditSort === deathAuditSortColumn;
    const indicator = header.querySelector('.sort-indicator');
    if (indicator) indicator.textContent = active
      ? (deathAuditSortDirection === 'asc' ? ' ▲' : ' ▼')
      : '';
    header.classList.toggle('sorted', active);
    header.setAttribute('aria-sort', active
      ? (deathAuditSortDirection === 'asc' ? 'ascending' : 'descending')
      : 'none');
  });
}

function renderDeathAuditPagination(total) {
  const container = document.getElementById('death-audit-pagination');
  if (!container) return;
  const pages = Math.ceil(total / deathAuditPageSize);
  if (pages <= 1) { container.innerHTML = ''; return; }
  const start = Math.max(1, deathAuditPage - 2);
  const end = Math.min(pages, start + 4);
  let html = `<button class="page-btn" ${deathAuditPage === 1 ? 'disabled' : ''} onclick="goDeathAuditPage(${deathAuditPage - 1})">‹</button>`;
  for (let page = start; page <= end; page += 1) {
    html += `<button class="page-btn ${page === deathAuditPage ? 'active' : ''}" onclick="goDeathAuditPage(${page})">${page}</button>`;
  }
  html += `<button class="page-btn" ${deathAuditPage === pages ? 'disabled' : ''} onclick="goDeathAuditPage(${deathAuditPage + 1})">›</button>`;
  container.innerHTML = html;
}

function goDeathAuditPage(page) {
  deathAuditPage = Math.max(1, page);
  loadDeathAuditResults();
}

async function exportDeathAudit(scope) {
  const response = await api('/api/death-audit/export', {
    method: 'POST',
    body: JSON.stringify({
      scope, result_filter: deathAuditFilter,
      search: document.getElementById('death-audit-search')?.value || ''
    })
  });
  if (!response) return;
  if (!(response instanceof Response)) {
    showSweetAlert({ type: 'warning', title: 'ส่งออกไม่สำเร็จ', message: response.detail || response.message || 'ไม่พบข้อมูลสำหรับส่งออก' });
    return;
  }
  const blob = await response.blob();
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `death_status_audit_${scope}.xlsx`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('th-TH');
}
