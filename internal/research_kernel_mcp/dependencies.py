"""Directed dependency traversal over atom IDs."""
from __future__ import annotations

from collections import deque


def reverse_edges(dependencies: dict[str, set[str]]) -> dict[str, set[str]]:
    dependents: dict[str, set[str]] = {}
    for atom_id, premises in dependencies.items():
        for premise in premises:
            dependents.setdefault(premise, set()).add(atom_id)
    return dependents


def walk(
    adjacency: dict[str, set[str]], root: str, *, reverse: bool = False
) -> tuple[dict[str, int], dict[str, str]]:
    """Return minimum hop counts and one next step toward the root for each reached ID.

    Forward ties follow the lexicographically first path from the root. In a reverse
    walk, output paths run in the original edge direction, so ties choose the smallest
    next ID toward the root.
    """
    distance = {root: 0}
    toward_root: dict[str, str] = {}
    queue = deque([root])
    while queue:
        atom_id = queue.popleft()
        next_distance = distance[atom_id] + 1
        for neighbor in sorted(adjacency.get(atom_id, ())):
            if neighbor not in distance:
                distance[neighbor] = next_distance
                toward_root[neighbor] = atom_id
                queue.append(neighbor)
            elif reverse and distance[neighbor] == next_distance:
                toward_root[neighbor] = min(toward_root[neighbor], atom_id)
    return distance, toward_root


def path_to_root(atom_id: str, toward_root: dict[str, str]) -> list[str]:
    path = [atom_id]
    while path[-1] in toward_root:
        path.append(toward_root[path[-1]])
    return path
