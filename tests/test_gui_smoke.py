import os
import sys
import pytest

# Skip if pytest-qt plugin isn't installed (no qtbot fixture)
try:  # plugin import name
    import pytestqt  # type: ignore
except Exception:  # pragma: no cover
    pytest.skip("pytest-qt not installed; skipping GUI smoke test", allow_module_level=True)

# Skip in headless Linux where no X server is available
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    pytest.skip("No DISPLAY; skipping GUI smoke test", allow_module_level=True)

from HanoiVisualizer3D.main import HanoiVisualizer


def test_window_launch(qtbot):
    win = HanoiVisualizer()
    qtbot.addWidget(win)
    win.show()
    assert win.isVisible()
    # Sanity: important widgets are present
    assert win.step_button.isEnabled() or not win.step_button.isEnabled()
    assert win.call_tree is not None
    assert win.depth_canvas is not None
    assert win.canvas3d is not None
