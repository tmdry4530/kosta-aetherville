from __future__ import annotations

import pytest

from aetherville_server.vehicles import astar_path


def test_astar_path_avoids_obstacles() -> None:
    path = astar_path((0, 0), (3, 0), obstacles={(1, 0), (1, 1)}, bounds=(-1, 4, -2, 2))

    assert path[0] == (0, 0)
    assert path[-1] == (3, 0)
    assert (1, 0) not in path


def test_astar_path_reports_unreachable_goal() -> None:
    with pytest.raises(ValueError, match="no path"):
        astar_path((0, 0), (2, 0), obstacles={(1, 0), (0, 1), (0, -1)}, bounds=(0, 2, -1, 1))
