from utils.graphs import Graph

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

def get_graph_from_thread(quotelinks: dict[int, list[int]], posts: list[dict]):
    """`generate_thread()` returns compatible args.
    
    Debugging thread: http://127.0.0.1:9001/g/thread/105205235
    """

    op = posts[0]
    is_op = 1

    g = Graph()
    g.node_count = len(posts)
    g.num_2_posts = dict()
    qls = set()

    for p in posts:
        pnum = p['num']
        g.num_2_posts[pnum] = p # save a loop by throwing this here

        g.add_node(pnum)
        post_qls = quotelinks.get(pnum, [])
        for rnum in post_qls:
            g.add_edge(pnum, rnum)
            qls.add(rnum)

        if not is_op and pnum not in qls:
            g.add_edge(op['num'], pnum)

        if not g.is_connected(pnum) and quotelinks:
            g.remove_node(pnum)

        is_op = 0
    return g
