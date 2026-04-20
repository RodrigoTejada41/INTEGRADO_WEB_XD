export function summaryCard(label, value) {
  return `
    <div class="card">
      <div class="subtitle">${label}</div>
      <h2 style="margin:6px 0 0;font-size:30px;">${value}</h2>
    </div>
  `;
}

export function sectionTitle(title, subtitle = "") {
  return `
    <div class="header">
      <div>
        <h2 class="title">${title}</h2>
        <p class="subtitle">${subtitle}</p>
      </div>
    </div>
  `;
}
