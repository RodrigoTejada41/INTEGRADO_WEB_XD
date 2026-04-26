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
          label: id === 'reportTopChart' ? 'Valor por produto' : 'Vendas por dia',
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
})();
