"""Shared DFS cycle-detection for any id -> [dependency ids] graph.

Used by workspace_items (wiki page dependency_ids) and projects/tasks (Gantt
depends_on) so both stay on one proven implementation instead of duplicating
the DFS.
"""


def detect_cycle(node_id: str, proposed_deps: list[str], all_deps: dict[str, list[str]]) -> bool:
    """Would setting `node_id`'s dependencies to `proposed_deps` create a cycle?

    `all_deps` maps every other node's id -> its current dependency list
    (excluding `node_id`'s own entry, since we're testing a proposed new one).
    """
    graph = dict(all_deps)
    graph[node_id] = proposed_deps
    visiting, visited = set(), set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True  # cycle
        if node in visited:
            return False
        visiting.add(node)
        for dep in graph.get(node, []) or []:
            if visit(dep):
                return True
        visiting.discard(node)
        visited.add(node)
        return False

    return visit(node_id)
