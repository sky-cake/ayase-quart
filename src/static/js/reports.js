const reportModal = document.getElementById('report_modal');
const reportForm = document.getElementById('report_form');
const closeReportButton = document.getElementById('report_close');
const reportButtons = document.querySelectorAll('button[report_url]');
const feedbackReport = document.getElementById('feedback_report');
const modalOverlay = document.getElementById('modal_overlay');

reportButtons.forEach(button => {
    button.addEventListener('click', () => {
        const replyModal = document.getElementById('reply_modal');
        if (replyModal) {
            replyModal.style.display = 'none';
        }

        const reportUrl = button.getAttribute('report_url');
        reportForm.setAttribute('action', reportUrl);
        feedbackReport.textContent = '';
        modalOverlay.style.display = 'block';
        reportModal.style.display = 'block';
    });
});

closeReportButton.addEventListener('click', () => {
    modalOverlay.style.display = 'none';
    reportModal.style.display = 'none';
});

modalOverlay.addEventListener('click', (event) => {
    if (event.target === modalOverlay) {
        modalOverlay.style.display = 'none';
        reportModal.style.display = 'none';
    }
});

reportForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(reportForm);
    try {
        const response = await fetch(reportForm.action, {
            method: 'POST',
            body: formData,
        });
        if (response.ok) {
            modalOverlay.style.display = 'none';
            reportModal.style.display = 'none';
            feedbackReport.textContent = 'Report submitted successfully!';
            feedbackReport.style.color = 'green';
        } else {
            const errorData = await response.json();
            feedbackReport.textContent = errorData.message || 'An error occurred.';
            feedbackReport.style.color = 'red';
        }
    } catch (error) {
        feedbackReport.textContent = 'Unable to submit report. Please try again.';
        feedbackReport.style.color = 'red';
    }
});