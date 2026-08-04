// Dedicated PERSON -> central death API -> OVST post-death audit.
let deceasedServicePage = 1;
let deceasedServicePageSize = 20;
let deceasedServicePollTimer = null;
let deceasedServiceSearchTimer = null;

function openDeceasedServiceReport() {
  activeDataQualityReport = deceasedServiceReport;
  document.getElementById('data-quality-report-list')?.classList.add('hidden');
  document.getElementById('data-quality-report-detail')?.classList.add('hidden');
  document.getElementById('deceased-service-report')?.classList.remove('hidden');
  document.getElementById('data-quality-back')?.classList.remove('hidden');
  document.getElementById('data-quality-store')?.classList.add('hidden');
  document.getElementById('data-quality-title').textContent = deceasedServiceReport.reportName;
  document.getElementById('data-quality-description').textContent = deceasedServiceReport.description;
  loadDeceasedServiceResults();
}

function setDeceasedServiceView(state = {}) {
  const hasStarted = state.status && state.status !== 'idle';
  document.getElementById('deceased-service-empty')?.classList.toggle('hidden', hasStarted);
  document.getElementById('deceased-service-results')?.classList.toggle('hidden', !hasStarted);
}

async function startDeceasedServiceAudit() {
  const button = document.getElementById('deceased-service-run');
  if (button) button.disabled = true;
  setDeceasedServiceView({ status: 'starting' });
  showDeceasedServiceLoading('กำลังเตรียมข้อมูล PERSON จาก HIS...');
  const result = await api('/api/deceased-service-audit/start', { method: 'POST' });
  if (result?.success) {
    deceasedServicePage = 1;
    showToast('เริ่มตรวจสอบข้อมูลแล้ว', 'success');
    loadDeceasedServiceResults();
  } else {
    if (button) button.disabled = false;
    hideDeceasedServiceLoading();
  }
}

async function loadDeceasedServiceResults() {
  const query = new URLSearchParams({
    search: document.getElementById('deceased-service-search')?.value || '',
    page: String(deceasedServicePage),
    page_size: String(deceasedServicePageSize)
  });
  const result = await api(`/api/deceased-service-audit/results?${query}`);
  if (!result?.success) {
    hideDeceasedServiceLoading();
    return;
  }
  setDeceasedServiceView(result.state || {});
  updateDeceasedServiceSummary(result);
  renderDeceasedServiceRows(result.rows || []);
  renderDeceasedServicePagination(result.filtered_count || 0);

  clearTimeout(deceasedServicePollTimer);
  if (['starting', 'running'].includes(result.state?.status)) {
    const state = result.state || {};
    const message = state.total
      ? `${state.message || 'กำลังตรวจสอบ'} ${formatNumber(state.processed || 0)} / ${formatNumber(state.total)} คน`
      : (state.message || 'กำลังเตรียมข้อมูล...');
    showDeceasedServiceLoading(message);
    deceasedServicePollTimer = setTimeout(loadDeceasedServiceResults, 1200);
  } else {
    hideDeceasedServiceLoading();
    if (result.state?.status === 'error') {
      showSweetAlert({ type: 'error', title: 'ตรวจสอบข้อมูลไม่สำเร็จ', message: result.state.message || 'ไม่สามารถเชื่อมต่อ HIS หรือ API Center ได้' });
    }
  }
}

function updateDeceasedServiceSummary(result) {
  const state = result.state || {};
  const counts = result.counts || {};
  document.getElementById('deceased-service-people-count').textContent = formatNumber(counts.people || 0);
  document.getElementById('deceased-service-visit-count').textContent = formatNumber(counts.services || 0);
  document.getElementById('deceased-service-target-count').textContent = formatNumber(state.target_count || 0);
  const info = document.getElementById('deceased-service-info');
  if (info) info.textContent = `ทั้งหมด ${formatNumber(counts.people || 0)} คน | แสดงผลหลังค้นหา ${formatNumber(result.filtered_count || 0)} คน`;
  const runButton = document.getElementById('deceased-service-run');
  if (runButton) runButton.disabled = ['starting', 'running'].includes(state.status);
  const notice = document.getElementById('deceased-service-notice');
  if (notice) {
    const visible = ['starting', 'running', 'error'].includes(state.status) || Number(state.missing_death_date_count || 0) > 0;
    notice.className = `connection-status ${state.status === 'error' ? 'error' : 'checking'}${visible ? '' : ' hidden'}`;
    notice.textContent = state.status === 'error'
      ? `ตรวจสอบไม่สำเร็จ: ${state.message || 'เกิดข้อผิดพลาด'}`
      : Number(state.missing_death_date_count || 0) > 0 && state.status === 'completed'
        ? `พบ CID ในฐานการตาย ${formatNumber(state.missing_death_date_count)} คนที่ไม่มีวันที่ตาย จึงไม่นำมาตรวจบริการหลังตาย`
        : `${state.message || 'กำลังตรวจสอบ'} ${formatNumber(state.processed || 0)} / ${formatNumber(state.total || 0)} คน`;
  }
}

function renderDeceasedServiceRows(rows) {
  const body = document.getElementById('deceased-service-tbody');
  if (!body) return;
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="9"><div class="empty-state"><p>ไม่พบผู้ที่มารับบริการหลังวันที่ตาย</p></div></td></tr>';
    return;
  }
  body.innerHTML = rows.map(row => `
    <tr>
      <td class="center-cell">${escapeHtml(row.PERSON_CID || '-')}</td>
      <td><strong>${escapeHtml(row.PID || '-')}</strong><br><small class="text-secondary">HN ${escapeHtml(row.HN || '-')}</small></td>
      <td>${escapeHtml(row.FULL_NAME || '-')}</td>
      <td class="center-cell"><span class="audit-pill audit-pill-deceased">${escapeHtml(row.DEATH_DATE || '-')}</span></td>
      <td class="center-cell">${escapeHtml(row.DEATH_CAUSE || '-')}</td>
      <td class="center-cell"><strong>${formatNumber(row.SERVICE_COUNT || 0)}</strong> ครั้ง</td>
      <td class="center-cell">${escapeHtml(row.FIRST_SERVICE_DATE || '-')}</td>
      <td class="center-cell">${escapeHtml(row.LAST_SERVICE_DATE || '-')}</td>
      <td class="center-cell"><button type="button" class="btn btn-outline deceased-service-detail-button" onclick="openDeceasedServiceDetail('${escapeHtml(row.PERSON_CID || '')}')">ดูรายละเอียด</button></td>
    </tr>`).join('');
}

function queueDeceasedServiceSearch() {
  clearTimeout(deceasedServiceSearchTimer);
  deceasedServiceSearchTimer = setTimeout(() => { deceasedServicePage = 1; loadDeceasedServiceResults(); }, 300);
}

function changeDeceasedServicePageSize(value) {
  deceasedServicePageSize = Number(value) || 20;
  deceasedServicePage = 1;
  loadDeceasedServiceResults();
}

function renderDeceasedServicePagination(total) {
  const container = document.getElementById('deceased-service-pagination');
  if (!container) return;
  const pages = Math.ceil(total / deceasedServicePageSize);
  if (pages <= 1) { container.innerHTML = ''; return; }
  const start = Math.max(1, deceasedServicePage - 2);
  const end = Math.min(pages, start + 4);
  let html = `<button class="page-btn" ${deceasedServicePage === 1 ? 'disabled' : ''} onclick="goDeceasedServicePage(${deceasedServicePage - 1})">‹</button>`;
  for (let page = start; page <= end; page += 1) html += `<button class="page-btn ${page === deceasedServicePage ? 'active' : ''}" onclick="goDeceasedServicePage(${page})">${page}</button>`;
  html += `<button class="page-btn" ${deceasedServicePage === pages ? 'disabled' : ''} onclick="goDeceasedServicePage(${deceasedServicePage + 1})">›</button>`;
  container.innerHTML = html;
}

function goDeceasedServicePage(page) {
  deceasedServicePage = Math.max(1, page);
  loadDeceasedServiceResults();
}

async function openDeceasedServiceDetail(cid) {
  const result = await api(`/api/deceased-service-audit/person/${encodeURIComponent(cid)}`);
  if (!result?.success) return;
  const person = result.person || {};
  document.getElementById('deceased-service-person-summary').textContent = `${person.FULL_NAME || '-'} · CID ${person.PERSON_CID || '-'} · วันที่ตาย ${person.DEATH_DATE || '-'} · สาเหตุ ${person.DEATH_CAUSE || '-'}`;
  const body = document.getElementById('deceased-service-detail-tbody');
  if (body) body.innerHTML = (result.services || []).map(service => `
    <tr><td class="center-cell">${escapeHtml(service.SERVICE_DATE || '-')}</td><td class="center-cell">${escapeHtml(service.SERVICE_TIME || '-')}</td><td class="center-cell">${escapeHtml(service.HN || '-')}</td><td class="center-cell">${escapeHtml(service.VN || '-')}</td><td class="center-cell">${formatNumber(service.DAYS_AFTER_DEATH || 0)} วัน</td></tr>`).join('');
  document.getElementById('deceased-service-modal')?.classList.remove('hidden');
}

function closeDeceasedServiceModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('deceased-service-modal')?.classList.add('hidden');
  document.getElementById('deceased-service-person-summary').textContent = '';
  document.getElementById('deceased-service-detail-tbody').innerHTML = '';
}

function showDeceasedServiceLoading(message) {
  showLoading();
  const text = document.querySelector('#loading-overlay .loading-content p');
  if (text) text.textContent = message || 'กำลังตรวจสอบข้อมูล...';
}

function hideDeceasedServiceLoading() {
  hideLoading();
  const text = document.querySelector('#loading-overlay .loading-content p');
  if (text) text.textContent = 'กำลังดำเนินการ...';
}
