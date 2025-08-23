document.addEventListener('DOMContentLoaded', () => {
    fetch(CHART_DATA_URL)
    .then(res => res.json())
    .then(({ labels, values }) => {
        const ctx = document.getElementById('portfolioLineChart').getContext('2d');
        new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels.map(d => new Date(d)),
            datasets: [{
            label: 'Total portfolio value',
            data: values,
            borderColor: 'rgba(54, 162, 235, 1)',
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            fill: true,
            tension: 0.1,
            pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
            x: {
                type: 'time',
                time: {
                unit: 'month',
                tooltipFormat: 'dd.MM.yyyy'
                },
                title: {
                display: true,
                text: 'Date'
                }
            },
            y: {
                title: {
                display: true,
                text: 'Value'
                },
                beginAtZero: false
            }
            },
            plugins: {
            legend: { display: false }
            }
        }
        });
    })
    .catch(err => console.error('Error fetching chart data', err));
});
