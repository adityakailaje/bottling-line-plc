import os

import pytest

pygame = pytest.importorskip("pygame")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from plant import Plant  # noqa: E402


def test_ui_draws_and_keys_toggle_faults():
    from ui import View
    view, pl = View(), Plant(seed=1)
    sensors = pl.step({})
    assert view.update(pl, sensors, {}) is True
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_o))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
    view.update(pl, sensors, {})
    assert pl.faults["overload"] is True and abs(pl.level_pct - 20.0) < 0.01
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    assert view.update(pl, sensors, {}) is False
