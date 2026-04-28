(function () {
  const charts = {};
  const palette = ['#0f766e', '#0369a1', '#b45309', '#15803d', '#7c2d12', '#4338ca', '#be123c'];

  function parseJson(value) {
    try {
      return JSON.parse(value || '[]');
    } catch (_error) {
      return [];
    }
  }

  function chartConfig(canvas, type, color) {
    const labels = parseJson(canvas.dataset.labels);
    const values = parseJson(canvas.dataset.values);
    const isCircular = type === 'doughnut';
    return {
      type,
      data: {
        labels,
        datasets: [{
          label: canvas.dataset.label || 'Valor de vendas',
          data: values,
          borderColor: isCircular ? '#ffffff' : color,
          backgroundColor: isCircular ? palette : `${color}26`,
          borderWidth: isCircular ? 2 : 2,
          fill: type === 'line',
          tension: 0.32,
          pointRadius: type === 'line' ? 4 : undefined,
          pointHoverRadius: type === 'line' ? 7 : undefined,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: isCircular, position: 'bottom' },
          tooltip: {
            callbacks: {
              label(context) {
                const value = Number(context.raw || 0);
                return `${context.label}: ${value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}`;
              },
            },
          },
        },
        scales: isCircular ? {} : {
          x: { grid: { display: false } },
          y: { beginAtZero: true, ticks: { callback: value => Number(value).toLocaleString('pt-BR') } },
        },
        onClick(_event, elements, chart) {
          if (!elements.length) return;
          const index = elements[0].index;
          const label = chart.data.labels[index];
          const search = document.querySelector('[data-table-search]');
          if (search && label) {
            search.value = label;
            search.dispatchEvent(new Event('input'));
          }
        },
      },
    };
  }

  function renderChart(id, type, color) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const labels = parseJson(canvas.dataset.labels);
    if (!labels.length) return;
    charts[id] = new Chart(canvas, chartConfig(canvas, type, color));
  }

  function renderAllCharts() {
    renderChart('reportDailyChart', 'line', '#0f766e');
    renderChart('reportTopChart', 'bar', '#b45309');
    renderChart('reportTypeChart', 'doughnut', '#0369a1');
    renderChart('reportPaymentChart', 'doughnut', '#15803d');
    renderChart('reportFamilyChart', 'bar', '#7c2d12');
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

  function setupTableTools() {
    const table = document.querySelector('[data-report-table]');
    const search = document.querySelector('[data-table-search]');
    const count = document.querySelector('[data-table-count]');
    if (!table || !search) return;
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const updateCount = () => {
      if (!count) return;
      count.textContent = String(rows.filter(row => row.style.display !== 'none').length);
    };
    search.addEventListener('input', () => {
      const term = search.value.trim().toLowerCase();
      rows.forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(term) ? '' : 'none';
      });
      updateCount();
    });
    table.querySelectorAll('th[data-sort]').forEach((header, columnIndex) => {
      header.addEventListener('click', () => {
        const direction = header.dataset.direction === 'asc' ? 'desc' : 'asc';
        header.dataset.direction = direction;
        const sorted = rows.slice().sort((a, b) => {
          const left = a.children[columnIndex]?.textContent.trim() || '';
          const right = b.children[columnIndex]?.textContent.trim() || '';
          const leftValue = header.dataset.sort === 'number' ? Number(left.replace(',', '.')) || 0 : left;
          const rightValue = header.dataset.sort === 'number' ? Number(right.replace(',', '.')) || 0 : right;
          if (leftValue < rightValue) return direction === 'asc' ? -1 : 1;
          if (leftValue > rightValue) return direction === 'asc' ? 1 : -1;
          return 0;
        });
        const body = table.querySelector('tbody');
        sorted.forEach(row => body.appendChild(row));
      });
    });
    updateCount();
  }

  async function setupAutoRefresh() {
    const dashboard = document.querySelector('.bi-dashboard');
    if (!dashboard || !dashboard.dataset.dashboardEndpoint) return;
    const refreshSeconds = Number(dashboard.dataset.refreshSeconds || 60);
    async function refresh() {
      dashboard.classList.add('bi-loading');
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
      } finally {
        dashboard.classList.remove('bi-loading');
      }
    }
    window.setInterval(refresh, Math.max(30, refreshSeconds) * 1000);
  }

  renderAllCharts();
  setupTheme();
  setupTableTools();
  setupAutoRefresh();
})();
