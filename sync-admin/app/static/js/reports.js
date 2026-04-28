(function () {
  function renderChart(id, type, color) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const labels = JSON.parse(canvas.dataset.labels || '[]');
    const values = JSON.parse(canvas.dataset.values || '[]');
    if (!labels.length) return;
    new Chart(canvas, {
      type,
      data: {
        labels,
        datasets: [{
          label: canvas.dataset.label || 'Valor de vendas',
          data: values,
          borderColor: color,
          backgroundColor: `${color}33`,
          fill: type === 'line',
          tension: 0.25,
        }],
      },
      options: { responsive: true, maintainAspectRatio: false },
    });
  }

  renderChart('reportDailyChart', 'line', '#0f766e');
  renderChart('reportTopChart', 'bar', '#b45309');
  renderChart('reportTypeChart', 'doughnut', '#0369a1');
  renderChart('reportPaymentChart', 'doughnut', '#15803d');
  renderChart('reportFamilyChart', 'bar', '#7c2d12');
})();
