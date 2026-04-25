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

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
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
      setText(`source-queued-count-${sourceId}`, snapshot.queued_count || '0');
      setText(`source-running-count-${sourceId}`, snapshot.running_count || '0');
      setText(`source-failed-count-${sourceId}`, snapshot.failed_count || '0');
    });
  }

  function renderAttentionRows(rows) {
    const body = document.getElementById('source-attention-body');
    if (!body) return;
    const items = Array.isArray(rows) ? rows : [];
    const canSync = String(body.dataset.canSync || '0') === '1';
    setText('kpi-source-attention-count', items.length);
    if (items.length === 0) {
      body.innerHTML = '<tr><td colspan="8" class="text-muted">Nenhuma fonte exige atencao no momento.</td></tr>';
      return;
    }
    body.innerHTML = items.map((row) => {
      const status = String(row.status || 'pending').toLowerCase();
      const badgeClass = status === 'failed' ? 'text-bg-danger' : (status === 'queued' || status === 'running' ? 'text-bg-warning' : 'text-bg-secondary');
      const actionCell = canSync
        ? `<form method="post" action="/dashboard/source-configs/${encodeURIComponent(row.id)}/sync" class="d-inline"><button type="submit" class="btn btn-sm btn-outline-primary">Sincronizar agora</button></form>`
        : '<span class="text-muted small">Somente leitura</span>';
      return `
        <tr data-source-attention-id="${escapeHtml(row.id)}">
          <td>${escapeHtml(row.nome)}</td>
          <td><code>${escapeHtml(row.connector_type)}</code></td>
          <td><span class="badge ${badgeClass}">${escapeHtml(row.status_label)}</span></td>
          <td>${escapeHtml(row.reason)}</td>
          <td>${escapeHtml(row.next_run_at)}</td>
          <td>${escapeHtml(row.last_action_at)}</td>
          <td><code>${escapeHtml(row.last_error)}</code></td>
          <td>${actionCell}</td>
        </tr>
      `;
    }).join('');
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
      setText('kpi-source-exec-queued', data.source_execution_overview.queued_count);
      setText('kpi-source-exec-running', data.source_execution_overview.running_count);
      setText('kpi-source-exec-done', data.source_execution_overview.done_count);
      setText('kpi-source-exec-failed', data.source_execution_overview.failed_count);
      if (data.remote_agent_operational) {
        setText('kpi-remote-agent-level', data.remote_agent_operational.label);
        setText('kpi-remote-agent-reason', data.remote_agent_operational.reason);
        setText('kpi-remote-agent-grace', data.remote_agent_operational.grace_minutes);
        setText('kpi-remote-agent-pull', data.remote_agent_operational.pull_enabled ? 'habilitado' : 'desabilitado');
      }
      if (data.remote_agent) {
        setText('kpi-remote-agent-registration', data.remote_agent.last_registration_at || '-');
        setText('kpi-remote-agent-poll', data.remote_agent.last_command_poll_at || '-');
      }

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
      renderAttentionRows(data.source_attention_rows || []);
      if (data.source_attention_summary) {
        setText('kpi-source-attention-failed', data.source_attention_summary.failed_count);
        setText('kpi-source-attention-queued', data.source_attention_summary.queued_count);
        setText('kpi-source-attention-running', data.source_attention_summary.running_count);
        setText('kpi-source-attention-overdue', data.source_attention_summary.overdue_count);
      }
      if (data.commercial_snapshot) {
        setText('kpi-commercial-period', `${data.commercial_snapshot.period_start} a ${data.commercial_snapshot.period_end}`);
        setText('kpi-commercial-total-sales', data.commercial_snapshot.total_sales_value);
        setText('kpi-commercial-total-records', data.commercial_snapshot.total_records);
        setText('kpi-commercial-distinct-products', data.commercial_snapshot.distinct_products);
        setText('kpi-commercial-average-ticket', data.commercial_snapshot.average_ticket);
        setText('kpi-commercial-top-product', data.commercial_snapshot.top_product);
        setText('kpi-commercial-top-product-value', data.commercial_snapshot.top_product_value);
      }
    } catch (_err) {
    }
  }

  renderChart();
  refreshDashboard();
  setInterval(refreshDashboard, 15000);
})();
