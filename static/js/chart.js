let loadChart = null;

function updateChart() {
    const serverId = document.getElementById('server-select').value;
    fetch(`/get_chart_data/${serverId}`)
        .then(response => response.json())
        .then(data => {
            if (loadChart) {
                loadChart.data.labels = data.labels;
                loadChart.data.datasets[0].data = data.data;
                loadChart.update();
            } else {
                createChart(data);
            }
        });
}

function createChart(data) {
    const ctx = document.getElementById('load-chart').getContext('2d');
    loadChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Нагрузка сервера (%)',
                data: data.data,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderWidth: 2,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', updateChart);
