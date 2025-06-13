import os
from time import perf_counter
from collections import defaultdict, deque


def printr(msg):
    print('\r\033[K', end='') # ANSI escape sequence to clear entire line
    print(f'\r{msg}', end='', flush=True)


def read_file(path: str) -> str:
    with open(path) as f:
        return f.read()


def make_src_path(*file_path):
    """Make a file path starting from src/."""
    if file_path:
        return os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), *file_path))

    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Perf:
    __slots__ = ('previous', 'checkpoints', 'topic', 'enabled')

    def __init__(self, topic: str=None, enabled=False):
        self.enabled = enabled
        if self.enabled:
            self.topic = topic
            self.checkpoints = []
            self.previous = perf_counter()

    def check(self, name: str=""):
        if self.enabled:
            now = perf_counter()
            elapsed = now - self.previous
            self.previous = now
            self.checkpoints.append((name, elapsed))

    # todo: call from logger for mass disabling
    def __repr__(self) -> str:
        if self.enabled:
            total = sum(point[1] for point in self.checkpoints)
            longest = max(max(len(point[0]) for point in self.checkpoints), 5) # 5 is len of 'total'
            topic = f'[{self.topic}]\n' if self.topic else ''
            return topic + '\n'.join(
                f'{name:<{longest}}: {elapsed:.4f} {elapsed / total * 100 :.1f}%'
                for name, elapsed in self.checkpoints
            ) + f'\n{"total":<{longest}}: {total:.4f}'
        else:
            return ''

class Graph:
    def __init__(self, node_count: int=0):
        self.graph: dict[int, set[int]] = defaultdict(set)
        self.node_count: int = node_count
        self.num_2_posts: dict[int, dict] = None

    def __contains__(self, item):
        return item in self.graph
    
    def __repr__(self):
        return '\n'.join(f'{k}: {v}' for k, v in self.graph.items())

    def add_node(self, value):
        if value not in self.graph:
            self.graph[value] = set()

    def add_edge(self, src, dest):
        has_src = src in self.graph
        has_dest = dest in self.graph

        if has_src and has_dest:
            self.graph[src].add(dest)
            self.graph[dest].add(src)
            return

        if has_src and not has_dest:
            self.graph[src].add(dest)
            return

        raise ValueError(src, dest, has_src, has_dest)

    def get_root(self):
        return min(self.graph) if self.graph else None
    
    def is_connected(self, node: int):
        return bool(self.graph.get(node))
    
    def remove_node(self, node: int):
        del self.graph[node]

    def get_bfs(self) -> list[int]:
        root = self.get_root()
        if root is None:
            return []
        visited = set()
        queue = deque([root])
        result = []

        while queue:
            node = queue.popleft()
            if node not in visited:
                visited.add(node)
                result.append(node)
                for neighbor in sorted(self.graph[node]):
                    if neighbor not in visited:
                        queue.append(neighbor)

        assert len(result) == self.node_count
        return result

    def get_dfs(self) -> list[int]:
        root = self.get_root()
        if root is None:
            return []
        visited = set()
        result = []

        def dfs_recursive(node):
            visited.add(node)
            result.append(node)
            for neighbor in sorted(self.graph[node]):
                if neighbor not in visited:
                    dfs_recursive(neighbor)

        dfs_recursive(root)
        assert len(result) == self.node_count
        return result

    def get_op_and_replies_to_op(self) -> list[int]:
        root = self.get_root()
        return [root, *sorted(self.graph.get(root, []))]

    def get_op(self) -> list[int]:
        return [self.get_root()]


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
