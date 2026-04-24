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

  function setBadge(el, status) {
    if (!el) return;
    const normalized = String(status || 'pending').toLowerCase();
    el.dataset.status = normalized;
    el.textContent = normalized;
    el.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-warning', 'text-bg-secondary', 'text-bg-primary');
    if (normalized === 'done' || normalized === 'ok') {
      el.classList.add('text-bg-success');
    } else if (normalized === 'failed' || normalized === 'dead_letter') {
      el.classList.add('text-bg-danger');
    } else if (normalized === 'queued' || normalized === 'running' || normalized === 'processing' || normalized === 'retrying') {
      el.classList.add('text-bg-warning');
    } else if (normalized === 'pending') {
      el.classList.add('text-bg-secondary');
    } else {
      el.classList.add('text-bg-primary');
    }
  }

  function refreshSourceRows(sourceConfigs, sourceStatusSnapshot) {
    const rows = document.querySelectorAll('tr[data-source-id]');
    rows.forEach((row) => {
      const sourceId = row.dataset.sourceId;
      const source = (sourceConfigs || []).find((item) => String(item.id) === String(sourceId));
      if (!source) return;
      const snapshot = (sourceStatusSnapshot || {})[sourceId] || {};
      const liveStatus = snapshot.live_status || source.last_status || 'pending';
      setBadge(document.getElementById(`source-live-status-${sourceId}`), liveStatus);
      setText(`source-last-action-${sourceId}`, snapshot.last_action || source.last_status || '-');
      setText(`source-last-action-at-${sourceId}`, snapshot.last_action_at || source.last_run_at || source.last_scheduled_at || '-');
    });
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
      setText('kpi-queue-pending', data.control.queue_pending_total);
      setText('kpi-queue-processing', data.control.queue_processing_total);
      setText('kpi-queue-dlq', data.control.queue_dead_letter_total);
      setText('kpi-destination-delivery', data.control.destination_delivery_total);
      setText('kpi-destination-failures', data.control.destination_delivery_failed_total);
      setText('kpi-source-active', data.source_cycle.active_count);
      setText('kpi-source-due', data.source_cycle.due_count);
      setText('kpi-source-overdue', data.source_cycle.overdue_count);
      setText('kpi-source-next-cycle', data.source_cycle.next_run_at);
      refreshSourceRows(data.source_configs || [], data.source_status_snapshot || {});
    } catch (_err) {
    }
  }

  renderChart();
  refreshDashboard();
  setInterval(refreshDashboard, 15000);
})();
