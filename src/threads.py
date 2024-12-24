# re-implemented from templates/macros.html
def render_thread_stats(post: dict) -> str:
    return f"""
    <div class="thread-stats">
        { 'Sticky /' if post['sticky'] else ''}
        { 'Closed /' if post['locked'] else ''}
        <span class="ts-replies" data-tip="Replies" title="Replies">{ post.get('nreplies', '?') }</span>
        /
        <span class="ts-images" data-tip="Images" title="Files">{ post.get('nimages', '?') }</span>
        /
        <span data-tip="Posters" class="ts-ips" title="Posters">
            { post.get('posters', '?') }
        </span>
    </div>
    """
