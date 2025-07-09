const maxBoards = 5;
const activeBoards = new Set();
const boardDataCache = new Map();
const boardColorAssignments = new Map();
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

function getColor(board) {
    if (!boardColorAssignments.has(board)) {
        const nextColorIndex = boardColorAssignments.size % palette.length;
        boardColorAssignments.set(board, palette[nextColorIndex]);
    }
    return boardColorAssignments.get(board);
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
                        filter: item => !item.text.startsWith('%')
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                title: {
                    display: true,
                    text: () => 'Archive Posts per Month'
                }
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
    if (boardDataCache.has(board)) {
        return boardDataCache.get(board);
    }
    showLoading(true);
    const response = await fetch(`/stats/${board}`);
    const data = await response.json();
    boardDataCache.set(board, data);
    showLoading(false);
    return data;
}

function populateDatasets(board, data, allMonths, datasets) {
    const monthMap = new Map();
    for (const item of data) {
        monthMap.set(item.year_month, {
            postCount: parseInt(item.post_count),
            fraction: parseFloat(item.fraction)
        });
    }

    const postCounts = [];
    const fractions = [];

    for (const month of allMonths) {
        const entry = monthMap.get(month);
        postCounts.push(entry ? entry.postCount : 0);
        fractions.push(entry ? entry.fraction : null);
    }

    const color = getColor(board);

    datasets.push({
        label: `${board}`,
        data: postCounts,
        backgroundColor: color,
        borderColor: color,
        fill: false,
        stepped: "middle"
    });

    datasets.push({
        label: `% of ${board}`,
        data: fractions,
        type: 'scatter',
        backgroundColor: color,
        borderColor: color,
        pointStyle: 'star',
        radius: 5,
        hoverRadius: 7,
        yAxisID: 'y1',
        spanGaps: true,
        order: 2,
        showLine: false
    });
}

async function updateChart() {
    const allMonthsSet = new Set();
    const boardDataArray = [];

    for (const board of activeBoards) {
        const data = await fetchBoardData(board);
        for (const item of data) {
            allMonthsSet.add(item.year_month);
        }
        boardDataArray.push({ board, data });
    }

    const allMonths = Array.from(allMonthsSet).sort();
    const datasets = [];

    for (const { board, data } of boardDataArray) {
        populateDatasets(board, data, allMonths, datasets);
    }

    chart.data.labels = allMonths;
    chart.data.datasets = datasets;
    chart.update();
}

function showLoading(state) {
    document.getElementById('loading').style.display = state ? 'block' : 'none';
}

function handleBoardToggleClick(event) {
    const button = event.currentTarget;
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

    updateChart();
}

function clearAllButtons() {
    activeBoards.clear();
    boardColorAssignments.clear();

    for (const button of doc_query_all('.board-toggle')) {
        button.classList.add('form_btn');
    }
}

async function handleSelectRandomClick() {
    clearAllButtons();
    const buttons = Array.from(doc_query_all('.board-toggle'));
    const shuffled = [...buttons].sort(() => 0.5 - Math.random());
    const selected = shuffled.slice(0, maxBoards);

    for (const button of selected) {
        const board = button.dataset.board;
        activeBoards.add(board);
        button.classList.remove('form_btn');
    }

    await updateChart();
}

function handleClearAllClick() {
    clearAllButtons();
    updateChart();
}

function initButtons() {
    const buttons = doc_query_all('.board-toggle');
    for (const button of buttons) {
        button.addEventListener('click', handleBoardToggleClick);
    }

    document.getElementById('select-random').addEventListener('click', handleSelectRandomClick);
    document.getElementById('clear-all').addEventListener('click', handleClearAllClick);
}

initChart();
initButtons();
