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

/**
 * Initialize upload zone with drag & drop
 */
function initUpload() {
  const zone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('file-input');

  if (!zone || !fileInput) return;

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

/**
 * Handle file selection
 */
function handleFileSelect(file) {
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
  const search = document.getElementById('facility-search');
  if (!dropdown) return;
  dropdown.classList.toggle('hidden');
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
    <button type="button" class="facility-option ${allActive ? 'active' : ''}" onclick="selectAllFacilities()">
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
        <button type="button" class="facility-option ${active ? 'active' : ''}" onclick="toggleFacility(${jsString(item.hoscode)})">
          <span class="facility-check">${active ? '✓' : ''}</span>
          <span class="facility-name">${escapeHtml(item.hoscode)} ${escapeHtml(item.hosname || '')}</span>
          <span class="facility-rows">${Number(item.rows || 0).toLocaleString()} แถว</span>
        </button>
      `;
    }).join('');
  }

  container.innerHTML = html;
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
      allData = result.data || [];
      currentColumns = result.columns || [];
      filteredData = [...allData];
      currentPage = 1;
      rowsPerPage = 20;
      searchTerm = '';
      sortCol = -1;
      sortDir = 'asc';

      // Update stats
      document.getElementById('matched-count').textContent = `จับคู่ได้: ${(result.matched_count || 0).toLocaleString()}`;
      document.getElementById('unmatched-count').textContent = `จับคู่ไม่ได้: ${(result.unmatched_count || 0).toLocaleString()}`;

      // Hide preview, show results
      document.getElementById('preview-section').classList.add('hidden');
      document.getElementById('results-section').classList.remove('hidden');

      // Clear search
      document.getElementById('search-input').value = '';
      const rowsSelect = document.getElementById('rows-select');
      if (rowsSelect) rowsSelect.value = '20';

      renderResultsTable();
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
      ? `<button class="btn btn-sm btn-success" onclick="downloadHistoryFile('${escapeHtml(item.file_id)}')">ดาวน์โหลด</button>`
      : '-';

    return `<tr>
      <td>${escapeHtml(item.original_filename || '-')}</td>
      <td>${escapeHtml(item.upload_time || '-')}</td>
      <td>${Number(item.total_rows || 0).toLocaleString()}</td>
      <td><span class="badge ${statusClass}">${statusText}</span></td>
      <td>${action}</td>
    </tr>`;
  }).join('');
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
  const displayColumns = currentColumns.filter(c => !c.startsWith('_'));

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
      const isUnmatched = row._matched === false;
      bodyHtml += `<tr class="${isUnmatched ? 'unmatched' : ''}">`;
      displayColumns.forEach(col => {
        const value = row[col] !== null && row[col] !== undefined ? row[col] : '';
        bodyHtml += `<td>${escapeHtml(String(value))}</td>`;
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

  if (!searchTerm) {
    filteredData = [...allData];
  } else {
    const displayColumns = currentColumns.filter(c => !c.startsWith('_'));
    filteredData = allData.filter(row => {
      return displayColumns.some(col => {
        const val = row[col];
        if (val === null || val === undefined) return false;
        return String(val).toLowerCase().includes(searchTerm);
      });
    });
  }

  currentPage = 1;
  renderResultsTable();
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

  const displayColumns = currentColumns.filter(c => !c.startsWith('_'));
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
function resetUpload() {
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

  zone.classList.remove('hidden');
  fileInfo.classList.add('hidden');
  progressContainer.classList.add('hidden');
  progressBar.style.width = '0%';
  previewSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  if (facilitySection) facilitySection.classList.add('hidden');
  if (facilityDropdown) facilityDropdown.classList.add('hidden');

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
