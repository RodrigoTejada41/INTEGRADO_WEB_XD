(function () {
  const canvas = document.getElementById('dailyChart');
  let chart = null;

  function renderChart() {
    if (!canvas) return;
    const labels = JSON.parse(canvas.dataset.labels || '[]');
    const values = JSON.parse(canvas.dataset.values || '[]');
    chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Registros',
          data: values,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37,99,235,.2)',
          fill: true,
          tension: 0.2,
        }],
      },
      options: { responsive: true, maintainAspectRatio: false },
    });
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = String(value);
  }

  async function refreshDashboard() {
    try {
      const resp = await fetch('/dashboard/data', { headers: { 'Accept': 'application/json' } });
      if (!resp.ok) return;
      const data = await resp.json();
      setText('kpi-total-records', data.summary.total_records);
      setText('kpi-last-received', data.summary.last_received);
      setText('kpi-api-status', data.summary.api_status);
      setText('kpi-failed-batches', data.summary.failed_batches);

      setText('kpi-control-health', data.control.api_health);
      setText('kpi-control-batches', data.control.sync_batches_total);
      setText('kpi-control-inserted', data.control.sync_records_inserted_total);
      setText('kpi-control-updated', data.control.sync_records_updated_total);
      setText('kpi-control-app-failures', data.control.sync_application_failures_total);
      setText('kpi-control-preflight-errors', data.control.preflight_connection_errors_total);
      setText('kpi-control-retention', data.control.retention_processed_total);
    } catch (_err) {
    }
  }

  renderChart();
  refreshDashboard();
  setInterval(refreshDashboard, 15000);
})();
