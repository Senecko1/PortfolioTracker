document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('holdingsChart');
    if (!canvas) return;

    const labels = JSON.parse(document.getElementById('chart-labels').textContent);
    const values = JSON.parse(document.getElementById('chart-values').textContent);

    const ctx1 = canvas.getContext('2d');
    new Chart(ctx1, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f',
                    '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ab'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.parsed + '%';
                        }
                    }
                }
            }
        }
    });
});
