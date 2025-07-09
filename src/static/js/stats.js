const maxBoards = 5;
let activeBoards = new Set();
let boardDataCache = {};
let boardColors = {};
let chart;

const palette = [
    "#1f77b4", // strong blue
    "#d62728", // strong red
    "#2ca02c", // strong green
    "#9467bd", // deep purple
    "#ff7f0e", // bold orange
    "#8c564b", // deep brown
    "#17becf", // bright teal
    "#7f7f7f", // dark gray
    "#bcbd22", // strong yellow-green
    "#e377c2"  // strong pink
];


let boardColorAssignments = {};
let assignedBoards = [];

function getColor(board) {
    if (!boardColorAssignments[board]) {
        const nextColorIndex = assignedBoards.length % palette.length;
        boardColorAssignments[board] = palette[nextColorIndex];
        assignedBoards.push(board);
    }
    return boardColorAssignments[board];
}

function initChart() {
    Chart.defaults.color = '#000000';
    const ctx = document.getElementById('activityChart').getContext('2d');
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: []
        },
        options: {
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'rect',
                        filter: function (item, chart) {
                            const label = item.text || '';
                            return !label.startsWith('%');
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                title: {
                    display: true,
                    text: (ctx) => 'Archive Posts per Month',
                },
            },
            responsive: true,
            scales: {
                x: { title: { display: true, text: 'Month' } },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Post Count •' }
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    title: { display: true, text: 'Fraction of Posts ✷' },
                    min: 0,
                    max: 1.1
                }
            }
        }
    });
}

async function fetchBoardData(board) {
    if (boardDataCache[board]) {
        return boardDataCache[board];
    }
    showLoading(true);
    const response = await fetch(`/stats/${board}`);
    const data = await response.json();
    boardDataCache[board] = data;
    showLoading(false);
    return data;
}

async function updateChart() {
    const allMonthsSet = new Set();
    const boardDataArray = [];

    for (const board of activeBoards) {
        const data = await fetchBoardData(board);
        data.forEach(item => allMonthsSet.add(item.year_month));
        boardDataArray.push({ board, data });
    }

    const allMonths = Array.from(allMonthsSet).sort();

    const datasets = [];

    boardDataArray.forEach(({ board, data }) => {
        const monthMap = Object.fromEntries(data.map(item => [item.year_month, parseInt(item.post_count)]));
        const fractionMap = Object.fromEntries(data.map(item => [item.year_month, parseFloat(item.fraction)]));

        const postCounts = allMonths.map(month => monthMap[month] || 0);
        const fractions = allMonths.map(month => fractionMap[month] !== undefined ? fractionMap[month] : null);

        datasets.push({
            label: `${board}`,
            data: postCounts,
            backgroundColor: getColor(board),
            borderColor: getColor(board),
            fill: false,
            stepped: "middle",
        });

        datasets.push({
            label: `% of ${board}`,
            data: fractions,
            type: 'scatter',
            backgroundColor: getColor(board),
            borderColor: getColor(board),
            pointStyle: 'star',
            radius: 5,
            hoverRadius: 7,
            yAxisID: 'y1',
            spanGaps: true,
            order: 2,
            showLine: false,
        });
    });

    chart.data.labels = allMonths;
    chart.data.datasets = datasets;
    chart.update();
}

function showLoading(state) {
    document.getElementById('loading').style.display = state ? 'block' : 'none';
}

function initButtons() {
    document.querySelectorAll('.board-toggle').forEach(button => {
        button.addEventListener('click', async () => {
            const board = button.dataset.board;

            if (activeBoards.has(board)) {
                activeBoards.delete(board);
                button.classList.add('form_btn');
            } else {
                if (activeBoards.size >= maxBoards) {
                    alert(`You can only compare up to ${maxBoards} boards at a time.`);
                    return;
                }
                activeBoards.add(board);
                button.classList.remove('form_btn');
            }

            await updateChart();
        });
    });

    function clear_all_buttons() {
        activeBoards.clear();
        document.querySelectorAll('.board-toggle').forEach(button => {
            button.classList.add('form_btn');
        });
    }

    document.getElementById('select-random').addEventListener('click', async () => {
        clear_all_buttons();
        const buttons = Array.from(document.querySelectorAll('.board-toggle'));
        const shuffled = buttons.sort(() => 0.5 - Math.random());
        const selected = shuffled.slice(0, 5);
        for (const button of selected) {
            const board = button.dataset.board;
            activeBoards.add(board);
            button.classList.remove('form_btn');
        }
        await updateChart();
    });

    document.getElementById('clear-all').addEventListener('click', () => {
        clear_all_buttons();
        updateChart();
    });
}

initChart();
initButtons();
