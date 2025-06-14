from collections import defaultdict, deque

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
