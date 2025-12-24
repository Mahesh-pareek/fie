// State
let currentSort = 'datetime';
let currentOrder = 'desc';
let selectedRowIdx = -1;
let trendChart = null;
let catChart = null;
let trendPeriod = 'monthly';
let currentView = 'dashboard';
let selectedTxIds = new Set();
let settings = {};
let merchantChart = null;
let statsCatChart = null;
let trendsData = null;  // Cache for trend toggle
let allTransactions = [];  // Cache for edit lookup

// ============ TOAST NOTIFICATIONS ============
function showToast(message, type = 'success') {
  // Remove existing toast
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
    <span class="toast-message">${message}</span>
  `;
  document.body.appendChild(toast);
  
  // Trigger animation
  requestAnimationFrame(() => toast.classList.add('show'));
  
  // Auto remove
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ============ API HELPERS ============
async function fetchJSON(url) {
  const r = await fetch(url);
  if (r.status === 401) {
    window.location.href = '/login';
    return null;
  }
  return r.json();
}

async function postJSON(url, data) {
  const r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  });
  if (r.status === 401) {
    window.location.href = '/login';
    return null;
  }
  return r.json();
}

async function deleteJSON(url) {
  const r = await fetch(url, {method: 'DELETE'});
  if (r.status === 401) {
    window.location.href = '/login';
    return null;
  }
  return r.json();
}

// ============ FORMATTERS ============
function humanAmount(a) {
  const sign = a < 0 ? '-' : '';
  return sign + '₹' + Math.abs(a).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short', year: '2-digit'});
}

function formatDateTime(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}) + ' ' + 
         d.toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit'});
}

// View switching
function switchView(view) {
  currentView = view;
  document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
  document.querySelectorAll('.sidebar a').forEach(a => a.classList.remove('active'));
  
  const viewEl = document.getElementById('view' + view.charAt(0).toUpperCase() + view.slice(1));
  if (viewEl) viewEl.style.display = 'block';
  
  const navEl = document.querySelector(`.sidebar a[data-view="${view}"]`);
  if (navEl) navEl.classList.add('active');
  
  // Load view-specific data
  if (view === 'dashboard') renderDashboard();
  if (view === 'transactions') loadTable();
  if (view === 'stats') renderStats();
  if (view === 'settings') loadSettings();
  if (view === 'rules') loadRules();
  if (view === 'logs') loadLogs();
}

// Dashboard - parallel loading
async function renderDashboard() {
  showLoading('dashboard');
  try {
    // Fetch all data in parallel
    const [summary, trends, stats, recentTxns, health] = await Promise.all([
      fetchJSON('/api/summary?scope=personal'),
      fetchJSON('/api/trends?scope=personal'),
      fetchJSON('/api/stats'),
      fetchJSON('/api/transactions?limit=5&sort=datetime&order=desc'),
      fetchJSON('/api/health')
    ]);
    
    renderSummaryData(summary, stats);
    renderTrendsData(trends);
    renderBudgetData(stats);
    renderInsights(stats);
    renderRecentTransactions(recentTxns);
    renderHealthBanner(health);
  } catch (e) {
    console.error('Dashboard error:', e);
  } finally {
    hideLoading('dashboard');
  }
}

function renderBudgetData(stats) {
  if (!stats) return;
  
  const budget = stats.monthly_budget || 0;
  document.getElementById('card-budget').textContent = humanAmount(stats.budget_remaining || 0);
  
  // Calculate days left in month
  const now = new Date();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const daysLeft = daysInMonth - now.getDate();
  const budgetDaysEl = document.getElementById('card-budget-days');
  if (budgetDaysEl) budgetDaysEl.textContent = `${daysLeft} days left`;
  
  if (budget <= 0) {
    document.getElementById('budgetSection').style.display = 'none';
    return;
  }
  
  document.getElementById('budgetSection').style.display = 'block';
  
  const spent = stats.this_month_spent || 0;
  const pct = stats.budget_used_percent || 0;
  const fill = document.getElementById('budgetFill');
  fill.style.width = Math.min(pct, 100) + '%';
  fill.className = 'budget-fill' + (pct > 80 ? ' warning' : '');
  
  document.getElementById('budgetSpent').textContent = humanAmount(spent);
  document.getElementById('budgetTotal').textContent = humanAmount(budget);
  
  const pctEl = document.getElementById('budgetPercent');
  if (pctEl) pctEl.textContent = Math.round(pct) + '%';
  
  const daysLeftEl = document.getElementById('budgetDaysLeft');
  if (daysLeftEl) daysLeftEl.textContent = `• ${daysLeft} days remaining`;
}

// Render insights
function renderInsights(stats) {
  if (!stats) return;
  
  // Vs Last Month comparison
  const thisMonth = stats.this_month_spent || 0;
  const lastMonth = stats.last_month_spent || 0;
  const vsLastEl = document.getElementById('insightVsLastMonth');
  
  if (vsLastEl && lastMonth > 0) {
    const diff = thisMonth - lastMonth;
    const pct = Math.round(Math.abs(diff / lastMonth) * 100);
    const isUp = diff > 0;
    vsLastEl.querySelector('.insight-text').innerHTML = isUp 
      ? `<strong class="insight-up">↑ ${pct}%</strong> more than last month`
      : `<strong class="insight-down">↓ ${pct}%</strong> less than last month`;
  }
  
  // Savings rate
  const income = stats.total_income || 0;
  const spent = stats.total_spent || 0;
  const savingsEl = document.getElementById('savingsRate');
  if (savingsEl && income > 0) {
    const savingsRate = Math.round(((income - spent) / income) * 100);
    const isGood = savingsRate > 0;
    savingsEl.innerHTML = isGood 
      ? `Savings rate: <strong class="insight-up">${savingsRate}%</strong>`
      : `Overspent by: <strong class="insight-down">${Math.abs(savingsRate)}%</strong>`;
  }
  
  // Transaction count this month
  const monthTxnsEl = document.getElementById('monthTxnsCount');
  if (monthTxnsEl) {
    const count = stats.this_month_transactions || stats.total_transactions || 0;
    monthTxnsEl.innerHTML = `<strong>${count}</strong> transactions this month`;
  }
}

// Render recent transactions
function renderRecentTransactions(txns) {
  const container = document.getElementById('recentTransactions');
  if (!container) return;
  
  if (!txns || txns.length === 0) {
    container.innerHTML = '<div class="recent-empty">No recent transactions</div>';
    return;
  }
  
  container.innerHTML = txns.slice(0, 5).map(t => {
    const isDebit = t.direction === 'debit';
    const amt = isDebit ? -t.amount : t.amount;
    const cats = (t.category || []).join(', ') || t.scope;
    const date = new Date(t.datetime);
    const timeStr = date.toLocaleDateString('en-IN', {day: 'numeric', month: 'short'});
    
    return `
      <div class="recent-item">
        <div class="recent-icon ${t.direction}">${isDebit ? '↑' : '↓'}</div>
        <div class="recent-info">
          <div class="recent-name">${t.counterparty}</div>
          <div class="recent-cat">${cats} • ${timeStr}</div>
        </div>
        <div class="recent-amount ${isDebit ? 'negative' : 'positive'}">${humanAmount(amt)}</div>
      </div>
    `;
  }).join('');
}

// Load metadata (scopes, categories)
async function loadMeta() {
  const meta = await fetchJSON('/api/meta');
  if (!meta) return;
  
  const scopeSel = document.getElementById('filterScope');
  const catSel = document.getElementById('filterCategory');
  scopeSel.innerHTML = '<option value="">All</option>' + meta.scopes.map(s => `<option value="${s}">${s}</option>`).join('');
  catSel.innerHTML = '<option value="">All</option>' + meta.categories.map(s => `<option value="${s}">${s}</option>`).join('');
}

// Loading helpers
function showLoading(view) {
  const el = document.getElementById(view + 'Loading');
  if (el) el.style.display = 'flex';
}
function hideLoading(view) {
  const el = document.getElementById(view + 'Loading');
  if (el) el.style.display = 'none';
}

// Render summary cards - uses pre-fetched data
function renderSummaryData(s, stats) {
  if (!s) return;
  
  document.getElementById('card-total').textContent = s.total_transactions;
  
  // Use separate spending/income data from backend
  const spendingByCat = s.spending_by_category || {};
  const incomeByCat = s.income_by_category || {};
  const creditsBreakdown = s.credits_breakdown || {};
  
  let spent = 0, income = 0;
  Object.values(spendingByCat).forEach(v => spent += v);
  Object.values(incomeByCat).forEach(v => income += v);
  
  // Splits are friend paybacks that offset spending
  const splitsAmount = creditsBreakdown.splits || 0;
  const depositsAmount = creditsBreakdown.deposits || 0;
  
  // Money Out = ALL expenses (gross spending)
  document.getElementById('card-spent').textContent = humanAmount(-spent);
  
  // Money In = deposits + splits (total credits)
  document.getElementById('card-income').textContent = humanAmount(income);
  
  // Show credits breakdown in Money In card subtitle
  const incomeBreakdownEl = document.getElementById('card-income-breakdown');
  if (incomeBreakdownEl) {
    if (splitsAmount > 0 && depositsAmount > 0) {
      incomeBreakdownEl.innerHTML = `<span class="credit-deposits">${humanAmount(depositsAmount)}</span> + <span class="credit-splits">${humanAmount(splitsAmount)} splits</span>`;
    } else if (splitsAmount > 0) {
      incomeBreakdownEl.innerHTML = `<span class="credit-splits">${humanAmount(splitsAmount)} from splits</span>`;
    } else {
      incomeBreakdownEl.textContent = 'deposits & income';
    }
  }
  
  // Show net spending info in Money Out card subtitle
  const spentTrendEl = document.getElementById('card-spent-trend');
  if (spentTrendEl && splitsAmount > 0) {
    const netSpent = spent - splitsAmount;
    spentTrendEl.innerHTML = `Net: ${humanAmount(-netSpent)} <span class="credit-splits">(after ${humanAmount(splitsAmount)} splits)</span>`;
    spentTrendEl.className = 'card-sub';
  } else if (stats) {
    const thisMonth = stats.this_month_spent || 0;
    const lastMonth = stats.last_month_spent || 0;
    if (spentTrendEl && lastMonth > 0) {
      const diff = thisMonth - lastMonth;
      const pct = Math.round(Math.abs(diff / lastMonth) * 100);
      if (diff > 0) {
        spentTrendEl.textContent = `↑ ${pct}% vs last month`;
        spentTrendEl.className = 'card-sub trend-up';
      } else {
        spentTrendEl.textContent = `↓ ${pct}% vs last month`;
        spentTrendEl.className = 'card-sub trend-down';
      }
    }
  }
  
  // Spending chart - ONLY expenses (debits), no income/deposits
  const labels = Object.keys(spendingByCat).filter(k => spendingByCat[k] > 0);
  const data = labels.map(k => Math.round(spendingByCat[k]));
  const colors = ['#3b82f6', '#ef4444', '#10b981', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899', '#6366f1', '#14b8a6', '#f97316'];
  
  const catCanvas = document.getElementById('catChart');
  if (!catCanvas || labels.length === 0) return;
  
  if (catChart) catChart.destroy();
  catChart = new Chart(catCanvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{data: data, backgroundColor: colors.slice(0, labels.length), borderWidth: 0}]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const idx = elements[0].index;
          const category = labels[idx];
          openCategoryDrilldown(category);
        }
      },
      plugins: {
        legend: {display: true, position: 'bottom', labels: {color: '#cfcfcf', font: {size: 10}}},
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.label}: ₹${ctx.raw.toLocaleString('en-IN')} (click for details)`
          }
        }
      }
    }
  });
}

// Outlier detection and capping for bar charts
// Returns { cappedValues, outlierIndices, capValue, originalValues }
function detectAndCapOutliers(values, threshold = 2.5) {
  if (values.length < 3) return { cappedValues: values, outlierIndices: [], capValue: null, originalValues: values };
  
  const absValues = values.map(v => Math.abs(v));
  const sorted = [...absValues].sort((a, b) => a - b);
  
  // Use IQR method to detect outliers
  const q1 = sorted[Math.floor(sorted.length * 0.25)];
  const q3 = sorted[Math.floor(sorted.length * 0.75)];
  const iqr = q3 - q1;
  const upperBound = q3 + threshold * iqr;
  
  // Also use median-based threshold as backup
  const median = sorted[Math.floor(sorted.length / 2)];
  const medianThreshold = median * 4; // 4x median is likely an outlier
  
  const capValue = Math.min(upperBound, medianThreshold > 0 ? medianThreshold : upperBound);
  
  // Only cap if we have significant outliers (at least 2x the cap)
  const outlierIndices = [];
  const cappedValues = values.map((v, i) => {
    const absV = Math.abs(v);
    if (absV > capValue && absV > capValue * 1.5) {
      outlierIndices.push(i);
      return v >= 0 ? capValue : -capValue;
    }
    return v;
  });
  
  return { 
    cappedValues, 
    outlierIndices, 
    capValue: outlierIndices.length > 0 ? capValue : null,
    originalValues: values 
  };
}

// Render trend chart - uses pre-fetched data
function renderTrendsData(trends) {
  trendsData = trends;  // Cache for toggle
  renderTrends();
}

function renderTrends() {
  if (!trendsData) return;
  
  const data = trendPeriod === 'monthly' ? trendsData.monthly : trendsData.weekly;
  if (!data || Object.keys(data).length === 0) return;
  
  const labels = Object.keys(data);
  const rawValues = Object.values(data).map(v => Math.round(v));
  
  // Detect and cap outliers
  const { cappedValues, outlierIndices, originalValues } = detectAndCapOutliers(rawValues);
  
  const trendCanvas = document.getElementById('trendChart');
  if (!trendCanvas) return;
  
  if (trendChart) trendChart.destroy();
  
  // Create pattern for capped bars
  const backgroundColors = cappedValues.map((v, i) => {
    const baseColor = v >= 0 ? '#2ecc71' : '#e74c3c';
    if (outlierIndices.includes(i)) {
      // Create striped pattern for outliers
      return createStripePattern(trendCanvas.getContext('2d'), baseColor);
    }
    return baseColor;
  });
  
  trendChart = new Chart(trendCanvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Net Flow',
        data: cappedValues,
        backgroundColor: backgroundColors,
        borderRadius: 4,
        // Store original values for tooltip
        originalData: originalValues
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {display: false},
        tooltip: {
          callbacks: {
            label: function(ctx) {
              const original = ctx.dataset.originalData ? ctx.dataset.originalData[ctx.dataIndex] : ctx.raw;
              const isCapped = outlierIndices.includes(ctx.dataIndex);
              const formatted = '₹' + Math.abs(original).toLocaleString('en-IN');
              return isCapped ? `${formatted} ⚠️ (large value)` : formatted;
            }
          }
        }
      },
      scales: {
        x: {grid: {display: false}, ticks: {color: '#888'}},
        y: {grid: {color: 'rgba(255,255,255,0.05)'}, ticks: {color: '#888'}}
      }
    }
  });
}

// Create diagonal stripe pattern for capped/outlier bars
function createStripePattern(ctx, color) {
  const patternCanvas = document.createElement('canvas');
  patternCanvas.width = 10;
  patternCanvas.height = 10;
  const pctx = patternCanvas.getContext('2d');
  
  // Background
  pctx.fillStyle = color;
  pctx.fillRect(0, 0, 10, 10);
  
  // Diagonal stripes
  pctx.strokeStyle = 'rgba(255,255,255,0.4)';
  pctx.lineWidth = 2;
  pctx.beginPath();
  pctx.moveTo(0, 10);
  pctx.lineTo(10, 0);
  pctx.stroke();
  pctx.beginPath();
  pctx.moveTo(-5, 5);
  pctx.lineTo(5, -5);
  pctx.stroke();
  pctx.beginPath();
  pctx.moveTo(5, 15);
  pctx.lineTo(15, 5);
  pctx.stroke();
  
  return ctx.createPattern(patternCanvas, 'repeat');
}

// Render transactions table
async function loadTable() {
  const search = document.getElementById('filterSearch').value || '';
  const scope = document.getElementById('filterScope').value || '';
  const category = document.getElementById('filterCategory').value || '';
  const direction = document.getElementById('filterDirection').value || '';
  
  const params = new URLSearchParams({
    limit: 500,
    sort: currentSort,
    order: currentOrder
  });
  if (scope) params.set('scope', scope);
  if (category) params.set('category', category);
  if (direction) params.set('direction', direction);
  if (search) params.set('search', search);
  
  const txs = await fetchJSON('/api/transactions?' + params.toString());
  if (!txs) return;
  
  allTransactions = txs;  // Cache for edit modal lookup
  
  const tbody = document.querySelector('#txTable tbody');
  tbody.innerHTML = '';
  
  selectedTxIds.clear();
  updateBulkDeleteBtn();
  
  txs.forEach((t, idx) => {
    const tr = document.createElement('tr');
    tr.dataset.idx = idx;
    tr.dataset.id = t.id;
    const amt = t.direction === 'credit' ? t.amount : -t.amount;
    const cats = (t.category || []).join(', ') || '—';
    const dateStr = formatDate(t.datetime);
    const dirIcon = t.direction === 'debit' ? '↑' : '↓';
    const reviewedBadge = t.reviewed ? '<span class="status-badge status-reviewed">✓</span>' : '';
    
    tr.innerHTML = `
      <td><input type="checkbox" class="txCheckbox" data-id="${t.id}"></td>
      <td class="date-cell">${dateStr}</td>
      <td class="amount-cell ${t.direction}">${humanAmount(amt)}</td>
      <td><span class="scope-tag">${t.scope}</span></td>
      <td class="category-cell">${cats}</td>
      <td class="counterparty-cell">
        <span class="dir-badge ${t.direction}">${dirIcon}</span>
        <span>${t.counterparty}</span>
        ${reviewedBadge}
      </td>
      <td class="actions-cell">
        <button class="editBtn" data-id="${t.id}">Edit</button>
        <button class="ruleBtn" data-id="${t.id}" title="Create rule from this">⚡</button>
        <button class="btn-danger btn-sm deleteBtn" data-id="${t.id}">✕</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  document.getElementById('rowCount').textContent = `${txs.length} transactions`;
  
  // Wire edit buttons
  document.querySelectorAll('.editBtn').forEach(b => {
    b.addEventListener('click', (e) => {
      e.stopPropagation();
      openModal(e.target.dataset.id);
    });
  });
  
  // Wire create rule buttons
  document.querySelectorAll('.ruleBtn').forEach(b => {
    b.addEventListener('click', (e) => {
      e.stopPropagation();
      createRuleFromTransaction(e.target.dataset.id);
    });
  });
  
  // Wire delete buttons
  document.querySelectorAll('.deleteBtn').forEach(b => {
    b.addEventListener('click', (e) => {
      e.stopPropagation();
      confirmDelete([e.target.dataset.id]);
    });
  });
  
  // Wire checkboxes
  document.querySelectorAll('.txCheckbox').forEach(cb => {
    cb.addEventListener('change', (e) => {
      const id = e.target.dataset.id;
      if (e.target.checked) selectedTxIds.add(id);
      else selectedTxIds.delete(id);
      updateBulkDeleteBtn();
    });
  });
  
  // Row click to select
  document.querySelectorAll('#txTable tbody tr').forEach(tr => {
    tr.addEventListener('click', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
      selectRow(parseInt(tr.dataset.idx));
    });
  });
  
  // Update active filters display
  updateActiveFilters();
}

function updateBulkDeleteBtn() {
  const btn = document.getElementById('bulkDeleteBtn');
  if (btn) {
    btn.style.display = selectedTxIds.size > 0 ? 'inline-block' : 'none';
    btn.textContent = `Delete Selected (${selectedTxIds.size})`;
  }
}

function toggleSelectAll(checked) {
  document.querySelectorAll('.txCheckbox').forEach(cb => {
    cb.checked = checked;
    const id = cb.dataset.id;
    if (checked) selectedTxIds.add(id);
    else selectedTxIds.delete(id);
  });
  updateBulkDeleteBtn();
}

function selectRow(idx) {
  document.querySelectorAll('#txTable tbody tr').forEach(tr => tr.classList.remove('selected'));
  const rows = document.querySelectorAll('#txTable tbody tr');
  if (idx >= 0 && idx < rows.length) {
    rows[idx].classList.add('selected');
    selectedRowIdx = idx;
    rows[idx].scrollIntoView({block: 'nearest'});
  }
}

function updateActiveFilters() {
  const container = document.getElementById('activeFilters');
  container.innerHTML = '';
  
  const scope = document.getElementById('filterScope').value;
  const category = document.getElementById('filterCategory').value;
  const direction = document.getElementById('filterDirection').value;
  const search = document.getElementById('filterSearch').value;
  
  const addPill = (label, clearFn) => {
    const pill = document.createElement('span');
    pill.className = 'filter-pill';
    pill.innerHTML = `${label} <button>&times;</button>`;
    pill.querySelector('button').onclick = clearFn;
    container.appendChild(pill);
  };
  
  if (scope) addPill(`Scope: ${scope}`, () => { document.getElementById('filterScope').value = ''; loadTable(); });
  if (category) addPill(`Category: ${category}`, () => { document.getElementById('filterCategory').value = ''; loadTable(); });
  if (direction) addPill(`Direction: ${direction}`, () => { document.getElementById('filterDirection').value = ''; loadTable(); });
  if (search) addPill(`Search: ${search}`, () => { document.getElementById('filterSearch').value = ''; loadTable(); });
}

// Modal
async function openModal(id) {
  document.getElementById('modalId').value = id;
  
  // Get transaction data
  const txn = allTransactions.find(t => t.id === id);
  
  // Populate scope dropdown
  const meta = await fetchJSON('/api/meta');
  if (meta) {
    const sel = document.getElementById('modalScope');
    sel.innerHTML = meta.scopes.map(s => `<option value="${s}" ${txn && txn.scope === s ? 'selected' : ''}>${s}</option>`).join('');
  }
  
  // Show current values
  if (txn) {
    document.getElementById('modalCategories').value = (txn.category || []).join(', ');
    // Show transaction info in modal header
    const infoEl = document.getElementById('modalTxnInfo');
    if (infoEl) {
      infoEl.innerHTML = `<strong>${txn.counterparty}</strong> · ₹${txn.amount} · ${txn.datetime?.split('T')[0] || ''}`;
    }
  } else {
    document.getElementById('modalCategories').value = '';
  }
  
  document.getElementById('editModal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('editModal').style.display = 'none';
}

async function saveModal() {
  const id = document.getElementById('modalId').value;
  const scope = document.getElementById('modalScope').value;
  const cats = document.getElementById('modalCategories').value.split(',').map(x => x.trim()).filter(x => x);
  
  const payload = {id, scope, category: cats};
  const result = await postJSON('/api/tag', payload);
  
  if (result && result.ok) {
    closeModal();
    showToast('Transaction updated successfully');
    render();
  } else {
    showToast('Save failed: ' + (result?.error || 'unknown error'), 'error');
  }
}

// Delete functionality
let pendingDeleteIds = [];

function confirmDelete(ids) {
  pendingDeleteIds = ids;
  const count = ids.length;
  document.getElementById('deleteCount').textContent = count === 1 ? 'this transaction' : `${count} transactions`;
  document.getElementById('deleteModal').style.display = 'flex';
}

function closeDeleteModal() {
  document.getElementById('deleteModal').style.display = 'none';
  pendingDeleteIds = [];
}

async function executeDelete() {
  if (pendingDeleteIds.length === 0) return;
  
  let result;
  if (pendingDeleteIds.length === 1) {
    result = await deleteJSON('/api/transaction/' + pendingDeleteIds[0]);
  } else {
    result = await postJSON('/api/transactions/bulk-delete', {ids: pendingDeleteIds});
  }
  
  closeDeleteModal();
  
  if (result && result.ok) {
    selectedTxIds.clear();
    showToast('Moved to trash');
    render();
  } else {
    showToast('Delete failed: ' + (result?.error || 'unknown error'), 'error');
  }
}

// Stats view
// Analytics charts storage
let analyticsCharts = {};

// Toggle collapsible sections
function toggleSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (section) section.classList.toggle('collapsed');
}

// Render analytics page with all scopes - parallel loading
async function renderStats() {
  showLoading('stats');
  try {
    // Fetch both in parallel
    const [data, trends] = await Promise.all([
      fetchJSON('/api/analytics'),
      fetchJSON('/api/trends?scope=personal')
    ]);
    if (!data) return;
    renderAnalyticsData(data, trends);
  } finally {
    hideLoading('stats');
  }
}

function renderAnalyticsData(data, trends) {
  
  const colors = {
    personal: '#3b82f6',
    education: '#8b5cf6',
    family: '#10b981',
    shared: '#f59e0b'
  };
  const catColors = ['#3b82f6', '#ef4444', '#10b981', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899', '#6366f1', '#14b8a6', '#f97316'];
  
  // === PERSONAL SECTION ===
  const personal = data.scopes.personal || {};
  setText('personalTxns', personal.total_transactions || 0);
  setText('personalSpent', humanAmount(personal.total_spent || 0));
  setText('personalThisMonth', humanAmount(personal.this_month_spent || 0));
  
  // Top categories for personal
  const topCatsEl = document.getElementById('personalTopCats');
  if (topCatsEl && personal.categories) {
    const sorted = Object.entries(personal.categories).sort((a,b) => b[1] - a[1]).slice(0, 5);
    topCatsEl.innerHTML = '<div class="top-list">' + sorted.map(([cat, amt]) => 
      `<div class="top-item"><span>${cat}</span><span>${humanAmount(amt)}</span></div>`
    ).join('') + '</div>';
  }
  
  // Top merchants for personal
  const topMerchEl = document.getElementById('personalTopMerchants');
  if (topMerchEl && personal.top_merchants) {
    topMerchEl.innerHTML = '<div class="top-list">' + personal.top_merchants.slice(0, 5).map(m => 
      `<div class="top-item"><span>${m.name}</span><span>${humanAmount(m.amount)}</span></div>`
    ).join('') + '</div>';
  }
  
  // Daily chart with category colors - store data for type switching
  if (trends && trends.daily_by_category) {
    dailyTrendsData = trends;
    renderStackedDailyChart('personalDailyChart', trends.daily_by_category, catColors, trends.daily_cumulative);
  }
  
  // Weekly chart
  if (personal.weekly) {
    renderBarChart('personalWeeklyChart', personal.weekly, colors.personal, 'Weekly Spending');
  }
  
  // Monthly chart
  if (personal.monthly) {
    renderBarChart('personalMonthlyChart', personal.monthly, colors.personal, 'Monthly Spending');
  }
  
  // === EDUCATION SECTION ===
  const education = data.scopes.education || {};
  setText('educationTxns', education.total_transactions || 0);
  setText('educationSpent', humanAmount(education.total_spent || 0));
  setText('educationThisMonth', humanAmount(education.this_month_spent || 0));
  if (education.monthly) {
    renderBarChart('educationMonthlyChart', education.monthly, colors.education, 'Monthly');
  }
  
  // === FAMILY SECTION ===
  const family = data.scopes.family || {};
  setText('familyTxns', family.total_transactions || 0);
  setText('familySpent', humanAmount(family.total_spent || 0));
  setText('familyThisMonth', humanAmount(family.this_month_spent || 0));
  if (family.monthly) {
    renderBarChart('familyMonthlyChart', family.monthly, colors.family, 'Monthly');
  }
  
  // === SHARED SECTION ===
  const shared = data.scopes.shared || {};
  setText('sharedTxns', shared.total_transactions || 0);
  setText('sharedSpent', humanAmount(shared.total_spent || 0));
  setText('sharedThisMonth', humanAmount(shared.this_month_spent || 0));
  if (shared.monthly) {
    renderBarChart('sharedMonthlyChart', shared.monthly, colors.shared, 'Monthly');
  }
  
  // === COMPARISON SECTION ===
  if (data.comparison) {
    // Monthly comparison stacked bar
    renderComparisonChart('comparisonMonthlyChart', data.comparison.monthly, colors);
    
    // Pie chart of total distribution
    renderPieChart('comparisonPieChart', data.comparison.totals, colors);
  }
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function renderBarChart(canvasId, data, color, label) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data) return;
  
  if (analyticsCharts[canvasId]) analyticsCharts[canvasId].destroy();
  
  const labels = Object.keys(data);
  const rawValues = Object.values(data);
  
  // Detect and cap outliers
  const { cappedValues, outlierIndices, originalValues } = detectAndCapOutliers(rawValues);
  
  // Create background colors with stripes for outliers
  const ctx = canvas.getContext('2d');
  const backgroundColors = cappedValues.map((v, i) => {
    if (outlierIndices.includes(i)) {
      return createStripePattern(ctx, color);
    }
    return color;
  });
  
  analyticsCharts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: label,
        data: cappedValues,
        backgroundColor: backgroundColors,
        borderRadius: 4,
        originalData: originalValues
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {display: false},
        tooltip: {
          callbacks: {
            label: function(ctx) {
              const original = ctx.dataset.originalData ? ctx.dataset.originalData[ctx.dataIndex] : ctx.raw;
              const isCapped = outlierIndices.includes(ctx.dataIndex);
              const formatted = '₹' + Math.abs(original).toLocaleString('en-IN');
              return isCapped ? `${formatted} ⚠️ (outlier capped)` : formatted;
            }
          }
        }
      },
      scales: {
        x: {grid: {display: false}, ticks: {color: '#888', maxRotation: 45}},
        y: {grid: {color: 'rgba(255,255,255,0.05)'}, ticks: {color: '#888'}}
      }
    }
  });
}

// ============ DAILY SPENDING CHART WITH DATE RANGE ============

let dailyChartType = 'bar';  // 'bar', 'line', 'cumulative'
let dailyDateRange = 30;     // days or 'custom'
let dailyTrendsData = null;

function renderStackedDailyChart(canvasId, dailyByCat, colors, cumulative = null) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  
  if (analyticsCharts[canvasId]) analyticsCharts[canvasId].destroy();
  
  // Get dates and calculate canvas width based on data points
  const dates = Object.keys(dailyByCat || {});
  const numDays = dates.length;
  
  // Update chart info
  const infoEl = document.getElementById('dailyChartInfo');
  if (infoEl && dailyTrendsData?.date_range) {
    const range = dailyTrendsData.date_range;
    infoEl.textContent = `Showing ${numDays} days${range.total_days > numDays ? ` of ${range.total_days} total` : ''}`;
  }
  
  // Dynamic canvas width for scrolling when > 30 days
  const container = document.getElementById('dailyChartContainer');
  if (container && numDays > 30) {
    const minWidth = Math.max(numDays * 25, container.clientWidth);
    canvas.style.minWidth = minWidth + 'px';
  } else if (canvas) {
    canvas.style.minWidth = '100%';
  }
  
  if (!dailyByCat || dates.length === 0) {
    if (infoEl) infoEl.textContent = 'No data for selected period';
    return;
  }
  
  // Build chart based on type
  if (dailyChartType === 'cumulative' && cumulative) {
    renderCumulativeChart(canvasId, cumulative, dates);
  } else if (dailyChartType === 'line') {
    renderDailyLineChart(canvasId, dailyByCat, colors, dates);
  } else {
    renderDailyBarChart(canvasId, dailyByCat, colors, dates);
  }
}

function renderDailyBarChart(canvasId, dailyByCat, colors, dates) {
  const canvas = document.getElementById(canvasId);
  const allCats = new Set();
  dates.forEach(d => Object.keys(dailyByCat[d] || {}).forEach(c => allCats.add(c)));
  const categories = Array.from(allCats);
  
  const datasets = categories.map((cat, i) => ({
    label: cat,
    data: dates.map(d => (dailyByCat[d] || {})[cat] || 0),
    backgroundColor: colors[i % colors.length],
    borderRadius: 2
  }));
  
  analyticsCharts[canvasId] = new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {labels: dates.map(d => d.slice(5)), datasets: datasets},
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {display: true, position: 'bottom', labels: {color: '#cfcfcf', font: {size: 10}}},
        tooltip: {
          callbacks: {
            title: (ctx) => dates[ctx[0].dataIndex],
            label: (ctx) => `${ctx.dataset.label}: ₹${ctx.raw.toLocaleString('en-IN')}`
          }
        }
      },
      scales: {
        x: {stacked: true, grid: {display: false}, ticks: {color: '#888', maxRotation: 45, font: {size: 10}}},
        y: {stacked: true, grid: {color: 'rgba(255,255,255,0.05)'}, ticks: {color: '#888'}}
      }
    }
  });
}

function renderDailyLineChart(canvasId, dailyByCat, colors, dates) {
  const canvas = document.getElementById(canvasId);
  const allCats = new Set();
  dates.forEach(d => Object.keys(dailyByCat[d] || {}).forEach(c => allCats.add(c)));
  const categories = Array.from(allCats);
  
  const datasets = categories.map((cat, i) => ({
    label: cat,
    data: dates.map(d => (dailyByCat[d] || {})[cat] || 0),
    borderColor: colors[i % colors.length],
    backgroundColor: colors[i % colors.length] + '33',
    fill: true,
    tension: 0.3,
    pointRadius: dates.length > 30 ? 0 : 3,
    pointHoverRadius: 5
  }));
  
  analyticsCharts[canvasId] = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {labels: dates.map(d => d.slice(5)), datasets: datasets},
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {mode: 'index', intersect: false},
      plugins: {
        legend: {display: true, position: 'bottom', labels: {color: '#cfcfcf', font: {size: 10}}},
        tooltip: {
          callbacks: {
            title: (ctx) => dates[ctx[0].dataIndex],
            label: (ctx) => `${ctx.dataset.label}: ₹${ctx.raw.toLocaleString('en-IN')}`
          }
        }
      },
      scales: {
        x: {grid: {display: false}, ticks: {color: '#888', maxRotation: 45, font: {size: 10}}},
        y: {grid: {color: 'rgba(255,255,255,0.05)'}, ticks: {color: '#888'}}
      }
    }
  });
}

function renderCumulativeChart(canvasId, cumulative, dates) {
  const canvas = document.getElementById(canvasId);
  const cumulativeData = dates.map(d => cumulative[d] || 0);
  
  // Fill gaps in cumulative data
  let lastValue = 0;
  const filledData = cumulativeData.map(v => {
    if (v > 0) lastValue = v;
    return lastValue;
  });
  
  analyticsCharts[canvasId] = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: dates.map(d => d.slice(5)),
      datasets: [{
        label: 'Cumulative Spending',
        data: filledData,
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,0.1)',
        fill: true,
        tension: 0.2,
        pointRadius: dates.length > 30 ? 0 : 3,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {mode: 'index', intersect: false},
      plugins: {
        legend: {display: false},
        tooltip: {
          callbacks: {
            title: (ctx) => dates[ctx[0].dataIndex],
            label: (ctx) => `Total spent: ₹${ctx.raw.toLocaleString('en-IN')}`
          }
        }
      },
      scales: {
        x: {grid: {display: false}, ticks: {color: '#888', maxRotation: 45, font: {size: 10}}},
        y: {grid: {color: 'rgba(255,255,255,0.05)'}, ticks: {color: '#888', callback: (v) => '₹' + (v/1000).toFixed(0) + 'k'}}
      }
    }
  });
}

// Initialize date range controls
function initDailyChartControls() {
  // Quick range buttons
  document.querySelectorAll('.range-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      const range = btn.dataset.range;
      const customEl = document.querySelector('.custom-range');
      
      if (range === 'custom') {
        customEl.style.display = 'flex';
        // Set default dates
        const today = new Date();
        const thirtyDaysAgo = new Date(today);
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        document.getElementById('dailyEndDate').value = today.toISOString().split('T')[0];
        document.getElementById('dailyStartDate').value = thirtyDaysAgo.toISOString().split('T')[0];
      } else {
        customEl.style.display = 'none';
        dailyDateRange = parseInt(range);
        await refreshDailyChart();
      }
    });
  });
  
  // Chart type toggle
  document.querySelectorAll('.chart-type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.chart-type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      dailyChartType = btn.dataset.type;
      
      // Re-render with current data
      if (dailyTrendsData) {
        const catColors = ['#3b82f6', '#ef4444', '#10b981', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899', '#6366f1'];
        renderStackedDailyChart('personalDailyChart', dailyTrendsData.daily_by_category, catColors, dailyTrendsData.daily_cumulative);
      }
    });
  });
}

async function applyCustomDateRange() {
  const startDate = document.getElementById('dailyStartDate').value;
  const endDate = document.getElementById('dailyEndDate').value;
  
  if (!startDate || !endDate) {
    showToast('Please select both dates', 'error');
    return;
  }
  
  dailyDateRange = 'custom';
  await refreshDailyChart(startDate, endDate);
}

async function refreshDailyChart(startDate = null, endDate = null) {
  let url = '/api/trends?scope=personal';
  
  if (startDate && endDate) {
    url += `&start=${startDate}&end=${endDate}`;
  } else if (typeof dailyDateRange === 'number') {
    const today = new Date();
    const startDt = new Date(today);
    startDt.setDate(startDt.getDate() - dailyDateRange);
    url += `&start=${startDt.toISOString().split('T')[0]}&end=${today.toISOString().split('T')[0]}`;
  }
  
  const trends = await fetchJSON(url);
  if (trends) {
    dailyTrendsData = trends;
    const catColors = ['#3b82f6', '#ef4444', '#10b981', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899', '#6366f1'];
    renderStackedDailyChart('personalDailyChart', trends.daily_by_category, catColors, trends.daily_cumulative);
  }
}

function renderComparisonChart(canvasId, monthlyData, colors) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !monthlyData) return;
  
  if (analyticsCharts[canvasId]) analyticsCharts[canvasId].destroy();
  
  const months = Object.keys(monthlyData);
  const scopes = ['personal', 'education', 'family', 'shared'];
  
  const datasets = scopes.map(scope => ({
    label: scope.charAt(0).toUpperCase() + scope.slice(1),
    data: months.map(m => monthlyData[m][scope] || 0),
    backgroundColor: colors[scope],
    borderRadius: 2
  }));
  
  analyticsCharts[canvasId] = new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {labels: months, datasets: datasets},
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {legend: {display: true, position: 'bottom', labels: {color: '#cfcfcf'}}},
      scales: {
        x: {grid: {display: false}, ticks: {color: '#888'}},
        y: {grid: {color: 'rgba(255,255,255,0.05)'}, ticks: {color: '#888'}}
      }
    }
  });
}

function renderPieChart(canvasId, totals, colors) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !totals) return;
  
  if (analyticsCharts[canvasId]) analyticsCharts[canvasId].destroy();
  
  const labels = Object.keys(totals).filter(k => totals[k] > 0);
  const data = labels.map(k => totals[k]);
  const bgColors = labels.map(k => colors[k] || '#888');
  
  analyticsCharts[canvasId] = new Chart(canvas.getContext('2d'), {
    type: 'pie',
    data: {
      labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
      datasets: [{data: data, backgroundColor: bgColors}]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {legend: {display: true, position: 'bottom', labels: {color: '#cfcfcf'}}}
    }
  });
}

// Settings
async function loadSettings() {
  const s = await fetchJSON('/api/settings');
  if (!s) return;
  settings = s;
  
  // Ensure budget_scopes exists
  if (!settings.budget_scopes) settings.budget_scopes = ['personal'];
  
  document.getElementById('settingBudget').value = s.monthly_budget || '';
  document.getElementById('settingAlertPct').value = s.alert_threshold || 80;
  
  // Render categories
  renderCategoryTags(s.categories || []);
  
  // Render budget scopes checkboxes
  const allScopes = s.scopes || ['personal', 'family', 'education', 'shared'];
  renderBudgetScopes(allScopes, s.budget_scopes || ['personal']);
  
  // Load auto-tagging rules and merchants
  await Promise.all([loadRules(), loadMerchants()]);
  setupMerchantAutocomplete();
}

function renderCategoryTags(cats) {
  const container = document.getElementById('categoryTags');
  if (!container) return;
  container.innerHTML = '';
  cats.forEach(cat => {
    const chip = document.createElement('span');
    chip.className = 'tag-chip';
    chip.innerHTML = `${cat} <button data-cat="${cat}">&times;</button>`;
    chip.querySelector('button').onclick = () => removeCategory(cat);
    container.appendChild(chip);
  });
}

function renderBudgetScopes(allScopes, selectedScopes) {
  const container = document.getElementById('budgetScopesCheckboxes');
  if (!container) return;
  container.innerHTML = '';
  
  allScopes.forEach(scope => {
    const label = document.createElement('label');
    const checked = selectedScopes.includes(scope) ? 'checked' : '';
    label.innerHTML = `<input type="checkbox" data-scope="${scope}" ${checked}> ${scope}`;
    label.querySelector('input').onchange = (e) => {
      if (e.target.checked) {
        if (!settings.budget_scopes.includes(scope)) {
          settings.budget_scopes.push(scope);
        }
      } else {
        settings.budget_scopes = settings.budget_scopes.filter(s => s !== scope);
      }
    };
    container.appendChild(label);
  });
}

function addCategory() {
  const input = document.getElementById('newCategoryInput');
  const cat = input.value.trim();
  if (!cat) return;
  
  if (!settings.categories) settings.categories = [];
  if (!settings.categories.includes(cat)) {
    settings.categories.push(cat);
    renderCategoryTags(settings.categories);
  }
  input.value = '';
}

function removeCategory(cat) {
  if (!settings.categories) return;
  settings.categories = settings.categories.filter(c => c !== cat);
  renderCategoryTags(settings.categories);
}

async function saveSettings() {
  settings.monthly_budget = parseFloat(document.getElementById('settingBudget').value) || 0;
  settings.alert_threshold = parseInt(document.getElementById('settingAlertPct').value) || 80;
  
  // budget_scopes is already updated via checkbox handlers
  
  const result = await postJSON('/api/settings', settings);
  if (result && result.ok) {
    alert('Settings saved successfully!');
  } else {
    alert('Failed to save settings: ' + (result?.error || 'unknown error'));
  }
}

// ============ AUTO-TAGGING RULES ============
let autoRules = [];
let merchants = [];

async function loadRules() {
  const rules = await fetchJSON('/api/rules');
  if (rules) {
    autoRules = rules;
    renderRulesList();
  }
}

async function loadMerchants() {
  const m = await fetchJSON('/api/merchants');
  if (m) merchants = m;
}

function renderRulesList() {
  const container = document.getElementById('rulesList');
  if (!container) return;
  
  if (autoRules.length === 0) {
    container.innerHTML = '<p class="hint">No rules defined yet. Add a rule to auto-tag transactions.</p>';
    return;
  }
  
  // Sort by priority
  const sorted = [...autoRules].sort((a, b) => (a.priority || 999) - (b.priority || 999));
  
  container.innerHTML = sorted.map((rule, idx) => {
    const conditions = formatConditions(rule);
    const actions = formatActions(rule);
    const enabledClass = rule.enabled ? 'active' : '';
    const cardClass = rule.enabled ? '' : 'disabled';
    
    return `
      <div class="rule-card ${cardClass}" data-id="${rule.id}">
        <div class="rule-info">
          <div class="rule-name">
            <span class="priority-badge">#${idx + 1}</span>
            ${rule.name}
          </div>
          <div class="rule-conditions-display">${conditions}</div>
          <div class="rule-actions-display">${actions}</div>
        </div>
        <div class="rule-controls">
          <div class="rule-toggle ${enabledClass}" onclick="toggleRule('${rule.id}')" title="Toggle rule"></div>
          <button class="btn-sm" onclick="editRule('${rule.id}')">✏️</button>
          <button class="btn-sm" onclick="deleteRule('${rule.id}')">🗑️</button>
        </div>
      </div>
    `;
  }).join('');
}

function formatConditions(rule) {
  const c = rule.conditions || {};
  const parts = [];
  
  if (rule.type === 'amount' || rule.type === 'combined') {
    if (c.amount_min !== undefined && c.amount_max !== undefined) {
      parts.push(`₹${c.amount_min} - ₹${c.amount_max}`);
    } else if (c.amount_min !== undefined) {
      parts.push(`≥ ₹${c.amount_min}`);
    } else if (c.amount_max !== undefined) {
      parts.push(`≤ ₹${c.amount_max}`);
    }
  }
  
  if (rule.type === 'merchant' || rule.type === 'combined') {
    // Show multiple merchants nicely
    if (c.merchant_contains) {
      const keywords = c.merchant_contains.split(',').map(k => k.trim()).slice(0, 3);
      const extra = c.merchant_contains.split(',').length - 3;
      let display = keywords.join(', ');
      if (extra > 0) display += ` +${extra} more`;
      parts.push(`contains "${display}"`);
    }
    if (c.merchant_exact) {
      const keywords = c.merchant_exact.split(',').map(k => k.trim()).slice(0, 2);
      const extra = c.merchant_exact.split(',').length - 2;
      let display = keywords.join(', ');
      if (extra > 0) display += ` +${extra} more`;
      parts.push(`= "${display}"`);
    }
  }
  
  if (c.direction) {
    parts.push(c.direction === 'debit' ? '📤 Expense' : '📥 Income');
  }
  
  return parts.length ? `If: ${parts.join(' AND ')}` : 'No conditions';
}

function formatActions(rule) {
  const a = rule.actions || {};
  const parts = [];
  
  if (a.scope) parts.push(`<span class="tag">${a.scope}</span>`);
  if (a.category && a.category.length) {
    parts.push(`<span class="tag">${a.category.join(', ')}</span>`);
  }
  
  return parts.length ? `→ ${parts.join(' ')}` : '';
}

async function toggleRule(ruleId) {
  const rule = autoRules.find(r => r.id === ruleId);
  if (!rule) return;
  
  const result = await fetch(`/api/rules/${ruleId}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({enabled: !rule.enabled})
  }).then(r => r.json());
  
  if (result.ok) {
    rule.enabled = !rule.enabled;
    renderRulesList();
  }
}

function openRuleModal(rule = null) {
  const modal = document.getElementById('ruleModal');
  const title = document.getElementById('ruleModalTitle');
  
  if (rule) {
    title.textContent = '✏️ Edit Rule';
    document.getElementById('ruleId').value = rule.id;
    document.getElementById('ruleName').value = rule.name || '';
    document.getElementById('ruleType').value = rule.type || 'amount';
    document.getElementById('ruleAmountMin').value = rule.conditions?.amount_min ?? '';
    document.getElementById('ruleAmountMax').value = rule.conditions?.amount_max ?? '';
    document.getElementById('ruleMerchantContains').value = rule.conditions?.merchant_contains || '';
    document.getElementById('ruleMerchantExact').value = rule.conditions?.merchant_exact || '';
    document.getElementById('ruleDirection').value = rule.conditions?.direction || '';
    document.getElementById('ruleScope').value = rule.actions?.scope || 'personal';
    document.getElementById('ruleCategory').value = (rule.actions?.category || []).join(', ');
    document.getElementById('ruleEnabled').checked = rule.enabled !== false;
  } else {
    title.textContent = '🤖 Add Auto-Tagging Rule';
    document.getElementById('ruleId').value = '';
    document.getElementById('ruleName').value = '';
    document.getElementById('ruleType').value = 'amount';
    document.getElementById('ruleAmountMin').value = '';
    document.getElementById('ruleAmountMax').value = '';
    document.getElementById('ruleMerchantContains').value = '';
    document.getElementById('ruleMerchantExact').value = '';
    document.getElementById('ruleDirection').value = '';
    document.getElementById('ruleScope').value = 'personal';
    document.getElementById('ruleCategory').value = '';
    document.getElementById('ruleEnabled').checked = true;
  }
  
  toggleRuleConditions();
  modal.style.display = 'flex';
}

function toggleRuleConditions() {
  const type = document.getElementById('ruleType').value;
  const amountEl = document.getElementById('amountConditions');
  const merchantEl = document.getElementById('merchantConditions');
  
  amountEl.style.display = (type === 'amount' || type === 'combined') ? 'block' : 'none';
  merchantEl.style.display = (type === 'merchant' || type === 'combined') ? 'block' : 'none';
}

async function saveRule() {
  const ruleId = document.getElementById('ruleId').value;
  const type = document.getElementById('ruleType').value;
  
  const conditions = {};
  
  if (type === 'amount' || type === 'combined') {
    const min = document.getElementById('ruleAmountMin').value;
    const max = document.getElementById('ruleAmountMax').value;
    if (min !== '') conditions.amount_min = parseFloat(min);
    if (max !== '') conditions.amount_max = parseFloat(max);
  }
  
  if (type === 'merchant' || type === 'combined') {
    const contains = document.getElementById('ruleMerchantContains').value.trim();
    const exact = document.getElementById('ruleMerchantExact').value.trim();
    if (contains) conditions.merchant_contains = contains;
    if (exact) conditions.merchant_exact = exact;
  }
  
  const direction = document.getElementById('ruleDirection').value;
  if (direction) conditions.direction = direction;
  
  const categoryStr = document.getElementById('ruleCategory').value.trim();
  const category = categoryStr ? categoryStr.split(',').map(c => c.trim()).filter(c => c) : [];
  
  const data = {
    name: document.getElementById('ruleName').value || 'Unnamed Rule',
    type: type,
    enabled: document.getElementById('ruleEnabled').checked,
    conditions: conditions,
    actions: {
      scope: document.getElementById('ruleScope').value,
      category: category
    }
  };
  
  let result;
  if (ruleId) {
    // Update existing
    result = await fetch(`/api/rules/${ruleId}`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    }).then(r => r.json());
  } else {
    // Create new
    result = await postJSON('/api/rules', data);
  }
  
  if (result && result.ok) {
    document.getElementById('ruleModal').style.display = 'none';
    await loadRules();
    showToast('Rule saved successfully!', 'success');
  } else {
    alert('Failed to save rule');
  }
}

function editRule(ruleId) {
  const rule = autoRules.find(r => r.id === ruleId);
  if (rule) openRuleModal(rule);
}

async function deleteRule(ruleId) {
  if (!confirm('Delete this rule?')) return;
  
  const result = await fetch(`/api/rules/${ruleId}`, {method: 'DELETE'}).then(r => r.json());
  if (result.ok) {
    await loadRules();
    showToast('Rule deleted', 'info');
  }
}

// ============ RULE TESTER ============
function testRule() {
  const merchant = document.getElementById('testMerchant')?.value?.trim() || '';
  const amount = parseFloat(document.getElementById('testAmount')?.value) || 0;
  const direction = document.getElementById('testDirection')?.value || 'debit';
  const resultDiv = document.getElementById('ruleTesterResult');
  
  if (!merchant && !amount) {
    resultDiv.innerHTML = '<div class="test-result no-match">Enter merchant name or amount to test</div>';
    return;
  }
  
  // Find matching rule (same logic as backend)
  const sortedRules = [...autoRules].filter(r => r.enabled).sort((a, b) => (a.priority || 999) - (b.priority || 999));
  
  let matchedRule = null;
  for (const rule of sortedRules) {
    const c = rule.conditions || {};
    let matches = true;
    
    // Check amount conditions
    if (rule.type === 'amount' || rule.type === 'combined') {
      if (c.amount_min !== undefined && amount < c.amount_min) matches = false;
      if (c.amount_max !== undefined && amount > c.amount_max) matches = false;
    }
    
    // Check merchant conditions
    if (rule.type === 'merchant' || rule.type === 'combined') {
      const lowerMerchant = merchant.toLowerCase();
      if (c.merchant_contains) {
        const keywords = c.merchant_contains.split(',').map(k => k.trim().toLowerCase());
        const hasMatch = keywords.some(k => lowerMerchant.includes(k));
        if (!hasMatch) matches = false;
      }
      if (c.merchant_exact) {
        const exactKeywords = c.merchant_exact.split(',').map(k => k.trim().toLowerCase());
        if (!exactKeywords.includes(lowerMerchant)) matches = false;
      }
    }
    
    // Check direction
    if (c.direction && c.direction !== direction) matches = false;
    
    if (matches) {
      matchedRule = rule;
      break;
    }
  }
  
  if (matchedRule) {
    const actions = matchedRule.actions || {};
    resultDiv.innerHTML = `
      <div class="test-result match">
        <div class="match-icon">✓</div>
        <div class="match-details">
          <div class="match-rule">Matches: <strong>${matchedRule.name}</strong></div>
          <div class="match-actions">
            → Scope: <span class="tag">${actions.scope || 'unchanged'}</span>
            ${actions.category?.length ? `Category: <span class="tag">${actions.category.join(', ')}</span>` : ''}
          </div>
        </div>
        <button class="btn-sm" onclick="editRule('${matchedRule.id}')">Edit Rule</button>
      </div>
    `;
  } else {
    resultDiv.innerHTML = `
      <div class="test-result no-match">
        <div class="match-icon">✗</div>
        <div class="match-details">
          <strong>No rule matches</strong>
          <div class="hint">This transaction would not be auto-tagged.</div>
        </div>
        <button class="btn-accent btn-sm" onclick="createRuleFromTest()">Create Rule</button>
      </div>
    `;
  }
}

function createRuleFromTest() {
  const merchant = document.getElementById('testMerchant')?.value?.trim() || '';
  const amount = parseFloat(document.getElementById('testAmount')?.value) || 0;
  
  const ruleName = merchant ? `${merchant} transactions` : `Amount ₹${amount}`;
  const ruleType = merchant ? 'merchant' : 'amount';
  
  openRuleModal({
    name: ruleName,
    type: ruleType,
    conditions: merchant 
      ? { merchant_contains: merchant.toLowerCase() }
      : { amount_min: Math.max(0, amount - 50), amount_max: amount + 50 },
    actions: { scope: 'personal', category: [] },
    enabled: true
  });
}

// ============ INLINE RULE CREATION ============
function createRuleFromTransaction(txId) {
  const txn = allTransactions.find(t => t.id === txId);
  if (!txn) {
    showToast('Transaction not found', 'error');
    return;
  }
  
  // Pre-fill rule based on transaction
  const merchantKeyword = extractMerchantKeyword(txn.counterparty);
  
  openRuleModal({
    name: `${merchantKeyword} transactions`,
    type: 'merchant',
    conditions: { merchant_contains: merchantKeyword.toLowerCase() },
    actions: { 
      scope: txn.scope || 'personal', 
      category: txn.category || [] 
    },
    enabled: true
  });
  
  showToast(`Creating rule for "${merchantKeyword}"`, 'info');
}

function extractMerchantKeyword(counterparty) {
  // Extract meaningful keyword from counterparty string
  // Remove common prefixes/suffixes and UPI IDs
  let name = counterparty || 'Unknown';
  
  // Remove UPI patterns like @paytm, @ybl, etc.
  name = name.replace(/@[a-z]+$/i, '').trim();
  
  // Remove "UPI-" prefix
  name = name.replace(/^UPI[-\s]*/i, '').trim();
  
  // Take first word if it's too long
  const words = name.split(/[\s\-_]+/);
  if (words[0] && words[0].length >= 3) {
    return words[0];
  }
  
  return name.slice(0, 20);
}

async function resetRulesToDefaults(mode) {
  const msg = mode === 'replace' 
    ? 'This will REPLACE all your rules with the defaults. Continue?' 
    : 'This will add any missing default rules. Continue?';
  
  if (!confirm(msg)) return;
  
  const result = await postJSON('/api/rules/reset', {mode: mode});
  if (result && result.ok) {
    showToast(`✅ Rules ${mode === 'replace' ? 'reset to' : 'merged with'} defaults (${result.count} rules)`);
    await loadRules();
  }
}

async function previewRules() {
  const skipManual = document.getElementById('skipManuallyEdited')?.checked ?? true;
  const result = await postJSON('/api/rules/preview', {only_unreviewed: skipManual});
  if (!result) return;
  
  const modal = document.getElementById('previewModal');
  const content = document.getElementById('previewContent');
  
  if (result.count === 0) {
    content.innerHTML = `<p class="hint">No transactions will be affected by the current rules.${skipManual ? ' (Manually edited transactions are being skipped)' : ''}</p>`;
  } else {
    content.innerHTML = `
      <div class="preview-count">${result.count} transactions will be updated${skipManual ? ' (skipping manually edited)' : ' (including all transactions)'}</div>
      ${result.matches.slice(0, 50).map(m => `
        <div class="preview-item">
          <div class="merchant">${m.counterparty}</div>
          <div>₹${m.amount}</div>
          <div>
            <span class="old">${m.current_scope} / ${(m.current_category || []).join(',') || '—'}</span>
          </div>
          <div>
            <span class="new">${m.new_scope} / ${(m.new_category || []).join(',')}</span>
            <div class="rule-applied">${m.rule_name}</div>
          </div>
        </div>
      `).join('')}
      ${result.count > 50 ? `<p class="hint">...and ${result.count - 50} more</p>` : ''}
    `;
  }
  
  modal.style.display = 'flex';
}

async function applyRules() {
  const skipManual = document.getElementById('skipManuallyEdited')?.checked ?? true;
  const msg = skipManual 
    ? 'Apply rules to unedited transactions? Manually edited transactions will be preserved.'
    : 'Apply rules to ALL transactions? This will overwrite your manual edits!';
  
  if (!confirm(msg)) return;
  
  const result = await postJSON('/api/rules/apply', {only_unreviewed: skipManual});
  if (result && result.ok) {
    showToast(`✅ Updated ${result.updated} of ${result.total} transactions${skipManual ? ' (manual edits preserved)' : ''}`);
    document.getElementById('previewModal').style.display = 'none';
    // Refresh views
    if (currentView === 'dashboard') renderDashboard();
    if (currentView === 'transactions') loadTable();
  } else {
    showToast('❌ Failed to apply rules', 'error');
  }
}

// Merchant autocomplete for quick rule creation
function setupMerchantAutocomplete() {
  const input = document.getElementById('merchantSearch');
  const dropdown = document.getElementById('merchantSuggestions');
  if (!input || !dropdown) return;
  
  input.addEventListener('input', () => {
    const query = input.value.toLowerCase();
    if (query.length < 2) {
      dropdown.classList.remove('show');
      return;
    }
    
    const matches = merchants.filter(m => m.name.toLowerCase().includes(query)).slice(0, 10);
    
    if (matches.length === 0) {
      dropdown.classList.remove('show');
      return;
    }
    
    dropdown.innerHTML = matches.map(m => `
      <div class="suggestion-item" data-merchant="${m.name}">
        <span class="merchant-name">${m.name}</span>
        <span class="merchant-stats">${m.count} txns · ₹${m.total.toLocaleString()}</span>
      </div>
    `).join('');
    
    dropdown.classList.add('show');
    
    dropdown.querySelectorAll('.suggestion-item').forEach(item => {
      item.addEventListener('click', () => {
        const merchantName = item.dataset.merchant;
        dropdown.classList.remove('show');
        input.value = '';
        
        // Open rule modal pre-filled with this merchant
        openRuleModal({
          name: `${merchantName} transactions`,
          type: 'merchant',
          conditions: {merchant_contains: merchantName.toLowerCase()},
          actions: {scope: 'personal', category: []},
          enabled: true
        });
      });
    });
  });
  
  // Hide dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.remove('show');
    }
  });
}

async function clearAllData() {
  if (!confirm('Are you sure you want to delete ALL transactions? This cannot be undone!')) return;
  if (!confirm('Really delete everything?')) return;
  
  const txs = await fetchJSON('/api/transactions?limit=10000');
  if (!txs || txs.length === 0) {
    alert('No transactions to delete');
    return;
  }
  
  const ids = txs.map(t => t.id);
  const result = await postJSON('/api/transactions/bulk-delete', {ids});
  
  if (result && result.ok) {
    alert('All data cleared');
    render();
  } else {
    alert('Failed to clear data');
  }
}

// Upload
function showUpload() {
  document.getElementById('uploadZone').style.display = 'block';
}

function hideUpload() {
  document.getElementById('uploadZone').style.display = 'none';
  document.getElementById('uploadProgress').style.display = 'none';
}

async function handleUpload(file) {
  if (!file || !file.name.endsWith('.pdf')) {
    showToast('Please select a PDF file', 'error');
    return;
  }
  
  document.getElementById('uploadProgress').style.display = 'block';
  document.getElementById('progressFill').style.width = '30%';
  document.getElementById('progressText').textContent = 'Uploading...';
  
  const fd = new FormData();
  fd.append('file', file);
  
  try {
    document.getElementById('progressFill').style.width = '60%';
    const r = await fetch('/api/load', {method: 'POST', body: fd});
    const j = await r.json();
    
    document.getElementById('progressFill').style.width = '100%';
    
    if (j.ok) {
      const autoTagMsg = j.auto_tagged > 0 ? ` (${j.auto_tagged} auto-tagged)` : '';
      document.getElementById('progressText').textContent = `✓ Uploaded ${j.count} transactions${autoTagMsg}`;
      showToast(`Imported ${j.count} transactions${autoTagMsg}`, 'success');
      setTimeout(() => {
        hideUpload();
        render();
      }, 1500);
    } else {
      document.getElementById('progressText').textContent = '✗ Error: ' + (j.error || 'Upload failed');
      showToast('Upload failed: ' + (j.error || 'Unknown error'), 'error');
    }
  } catch (e) {
    document.getElementById('progressText').textContent = '✗ Error: ' + e.message;
    showToast('Upload failed: ' + e.message, 'error');
  }
}

// Keyboard shortcuts
function handleKeyboard(e) {
  // Don't trigger if typing in input
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {
    if (e.key === 'Escape') e.target.blur();
    return;
  }
  
  switch (e.key) {
    case '/':
      e.preventDefault();
      document.getElementById('filterSearch').focus();
      break;
    case 'u':
    case 'U':
      showUpload();
      break;
    case 'e':
    case 'E':
      window.location = '/api/export.csv';
      break;
    case 'd':
    case 'D':
      switchView('dashboard');
      break;
    case 't':
    case 'T':
      switchView('transactions');
      break;
    case 's':
    case 'S':
      switchView('settings');
      break;
    case 'a':
    case 'A':
      switchView('stats');
      break;
    case '?':
      toggleShortcuts();
      break;
    case 'Escape':
      closeModal();
      closeDeleteModal();
      hideUpload();
      document.getElementById('shortcutsHelp').style.display = 'none';
      break;
    case 'ArrowDown':
      e.preventDefault();
      selectRow(selectedRowIdx + 1);
      break;
    case 'ArrowUp':
      e.preventDefault();
      selectRow(Math.max(0, selectedRowIdx - 1));
      break;
    case 'Enter':
      if (selectedRowIdx >= 0) {
        const rows = document.querySelectorAll('#txTable tbody tr');
        if (rows[selectedRowIdx]) {
          openModal(rows[selectedRowIdx].dataset.id);
        }
      }
      break;
    case 'Delete':
    case 'Backspace':
      if (selectedRowIdx >= 0 && currentView === 'transactions') {
        const rows = document.querySelectorAll('#txTable tbody tr');
        if (rows[selectedRowIdx]) {
          confirmDelete([rows[selectedRowIdx].dataset.id]);
        }
      }
      break;
  }
}

function toggleShortcuts() {
  const panel = document.getElementById('shortcutsHelp');
  panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

// Main render
async function render() {
  try {
    await loadMeta();
    switchView(currentView);
  } catch (err) {
    console.error('Render error:', err);
  }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  render();
  
  // Sidebar navigation
  document.querySelectorAll('.sidebar a[data-view]').forEach(a => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      switchView(a.dataset.view);
    });
  });
  
  // Filters - with null checks
  const applyBtn = document.getElementById('applyFilters');
  if (applyBtn) applyBtn.addEventListener('click', loadTable);
  
  // Enter key on search triggers filter
  const searchInput = document.getElementById('filterSearch');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        loadTable();
      }
    });
  }
  
  // Enter key on filter selects also triggers
  ['filterScope', 'filterCategory', 'filterDirection'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => loadTable());
    }
  });
  
  const clearBtn = document.getElementById('clearFilters');
  if (clearBtn) clearBtn.addEventListener('click', () => {
    document.getElementById('filterScope').value = '';
    document.getElementById('filterCategory').value = '';
    document.getElementById('filterDirection').value = '';
    document.getElementById('filterSearch').value = '';
    loadTable();
  });
  
  // Save filter button
  const saveFilterBtn = document.getElementById('saveFilterBtn');
  if (saveFilterBtn) saveFilterBtn.addEventListener('click', showSaveFilterModal);
  
  // Load saved filters
  loadSavedFilters();
  
  // Initialize daily chart controls (date range, chart type)
  initDailyChartControls();
  
  // Sorting
  document.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => {
      const sort = th.dataset.sort;
      if (currentSort === sort) {
        currentOrder = currentOrder === 'desc' ? 'asc' : 'desc';
      } else {
        currentSort = sort;
        currentOrder = 'desc';
      }
      loadTable();
    });
  });
  
  // Select all checkbox
  const selectAllCb = document.getElementById('selectAll');
  if (selectAllCb) {
    selectAllCb.addEventListener('change', (e) => toggleSelectAll(e.target.checked));
  }
  
  // Bulk delete
  const bulkDelBtn = document.getElementById('bulkDeleteBtn');
  if (bulkDelBtn) {
    bulkDelBtn.addEventListener('click', () => {
      confirmDelete(Array.from(selectedTxIds));
    });
  }
  
  // Upload
  document.getElementById('showUploadModal').addEventListener('click', showUpload);
  document.getElementById('closeUpload').addEventListener('click', hideUpload);
  document.getElementById('fileInput').addEventListener('change', (e) => {
    if (e.target.files[0]) handleUpload(e.target.files[0]);
  });
  
  // Drag and drop
  const uploadZone = document.getElementById('uploadZone');
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
  });
  uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
  });
  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]);
  });
  
  // Export
  document.getElementById('exportCsvBtn').addEventListener('click', () => {
    window.location = '/api/export.csv';
  });
  
  // Modal
  document.getElementById('modalCancel').addEventListener('click', closeModal);
  document.getElementById('modalSave').addEventListener('click', saveModal);
  
  // Delete modal
  document.getElementById('cancelDelete').addEventListener('click', closeDeleteModal);
  document.getElementById('confirmDelete').addEventListener('click', executeDelete);
  
  // Settings
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');
  if (saveSettingsBtn) saveSettingsBtn.addEventListener('click', saveSettings);
  
  const addCatBtn = document.getElementById('addCategoryBtn');
  if (addCatBtn) addCatBtn.addEventListener('click', addCategory);
  
  const clearDataBtn = document.getElementById('clearAllDataBtn');
  if (clearDataBtn) clearDataBtn.addEventListener('click', clearAllData);
  
  // Auto-tagging rules
  const addRuleBtn = document.getElementById('addRuleBtn');
  if (addRuleBtn) addRuleBtn.addEventListener('click', () => openRuleModal());
  
  const previewRulesBtn = document.getElementById('previewRulesBtn');
  if (previewRulesBtn) previewRulesBtn.addEventListener('click', previewRules);
  
  const applyRulesBtn = document.getElementById('applyRulesBtn');
  if (applyRulesBtn) applyRulesBtn.addEventListener('click', applyRules);
  
  const ruleSaveBtn = document.getElementById('ruleSave');
  if (ruleSaveBtn) ruleSaveBtn.addEventListener('click', saveRule);
  
  const ruleCancelBtn = document.getElementById('ruleCancel');
  if (ruleCancelBtn) ruleCancelBtn.addEventListener('click', () => {
    document.getElementById('ruleModal').style.display = 'none';
  });
  
  const previewApplyBtn = document.getElementById('previewApply');
  if (previewApplyBtn) previewApplyBtn.addEventListener('click', applyRules);
  
  const previewCancelBtn = document.getElementById('previewCancel');
  if (previewCancelBtn) previewCancelBtn.addEventListener('click', () => {
    document.getElementById('previewModal').style.display = 'none';
  });
  
  // Logout
  document.getElementById('logoutBtn').addEventListener('click', async () => {
    await postJSON('/api/logout', {});
    window.location.href = '/login';
  });
  
  // Shortcuts panel
  document.getElementById('showShortcuts').addEventListener('click', toggleShortcuts);
  document.getElementById('closeShortcuts').addEventListener('click', () => {
    document.getElementById('shortcutsHelp').style.display = 'none';
  });
  
  // Trend toggle
  document.querySelectorAll('.trend-toggle button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.trend-toggle button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      trendPeriod = btn.dataset.period;
      renderTrends();
    });
  });
  
  // Global keyboard
  document.addEventListener('keydown', handleKeyboard);
});

// ============ ACTIVITY LOGS ============

async function loadLogs() {
  const action = document.getElementById('logActionFilter')?.value || '';
  const search = document.getElementById('logSearchInput')?.value || '';
  
  const params = new URLSearchParams();
  if (action) params.set('action', action);
  if (search) params.set('search', search);
  
  const result = await fetchJSON('/api/logs?' + params.toString());
  if (!result) return;
  
  const container = document.getElementById('logsList');
  if (!container) return;
  
  if (!result.logs || result.logs.length === 0) {
    container.innerHTML = '<div class="empty-state">No activity logs yet</div>';
    return;
  }
  
  container.innerHTML = result.logs.map(log => {
    const date = new Date(log.timestamp);
    const timeStr = date.toLocaleDateString('en-IN') + ' ' + date.toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit'});
    
    let icon = '●';
    let iconClass = '';
    switch(log.action) {
      case 'upload': icon = '↑'; iconClass = 'log-upload'; break;
      case 'edit': icon = '✎'; iconClass = 'log-edit'; break;
      case 'delete': icon = '✕'; iconClass = 'log-delete'; break;
      case 'bulk_delete': icon = '✕'; iconClass = 'log-delete'; break;
      case 'auto_tag': icon = '⚡'; iconClass = 'log-auto'; break;
      case 'restore': icon = '↺'; iconClass = 'log-restore'; break;
    }
    
    let details = '';
    const d = log.details || {};
    switch(log.action) {
      case 'upload':
        details = `Uploaded <strong>${d.filename}</strong> (${d.transactions_added} transactions)`;
        break;
      case 'edit':
        details = `Edited <strong>${d.counterparty}</strong>`;
        if (d.new?.scope) details += ` → scope: ${d.new.scope}`;
        if (d.new?.category) details += ` → category: ${d.new.category.join(', ')}`;
        break;
      case 'delete':
        details = `Deleted <strong>${d.counterparty}</strong> (₹${d.amount})`;
        break;
      case 'bulk_delete':
        details = `Deleted <strong>${d.count}</strong> transactions`;
        break;
      case 'auto_tag':
        details = `Auto-tagged <strong>${d.updated}</strong> of ${d.total} transactions`;
        break;
      case 'restore':
        details = `Restored <strong>${d.counterparty}</strong>`;
        break;
      default:
        details = JSON.stringify(d).substring(0, 100);
    }
    
    return `
      <div class="log-item">
        <span class="log-icon ${iconClass}">${icon}</span>
        <div class="log-content">
          <div class="log-details">${details}</div>
          <div class="log-meta">${timeStr} · ${log.user}</div>
        </div>
      </div>
    `;
  }).join('');
}

async function clearLogs() {
  if (!confirm('Clear all activity logs? This cannot be undone.')) return;
  
  const result = await postJSON('/api/logs/clear', {});
  if (result && result.ok) {
    showToast('Logs cleared');
    loadLogs();
  }
}

// ============ TRASH ============

async function showTrashModal() {
  const result = await fetchJSON('/api/trash');
  if (!result) return;
  
  const container = document.getElementById('trashList');
  if (!container) return;
  
  if (!result || result.length === 0) {
    container.innerHTML = '<div class="empty-state">Trash is empty</div>';
  } else {
    container.innerHTML = result.map(item => {
      const t = item.transaction;
      const delDate = new Date(item.deleted_at).toLocaleDateString('en-IN');
      return `
        <div class="trash-item">
          <div class="trash-info">
            <strong>${t.counterparty}</strong>
            <span class="trash-amount ${t.direction === 'credit' ? 'credit' : 'debit'}">
              ${t.direction === 'credit' ? '+' : '-'}₹${t.amount}
            </span>
            <span class="trash-date">Deleted ${delDate}</span>
          </div>
          <button class="btn-sm btn-outline" onclick="restoreTransaction('${item.id}')">Restore</button>
        </div>
      `;
    }).join('');
  }
  
  document.getElementById('trashModal').style.display = 'flex';
}

function closeTrashModal() {
  document.getElementById('trashModal').style.display = 'none';
}

async function restoreTransaction(id) {
  const result = await postJSON(`/api/trash/restore/${id}`, {});
  if (result && result.ok) {
    showToast('Transaction restored');
    showTrashModal();  // Refresh
  }
}

async function emptyTrash() {
  if (!confirm('Permanently delete all trashed transactions? This cannot be undone.')) return;
  
  const result = await postJSON('/api/trash/empty', {});
  if (result && result.ok) {
    showToast(`Deleted ${result.deleted} transactions permanently`);
    closeTrashModal();
  }
}

// ============ DATA HEALTH BANNER ============

function renderHealthBanner(health) {
  if (!health) return;
  
  // Reviewed percentage
  const reviewedEl = document.getElementById('healthReviewed');
  const reviewedPctEl = document.getElementById('healthReviewedPct');
  if (reviewedPctEl) {
    reviewedPctEl.textContent = `${health.reviewed_pct}%`;
    if (health.reviewed_pct >= 80) reviewedEl?.classList.add('success');
    else if (health.reviewed_pct < 50) reviewedEl?.classList.add('warning');
  }
  
  // Uncategorized count
  const uncatEl = document.getElementById('healthUncategorized');
  const uncatCountEl = document.getElementById('healthUncategorizedCount');
  if (uncatCountEl) {
    uncatCountEl.textContent = health.uncategorized_count;
    if (health.uncategorized_count > 10) uncatEl?.classList.add('warning');
    else if (health.uncategorized_count === 0) uncatEl?.classList.add('success');
  }
  
  // Top uncategorized merchant
  const topMerchantEl = document.getElementById('healthTopMerchantName');
  if (topMerchantEl) {
    if (health.top_uncategorized_merchant) {
      topMerchantEl.textContent = `${health.top_uncategorized_merchant} (${health.top_uncategorized_count})`;
    } else {
      topMerchantEl.textContent = 'None';
    }
  }
}

// ============ DUPLICATES ============

async function checkDuplicates() {
  const duplicates = await fetchJSON('/api/duplicates');
  if (!duplicates) return;
  
  const container = document.getElementById('duplicatesContent');
  
  if (!duplicates || duplicates.length === 0) {
    container.innerHTML = '<div class="empty-state">No potential duplicates found 🎉</div>';
  } else {
    container.innerHTML = duplicates.map(group => `
      <div class="duplicate-group" data-key="${group.key}">
        <div class="duplicate-group-header">
          <strong>${group.transactions[0].counterparty}</strong>
          <span class="count-badge">${group.count} similar</span>
        </div>
        ${group.transactions.map((t, idx) => `
          <div class="duplicate-item">
            <input type="radio" name="keep_${group.key}" value="${t.id}" ${idx === 0 ? 'checked' : ''}>
            <div class="duplicate-item-info">
              <span class="amount">₹${t.amount}</span>
              <span class="date">${formatDateTime(t.datetime)}</span>
            </div>
          </div>
        `).join('')}
        <div class="duplicate-actions">
          <button class="btn-sm btn-accent" onclick="mergeDuplicateGroup('${group.key}')">Keep Selected, Delete Others</button>
          <button class="btn-sm btn-outline" onclick="ignoreDuplicateGroup(this)">Ignore</button>
        </div>
      </div>
    `).join('');
  }
  
  document.getElementById('duplicatesModal').style.display = 'flex';
}

function closeDuplicatesModal() {
  document.getElementById('duplicatesModal').style.display = 'none';
}

async function mergeDuplicateGroup(groupKey) {
  const group = document.querySelector(`.duplicate-group[data-key="${groupKey}"]`);
  if (!group) return;
  
  const selected = group.querySelector(`input[name="keep_${groupKey}"]:checked`);
  if (!selected) {
    showToast('Select which transaction to keep', 'error');
    return;
  }
  
  const keepId = selected.value;
  const allIds = Array.from(group.querySelectorAll('input[type="radio"]')).map(r => r.value);
  const deleteIds = allIds.filter(id => id !== keepId);
  
  const result = await postJSON('/api/duplicates/merge', { keep_id: keepId, delete_ids: deleteIds });
  if (result && result.ok) {
    showToast(`Merged: kept 1, deleted ${result.deleted}`);
    group.remove();
    
    // Check if any groups left
    if (document.querySelectorAll('.duplicate-group').length === 0) {
      document.getElementById('duplicatesContent').innerHTML = '<div class="empty-state">All duplicates resolved 🎉</div>';
    }
  }
}

function ignoreDuplicateGroup(btn) {
  const group = btn.closest('.duplicate-group');
  if (group) group.remove();
  
  if (document.querySelectorAll('.duplicate-group').length === 0) {
    document.getElementById('duplicatesContent').innerHTML = '<div class="empty-state">All duplicates reviewed</div>';
  }
}

// ============ CATEGORY DRILLDOWN ============

async function openCategoryDrilldown(category) {
  const data = await fetchJSON(`/api/categories/${encodeURIComponent(category)}/drilldown?scope=personal`);
  if (!data) return;
  
  // Update drawer content
  document.getElementById('drilldownTitle').textContent = `📊 ${category.charAt(0).toUpperCase() + category.slice(1)}`;
  document.getElementById('drilldownTotal').textContent = humanAmount(-data.total_spent);
  document.getElementById('drilldownCount').textContent = data.transaction_count;
  
  // Render merchants
  const maxAmount = data.merchants.length > 0 ? data.merchants[0].amount : 1;
  document.getElementById('drilldownMerchants').innerHTML = data.merchants.map(m => `
    <div class="merchant-item">
      <div style="flex:1">
        <div class="merchant-name">${m.name}</div>
        <div class="merchant-bar"><div class="merchant-bar-fill" style="width:${(m.amount/maxAmount)*100}%"></div></div>
      </div>
      <div style="text-align:right">
        <div class="merchant-amount">₹${m.amount.toLocaleString('en-IN')}</div>
        <div class="merchant-count">${m.count} txns · avg ₹${m.avg_amount}</div>
      </div>
    </div>
  `).join('') || '<div class="empty-state">No merchants</div>';
  
  // Render recent transactions
  document.getElementById('drilldownRecent').innerHTML = data.recent_transactions.map(t => `
    <div class="recent-mini-item">
      <span class="date">${t.date}</span>
      <span class="merchant">${t.merchant}</span>
      <span class="amount ${t.direction}">₹${t.amount.toLocaleString('en-IN')}</span>
    </div>
  `).join('') || '<div class="empty-state">No transactions</div>';
  
  // Show drawer
  document.getElementById('drilldownDrawer').style.display = 'block';
}

function closeDrilldown() {
  document.getElementById('drilldownDrawer').style.display = 'none';
}

// ============ SAVED FILTERS ============

let savedFilters = [];

async function loadSavedFilters() {
  const filters = await fetchJSON('/api/filters');
  if (filters) {
    savedFilters = filters;
    renderSavedFilters();
  }
}

function renderSavedFilters() {
  const container = document.getElementById('savedFiltersList');
  if (!container) return;
  
  if (savedFilters.length === 0) {
    container.innerHTML = '<div style="font-size:11px;color:var(--muted-dim)">No saved filters</div>';
    return;
  }
  
  container.innerHTML = savedFilters.map(f => `
    <div class="saved-filter-item" onclick="applySavedFilter('${f.id}')">
      <span class="filter-name">${f.name}</span>
      <span class="filter-delete" onclick="event.stopPropagation(); deleteSavedFilter('${f.id}')">✕</span>
    </div>
  `).join('');
}

function applySavedFilter(filterId) {
  const filter = savedFilters.find(f => f.id === filterId);
  if (!filter) return;
  
  const f = filter.filters;
  if (f.scope) document.getElementById('filterScope').value = f.scope;
  if (f.category) document.getElementById('filterCategory').value = f.category;
  if (f.direction) document.getElementById('filterDirection').value = f.direction;
  if (f.search) document.getElementById('filterSearch').value = f.search;
  
  applyFilters();
  showToast(`Applied filter: ${filter.name}`);
}

function showSaveFilterModal() {
  document.getElementById('filterNameInput').value = '';
  document.getElementById('saveFilterModal').style.display = 'flex';
}

async function confirmSaveFilter() {
  const name = document.getElementById('filterNameInput').value.trim();
  if (!name) {
    showToast('Please enter a name', 'error');
    return;
  }
  
  const filters = {
    scope: document.getElementById('filterScope').value,
    category: document.getElementById('filterCategory').value,
    direction: document.getElementById('filterDirection').value,
    search: document.getElementById('filterSearch').value
  };
  
  const result = await postJSON('/api/filters', { name, filters });
  if (result && result.ok) {
    showToast('Filter saved!');
    document.getElementById('saveFilterModal').style.display = 'none';
    loadSavedFilters();
  }
}

async function deleteSavedFilter(filterId) {
  const result = await fetch(`/api/filters/${filterId}`, { method: 'DELETE' }).then(r => r.json());
  if (result && result.ok) {
    showToast('Filter deleted');
    loadSavedFilters();
  }
}
