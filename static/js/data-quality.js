let dataQualityReports = [];
let dataQualityReportCatalog = [];
let dataQualityReportsLoaded = false;
let activeDataQualityReport = null;
let dataQualityPage = 1;
let dataQualityPageSize = 20;
let dataQualitySortBy = '';
let dataQualitySortDirection = 'asc';
let dataQualitySearchTimer = null;
let dataQualityStatusFilter = 'all';
let dataQualityAbnormalFilter = 'all';
let dataQualitySummary = { total: 0, normal: 0, abnormal: 0, weight_abnormal: 0, height_abnormal: 0, both_abnormal: 0 };
let dataQualityLoadingCount = 0;
const deceasedServiceReportCode = 'deceased-service-after-death';
const deceasedServiceReport = {
  reportCode: deceasedServiceReportCode,
  reportName: 'ตายแล้วมารับบริการ',
  category: 'ข้อมูลบุคคลและบริการ',
  description: 'เทียบ PERSON กับ API การตาย แล้วตรวจการรับบริการหลังวันที่ตายแบบกลุ่มรายบุคคล'
};

const dataQualityAbnormalGroupFallbacks = {
  'abnormal-weight-height': [
    { value: 'weight', label: 'น้ำหนักผิดปกติ', matches: ['weight', 'both'] },
    { value: 'height', label: 'ส่วนสูงผิดปกติ', matches: ['height', 'both'] },
    { value: 'both', label: 'ผิดปกติทั้งสองค่า', matches: ['both'] }
  ],
  'living-person-basic-invalid': [
    { value: 'cid_invalid', label: 'CID ผิดปกติ' },
    { value: 'name_invalid', label: 'ชื่อไม่ครบ/ไม่สมเหตุสมผล' },
    { value: 'sex_invalid', label: 'เพศผิดปกติ' },
    { value: 'birth_invalid', label: 'วันเกิด/อายุผิดปกติ' },
    { value: 'patient_link_invalid', label: 'ไม่พบ HN ใน PATIENT' },
    { value: 'death_conflict', label: 'สถานะเสียชีวิตขัดแย้ง' }
  ],
  'living-person-patient-conflict': [
    { value: 'patient_missing', label: 'ไม่พบ PATIENT' },
    { value: 'cid_conflict', label: 'CID ขัดแย้ง' },
    { value: 'name_conflict', label: 'ชื่อขัดแย้ง' },
    { value: 'sex_conflict', label: 'เพศขัดแย้ง' },
    { value: 'birthdate_conflict', label: 'วันเกิดขัดแย้ง' },
    { value: 'death_conflict', label: 'สถานะเสียชีวิตขัดแย้ง' }
  ],
  'living-person-found-death': [
    { value: 'death_file_found', label: 'พบในแฟ้ม DEATH' },
    { value: 'patient_death_conflict', label: 'PATIENT ระบุเสียชีวิต' },
    { value: 'person_death_date_conflict', label: 'PERSON มีวันเสียชีวิต' },
    { value: 'death_date_conflict', label: 'วันที่เสียชีวิตขัดแย้ง' }
  ]
};

async function initDataQualityReports() {
  if (dataQualityReportsLoaded) return;
  const container = document.getElementById('data-quality-report-list');
  if (!container) return;
  showDataQualityLoading('กำลังโหลดรายการรายงานจาก Control...');
  try {
    const result = await api('/api/data-quality/reports');
    if (!result?.success) {
      dataQualityReportCatalog = [];
      dataQualityReportsLoaded = true;
      rebuildInstalledDataQualityReports();
      renderDataQualityReportList();
      const notice = document.getElementById('data-quality-notice');
      if (notice) {
        notice.textContent = result?.detail || 'ไม่สามารถโหลดรายงานจาก Control ได้ แต่ยังใช้รายงานภายในเครื่องได้';
        notice.classList.remove('hidden');
      }
      return;
    }
    dataQualityReportCatalog = result.reports || [];
    dataQualityReportsLoaded = true;
    rebuildInstalledDataQualityReports();
    renderDataQualityReportList();
  } finally {
    hideDataQualityLoading();
  }
}

function dataQualityStorePreferenceKey() {
  const username = String(getUserData()?.username || 'default').trim() || 'default';
  return `dex_data_quality_optional_reports:${username}`;
}

function getSelectedOptionalDataQualityReports() {
  try {
    const value = JSON.parse(localStorage.getItem(dataQualityStorePreferenceKey()) || '[]');
    return Array.isArray(value) ? value.map(String) : [];
  } catch (_) {
    return [];
  }
}

function rebuildInstalledDataQualityReports() {
  const selected = new Set(getSelectedOptionalDataQualityReports());
  dataQualityReports = dataQualityReportCatalog.filter(report =>
    report.publicationMode !== 'optional' || selected.has(String(report.reportCode))
  );
}

function openDataQualityReportStore() {
  const modal = document.getElementById('data-quality-store-modal');
  if (!modal) return;
  renderDataQualityReportStore();
  modal.classList.remove('hidden');
}

function closeDataQualityReportStore(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('data-quality-store-modal')?.classList.add('hidden');
}

function renderDataQualityReportStore() {
  const container = document.getElementById('data-quality-store-list');
  if (!container) return;
  const optionalReports = dataQualityReportCatalog.filter(report => report.publicationMode === 'optional');
  const selected = new Set(getSelectedOptionalDataQualityReports());
  if (!optionalReports.length) {
    container.innerHTML = '<div class="empty-state report-store-empty"><p>ยังไม่มีรายงานทางเลือกที่ Control เผยแพร่</p></div>';
    return;
  }
  container.innerHTML = optionalReports.map(report => {
    const checked = selected.has(String(report.reportCode));
    return `<label class="report-store-item">
      <input type="checkbox" data-optional-report-code="${escapeHtml(report.reportCode)}" ${checked ? 'checked' : ''}>
      <span class="report-store-check">${checked ? '✓' : ''}</span>
      <span class="report-store-content"><small>${escapeHtml(report.category || 'คุณภาพข้อมูล')}</small><strong>${escapeHtml(report.reportName)}</strong><span>${escapeHtml(report.description || '')}</span></span>
    </label>`;
  }).join('');
  container.querySelectorAll('[data-optional-report-code]').forEach(input => {
    input.addEventListener('change', () => toggleOptionalDataQualityReport(input.dataset.optionalReportCode, input.checked));
  });
}

function toggleOptionalDataQualityReport(code, enabled) {
  const selected = new Set(getSelectedOptionalDataQualityReports());
  if (enabled) selected.add(String(code)); else selected.delete(String(code));
  localStorage.setItem(dataQualityStorePreferenceKey(), JSON.stringify([...selected]));
  rebuildInstalledDataQualityReports();
  renderDataQualityReportList();
  renderDataQualityReportStore();
}

function renderDataQualityReportList() {
  const container = document.getElementById('data-quality-report-list');
  if (!container) return;
  const visibleReports = [...dataQualityReports, deceasedServiceReport];
  container.innerHTML = visibleReports.map(report => `
    <button type="button" class="data-quality-report-card glass-card" data-report-code="${escapeHtml(report.reportCode)}">
      <span class="data-quality-card-icon"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19V9"/><path d="M10 19V5"/><path d="M16 19v-7"/><path d="M22 19V3"/></svg></span>
      <span class="data-quality-card-content"><small>${escapeHtml(report.category || 'คุณภาพข้อมูล')}${report.publicationMode === 'optional' ? ' · รายงานทางเลือก' : ''}</small><strong>${escapeHtml(report.reportName)}</strong><span>${escapeHtml(report.description || '')}</span></span>
      <span class="data-quality-card-arrow">›</span>
    </button>`).join('');
  container.querySelectorAll('[data-report-code]').forEach(button => {
    button.addEventListener('click', () => openDataQualityReport(button.dataset.reportCode));
  });
}

function openDataQualityReport(code) {
  if (code === deceasedServiceReportCode) {
    openDeceasedServiceReport();
    return;
  }
  activeDataQualityReport = dataQualityReports.find(item => item.reportCode === code);
  if (!activeDataQualityReport) return;
  dataQualityPage = 1;
  dataQualityStatusFilter = 'all';
  dataQualityAbnormalFilter = 'all';
  const initialSort = activeDataQualityReport.defaultSort || {};
  dataQualitySortBy = initialSort.field || '';
  dataQualitySortDirection = initialSort.direction === 'desc' ? 'desc' : 'asc';
  resetDataQualityResultState();
  document.getElementById('data-quality-report-list')?.classList.add('hidden');
  document.getElementById('data-quality-report-detail')?.classList.remove('hidden');
  document.getElementById('data-quality-back')?.classList.remove('hidden');
  document.getElementById('data-quality-store')?.classList.add('hidden');
  document.getElementById('data-quality-title').textContent = activeDataQualityReport.reportName;
  document.getElementById('data-quality-description').textContent = activeDataQualityReport.description || '';
  const normalDescription = document.querySelector('.data-quality-card-normal .result-filter-desc');
  if (normalDescription) normalDescription.textContent = 'ข้อมูลอยู่ในเกณฑ์ที่กำหนด';
  renderDataQualityCriteria();
  document.getElementById('data-quality-export')?.classList.toggle('hidden', !activeDataQualityReport.allowExport);
  renderDataQualityFilters();
  renderDataQualityAbnormalTabs();
  syncDataQualityAbnormalControls();
  applyDefaultDataQualityDateRange();
  runDataQualityReport(true, true);
}

function resetDataQualityResultState() {
  dataQualitySummary = { total: 0, normal: 0, abnormal: 0, weight_abnormal: 0, height_abnormal: 0, both_abnormal: 0 };
  ['all', 'normal', 'abnormal'].forEach(key => {
    const element = document.getElementById(`data-quality-count-${key}`);
    if (element) element.textContent = '0';
  });
  const info = document.getElementById('data-quality-info');
  if (info) info.textContent = 'กำลังเตรียมข้อมูลรายงาน...';
  const pagination = document.getElementById('data-quality-pagination');
  if (pagination) pagination.innerHTML = '';
}

function renderDataQualityCriteria() {
  const panel = document.getElementById('data-quality-criteria');
  const content = document.getElementById('data-quality-criteria-text');
  if (!panel || !content) return;
  const fallback = activeDataQualityReport?.reportCode === 'abnormal-weight-height'
    ? `• ใช้ข้อมูล OPDSCREEN วันที่รับบริการล่าสุดของแต่ละ HN และ VN ล่าสุดเมื่อมีหลายรายการในวันเดียวกัน\n• ตรวจเฉพาะบุคคลที่มีข้อมูลใน PERSON และ PERSON.DEATH = 'N'\n• อายุต่ำกว่า 2 ปี: น้ำหนัก 0.5–30 กก. และส่วนสูง 20–120 ซม.\n• อายุ 2–17 ปี: น้ำหนัก 5–200 กก. และส่วนสูง 40–220 ซม.\n• อายุ 18 ปีขึ้นไป: น้ำหนัก 20–300 กก. และส่วนสูง 100–250 ซม.\nค่าที่อยู่นอกช่วงตามอายุจะถูกจัดเป็นข้อมูลผิดปกติ`
    : '';
  const criteria = String(activeDataQualityReport?.criteriaDescription || fallback).trim();
  content.textContent = criteria;
  panel.classList.toggle('hidden', !criteria);
  const details = document.getElementById('data-quality-criteria-content');
  const toggle = document.getElementById('data-quality-criteria-toggle');
  details?.classList.add('hidden');
  toggle?.classList.remove('expanded');
  toggle?.setAttribute('aria-expanded', 'false');
}

function toggleDataQualityCriteria() {
  const details = document.getElementById('data-quality-criteria-content');
  const toggle = document.getElementById('data-quality-criteria-toggle');
  if (!details || !toggle) return;
  const expanded = toggle.getAttribute('aria-expanded') === 'true';
  details.classList.toggle('hidden', expanded);
  toggle.classList.toggle('expanded', !expanded);
  toggle.setAttribute('aria-expanded', String(!expanded));
}

function showDataQualityReportList() {
  activeDataQualityReport = null;
  document.getElementById('data-quality-report-list')?.classList.remove('hidden');
  document.getElementById('data-quality-report-detail')?.classList.add('hidden');
  document.getElementById('deceased-service-report')?.classList.add('hidden');
  document.getElementById('data-quality-back')?.classList.add('hidden');
  document.getElementById('data-quality-store')?.classList.remove('hidden');
  document.getElementById('data-quality-title').textContent = 'ตรวจสอบคุณภาพข้อมูล';
  document.getElementById('data-quality-description').textContent = 'เลือกรายงานเพื่อตรวจข้อมูลผิดปกติหรือขัดแย้งใน HIS';
}

function renderDataQualityFilters() {
  const panel = document.getElementById('data-quality-filters');
  const showDateFilters = activeDataQualityReport?.showDateFilters !== false;
  const filters = (activeDataQualityReport?.filters || []).filter(filter =>
    filter.type !== 'hidden'
    && filter.operator !== 'abnormal_group'
    && (showDateFilters || filter.type !== 'date')
  );
  panel.classList.remove('hidden');
  const heading = filters.length ? 'ตัวกรองรายงาน' : 'ข้อมูลรายงาน';
  const description = filters.length ? 'ปรับเงื่อนไขแล้วดึงข้อมูลชุดใหม่จาก HIS' : 'ดึงข้อมูลล่าสุดจาก HIS และสร้าง Cache ใหม่';
  panel.classList.toggle('data-quality-filter-panel-compact', !filters.length);
  panel.innerHTML = `<div class="data-quality-filter-heading"><div><strong>${heading}</strong><span>${description}</span></div><button class="btn btn-primary" type="button" onclick="applyDataQualityFilters()"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 5v4h4"/><path d="M4 13a8.1 8.1 0 0 0 15.5 2M20 19v-4h-4"/></svg>ดึงข้อมูลใหม่</button></div>${filters.length ? `<div class="data-quality-filter-grid">${filters.map(filter => {
    const id = `dq-filter-${filter.name}`;
    if (filter.type === 'select') {
      const abnormalChange = filter.operator === 'abnormal_group' ? ' onchange="syncDataQualityAbnormalSelect(this.value)"' : '';
      return `<label><span>${escapeHtml(filter.label)}</span><select id="${id}"${abnormalChange}><option value="">ทั้งหมด</option>${(filter.options || []).map(option => `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`).join('')}</select></label>`;
    }
    return `<label><span>${escapeHtml(filter.label)}</span><input id="${id}" type="${filter.type === 'date' ? 'date' : 'text'}"></label>`;
  }).join('')}</div>` : ''}`;
}

function applyDefaultDataQualityDateRange() {
  const months = Math.max(0, Number(activeDataQualityReport?.defaultDateRangeMonths ?? 3));
  const today = new Date();
  const startInput = document.getElementById('dq-filter-start_date');
  const endInput = document.getElementById('dq-filter-end_date');
  const mode = activeDataQualityReport?.defaultDateMode
    || (activeDataQualityReport?.reportCode === 'abnormal-weight-height' ? 'fiscal_year' : 'rolling_months');
  const exactStart = /^\d{4}-\d{2}-\d{2}$/.test(activeDataQualityReport?.defaultStartDate || '') ? activeDataQualityReport.defaultStartDate : '';
  const exactEnd = /^\d{4}-\d{2}-\d{2}$/.test(activeDataQualityReport?.defaultEndDate || '') ? activeDataQualityReport.defaultEndDate : '';
  if (mode === 'fiscal_year') {
    const startYear = today.getMonth() >= 9 ? today.getFullYear() : today.getFullYear() - 1;
    if (startInput) startInput.value = `${startYear}-10-01`;
    if (endInput) endInput.value = `${startYear + 1}-09-30`;
    return;
  }
  if (mode === 'date_range') {
    if (startInput) startInput.value = exactStart;
    if (endInput) endInput.value = exactEnd;
    return;
  }
  if (startInput && exactStart) startInput.value = exactStart;
  else if (startInput && months) {
    const originalDay = today.getDate();
    const start = new Date(today.getFullYear(), today.getMonth() - months, 1);
    const lastDay = new Date(start.getFullYear(), start.getMonth() + 1, 0).getDate();
    start.setDate(Math.min(originalDay, lastDay));
    startInput.value = formatDataQualityDate(start);
  }
  if (endInput) endInput.value = exactEnd || formatDataQualityDate(today);
}

function formatDataQualityDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function collectDataQualityFilters() {
  const values = {};
  (activeDataQualityReport?.filters || []).filter(filter => filter.type !== 'hidden').forEach(filter => {
    const value = document.getElementById(`dq-filter-${filter.name}`)?.value || '';
    if (value) values[filter.name] = value;
  });
  if (dataQualityStatusFilter !== 'all') values.quality_status = dataQualityStatusFilter;
  if (dataQualityStatusFilter === 'abnormal' && dataQualityAbnormalFilter !== 'all') values.abnormal_group = dataQualityAbnormalFilter;
  return values;
}

function setDataQualityStatus(value) {
  dataQualityStatusFilter = value;
  if (value !== 'abnormal') dataQualityAbnormalFilter = 'all';
  syncDataQualityAbnormalControls();
  document.querySelectorAll('[data-quality-status]').forEach(button => button.classList.toggle('active', button.dataset.qualityStatus === value));
  document.getElementById('data-quality-abnormal-tabs')?.classList.toggle('hidden', value !== 'abnormal' || !supportsDataQualityAbnormalGroups());
  dataQualityPage = 1; runDataQualityReport(false);
}

function setDataQualityAbnormalFilter(value) {
  const allowed = getDataQualityAbnormalOptions().map(option => String(option.value));
  dataQualityAbnormalFilter = allowed.includes(String(value)) ? String(value) : 'all';
  if (dataQualityAbnormalFilter !== 'all') dataQualityStatusFilter = 'abnormal';
  syncDataQualityAbnormalControls();
  dataQualityPage = 1; runDataQualityReport(false);
}

function syncDataQualityAbnormalSelect(value) {
  setDataQualityAbnormalFilter(value || 'all');
}

function syncDataQualityAbnormalControls() {
  document.querySelectorAll('[data-quality-status]').forEach(button => button.classList.toggle('active', button.dataset.qualityStatus === dataQualityStatusFilter));
  document.getElementById('data-quality-abnormal-tabs')?.classList.toggle('hidden', dataQualityStatusFilter !== 'abnormal' || !supportsDataQualityAbnormalGroups());
  document.querySelectorAll('[data-quality-abnormal]').forEach(button => button.classList.toggle('active', button.dataset.qualityAbnormal === dataQualityAbnormalFilter));
  const abnormalSelect = (activeDataQualityReport?.filters || []).find(filter => filter.operator === 'abnormal_group');
  const select = abnormalSelect ? document.getElementById(`dq-filter-${abnormalSelect.name}`) : null;
  if (select) select.value = dataQualityAbnormalFilter === 'all' ? '' : dataQualityAbnormalFilter;
}

function supportsDataQualityAbnormalGroups() {
  return getDataQualityAbnormalOptions().length > 0;
}

function getDataQualityAbnormalOptions() {
  const filter = (activeDataQualityReport?.filters || []).find(item => item.operator === 'abnormal_group' || item.name === 'abnormal_group');
  const configured = Array.isArray(filter?.options)
    ? filter.options.filter(option => option && String(option.value || '').trim())
    : [];
  if (configured.length) return configured;
  return dataQualityAbnormalGroupFallbacks[activeDataQualityReport?.reportCode] || [];
}

function renderDataQualityAbnormalTabs() {
  const container = document.getElementById('data-quality-abnormal-tabs');
  if (!container) return;
  const options = getDataQualityAbnormalOptions();
  container.innerHTML = options.length ? `
    <button type="button" class="data-quality-tab-all active" data-quality-abnormal="all">ทั้งหมด <strong data-quality-group-count="all">0</strong></button>
    ${options.map((option, index) => `<button type="button" class="data-quality-tab-tone-${index % 4}" data-quality-abnormal="${escapeHtml(String(option.value))}">${escapeHtml(option.label || option.value)} <strong data-quality-group-count="${escapeHtml(String(option.value))}">0</strong></button>`).join('')}
  ` : '';
  container.querySelectorAll('[data-quality-abnormal]').forEach(button => {
    button.addEventListener('click', () => setDataQualityAbnormalFilter(button.dataset.qualityAbnormal || 'all'));
  });
  container.classList.add('hidden');
}

function applyDataQualityFilters() { dataQualityPage = 1; runDataQualityReport(true, true); }
function changeDataQualityPageSize(value) { dataQualityPageSize = Number(value) || 20; dataQualityPage = 1; runDataQualityReport(false); }
function queueDataQualitySearch() { clearTimeout(dataQualitySearchTimer); dataQualitySearchTimer = setTimeout(() => { dataQualityPage = 1; runDataQualityReport(false); }, 350); }

async function runDataQualityReport(includeSummary = false, refreshCache = false) {
  if (!activeDataQualityReport) return;
  if (refreshCache) showDataQualityLoading('กำลังอ่านและตรวจสอบข้อมูลล่าสุดจาก HIS...');
  try {
  const body = document.getElementById('data-quality-tbody');
  const columns = activeDataQualityReport.columns || [];
  if (refreshCache) body.innerHTML = `<tr><td colspan="${Math.max(columns.length, 1)}"><div class="data-quality-loading"><div class="spinner"></div><span>กำลังตรวจสอบข้อมูลล่าสุดใน HIS...</span></div></td></tr>`;
  renderDataQualityHeaders(columns);
  const result = await api(`/api/data-quality/reports/${encodeURIComponent(activeDataQualityReport.reportCode)}/query`, {
    method: 'POST', body: JSON.stringify({
      filters: collectDataQualityFilters(), search: document.getElementById('data-quality-search')?.value || '',
      page: dataQualityPage, page_size: dataQualityPageSize,
      sort_by: dataQualitySortBy, sort_direction: dataQualitySortDirection,
      include_summary: includeSummary,
      refresh_cache: refreshCache
    })
  });
  if (!result?.success) {
    body.innerHTML = `<tr><td colspan="${Math.max(columns.length, 1)}"><div class="empty-state"><p>${escapeHtml(result?.detail || 'ตรวจสอบข้อมูลไม่สำเร็จ')}</p></div></td></tr>`;
    return;
  }
  renderDataQualityRows(result.rows || [], columns);
  renderDataQualityPagination(result.filtered_count || 0);
  const summary = result.summary;
  if (summary) {
    dataQualitySummary = summary;
    document.getElementById('data-quality-count-all').textContent = Number(summary.total || 0).toLocaleString();
    document.getElementById('data-quality-count-normal').textContent = Number(summary.normal || 0).toLocaleString();
    document.getElementById('data-quality-count-abnormal').textContent = Number(summary.abnormal || 0).toLocaleString();
    document.querySelectorAll('[data-quality-group-count]').forEach(element => {
      const group = element.dataset.qualityGroupCount;
      const count = group === 'all' ? summary.abnormal : summary.abnormal_groups?.[group];
      element.textContent = Number(count || 0).toLocaleString();
    });
  }
  const suffix = result.truncated ? ` (จำกัด ${Number(result.filtered_count).toLocaleString()} รายการ)` : '';
  document.getElementById('data-quality-info').textContent = `ทั้งหมด ${Number(dataQualitySummary.total || 0).toLocaleString()} แถว | แสดงผลหลังกรอง ${Number(result.filtered_count).toLocaleString()} แถว${suffix}`;
  } finally {
    if (refreshCache) hideDataQualityLoading();
  }
}

function showDataQualityLoading(message) {
  dataQualityLoadingCount += 1;
  showLoading();
  const text = document.querySelector('#loading-overlay .loading-content p');
  if (text) text.textContent = message || 'กำลังตรวจสอบข้อมูล...';
}

function hideDataQualityLoading() {
  dataQualityLoadingCount = Math.max(0, dataQualityLoadingCount - 1);
  if (dataQualityLoadingCount > 0) return;
  hideLoading();
  const text = document.querySelector('#loading-overlay .loading-content p');
  if (text) text.textContent = 'กำลังดำเนินการ...';
}

function renderDataQualityHeaders(columns) {
  document.getElementById('data-quality-thead').innerHTML = `<tr>${columns.map(column => {
    const active = dataQualitySortBy === column.field;
    const indicator = active ? (dataQualitySortDirection === 'asc' ? ' ▲' : ' ▼') : '';
    return `<th class="${column.sortable ? `sortable${active ? ' sorted' : ''}` : ''}" ${column.sortable ? `onclick="sortDataQuality('${column.field}')"` : ''}>${escapeHtml(column.label || column.field)}${column.sortable ? `<span class="sort-indicator">${indicator}</span>` : ''}</th>`;
  }).join('')}</tr>`;
}

function sortDataQuality(field) {
  if (dataQualitySortBy === field) dataQualitySortDirection = dataQualitySortDirection === 'asc' ? 'desc' : 'asc';
  else { dataQualitySortBy = field; dataQualitySortDirection = 'asc'; }
  dataQualityPage = 1; runDataQualityReport(false);
}

function renderDataQualityRows(rows, columns) {
  const body = document.getElementById('data-quality-tbody');
  if (!rows.length) { body.innerHTML = `<tr><td colspan="${columns.length}"><div class="empty-state"><p>ไม่พบข้อมูลผิดปกติตามเงื่อนไข</p></div></td></tr>`; return; }
  body.innerHTML = rows.map(row => `<tr>${columns.map(column => {
    let value = row[column.field];
    if (value === null || value === undefined || value === '') value = '-';
    if (column.type === 'sex' && value !== '-') value = formatSex(value);
    if (column.type === 'number' && value !== '-') value = Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
    if (column.type === 'status' && value !== '-') return `<td><span class="status-badge ${value === 'ปกติ' ? 'success' : 'warning'}">${escapeHtml(value)}</span></td>`;
    return `<td>${escapeHtml(String(value))}</td>`;
  }).join('')}</tr>`).join('');
}

function renderDataQualityPagination(total) {
  const pages = Math.max(1, Math.ceil(total / dataQualityPageSize));
  if (dataQualityPage > pages) dataQualityPage = pages;
  const container = document.getElementById('data-quality-pagination');
  if (total <= dataQualityPageSize) { container.innerHTML = ''; return; }
  let startPage = Math.max(1, dataQualityPage - 2);
  let endPage = Math.min(pages, startPage + 4);
  if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);
  let html = `<button class="page-btn" ${dataQualityPage === 1 ? 'disabled' : ''} onclick="goDataQualityPage(${dataQualityPage - 1})"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6"/></svg></button>`;
  if (startPage > 1) { html += `<button class="page-btn" onclick="goDataQualityPage(1)">1</button>`; if (startPage > 2) html += '<span class="page-ellipsis">...</span>'; }
  for (let page = startPage; page <= endPage; page++) html += `<button class="page-btn ${page === dataQualityPage ? 'active' : ''}" onclick="goDataQualityPage(${page})">${page}</button>`;
  if (endPage < pages) { if (endPage < pages - 1) html += '<span class="page-ellipsis">...</span>'; html += `<button class="page-btn" onclick="goDataQualityPage(${pages})">${pages}</button>`; }
  html += `<button class="page-btn" ${dataQualityPage === pages ? 'disabled' : ''} onclick="goDataQualityPage(${dataQualityPage + 1})"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg></button>`;
  const startRow = (dataQualityPage - 1) * dataQualityPageSize + 1;
  const endRow = Math.min(dataQualityPage * dataQualityPageSize, total);
  html += `<span class="page-info">แสดง ${startRow.toLocaleString()}-${endRow.toLocaleString()} จาก ${Number(total).toLocaleString()} แถว</span>`;
  container.innerHTML = html;
}

function goDataQualityPage(page) { dataQualityPage = Math.max(1, page); runDataQualityReport(false); }

async function exportDataQualityReport(scope = 'filtered') {
  if (!activeDataQualityReport) return;
  const response = await api(`/api/data-quality/reports/${encodeURIComponent(activeDataQualityReport.reportCode)}/export`, {
    method: 'POST', body: JSON.stringify({
      scope,
      filters: collectDataQualityFilters(),
      search: document.getElementById('data-quality-search')?.value || ''
    })
  });
  if (!(response instanceof Response) || !response.ok) { showToast('ส่งออก Excel ไม่สำเร็จ', 'error'); return; }
  const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement('a');
  link.href = url; link.download = `${activeDataQualityReport.reportCode}.xlsx`; link.click(); URL.revokeObjectURL(url);
  showToast(scope === 'filtered' ? 'ส่งออก Excel ตามที่กรองสำเร็จ' : 'ส่งออก Excel ทั้งหมดสำเร็จ', 'success');
}
