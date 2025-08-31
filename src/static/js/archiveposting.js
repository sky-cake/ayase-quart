function create_quotelink(board, op_thread_num, bq) {
    bq.innerHTML = bq.innerHTML.replace(/&gt;(\d+)/g, `<a href="/${board}/thread/${op_thread_num}#p$1" class="quotelink" data-board="${board}">&gt;$1</a>`);
}

function focus_comment(link) {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const commentBox = document.getElementById('comment');
        if (commentBox) {
            const quoteText = `${link.textContent}\n`;
            commentBox.value += quoteText;
            commentBox.focus();
        }
    });
}

let op_thread_num = document.getElementById("op_thread_num");
if (op_thread_num) {
    let tools = document.getElementById("tools");
    let board = false;
    if (tools) {
        board = tools.getAttribute('data-board');
    }
    if (board) {
        op_thread_num = op_thread_num.getAttribute('data-num');
        document.querySelectorAll('blockquote').forEach((bq) => create_quotelink(board, op_thread_num, bq));
        document.querySelectorAll('.quotelink').forEach((link) => focus_comment(link));
    }
}
