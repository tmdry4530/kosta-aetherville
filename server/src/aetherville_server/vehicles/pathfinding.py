"""Small A* grid pathfinding implementation for vehicle demo routes."""

from __future__ import annotations

import heapq
from collections.abc import Iterable

GridPoint = tuple[int, int]


def astar_path(
    start: GridPoint,
    goal: GridPoint,
    *,
    obstacles: Iterable[GridPoint] = (),
    bounds: tuple[int, int, int, int] = (-8, 8, -8, 8),
) -> list[GridPoint]:
    """Return an inclusive Manhattan-grid path from start to goal."""

    blocked = set(obstacles)
    if start in blocked or goal in blocked:
        raise ValueError("start and goal must not be blocked")

    frontier: list[tuple[int, GridPoint]] = [(0, start)]
    came_from: dict[GridPoint, GridPoint | None] = {start: None}
    cost_so_far: dict[GridPoint, int] = {start: 0}

    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal:
            return _reconstruct_path(came_from, current)

        for neighbor in _neighbors(current, bounds):
            if neighbor in blocked:
                continue
            new_cost = cost_so_far[current] + 1
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + _heuristic(neighbor, goal)
                heapq.heappush(frontier, (priority, neighbor))
                came_from[neighbor] = current

    raise ValueError(f"no path from {start} to {goal}")


def _neighbors(point: GridPoint, bounds: tuple[int, int, int, int]) -> list[GridPoint]:
    min_x, max_x, min_z, max_z = bounds
    x, z = point
    candidates = [(x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)]
    return [
        candidate
        for candidate in candidates
        if min_x <= candidate[0] <= max_x and min_z <= candidate[1] <= max_z
    ]


def _heuristic(a: GridPoint, b: GridPoint) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _reconstruct_path(
    came_from: dict[GridPoint, GridPoint | None], current: GridPoint
) -> list[GridPoint]:
    path = [current]
    parent = came_from[current]
    while parent is not None:
        current = parent
        path.append(current)
        parent = came_from[current]
    return list(reversed(path))
