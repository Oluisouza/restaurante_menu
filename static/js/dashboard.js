// Os dados vêm da view: o Django calcula, o JavaScript só desenha.
const serie = JSON.parse(document.getElementById('dados-serie').textContent);
const reais = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

new Chart(document.getElementById('grafico-faturamento'), {
    type: 'line',
    data: {
        labels: serie.map(ponto => ponto.dia),
        datasets: [{
            label: 'Faturamento',
            // O Decimal chega como texto ("12.00") para não perder centavos no caminho.
            data: serie.map(ponto => Number(ponto.total)),
            borderColor: '#1f6f5c',
            backgroundColor: 'rgba(31, 111, 92, 0.10)',
            fill: true,
            tension: 0.25,
            pointRadius: 2,
        }],
    },
    options: {
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: contexto => reais.format(contexto.parsed.y) } },
        },
        scales: {
            y: { beginAtZero: true, ticks: { callback: valor => reais.format(valor) } },
        },
    },
});