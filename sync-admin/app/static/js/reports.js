(function () {
  const charts = {};
  const palette = ['#14b8a6', '#2563eb', '#f59e0b', '#22c55e', '#ef4444', '#6366f1', '#ec4899'];
  const rowsPerPage = 10;

  function parseJson(value) {
    try {
      return JSON.parse(value || '[]');
    } catch (_error) {
      return [];
    }
  }

  function money(value) {
    return Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function parseLocalizedNumber(value) {
    const normalized = String(value || '')
      .replace(/[^\d,.-]/g, '')
      .replace(/\./g, '')
      .replace(',', '.');
    return Number(normalized) || 0;
  }

  function normalizeChartLabel(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim()
      .toLowerCase();
  }

  function circularColors(labels) {
    return labels.map((label, index) => {
      if (normalizeChartLabel(label) === 'nao informado') return '#000000';
      return palette[index % palette.length];
    });
  }

  function chartConfig(canvas, type, color) {
    const labels = parseJson(canvas.dataset.labels);
    const values = parseJson(canvas.dataset.values);
    const isCircular = type === 'doughnut';
    const legendLimit = Number(canvas.dataset.legendLimit || 8);
    return {
      type,
      data: {
        labels,
        datasets: [{
          label: canvas.dataset.label || 'Valor de vendas',
          data: values,
          borderColor: isCircular ? '#ffffff' : color,
          backgroundColor: isCircular ? circularColors(labels) : `${color}24`,
          borderWidth: isCircular ? 3 : 2,
          borderRadius: type === 'bar' ? 10 : 0,
          fill: type === 'line',
          tension: 0.36,
          pointRadius: type === 'line' ? 4 : undefined,
          pointHoverRadius: type === 'line' ? 7 : undefined,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        animation: { duration: 520, easing: 'easeOutQuart' },
        plugins: {
          legend: {
            display: isCircular && labels.length <= legendLimit,
            position: 'bottom',
            labels: { boxWidth: 10, usePointStyle: true },
          },
          tooltip: {
            backgroundColor: '#0f172a',
            padding: 12,
            cornerRadius: 12,
            callbacks: {
              label(context) {
                return `${context.label}: ${money(context.raw)}`;
              },
            },
          },
        },
        scales: isCircular ? {} : {
          x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
          y: { beginAtZero: true, ticks: { callback: value => Number(value).toLocaleString('pt-BR') } },
        },
        onClick(_event, elements, chart) {
          if (!elements.length) return;
          const label = chart.data.labels[elements[0].index];
          if (canvas.dataset.drillParam) {
            navigateReportFilter(canvas.dataset.drillParam, label, canvas.dataset.drillView);
            return;
          }
          applyTableSearch(label);
        },
      },
    };
  }

  function destroyCharts() {
    Object.values(charts).forEach(chart => chart.destroy());
    Object.keys(charts).forEach(key => delete charts[key]);
  }

  function renderChart(id, type, color) {
    const canvas = document.getElementById(id);
    if (!canvas || typeof Chart === 'undefined') return;
    const labels = parseJson(canvas.dataset.labels);
    if (!labels.length) {
      const empty = document.createElement('div');
      empty.className = 'bi-empty-chart';
      empty.textContent = 'Sem dados para o filtro atual.';
      canvas.replaceWith(empty);
      return;
    }
    charts[id] = new Chart(canvas, chartConfig(canvas, type, color));
  }

  function renderAllCharts() {
    destroyCharts();
    renderChart('reportDailyChart', 'line', '#14b8a6');
    renderChart('reportTopChart', 'bar', '#f59e0b');
    renderChart('reportTypeChart', 'doughnut', '#2563eb');
    renderChart('reportPaymentChart', 'doughnut', '#22c55e');
    renderChart('reportFamilyChart', 'bar', '#ef4444');
    renderChart('reportTerminalChart', 'bar', '#64748b');
  }

  function setupTheme() {
    const storedTheme = localStorage.getItem('sync-admin-theme');
    if (storedTheme === 'dark') document.body.dataset.theme = 'dark';
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.addEventListener('click', () => {
        const nextTheme = document.body.dataset.theme === 'dark' ? 'light' : 'dark';
        if (nextTheme === 'dark') {
          document.body.dataset.theme = 'dark';
        } else {
          delete document.body.dataset.theme;
        }
        localStorage.setItem('sync-admin-theme', nextTheme);
      });
    });
  }

  function visibleRows(table) {
    return Array.from(table.querySelectorAll('tbody tr')).filter(row => row.dataset.filtered !== 'true');
  }

  function applyPage(table, page) {
    const rows = visibleRows(table);
    const totalPages = Math.max(1, Math.ceil(rows.length / rowsPerPage));
    const currentPage = Math.min(Math.max(page, 1), totalPages);
    rows.forEach((row, index) => {
      row.style.display = index >= (currentPage - 1) * rowsPerPage && index < currentPage * rowsPerPage ? '' : 'none';
    });
    table.dataset.page = String(currentPage);
    renderPagination(table, totalPages, currentPage);
    updateTableCount(table);
  }

  function renderPagination(table, totalPages, currentPage) {
    const pagination = document.querySelector('[data-table-pagination]');
    if (!pagination) return;
    pagination.innerHTML = '';
    for (let page = 1; page <= totalPages; page += 1) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `bi-page-button${page === currentPage ? ' is-active' : ''}`;
      button.textContent = String(page);
      button.addEventListener('click', () => applyPage(table, page));
      pagination.appendChild(button);
    }
  }

  function updateTableCount(table) {
    const count = document.querySelector('[data-table-count]');
    if (!count) return;
    count.textContent = String(visibleRows(table).length);
  }

  function applyTableSearch(term) {
    const search = document.querySelector('[data-table-search]');
    if (!search || !term) return;
    search.value = term;
    search.dispatchEvent(new Event('input'));
  }

  function reportUrlWithFilter(param, value, view) {
    const form = document.querySelector('[data-report-filters]');
    const params = form
      ? new URLSearchParams(new FormData(form))
      : new URLSearchParams(window.location.search);
    if (view) params.set('report_view', view);
    if (param && value) params.set(param, value);
    const action = form?.action || window.location.pathname;
    return `${action}?${params.toString()}`;
  }

  function navigateReportFilter(param, value, view) {
    if (!param || !value) return;
    window.location.href = reportUrlWithFilter(param, value, view);
  }

  function setupTableTools() {
    const table = document.querySelector('[data-report-table]');
    const search = document.querySelector('[data-table-search]');
    if (!table || !search) return;
    const rows = Array.from(table.querySelectorAll('tbody tr'));

    search.addEventListener('input', () => {
      const term = search.value.trim().toLowerCase();
      rows.forEach(row => {
        row.dataset.filtered = row.textContent.toLowerCase().includes(term) ? 'false' : 'true';
      });
      applyPage(table, 1);
    });

    table.querySelectorAll('th[data-sort]').forEach((header, columnIndex) => {
      header.addEventListener('click', () => {
        const direction = header.dataset.direction === 'asc' ? 'desc' : 'asc';
        header.dataset.direction = direction;
        const sorted = rows.slice().sort((a, b) => {
          const left = a.children[columnIndex]?.textContent.trim() || '';
          const right = b.children[columnIndex]?.textContent.trim() || '';
          const leftValue = header.dataset.sort === 'number' ? parseLocalizedNumber(left) : left;
          const rightValue = header.dataset.sort === 'number' ? parseLocalizedNumber(right) : right;
          if (leftValue < rightValue) return direction === 'asc' ? -1 : 1;
          if (leftValue > rightValue) return direction === 'asc' ? 1 : -1;
          return 0;
        });
        const body = table.querySelector('tbody');
        sorted.forEach(row => body.appendChild(row));
        applyPage(table, Number(table.dataset.page || 1));
      });
    });

    applyPage(table, 1);
  }

  function setupDrilldown() {
    document.querySelectorAll('[data-drilldown]').forEach(button => {
      button.addEventListener('click', () => applyTableSearch(button.dataset.drilldown));
    });
    document.querySelectorAll('[data-drill-param][data-drill-value]').forEach(element => {
      element.addEventListener('click', event => {
        event.preventDefault();
        navigateReportFilter(element.dataset.drillParam, element.dataset.drillValue, element.dataset.drillView);
      });
    });
  }

  async function replaceDashboardFrom(url) {
    const dashboard = document.querySelector('.bi-dashboard');
    if (!dashboard) return;
    dashboard.classList.add('bi-loading');
    try {
      const response = await fetch(url, { headers: { Accept: 'text/html' } });
      if (!response.ok) return;
      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const nextDashboard = doc.querySelector('.bi-dashboard');
      if (!nextDashboard) return;
      destroyCharts();
      dashboard.replaceWith(nextDashboard);
      window.history.replaceState({}, '', url);
      initReports();
    } finally {
      const current = document.querySelector('.bi-dashboard');
      if (current) current.classList.remove('bi-loading');
    }
  }

  function setupAjaxFilters() {
    document.querySelectorAll('[data-report-filters]').forEach(form => {
      form.addEventListener('submit', event => {
        event.preventDefault();
        const url = `${form.action || window.location.pathname}?${new URLSearchParams(new FormData(form)).toString()}`;
        replaceDashboardFrom(url);
      });
    });
  }

  function setupAutoRefresh() {
    const dashboard = document.querySelector('.bi-dashboard');
    if (!dashboard || !dashboard.dataset.dashboardEndpoint || dashboard.dataset.refreshBound === 'true') return;
    dashboard.dataset.refreshBound = 'true';
    const refreshSeconds = Number(dashboard.dataset.refreshSeconds || 60);
    window.setInterval(async () => {
      if (!document.body.contains(dashboard)) return;
      try {
        const response = await fetch(dashboard.dataset.dashboardEndpoint, { headers: { Accept: 'application/json' } });
        if (!response.ok) return;
        const payload = await response.json();
        document.querySelectorAll('[data-kpi-key]').forEach(card => {
          const item = (payload.kpi_cards || []).find(kpi => kpi.key === card.dataset.kpiKey);
          if (!item) return;
          const value = card.querySelector('[data-kpi-value]');
          const hint = card.querySelector('[data-kpi-hint]');
          if (value) value.textContent = item.value;
          if (hint) hint.textContent = item.hint;
        });
      } catch (_error) {
        /* Auto-refresh is best effort; manual filters keep the page usable. */
      }
    }, Math.max(30, refreshSeconds) * 1000);
  }

  function initReports() {
    renderAllCharts();
    setupTheme();
    setupTableTools();
    setupDrilldown();
    setupAjaxFilters();
    setupAutoRefresh();
  }

  initReports();
})();
