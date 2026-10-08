/**
 * RAMPulse - Real-Time Memory Dashboard & Process Monitor
 * Frontend Controller & Chart Visualizations
 */

document.addEventListener('DOMContentLoaded', () => {
  // Global Application State
  const state = {
    isPaused: false,
    refreshInterval: 2,
    viewMode: 'grouped', // 'grouped' | 'flat'
    search: '',
    minMb: 0,
    sortBy: 'rss',
    sortOrder: 'desc',
    processes: [],
    systemSummary: null,
    history: [],
    topApps: [],
    ws: null,
    wsConnected: false,
    pendingKillTarget: null,
    pollingTimer: null,
  };

  // DOM Element References
  const dom = {
    // Header & Meta
    metaHost: document.getElementById('meta-host'),
    metaOs: document.getElementById('meta-os'),
    metaUptime: document.getElementById('meta-uptime'),
    metaCores: document.getElementById('meta-cores'),
    connectionStatus: document.getElementById('connection-status'),
    liveIndicator: document.getElementById('live-indicator'),
    btnPause: document.getElementById('btn-pause'),
    btnPauseText: document.getElementById('btn-pause-text'),
    btnRefresh: document.getElementById('btn-refresh'),
    refreshSelect: document.getElementById('refresh-interval-select'),

    // Health Banner
    healthBanner: document.getElementById('health-banner'),
    bannerStatus: document.getElementById('banner-status'),
    bannerMessage: document.getElementById('banner-message'),
    bannerSummaryMetric: document.getElementById('banner-summary-metric'),

    // RAM Card
    ramPercent: document.getElementById('ram-percent'),
    ramBarUsed: document.getElementById('ram-bar-used'),
    ramUsed: document.getElementById('ram-used'),
    ramFree: document.getElementById('ram-free'),
    ramTotal: document.getElementById('ram-total'),

    // Swap Card
    swapPercent: document.getElementById('swap-percent'),
    swapBarUsed: document.getElementById('swap-bar-used'),
    swapUsed: document.getElementById('swap-used'),
    swapFree: document.getElementById('swap-free'),
    swapTotal: document.getElementById('swap-total'),

    // Telemetry Card
    procAppsCount: document.getElementById('proc-apps-count'),
    procTotalCount: document.getElementById('proc-total-count'),
    procThreadsCount: document.getElementById('proc-threads-count'),
    procHeavyCount: document.getElementById('proc-heavy-count'),

    // Top Hog Card
    topHogName: document.getElementById('top-hog-name'),
    topHogPercent: document.getElementById('top-hog-percent'),
    topHogMemory: document.getElementById('top-hog-memory'),
    topHogInstances: document.getElementById('top-hog-instances'),
    topHogCategory: document.getElementById('top-hog-category'),

    // Toolbar & Controls
    btnModeGrouped: document.getElementById('btn-mode-grouped'),
    btnModeFlat: document.getElementById('btn-mode-flat'),
    filterSearch: document.getElementById('filter-search'),
    btnClearSearch: document.getElementById('btn-clear-search'),
    pillBtns: document.querySelectorAll('.pill-btn'),
    selectSort: document.getElementById('select-sort'),

    // Process Table
    procsTable: document.getElementById('procs-table'),
    procsTbody: document.getElementById('procs-tbody'),
    footerCount: document.getElementById('footer-count'),

    // Modals
    modalDetails: document.getElementById('modal-details'),
    modalProcTitle: document.getElementById('modal-proc-title'),
    modalProcBadge: document.getElementById('modal-proc-badge'),
    modalProcBody: document.getElementById('modal-proc-body'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalDismissBtn: document.getElementById('modal-dismiss-btn'),
    modalKillBtn: document.getElementById('modal-kill-btn'),

    modalConfirmKill: document.getElementById('modal-confirm-kill'),
    confirmKillClose: document.getElementById('confirm-kill-close'),
    btnCancelKill: document.getElementById('btn-cancel-kill'),
    btnDoKill: document.getElementById('btn-do-kill'),
    killTargetName: document.getElementById('kill-target-name'),
    killTargetMeta: document.getElementById('kill-target-meta'),

    // Toast Container
    toastContainer: document.getElementById('toast-container'),
  };

  // Chart Instances
  let chartTimeline = null;
  let chartDistribution = null;
  let chartTopBars = null;

  // ==========================================================================
  // Chart Initializations
  // ==========================================================================
  function initCharts() {
    Chart.defaults.color = '#9ca3af';
    Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";

    // 1. Timeline Line Chart
    const ctxTimeline = document.getElementById('chart-timeline').getContext('2d');
    const gradCyan = ctxTimeline.createLinearGradient(0, 0, 0, 240);
    gradCyan.addColorStop(0, 'rgba(6, 182, 212, 0.35)');
    gradCyan.addColorStop(1, 'rgba(6, 182, 212, 0.0)');

    chartTimeline = new Chart(ctxTimeline, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'RAM %',
            data: [],
            borderColor: '#06b6d4',
            backgroundColor: gradCyan,
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            pointHoverRadius: 4,
          },
          {
            label: 'Swap %',
            data: [],
            borderColor: '#8b5cf6',
            backgroundColor: 'transparent',
            borderWidth: 2,
            borderDash: [4, 4],
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            pointHoverRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: { maxTicksLimit: 8, font: { size: 10 } },
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              callback: (val) => `${val}%`,
              stepSize: 25,
              font: { size: 10 },
            },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: '#111827',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            titleFont: { size: 11 },
            bodyFont: { size: 11 },
            callbacks: {
              label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}%`,
            },
          },
        },
      },
    });

    // 2. RAM Distribution Donut Chart
    const ctxDistribution = document.getElementById('chart-distribution').getContext('2d');
    chartDistribution = new Chart(ctxDistribution, {
      type: 'doughnut',
      data: {
        labels: ['Used RAM', 'Free RAM'],
        datasets: [
          {
            data: [0, 100],
            backgroundColor: ['#06b6d4', '#10b981'],
            borderColor: '#0a0d14',
            borderWidth: 3,
            hoverOffset: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 12,
              padding: 12,
              font: { size: 11 },
            },
          },
          tooltip: {
            backgroundColor: '#111827',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ${ctx.raw} GB`,
            },
          },
        },
      },
    });

    // 3. Top Apps Horizontal Bar Chart
    const ctxTopBars = document.getElementById('chart-top-bars').getContext('2d');
    chartTopBars = new Chart(ctxTopBars, {
      type: 'bar',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Occupied RAM (MB)',
            data: [],
            backgroundColor: [
              'rgba(244, 63, 94, 0.75)',
              'rgba(245, 158, 11, 0.75)',
              'rgba(6, 182, 212, 0.75)',
              'rgba(139, 92, 246, 0.75)',
              'rgba(16, 185, 129, 0.75)',
              'rgba(14, 165, 233, 0.75)',
              'rgba(168, 85, 247, 0.75)',
              'rgba(234, 179, 8, 0.75)',
            ],
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: {
              callback: (val) => `${val} MB`,
              font: { size: 10 },
            },
          },
          y: {
            grid: { display: false },
            ticks: {
              font: { size: 11, weight: '600' },
              color: '#e5e7eb',
            },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#111827',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            callbacks: {
              label: (ctx) => ` Occupied: ${ctx.raw} MB`,
            },
          },
        },
      },
    });
  }

  // ==========================================================================
  // WebSocket Stream & Polling Fallback
  // ==========================================================================
  function setupWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/live`;

    try {
      state.ws = new WebSocket(wsUrl);

      state.ws.onopen = () => {
        state.wsConnected = true;
        dom.connectionStatus.textContent = 'LIVE (WebSocket)';
        dom.liveIndicator.classList.remove('status-offline');
        dom.liveIndicator.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        // Send initial interval
        state.ws.send(JSON.stringify({ action: 'set_interval', interval: state.refreshInterval }));
      };

      state.ws.onmessage = (event) => {
        if (state.isPaused) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'telemetry') {
            handleTelemetryUpdate(data);
          }
        } catch (err) {
          console.error('Error parsing live payload', err);
        }
      };

      state.ws.onclose = () => {
        state.wsConnected = false;
        dom.connectionStatus.textContent = 'POLLING (HTTP)';
        dom.liveIndicator.style.borderColor = 'rgba(245, 158, 11, 0.3)';
        startPolling();
        // Retry WebSocket after 5s
        setTimeout(setupWebSocket, 5000);
      };

      state.ws.onerror = () => {
        state.wsConnected = false;
        dom.connectionStatus.textContent = 'POLLING (HTTP)';
        startPolling();
      };
    } catch (e) {
      startPolling();
    }
  }

  function startPolling() {
    if (state.pollingTimer) return;
    state.pollingTimer = setInterval(async () => {
      if (state.isPaused) return;
      await fetchAllData();
    }, state.refreshInterval * 1000);
  }

  // ==========================================================================
  // Data Fetching & Handling
  // ==========================================================================
  async function fetchAllData() {
    try {
      const [summaryRes, historyRes, procsRes] = await Promise.all([
        fetch('/api/system').then((r) => r.json()),
        fetch('/api/history').then((r) => r.json()),
        fetchProcessesData(),
      ]);

      handleTelemetryUpdate({
        summary: summaryRes,
        history: historyRes.history || [],
        top_apps: [],
      });

      if (procsRes) {
        renderProcessTable(procsRes.processes);
      }
    } catch (err) {
      console.error('Fetch error:', err);
    }
  }

  async function fetchProcessesData() {
    const params = new URLSearchParams({
      grouped: state.viewMode === 'grouped',
      sort_by: state.sortBy,
      sort_order: state.sortOrder,
      search: state.search,
      min_mb: state.minMb,
    });
    const res = await fetch(`/api/processes?${params.toString()}`);
    return await res.json();
  }

  async function refreshProcessList() {
    try {
      const data = await fetchProcessesData();
      state.processes = data.processes || [];
      renderProcessTable(state.processes);
    } catch (err) {
      console.error('Failed to load processes', err);
    }
  }

  function handleTelemetryUpdate(payload) {
    if (payload.summary) {
      state.systemSummary = payload.summary;
      updateSummaryUI(payload.summary);
    }

    if (payload.history && payload.history.length > 0) {
      state.history = payload.history;
      updateTimelineChart(payload.history);
    }

    if (payload.top_apps && payload.top_apps.length > 0) {
      state.topApps = payload.top_apps;
      updateTopAppsUI(payload.top_apps);
    }

    // Refresh process table regularly if user is not in a modal
    if (!dom.modalDetails.open && !dom.modalConfirmKill.open) {
      refreshProcessList();
    }
  }

  // ==========================================================================
  // UI Update Routines
  // ==========================================================================
  function updateSummaryUI(summary) {
    const { system, ram, swap, health } = summary;

    // Header Meta
    dom.metaHost.textContent = system.hostname;
    dom.metaOs.textContent = system.os;
    dom.metaUptime.textContent = `Up: ${system.uptime}`;
    dom.metaCores.textContent = system.cpu_cores;

    // Health Banner
    dom.healthBanner.className = `health-banner banner-${health.color === 'emerald' ? 'optimal' : health.color === 'amber' ? 'moderate' : health.color === 'orange' ? 'high' : 'critical'}`;
    dom.bannerStatus.textContent = health.status;
    dom.bannerMessage.textContent = health.message;
    dom.bannerSummaryMetric.textContent = `RAM: ${ram.percent}% Used (${ram.used_formatted} / ${ram.total_formatted})`;

    // RAM Card
    dom.ramPercent.textContent = `${ram.percent}%`;
    dom.ramBarUsed.style.width = `${Math.min(100, ram.percent)}%`;
    dom.ramUsed.textContent = ram.used_formatted;
    dom.ramFree.textContent = ram.available_formatted;
    dom.ramTotal.textContent = ram.total_formatted;

    // Swap Card
    dom.swapPercent.textContent = `${swap.percent}%`;
    dom.swapBarUsed.style.width = `${Math.min(100, swap.percent)}%`;
    dom.swapUsed.textContent = swap.used_formatted;
    dom.swapFree.textContent = swap.free_formatted;
    dom.swapTotal.textContent = swap.total_formatted;

    // Update Donut Chart
    if (chartDistribution) {
      chartDistribution.data.datasets[0].data = [ram.used_gb, ram.available_gb];
      chartDistribution.data.labels = [`Used (${ram.used_gb} GB)`, `Available (${ram.available_gb} GB)`];
      chartDistribution.update('none');
    }
  }

  function updateTimelineChart(history) {
    if (!chartTimeline || !history || history.length === 0) return;

    const labels = history.map((h) => h.timestamp);
    const ramData = history.map((h) => h.ram_percent);
    const swapData = history.map((h) => h.swap_percent);

    chartTimeline.data.labels = labels;
    chartTimeline.data.datasets[0].data = ramData;
    chartTimeline.data.datasets[1].data = swapData;
    chartTimeline.update('none');
  }

  function updateTopAppsUI(topApps) {
    if (!topApps || topApps.length === 0) return;

    // Top Hog Card (#1 consumer)
    const hog = topApps[0];
    dom.topHogName.textContent = hog.display_name;
    dom.topHogPercent.textContent = `${hog.memory_percent}%`;
    dom.topHogMemory.textContent = hog.rss_formatted;
    dom.topHogInstances.textContent = hog.instance_count > 1 ? `${hog.instance_count} instances` : `PID ${hog.pid || 'single'}`;
    dom.topHogCategory.textContent = hog.category;

    // Top Apps Bar Chart
    if (chartTopBars) {
      const top8 = topApps.slice(0, 8);
      chartTopBars.data.labels = top8.map((app) => app.display_name);
      chartTopBars.data.datasets[0].data = top8.map((app) => app.rss_mb);
      chartTopBars.update();
    }
  }

  // ==========================================================================
  // Process Table Rendering
  // ==========================================================================
  function renderProcessTable(procs) {
    if (!procs || procs.length === 0) {
      dom.procsTbody.innerHTML = `
        <tr>
          <td colspan="8" class="loading-state">
            <span>No matching processes found for the specified filters.</span>
          </td>
        </tr>
      `;
      dom.footerCount.textContent = 'Showing 0 processes';
      return;
    }

    // Telemetry stats
    const totalThreads = procs.reduce((acc, p) => acc + (p.num_threads || 1), 0);
    const heavyCount = procs.filter((p) => p.rss_mb >= 500).length;
    dom.procTotalCount.textContent = procs.length;
    dom.procThreadsCount.textContent = totalThreads;
    dom.procHeavyCount.textContent = heavyCount;
    dom.procAppsCount.textContent = `${procs.length} ${state.viewMode === 'grouped' ? 'Apps' : 'PIDs'}`;
    dom.footerCount.textContent = `Showing ${procs.length} ${state.viewMode === 'grouped' ? 'grouped applications' : 'individual processes'}`;

    const rowsHtml = procs
      .map((p) => {
        const isGrouped = state.viewMode === 'grouped';
        const initial = (p.display_name || p.name || 'P').charAt(0).toUpperCase();

        // Memory bar severity
        const memPercent = p.memory_percent || 0;
        const fillClass = memPercent > 10 ? 'fill-high' : memPercent > 4 ? 'fill-mid' : '';

        // PID / Instance formatting
        let pidCol = '';
        if (isGrouped && p.instance_count > 1) {
          pidCol = `<span class="instance-badge">${p.instance_count} instances</span>`;
        } else if (p.pid != null) {
          pidCol = `<span class="pid-pill">${p.pid}</span>`;
        } else {
          pidCol = `<span class="pid-pill">-</span>`;
        }

        // Actions
        let actionButtons = '';
        const canEnd = !p.is_protected && (p.pid != null || (p.pids && p.pids.length === 1));
        const targetPid = p.pid != null ? p.pid : (p.pids && p.pids.length === 1 ? p.pids[0] : null);

        if (targetPid != null) {
          actionButtons += `<button class="btn-table-action btn-inspect" data-pid="${targetPid}" title="Inspect full details">Details</button>`;
        }

        if (p.is_protected) {
          actionButtons += `<button class="btn-table-action btn-disabled" title="Windows Core Process Protected" disabled>&#128274; Protected</button>`;
        } else if (canEnd && targetPid != null) {
          actionButtons += `<button class="btn-table-action btn-kill-action" data-kill-pid="${targetPid}" data-kill-name="${escapeHtml(p.display_name)}" data-kill-mem="${p.rss_formatted}" title="End process">End Task</button>`;
        }

        return `
          <tr data-pid="${targetPid || ''}">
            <td class="col-name">
              <div class="proc-name-cell">
                <div class="proc-icon">${initial}</div>
                <div class="proc-title-stack">
                  <span class="proc-display-name">${escapeHtml(p.display_name)}</span>
                  <span class="proc-raw-name">${escapeHtml(p.name)}</span>
                </div>
              </div>
            </td>
            <td class="col-pid">${pidCol}</td>
            <td class="col-category">
              <span class="badge-category">${escapeHtml(p.category || 'Other')}</span>
            </td>
            <td class="col-mem text-right">
              <div class="mem-cell-stack">
                <span class="mem-value">${p.rss_formatted}</span>
                <div class="mem-mini-bar">
                  <div class="mem-mini-fill ${fillClass}" style="width: ${Math.min(100, memPercent * 5)}%;"></div>
                </div>
              </div>
            </td>
            <td class="col-percent text-right mono-cell">${p.memory_percent}%</td>
            <td class="col-cpu text-right mono-cell">${p.cpu_percent}%</td>
            <td class="col-user mono-cell" title="${escapeHtml(p.username)}">${escapeHtml(truncate(p.username, 16))}</td>
            <td class="col-actions text-center">
              <div class="action-btn-group">${actionButtons}</div>
            </td>
          </tr>
        `;
      })
      .join('');

    dom.procsTbody.innerHTML = rowsHtml;
  }

  // ==========================================================================
  // Process Details & Kill Modals
  // ==========================================================================
  async function showProcessDetails(pid) {
    if (!pid) return;
    try {
      const res = await fetch(`/api/processes/${pid}`);
      if (!res.ok) throw new Error('Process details unavailable');
      const d = await res.json();

      dom.modalProcTitle.textContent = `${d.display_name} (PID ${d.pid})`;
      dom.modalProcBadge.textContent = d.category;

      dom.modalProcBody.innerHTML = `
        <div class="detail-row">
          <span class="detail-label">Binary Name</span>
          <span class="detail-value">${escapeHtml(d.name)}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Occupied RAM (RSS)</span>
          <span class="detail-value font-bold" style="color: var(--accent-cyan);">${d.rss_formatted} (${d.memory_percent}% of RAM)</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Virtual Memory (VMS)</span>
          <span class="detail-value">${d.vms_formatted}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">CPU Usage</span>
          <span class="detail-value">${d.cpu_percent}%</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Status</span>
          <span class="detail-value">${d.status}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Threads Count</span>
          <span class="detail-value">${d.num_threads}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">User Account</span>
          <span class="detail-value">${escapeHtml(d.username)}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Started At</span>
          <span class="detail-value">${d.create_time}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Executable Location</span>
          <span class="detail-value" style="font-size: 11px;">${escapeHtml(d.exe)}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Command Line</span>
          <span class="detail-value" style="font-size: 11px;">${escapeHtml(d.cmdline)}</span>
        </div>
      `;

      if (d.is_protected) {
        dom.modalKillBtn.style.display = 'none';
      } else {
        dom.modalKillBtn.style.display = 'inline-flex';
        dom.modalKillBtn.onclick = () => {
          dom.modalDetails.close();
          confirmKillProcess(d.pid, d.display_name, d.rss_formatted);
        };
      }

      dom.modalDetails.showModal();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  function confirmKillProcess(pid, name, memoryFormatted) {
    state.pendingKillTarget = { pid, name };
    dom.killTargetName.textContent = name;
    dom.killTargetMeta.textContent = `PID: ${pid} | Memory to release: ${memoryFormatted}`;
    dom.modalConfirmKill.showModal();
  }

  async function executeKillProcess() {
    if (!state.pendingKillTarget) return;
    const { pid, name } = state.pendingKillTarget;
    dom.modalConfirmKill.close();

    try {
      const res = await fetch(`/api/processes/${pid}/kill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: false }),
      });

      const result = await res.json();
      if (!res.ok || !result.success) {
        throw new Error(result.detail || result.error || 'Failed to terminate process');
      }

      showToast(`Terminated ${name} (PID ${pid})`, 'success');
      // Refresh process list instantly
      await refreshProcessList();
      await fetchAllData();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      state.pendingKillTarget = null;
    }
  }

  // ==========================================================================
  // Toast Notifications
  // ==========================================================================
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span>${type === 'success' ? '&#10003;' : '&#9888;'}</span>
      <span>${escapeHtml(message)}</span>
    `;
    dom.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 4000);
  }

  // ==========================================================================
  // Event Listeners & Interactive Controls
  // ==========================================================================

  // View Mode toggle: Grouped vs Flat
  dom.btnModeGrouped.addEventListener('click', () => {
    state.viewMode = 'grouped';
    dom.btnModeGrouped.classList.add('active');
    dom.btnModeFlat.classList.remove('active');
    refreshProcessList();
  });

  dom.btnModeFlat.addEventListener('click', () => {
    state.viewMode = 'flat';
    dom.btnModeFlat.classList.add('active');
    dom.btnModeGrouped.classList.remove('active');
    refreshProcessList();
  });

  // Search input with debounce
  let searchTimeout = null;
  dom.filterSearch.addEventListener('input', (e) => {
    state.search = e.target.value.trim();
    dom.btnClearSearch.classList.toggle('hidden', state.search.length === 0);
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(refreshProcessList, 250);
  });

  dom.btnClearSearch.addEventListener('click', () => {
    dom.filterSearch.value = '';
    state.search = '';
    dom.btnClearSearch.classList.add('hidden');
    refreshProcessList();
  });

  // Min RAM Filter Pills
  dom.pillBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      dom.pillBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.minMb = parseFloat(btn.dataset.min || '0');
      refreshProcessList();
    });
  });

  // Sort dropdown
  dom.selectSort.addEventListener('change', (e) => {
    state.sortBy = e.target.value;
    refreshProcessList();
  });

  // Table header sorting
  dom.procsTable.querySelectorAll('th[data-sort]').forEach((th) => {
    th.addEventListener('click', () => {
      const field = th.dataset.sort;
      if (state.sortBy === field) {
        state.sortOrder = state.sortOrder === 'desc' ? 'asc' : 'desc';
      } else {
        state.sortBy = field;
        state.sortOrder = 'desc';
      }
      dom.selectSort.value = field;
      refreshProcessList();
    });
  });

  // Row inspection and Kill button delegation
  dom.procsTbody.addEventListener('click', (e) => {
    // Check if clicked button
    const killBtn = e.target.closest('[data-kill-pid]');
    if (killBtn) {
      e.stopPropagation();
      const pid = parseInt(killBtn.dataset.killPid, 10);
      const name = killBtn.dataset.killName;
      const mem = killBtn.dataset.killMem;
      confirmKillProcess(pid, name, mem);
      return;
    }

    const inspectBtn = e.target.closest('[data-pid]');
    if (inspectBtn) {
      const pid = parseInt(inspectBtn.dataset.pid, 10);
      if (pid) showProcessDetails(pid);
      return;
    }

    // Clicked table row
    const row = e.target.closest('tr[data-pid]');
    if (row && row.dataset.pid) {
      const pid = parseInt(row.dataset.pid, 10);
      if (pid) showProcessDetails(pid);
    }
  });

  // Modal Closers
  dom.modalCloseBtn.onclick = () => dom.modalDetails.close();
  dom.modalDismissBtn.onclick = () => dom.modalDetails.close();
  dom.confirmKillClose.onclick = () => dom.modalConfirmKill.close();
  dom.btnCancelKill.onclick = () => dom.modalConfirmKill.close();
  dom.btnDoKill.onclick = executeKillProcess;

  // Header Controls: Pause/Resume
  dom.btnPause.addEventListener('click', () => {
    state.isPaused = !state.isPaused;
    if (state.isPaused) {
      dom.btnPauseText.textContent = 'Resume';
      dom.liveIndicator.style.opacity = '0.5';
    } else {
      dom.btnPauseText.textContent = 'Pause';
      dom.liveIndicator.style.opacity = '1';
    }
    if (state.ws && state.wsConnected) {
      state.ws.send(JSON.stringify({ action: state.isPaused ? 'pause' : 'resume' }));
    }
  });

  // Refresh interval select
  dom.refreshSelect.addEventListener('change', (e) => {
    state.refreshInterval = parseFloat(e.target.value);
    if (state.ws && state.wsConnected) {
      state.ws.send(JSON.stringify({ action: 'set_interval', interval: state.refreshInterval }));
    }
    if (state.pollingTimer) {
      clearInterval(state.pollingTimer);
      state.pollingTimer = null;
      startPolling();
    }
  });

  // Manual refresh button
  dom.btnRefresh.addEventListener('click', async () => {
    dom.btnRefresh.classList.add('loading');
    await fetchAllData();
    setTimeout(() => dom.btnRefresh.classList.remove('loading'), 300);
  });

  // ==========================================================================
  // Helper Utilities
  // ==========================================================================
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function truncate(str, maxLen) {
    if (!str) return '';
    return str.length > maxLen ? str.slice(0, maxLen - 1) + '…' : str;
  }

  // ==========================================================================
  // Initialization Sequence
  // ==========================================================================
  initCharts();
  fetchAllData();
  setupWebSocket();
});
