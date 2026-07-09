// ============================================================
// Upload & Transform Module - Data Exchange Tools
// ============================================================

// State
let currentFileId = null;
let allData = [];
let filteredData = [];
let currentColumns = [];
let currentPage = 1;
let rowsPerPage = 20;
let sortCol = -1;
let sortDir = 'asc';
let searchTerm = '';
let availableFacilities = [];
let selectedHoscodes = [];
let facilityEventsBound = false;
let uploadEventsBound = false;
let isUploading = false;
let isHistoryDetailMode = false;
let activeResultFilter = 'all';
let centralDeathLookupAvailable = true;
let centralDeathLookupMessage = '';

function setHistoryDetailMode(enabled) {
  isHistoryDetailMode = Boolean(enabled);

  const uploadSection = document.getElementById('section-upload');
  const title = document.getElementById('upload-section-title');
  const backHistoryBtn = document.getElementById('btn-back-history');
  const newUploadBtn = document.getElementById('btn-new-upload-top');
  const fileRemoveBtn = document.querySelector('#file-info .btn-danger');

  uploadSection?.classList.toggle('history-detail-mode', isHistoryDetailMode);
  if (title) title.textContent = isHistoryDetailMode ? 'รายละเอียดประวัติการแปลงข้อมูล' : 'อัปโหลดไฟล์ Exchange';
  backHistoryBtn?.classList.toggle('hidden', !isHistoryDetailMode);
  newUploadBtn?.classList.toggle('hidden', isHistoryDetailMode || !currentFileId);
  fileRemoveBtn?.classList.toggle('hidden', isHistoryDetailMode);
}

function markHistorySidebarActive() {
  document.querySelectorAll('.sidebar-item').forEach(item => {
    item.classList.toggle('active', item.dataset.section === 'history');
  });
}

function returnToHistoryList() {
  setHistoryDetailMode(false);
  resetResultViewOnly();
  showSection('history');
}

/**
 * Initialize upload zone with drag & drop
 */
function initUpload() {
  const zone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('file-input');

  if (!zone || !fileInput) return;
  bindFacilitySelectorEvents();
  if (uploadEventsBound) return;
  uploadEventsBound = true;

  // Prevent default drag behaviors on the whole document
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    document.body.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
  });

  // Highlight drop zone
  ['dragenter', 'dragover'].forEach(eventName => {
    zone.addEventListener(eventName, () => {
      zone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    zone.addEventListener(eventName, () => {
      zone.classList.remove('drag-over');
    });
  });

  // Handle drop
  zone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  });

  // Handle file input change
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  });

  // Click zone to open file picker
  zone.addEventListener('click', (e) => {
    if (e.target.tagName !== 'BUTTON') {
      fileInput.click();
    }
  });
}

function bindFacilitySelectorEvents() {
  if (facilityEventsBound) return;
  facilityEventsBound = true;

  const select = document.getElementById('facility-select');
  const dropdown = document.getElementById('facility-dropdown');
  const trigger = document.querySelector('.facility-select-trigger');

  if (trigger) {
    trigger.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleFacilityDropdown();
    });
    trigger.removeAttribute('onclick');
  }

  if (select) {
    select.addEventListener('click', (event) => {
      event.stopPropagation();
    });
  }

  if (dropdown) {
    dropdown.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();

      const option = event.target.closest('.facility-option');
      if (!option) return;

      if (option.dataset.action === 'all') {
        selectAllFacilities();
        return;
      }

      const hoscode = option.dataset.hoscode;
      if (hoscode) toggleFacility(hoscode);
    });
  }

  document.addEventListener('click', () => {
    const activeDropdown = document.getElementById('facility-dropdown');
    const activeSelect = document.getElementById('facility-select');
    if (activeDropdown) activeDropdown.classList.add('hidden');
    if (activeSelect) activeSelect.classList.remove('open');
  });
}

/**
 * Handle file selection
 */
function handleFileSelect(file) {
  if (isUploading) {
    showToast('กำลังอัปโหลดไฟล์อยู่ กรุณารอสักครู่', 'warning');
    return;
  }

  const validTypes = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  ];
  const validExtensions = ['.xlsx'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();

  if (!validTypes.includes(file.type) && !validExtensions.includes(ext)) {
    showToast('กรุณาเลือกไฟล์ Excel (.xlsx) เท่านั้น', 'error');
    return;
  }

  uploadFile(file);
}

/**
 * Upload file to server
 */
async function uploadFile(file) {
  const zone = document.getElementById('upload-zone');
  const fileInfo = document.getElementById('file-info');
  const progressContainer = document.getElementById('progress-container');
  const progressBar = document.getElementById('progress-bar');

  if (isUploading) return;
  isUploading = true;

  // Show progress
  zone.classList.add('hidden');
  progressContainer.classList.remove('hidden');

  // Simulate progress while uploading
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress += Math.random() * 15;
    if (progress > 90) progress = 90;
    progressBar.style.width = progress + '%';
  }, 200);

  try {
    const formData = new FormData();
    formData.append('file', file);

    const result = await api('/api/upload', {
      method: 'POST',
      body: formData
    });

    clearInterval(progressInterval);
    progressBar.style.width = '100%';

    if (result && result.success) {
      currentFileId = result.file_id;
      availableFacilities = result.facilities || [];
      selectedHoscodes = [];

      // Show file info
      document.getElementById('file-name').textContent = file.name;
      document.getElementById('file-size').textContent = formatFileSize(file.size);
      document.getElementById('file-rows').textContent = result.total_rows?.toLocaleString() || '-';

      setTimeout(() => {
        progressContainer.classList.add('hidden');
        fileInfo.classList.remove('hidden');
        document.getElementById('btn-new-upload-top')?.classList.remove('hidden');

        // Show preview
        if (result.preview && result.columns) {
          renderPreviewTable(result.preview, result.columns);
          renderFacilitySelector();
          document.getElementById('preview-section').classList.remove('hidden');
        }

        showToast('อัปโหลดไฟล์สำเร็จ', 'success');
      }, 500);
    } else {
      throw new Error(result?.message || 'Upload failed');
    }
  } catch (error) {
    clearInterval(progressInterval);
    progressContainer.classList.add('hidden');
    zone.classList.remove('hidden');
    showToast(error.message || 'เกิดข้อผิดพลาดในการอัปโหลดไฟล์', 'error');
  } finally {
    isUploading = false;
    const fileInput = document.getElementById('file-input');
    if (fileInput) fileInput.value = '';
  }
}

/**
 * Render preview table
 */
function renderPreviewTable(rows, columns) {
  const thead = document.getElementById('preview-thead');
  const tbody = document.getElementById('preview-tbody');

  // Build header
  let headerHtml = '<tr>';
  columns.forEach(col => {
    headerHtml += `<th>${escapeHtml(col)}</th>`;
  });
  headerHtml += '</tr>';
  thead.innerHTML = headerHtml;

  // Build body
  let bodyHtml = '';
  rows.forEach(row => {
    bodyHtml += '<tr>';
    columns.forEach(col => {
      const value = row[col] !== null && row[col] !== undefined ? row[col] : '';
      bodyHtml += `<td>${escapeHtml(String(value))}</td>`;
    });
    bodyHtml += '</tr>';
  });
  tbody.innerHTML = bodyHtml;
}

function getSelectedHoscodesPayload() {
  return selectedHoscodes.length ? selectedHoscodes : [];
}

function jsString(value) {
  return JSON.stringify(String(value ?? ''));
}

function renderFacilitySelector() {
  bindFacilitySelectorEvents();
  const section = document.getElementById('facility-filter-section');
  if (!section) return;

  if (!availableFacilities.length) {
    section.classList.add('hidden');
    return;
  }

  section.classList.remove('hidden');
  updateFacilityLabel();
  renderFacilityOptions('');
}

function toggleFacilityDropdown() {
  const dropdown = document.getElementById('facility-dropdown');
  const select = document.getElementById('facility-select');
  const search = document.getElementById('facility-search');
  if (!dropdown) return;
  dropdown.classList.toggle('hidden');
  if (select) select.classList.toggle('open', !dropdown.classList.contains('hidden'));
  if (!dropdown.classList.contains('hidden') && search) {
    search.value = '';
    renderFacilityOptions('');
    search.focus();
  }
}

function selectAllFacilities() {
  selectedHoscodes = [];
  updateFacilityLabel();
  renderFacilityOptions(document.getElementById('facility-search')?.value || '');
}

function toggleFacility(hoscode) {
  if (selectedHoscodes.includes(hoscode)) {
    selectedHoscodes = selectedHoscodes.filter(code => code !== hoscode);
  } else {
    selectedHoscodes.push(hoscode);
  }
  updateFacilityLabel();
  renderFacilityOptions(document.getElementById('facility-search')?.value || '');
}

function updateFacilityLabel() {
  const label = document.getElementById('facility-select-label');
  const count = document.getElementById('facility-selected-count');
  if (!label || !count) return;

  if (!selectedHoscodes.length) {
    label.textContent = 'ทั้งหมด';
    count.textContent = `ทั้งหมด ${availableFacilities.length.toLocaleString()} หน่วยบริการ`;
    return;
  }

  const selectedNames = availableFacilities
    .filter(item => selectedHoscodes.includes(item.hoscode))
    .slice(0, 2)
    .map(item => `${item.hoscode} ${item.hosname || ''}`.trim());
  label.textContent = selectedNames.join(', ') + (selectedHoscodes.length > 2 ? ` +${selectedHoscodes.length - 2}` : '');
  count.textContent = `เลือก ${selectedHoscodes.length.toLocaleString()} หน่วยบริการ`;
}

function renderFacilityOptions(keyword = '') {
  const container = document.getElementById('facility-options');
  if (!container) return;

  const term = keyword.toLowerCase().trim();
  const rows = availableFacilities.filter(item => {
    const text = `${item.hoscode} ${item.hosname || ''}`.toLowerCase();
    return !term || text.includes(term);
  });

  const allActive = selectedHoscodes.length === 0;
  let html = `
    <button type="button" class="facility-option ${allActive ? 'active' : ''}" data-action="all">
      <span class="facility-check">${allActive ? '✓' : ''}</span>
      <span class="facility-name">ทั้งหมด</span>
      <span class="facility-rows">${availableFacilities.reduce((sum, item) => sum + Number(item.rows || 0), 0).toLocaleString()} แถว</span>
    </button>
  `;

  if (!rows.length) {
    html += '<div class="facility-empty">ไม่พบหน่วยบริการ</div>';
  } else {
    html += rows.map(item => {
      const active = selectedHoscodes.includes(item.hoscode);
      return `
        <button type="button" class="facility-option ${active ? 'active' : ''}" data-action="toggle" data-hoscode="${escapeHtml(item.hoscode)}">
          <span class="facility-check">${active ? '✓' : ''}</span>
          <span class="facility-name">${escapeHtml(item.hoscode)} ${escapeHtml(item.hosname || '')}</span>
          <span class="facility-rows">${Number(item.rows || 0).toLocaleString()} แถว</span>
        </button>
      `;
    }).join('');
  }

  container.innerHTML = html;
}

function isTrueFlag(value) {
  return value === true || value === 'true' || value === 1 || value === '1';
}

function isRowMatched(row) {
  return isTrueFlag(row?._matched);
}

function isPidMatched(row) {
  return isTrueFlag(row?._pid_matched) || row?._match_method === 'pid';
}

function isCidMatched(row) {
  return isTrueFlag(row?._cid_matched) || row?._match_method === 'cid';
}

function isCentralDeathMismatch(row) {
  return isTrueFlag(row?._central_death_mismatch);
}

function getDisplayColumns() {
  return currentColumns.filter(c => !String(c).startsWith('_'));
}

function rowMatchesActiveResultFilter(row) {
  if (activeResultFilter === 'pidMatched') return isPidMatched(row);
  if (activeResultFilter === 'pidUnmatched') return !isPidMatched(row);
  if (activeResultFilter === 'cidMatched') return isCidMatched(row);
  if (activeResultFilter === 'cidUnmatched') return !isRowMatched(row);
  if (activeResultFilter === 'centralDeath') return isCentralDeathMismatch(row);
  return true;
}

function rowMatchesSearchTerm(row) {
  if (!searchTerm) return true;
  return getDisplayColumns().some(col => {
    const val = row[col];
    if (val === null || val === undefined) return false;
    return String(val).toLowerCase().includes(searchTerm);
  });
}

function applyResultFilters(render = true) {
  filteredData = allData.filter(row => rowMatchesActiveResultFilter(row) && rowMatchesSearchTerm(row));
  currentPage = 1;
  if (render) renderResultsTable();
}

function updateResultFilterCards(result = {}) {
  if (Object.prototype.hasOwnProperty.call(result, 'central_death_lookup_available')) {
    centralDeathLookupAvailable = result.central_death_lookup_available !== false;
  } else {
    centralDeathLookupAvailable = true;
  }
  centralDeathLookupMessage = result.central_death_lookup_message || '';

  const counts = {
    all: allData.length,
    pidMatched: allData.filter(isPidMatched).length,
    pidUnmatched: allData.filter(row => !isPidMatched(row)).length,
    cidMatched: allData.filter(isCidMatched).length,
    cidUnmatched: allData.filter(row => !isRowMatched(row)).length,
    centralDeath: allData.filter(isCentralDeathMismatch).length
  };

  const allCount = document.getElementById('filter-count-all');
  const pidMatchedCount = document.getElementById('filter-count-pid-matched');
  const pidUnmatchedCount = document.getElementById('filter-count-pid-unmatched');
  const cidMatchedCount = document.getElementById('filter-count-cid-matched');
  const cidUnmatchedCount = document.getElementById('filter-count-cid-unmatched');
  const centralDeathCount = document.getElementById('filter-count-central-death');
  if (allCount) allCount.textContent = counts.all.toLocaleString();
  if (pidMatchedCount) pidMatchedCount.textContent = Number(result.pid_matched_count ?? counts.pidMatched).toLocaleString();
  if (pidUnmatchedCount) pidUnmatchedCount.textContent = Number(result.pid_unmatched_count ?? counts.pidUnmatched).toLocaleString();
  if (cidMatchedCount) cidMatchedCount.textContent = Number(result.cid_matched_count ?? counts.cidMatched).toLocaleString();
  if (cidUnmatchedCount) cidUnmatchedCount.textContent = Number(result.cid_unmatched_count ?? counts.cidUnmatched).toLocaleString();
  if (centralDeathCount) {
    centralDeathCount.textContent = Number(result.central_death_mismatch_count ?? counts.centralDeath).toLocaleString();
  }

  const centralCard = document.getElementById('filter-card-central-death');
  const hasDischarge = Boolean(result.has_discharge);
  const centralDesc = centralCard?.querySelector('.result-filter-desc');
  if (centralDeathCount && hasDischarge && !centralDeathLookupAvailable) {
    centralDeathCount.textContent = 'ใช้ไม่ได้';
  }
  centralCard?.classList.toggle('hidden', !hasDischarge);
  centralCard?.classList.toggle('result-filter-card-unavailable', hasDischarge && !centralDeathLookupAvailable);
  if (centralCard && hasDischarge) {
    centralCard.setAttribute(
      'title',
      centralDeathLookupAvailable
        ? 'กรองรายการที่ DISCHARGE ไม่ใช่ 1 แต่พบ CID ในฐานคนตายกลาง'
        : (centralDeathLookupMessage || 'ไม่สามารถเชื่อมต่อ API Center เพื่อเทียบข้อมูลการตายกับส่วนกลางได้')
    );
  }
  if (centralDesc) {
    centralDesc.textContent = centralDeathLookupAvailable
      ? 'DISCHARGE ไม่ใช่ 1 แต่พบ CID ในฐานคนตายกลาง'
      : 'ไม่สามารถเชื่อมต่อ API Center เพื่อเทียบข้อมูลนี้';
  }
  if (!hasDischarge && activeResultFilter === 'centralDeath') {
    activeResultFilter = 'all';
  } else if (!centralDeathLookupAvailable && activeResultFilter === 'centralDeath') {
    activeResultFilter = 'all';
  }

  document.querySelectorAll('.result-filter-card').forEach(card => {
    card.classList.toggle('active', card.dataset.filter === activeResultFilter);
  });
}

function setResultFilter(filterName) {
  if (filterName === 'centralDeath' && !centralDeathLookupAvailable) {
    showSweetAlert({
      type: 'warning',
      title: 'ยังเทียบข้อมูลการตายกับส่วนกลางไม่ได้',
      message: centralDeathLookupMessage || 'ไม่สามารถเชื่อมต่อ API Center ได้ อาจเกิดจาก internet ขาดการเชื่อมต่อ หรือ API Center ไม่พร้อมใช้งาน ระบบยังสามารถแปลงข้อมูลและดูประวัติได้ตามปกติ ยกเว้นการเทียบฐานคนตายกลาง',
      confirmText: 'เข้าใจแล้ว'
    });
    return;
  }

  activeResultFilter = filterName;
  updateResultFilterCards({
    has_discharge: !document.getElementById('filter-card-central-death')?.classList.contains('hidden'),
    central_death_lookup_available: centralDeathLookupAvailable,
    central_death_lookup_message: centralDeathLookupMessage
  });
  applyResultFilters(true);
}

function showResultData(result, options = {}) {
  setHistoryDetailMode(Boolean(options.historyDetail));

  currentFileId = result.file_id || currentFileId;
  allData = result.data || [];
  currentColumns = result.columns || [];
  activeResultFilter = 'all';
  filteredData = [...allData];
  currentPage = 1;
  rowsPerPage = 20;
  searchTerm = '';
  sortCol = -1;
  sortDir = 'asc';

  document.getElementById('matched-count').textContent = `จับคู่รวมได้: ${(result.matched_count || 0).toLocaleString()}`;
  document.getElementById('unmatched-count').textContent = `จับคู่รวมไม่ได้: ${(result.unmatched_count || 0).toLocaleString()}`;

  const filename = result.filename || options.filename || document.getElementById('file-name')?.textContent || '-';
  document.getElementById('file-name').textContent = filename;
  document.getElementById('file-size').textContent = options.fileSize || '-';
  document.getElementById('file-rows').textContent = Number(result.total_rows || allData.length || 0).toLocaleString();

  document.getElementById('upload-zone')?.classList.add('hidden');
  document.getElementById('progress-container')?.classList.add('hidden');
  document.getElementById('file-info')?.classList.remove('hidden');
  document.getElementById('preview-section')?.classList.add('hidden');
  document.getElementById('facility-filter-section')?.classList.add('hidden');
  document.getElementById('results-section')?.classList.remove('hidden');
  document.getElementById('btn-new-upload-top')?.classList.toggle('hidden', Boolean(options.historyDetail));
  document.querySelector('#file-info .btn-danger')?.classList.toggle('hidden', Boolean(options.historyDetail));

  const searchInput = document.getElementById('search-input');
  if (searchInput) searchInput.value = '';

  const rowsSelect = document.getElementById('rows-select');
  if (rowsSelect) rowsSelect.value = '20';

  updateResultFilterCards(result);
  applyResultFilters(false);
  renderResultsTable();
}

/**
 * Transform data
 */
async function transformData() {
  if (!currentFileId) {
    showToast('ไม่พบไฟล์ที่อัปโหลด กรุณาอัปโหลดไฟล์ใหม่', 'error');
    return;
  }

  const btn = document.getElementById('btn-transform');
  const originalText = btn.innerHTML;

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="width:20px;height:20px;"></div> กำลังแปลงข้อมูล...';

  showLoading();

  try {
    const result = await api('/api/transform', {
      method: 'POST',
      body: JSON.stringify({
        file_id: currentFileId,
        hoscodes: getSelectedHoscodesPayload()
      })
    });

    hideLoading();
    btn.disabled = false;
    btn.innerHTML = originalText;

    if (result && result.success) {
      showResultData(result);
      showToast(`แปลงข้อมูลสำเร็จ ${Number(result.total_rows || allData.length).toLocaleString()} แถว`, 'success');
    } else {
      throw new Error(result?.message || 'Transform failed');
    }
  } catch (error) {
    hideLoading();
    btn.disabled = false;
    btn.innerHTML = originalText;
    showToast(error.message || 'เกิดข้อผิดพลาดในการแปลงข้อมูล', 'error');
  }
}

/**
 * Load transform history
 */
async function loadHistory() {
  const tbody = document.getElementById('history-tbody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="spinner" style="width:24px;height:24px;"></div><p>กำลังโหลดประวัติ...</p></div></td></tr>`;

  const result = await api('/api/history', { method: 'GET' });
  const items = result?.data || [];

  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state">
      <span class="empty-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      </span>
      <p>ยังไม่มีประวัติการแปลงข้อมูล</p>
    </div></td></tr>`;
    return;
  }

  tbody.innerHTML = items.map(item => {
    const statusClass = item.status === 'completed' ? 'badge-success' : 'badge-info';
    const statusText = item.status === 'completed' ? 'แปลงสำเร็จ' : 'อัปโหลดแล้ว';
    const action = item.status === 'completed'
      ? `<div class="history-actions">
          <button class="btn history-icon-btn history-detail-btn" onclick='openHistoryDetail(${jsString(item.file_id)})' title="ดูรายละเอียด" aria-label="ดูรายละเอียด">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
          </button>
          <button class="btn history-icon-btn history-download-btn" onclick='downloadHistoryFile(${jsString(item.file_id)})' title="ดาวน์โหลด" aria-label="ดาวน์โหลด">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>
          </button>
        </div>`
      : '-';

    return `<tr>
      <td>${escapeHtml(item.original_filename || '-')}</td>
      <td>${escapeHtml(formatDate(item.upload_time))}</td>
      <td>${Number(item.total_rows || 0).toLocaleString()}</td>
      <td><span class="badge ${statusClass}">${statusText}</span></td>
      <td>${action}</td>
    </tr>`;
  }).join('');
}

async function openHistoryDetail(fileId) {
  showLoading();

  try {
    const result = await api(`/api/history/${encodeURIComponent(fileId)}`, { method: 'GET' });
    hideLoading();

    if (!result || !result.success) {
      throw new Error(result?.message || 'ไม่พบรายละเอียดประวัติ');
    }

    showSection('upload', false);
    showResultData(result, { historyDetail: true });
    markHistorySidebarActive();
    if (typeof setRoute === 'function') setRoute('/history', true);
    document.getElementById('section-upload')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    showToast('เปิดรายละเอียดประวัติแล้ว', 'success');
  } catch (error) {
    hideLoading();
    showToast(error.message || 'เกิดข้อผิดพลาดในการเปิดรายละเอียด', 'error');
  }
}

function downloadHistoryFile(fileId) {
  currentFileId = fileId;
  exportExcel();
}

/**
 * Render results table with current filters, sort, and pagination
 */
function renderResultsTable() {
  const thead = document.getElementById('results-thead');
  const tbody = document.getElementById('results-tbody');

  // Filter columns (exclude internal fields starting with _)
  const displayColumns = getDisplayColumns();

  // Build header with sort indicators
  let headerHtml = '<tr>';
  displayColumns.forEach((col, index) => {
    const isSorted = sortCol === index;
    const sortIndicator = isSorted
      ? (sortDir === 'asc' ? ' ▲' : ' ▼')
      : '';
    headerHtml += `<th onclick="handleSort(${index})" class="sortable${isSorted ? ' sorted' : ''}">`;
    headerHtml += `${escapeHtml(col)}<span class="sort-indicator">${sortIndicator}</span></th>`;
  });
  headerHtml += '</tr>';
  thead.innerHTML = headerHtml;

  // Calculate pagination
  const totalPages = Math.ceil(filteredData.length / rowsPerPage);
  if (currentPage > totalPages && totalPages > 0) currentPage = totalPages;
  const startIdx = (currentPage - 1) * rowsPerPage;
  const endIdx = startIdx + rowsPerPage;
  const pageData = filteredData.slice(startIdx, endIdx);

  // Build body
  let bodyHtml = '';
  if (pageData.length === 0) {
    bodyHtml = `<tr><td colspan="${displayColumns.length}">
      <div class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <p>ไม่พบข้อมูลที่ตรงกับการค้นหา</p>
      </div>
    </td></tr>`;
  } else {
    pageData.forEach(row => {
      const isUnmatched = !isRowMatched(row);
      const isCentralDeath = isCentralDeathMismatch(row);
      bodyHtml += `<tr class="${isUnmatched ? 'unmatched' : ''}${isCentralDeath ? ' central-death-mismatch' : ''}">`;
      displayColumns.forEach(col => {
        const value = row[col] !== null && row[col] !== undefined ? row[col] : '';
        if (col === 'เงื่อนไขที่ใช้') {
          const pillClass = value === 'PID' ? 'match-pill-pid' : (value === 'CID' ? 'match-pill-cid' : 'match-pill-none');
          const icon = value === 'PID' ? '✓' : (value === 'CID' ? '↔' : '−');
          bodyHtml += `<td class="result-symbol-cell"><span class="result-symbol-pill ${pillClass}" title="${escapeHtml(String(value))}">${icon} ${escapeHtml(String(value))}</span></td>`;
        } else if (col === 'เทียบตาย') {
          const pillClass = value === 'พบข้อมูล' ? 'death-pill-found' : (value === 'ไม่พบข้อมูล' ? 'death-pill-clear' : (value === 'ใช้ไม่ได้' ? 'death-pill-unavailable' : 'death-pill-skip'));
          const icon = value === 'พบข้อมูล' ? '!' : (value === 'ไม่พบข้อมูล' ? '✓' : (value === 'ใช้ไม่ได้' ? '×' : '−'));
          bodyHtml += `<td class="result-symbol-cell"><span class="result-symbol-pill ${pillClass}" title="${escapeHtml(String(value))}">${icon}</span></td>`;
        } else {
          bodyHtml += `<td>${escapeHtml(String(value))}</td>`;
        }
      });
      bodyHtml += '</tr>';
    });
  }
  tbody.innerHTML = bodyHtml;

  renderPagination(totalPages);
  renderDataTableInfo();
}

function renderDataTableInfo() {
  const info = document.getElementById('datatable-info');
  if (!info) return;
  info.textContent = `ทั้งหมด ${allData.length.toLocaleString()} แถว | แสดงผลหลังกรอง ${filteredData.length.toLocaleString()} แถว`;
}

/**
 * Handle search with debounce
 */
const handleSearch = debounce(function (value) {
  searchTerm = value.toLowerCase().trim();
  applyResultFilters(true);
}, 300);

/**
 * Handle rows per page change
 */
function handleRowsPerPageChange(value) {
  rowsPerPage = parseInt(value, 10);
  currentPage = 1;
  renderResultsTable();
}

/**
 * Handle column sort
 */
function handleSort(colIndex) {
  if (sortCol === colIndex) {
    sortDir = sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    sortCol = colIndex;
    sortDir = 'asc';
  }

  const displayColumns = getDisplayColumns();
  const colName = displayColumns[colIndex];

  filteredData.sort((a, b) => {
    let valA = a[colName];
    let valB = b[colName];

    if (valA === null || valA === undefined) valA = '';
    if (valB === null || valB === undefined) valB = '';

    // Try numeric comparison
    const numA = Number(valA);
    const numB = Number(valB);
    if (!isNaN(numA) && !isNaN(numB) && valA !== '' && valB !== '') {
      return sortDir === 'asc' ? numA - numB : numB - numA;
    }

    // String comparison
    const strA = String(valA).toLowerCase();
    const strB = String(valB).toLowerCase();
    if (strA < strB) return sortDir === 'asc' ? -1 : 1;
    if (strA > strB) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  currentPage = 1;
  renderResultsTable();
}

/**
 * Handle page change
 */
function handlePageChange(page) {
  currentPage = page;
  renderResultsTable();
  document.getElementById('results-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Render pagination controls
 */
function renderPagination(totalPages) {
  const container = document.getElementById('pagination');
  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }

  let html = '';

  // Previous button
  html += `<button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="handlePageChange(${currentPage - 1})">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
  </button>`;

  // Page numbers
  const maxVisible = 5;
  let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
  let endPage = Math.min(totalPages, startPage + maxVisible - 1);
  if (endPage - startPage < maxVisible - 1) {
    startPage = Math.max(1, endPage - maxVisible + 1);
  }

  if (startPage > 1) {
    html += `<button class="page-btn" onclick="handlePageChange(1)">1</button>`;
    if (startPage > 2) {
      html += `<span class="page-ellipsis">...</span>`;
    }
  }

  for (let i = startPage; i <= endPage; i++) {
    html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="handlePageChange(${i})">${i}</button>`;
  }

  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      html += `<span class="page-ellipsis">...</span>`;
    }
    html += `<button class="page-btn" onclick="handlePageChange(${totalPages})">${totalPages}</button>`;
  }

  // Next button
  html += `<button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="handlePageChange(${currentPage + 1})">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
  </button>`;

  // Page info
  const startRow = (currentPage - 1) * rowsPerPage + 1;
  const endRow = Math.min(currentPage * rowsPerPage, filteredData.length);
  html += `<span class="page-info">แสดง ${startRow.toLocaleString()}-${endRow.toLocaleString()} จาก ${filteredData.length.toLocaleString()} แถว</span>`;

  container.innerHTML = html;
}

/**
 * Export results to Excel
 */
async function exportExcel() {
  if (!currentFileId) {
    showToast('ไม่มีข้อมูลสำหรับส่งออก', 'error');
    return;
  }

  showLoading();

  try {
    const response = await api('/api/export', {
      method: 'POST',
      body: JSON.stringify({ file_id: currentFileId })
    });

    hideLoading();

    if (response && response instanceof Response) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      // Get filename from content-disposition or use default
      const disposition = response.headers.get('content-disposition');
      let filename = 'export_result.xlsx';
      if (disposition) {
        const match = disposition.match(/filename[^;=\n]*=(['"]?)([^'"\n]*?)\1(;|$)/);
        if (match && match[2]) filename = decodeURIComponent(match[2]);
      }

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      showToast('ส่งออกไฟล์ Excel สำเร็จ', 'success');
    } else if (response && response.success === false) {
      throw new Error(response.message || 'Export failed');
    }
  } catch (error) {
    hideLoading();
    showToast(error.message || 'เกิดข้อผิดพลาดในการส่งออกไฟล์', 'error');
  }
}

/**
 * Reset upload - clear everything for new upload
 */
function resetResultViewOnly() {
  const fileInfo = document.getElementById('file-info');
  const resultsSection = document.getElementById('results-section');
  const newUploadTop = document.getElementById('btn-new-upload-top');
  const backHistoryBtn = document.getElementById('btn-back-history');
  const fileRemoveBtn = document.querySelector('#file-info .btn-danger');

  fileInfo?.classList.add('hidden');
  resultsSection?.classList.add('hidden');
  newUploadTop?.classList.add('hidden');
  backHistoryBtn?.classList.add('hidden');
  fileRemoveBtn?.classList.remove('hidden');

  const searchInput = document.getElementById('search-input');
  if (searchInput) searchInput.value = '';
  document.getElementById('results-thead').innerHTML = '';
  document.getElementById('results-tbody').innerHTML = '';
  document.getElementById('pagination').innerHTML = '';
}

function resetUpload() {
  setHistoryDetailMode(false);

  currentFileId = null;
  allData = [];
  filteredData = [];
  currentColumns = [];
  availableFacilities = [];
  selectedHoscodes = [];
  currentPage = 1;
  rowsPerPage = 20;
  sortCol = -1;
  sortDir = 'asc';
  searchTerm = '';
  activeResultFilter = 'all';

  // Reset UI
  const zone = document.getElementById('upload-zone');
  const fileInfo = document.getElementById('file-info');
  const progressContainer = document.getElementById('progress-container');
  const progressBar = document.getElementById('progress-bar');
  const previewSection = document.getElementById('preview-section');
  const resultsSection = document.getElementById('results-section');
  const fileInput = document.getElementById('file-input');
  const facilitySection = document.getElementById('facility-filter-section');
  const facilityDropdown = document.getElementById('facility-dropdown');
  const facilitySelect = document.getElementById('facility-select');
  const newUploadTop = document.getElementById('btn-new-upload-top');

  zone.classList.remove('hidden');
  fileInfo.classList.add('hidden');
  progressContainer.classList.add('hidden');
  progressBar.style.width = '0%';
  previewSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  if (facilitySection) facilitySection.classList.add('hidden');
  if (facilityDropdown) facilityDropdown.classList.add('hidden');
  if (facilitySelect) facilitySelect.classList.remove('open');
  if (newUploadTop) newUploadTop.classList.add('hidden');

  // Clear file input
  if (fileInput) fileInput.value = '';

  // Clear tables
  document.getElementById('preview-thead').innerHTML = '';
  document.getElementById('preview-tbody').innerHTML = '';
  document.getElementById('results-thead').innerHTML = '';
  document.getElementById('results-tbody').innerHTML = '';
  document.getElementById('pagination').innerHTML = '';

  // Clear search
  const searchInput = document.getElementById('search-input');
  if (searchInput) searchInput.value = '';
}
