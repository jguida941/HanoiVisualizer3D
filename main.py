import sys
import os
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QPushButton, QLabel, QSlider, QSpinBox,
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QDockWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush, QAction, QKeySequence, QPainter


# Module logger (configured in __main__)
logger = logging.getLogger(__name__)

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavToolbar,
)
from matplotlib.figure import Figure

# Quiet toolbar to suppress status messages and reduce layout jitter
class QuietToolbar(NavToolbar):
    def set_message(self, s):  # type: ignore[override]
        pass

# Pure algorithm helpers imported from a small core module
try:
    # If launched as a package:  python -m HanoiVisualizer3D.main
    if __package__:
        from .hanoi_core import generate_moves, validate_sequence, Move
    else:
        # If launched as a script: python HanoiVisualizer3D/main.py
        from hanoi_core import generate_moves, validate_sequence, Move  # type: ignore
except ImportError as e:
    # Surface real import errors instead of hiding them
    raise


# Use an instance attribute for current disk count; keep a default for reference
DEFAULT_NUMBER_OF_DISKS = 3
DISK_HEIGHT = 20
DISK_WIDTH_STEP = 30
BASE_DISK_WIDTH = 60
ROD_WIDTH = 10
ROD_HEIGHT = 200
VIEW_WIDTH = 1100
VIEW_HEIGHT = 720

MIN_TIMER_INTERVAL = 100
MAX_TIMER_INTERVAL = 2000

def _clamp(x: float | int) -> int:
    """Clamp to [0, 255] for RGB channel safety."""
    return max(0, min(255, int(x)))

class HanoiVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tower of Hanoi Visualizer")
        self.setGeometry(100, 100, VIEW_WIDTH, VIEW_HEIGHT)
        # Logging configured in __main__
        # Ensure a status bar exists early (used for move messages)
        self.statusBar()

        # Instance-managed state (avoid module-level globals)
        self.num_disks = DEFAULT_NUMBER_OF_DISKS
        # Typed attributes for clarity
        self.rods = {'A': [], 'B': [], 'C': []}
        self.rod_positions = {'A': 0, 'B': 0, 'C': 0}
        self.rod_items = []  # track rod graphics items for resize repositioning
        self.move_sequence = []
        self.depth_sequence = []
        self.move_index = 0
        self.fast_forwarding = False
        self._tree_index = 0
        self._ff_busy = False
        # Call-tree move nodes; used for live highlighting
        self._move_items = []
        self._last_highlight = -1
        self._did_initial_resize = False

        # Control panel
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls.setLayout(controls_layout)
        controls_layout.setSpacing(10)

        # Start button
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_animation)
        controls_layout.addWidget(self.start_button)

        # Step button
        self.step_button = QPushButton("Step")
        self.step_button.clicked.connect(self.step_once)
        controls_layout.addWidget(self.step_button)

        # Speed controls
        self.speed_label = QLabel("Speed: 600 ms")
        controls_layout.addWidget(self.speed_label)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(MIN_TIMER_INTERVAL)
        self.speed_slider.setMaximum(MAX_TIMER_INTERVAL)
        self.speed_slider.setValue(600)
        self.speed_slider.valueChanged.connect(self.adjust_speed)
        controls_layout.addWidget(self.speed_slider)

        # Move counter
        self.move_counter_label = QLabel("Move: 0")
        controls_layout.addWidget(self.move_counter_label)

        # Reset button
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_board)
        controls_layout.addWidget(self.reset_button)

        # Disk count selector
        self.disk_selector = QSpinBox()
        self.disk_selector.setMinimum(1)
        self.disk_selector.setMaximum(10)
        # Reflect current disk count in the selector
        self.disk_selector.setValue(self.num_disks)
        self.disk_selector.valueChanged.connect(self.change_disk_count)
        controls_layout.addWidget(self.disk_selector)

        # Dock the control panel
        controls_dock = QDockWidget("Controls", self)
        controls_dock.setWidget(controls)
        controls_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, controls_dock)

        # Central 2D graphics view (simpler than a splitter with one child)
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        # Prevent center view from collapsing when docks are large
        try:
            self.view.setMinimumHeight(320)
            self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        except Exception:
            pass
        # Nicer visuals and adequate performance for small item counts
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate
        )
        self.scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        # Initialize a sensible scene rect and compute rod positions; kept in sync on resize
        self.scene.setSceneRect(0, 0, VIEW_WIDTH, VIEW_HEIGHT)
        self.compute_rod_positions()
        self.setCentralWidget(self.view)

        # Recursion call-tree panel
        self.call_tree = QTreeWidget()
        self.call_tree.setHeaderLabel("Recursion Call Tree")
        # Dock the recursion call tree
        calltree_dock = QDockWidget("Recursion Call Tree", self)
        calltree_dock.setWidget(self.call_tree)
        calltree_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, calltree_dock)

        # Depth chart (Matplotlib OO API; avoids pyplot globals)
        self.depth_fig = Figure(figsize=(6.5, 3.2))
        try:
            self.depth_fig.set_dpi(120)
        except Exception:
            pass
        self.depth_ax = self.depth_fig.add_subplot(111)
        self.depth_canvas = FigureCanvas(self.depth_fig)
        try:
            self.depth_canvas.setMinimumSize(380, 220)
        except Exception:
            pass
        # Add Matplotlib toolbar and canvas in a container
        depth_container = QWidget()
        dl = QVBoxLayout(depth_container)
        dl.setContentsMargins(0, 0, 0, 0)
        depth_tb = QuietToolbar(self.depth_canvas, self)
        # Reduce layout churn from continuously-updating coordinates label
        if hasattr(depth_tb, 'coordinates'):
            try:
                depth_tb.coordinates.setMinimumWidth(110)
            except Exception:
                pass
        dl.addWidget(depth_tb)
        dl.addWidget(self.depth_canvas)
        # Dock the depth chart
        depth_dock = QDockWidget("Depth Chart", self)
        depth_dock.setWidget(depth_container)
        depth_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, depth_dock)

        # 3D Matplotlib view dock (OO API)
        self.fig3d = Figure(figsize=(7.2, 4.8))
        try:
            self.fig3d.set_dpi(120)
        except Exception:
            pass
        self.ax3d = self.fig3d.add_subplot(111, projection='3d')
        self.canvas3d = FigureCanvas(self.fig3d)
        try:
            self.canvas3d.setMinimumHeight(260)
        except Exception:
            pass
        # Add Matplotlib toolbar and canvas in a container
        mat3d_container = QWidget()
        ml = QVBoxLayout(mat3d_container)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.addWidget(QuietToolbar(self.canvas3d, self))
        ml.addWidget(self.canvas3d)
        mat3d_dock = QDockWidget("3D View", self)
        mat3d_dock.setWidget(mat3d_container)
        mat3d_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, mat3d_dock)
        # Save dock refs and set sensible minimums
        self.controls_dock = controls_dock
        self.calltree_dock = calltree_dock
        self.depth_dock = depth_dock
        self.mat3d_dock = mat3d_dock
        try:
            self.mat3d_dock.setMinimumHeight(220)
            self.depth_dock.setMinimumHeight(160)
            self.depth_dock.setMinimumWidth(260)
        except Exception:
            pass

        # Add a View menu with dock toggles so closed docks are recoverable
        self._build_menus(controls_dock, calltree_dock, depth_dock, mat3d_dock)

        # Parent a QTimer to self for lifecycle safety
        self.timer = QTimer(self)
        self.timer.setInterval(600)
        self.timer.timeout.connect(self.perform_next_move)

        # Install keyboard shortcuts and connect tree interactions
        self._install_shortcuts()
        self.call_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.call_tree.itemActivated.connect(self.on_tree_item_clicked)

        # Initial scene setup
        self.init_disks()
        self._update_controls_state()

    def init_rods(self):
        """(Re)create the three vertical rods and store items for resizing."""
        for item in getattr(self, 'rod_items', []):
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self.rod_items = []
        scene_h = self.scene.sceneRect().height()
        for key in ('A', 'B', 'C'):
            x = self.rod_positions[key]
            rod = QGraphicsRectItem(x - ROD_WIDTH // 2, scene_h - ROD_HEIGHT, ROD_WIDTH, ROD_HEIGHT)
            rod.setBrush(QColor("black"))
            rod.setZValue(-100)  # always behind disks
            self.scene.addItem(rod)
            self.rod_items.append(rod)

    def position_rods(self):
        """Update rod positions to current scene size and computed centers."""
        if len(self.rod_items) != 3:
            return
        scene_h = self.scene.sceneRect().height()
        for idx, key in enumerate(('A', 'B', 'C')):
            x = self.rod_positions[key]
            self.rod_items[idx].setRect(x - ROD_WIDTH // 2, scene_h - ROD_HEIGHT, ROD_WIDTH, ROD_HEIGHT)

    def init_disks(self):
        """Clear and reinitialize scene, rods, and disks consistently.
        - Computes rod positions from current scene rect
        - Rebuilds rods and initial disk stack on 'A'
        - Resets animation state
        """
        self.scene.clear()
        self.rods = {'A': [], 'B': [], 'C': []}
        # Drop any stale references to cleared QGraphicsItems
        self.rod_items = []
        # Keep scene rect as-is; recompute rod centers for current width
        self.compute_rod_positions()
        self.init_rods()

        # Scale disk widths to available region
        max_total_width = max(40, int(self.scene.sceneRect().width() / 3) - 20)
        max_disk_width = min(
            BASE_DISK_WIDTH + (self.num_disks - 1) * DISK_WIDTH_STEP,
            max_total_width,
        )
        width_step = max(max_disk_width // max(1, self.num_disks), 10)

        for i in range(self.num_disks, 0, -1):
            width = width_step * i
            disk = QGraphicsRectItem(0, 0, width, DISK_HEIGHT)
            disk.setBrush(QColor(100 + i * 15, 100, 255))
            disk.setData(0, i)  # tag disk number (1=smallest)
            self.scene.addItem(disk)
            self.rods['A'].append(disk)

        self.position_disks('A')
        self.update_3d_view()

        # Reset animation state
        self.move_sequence = []
        self.depth_sequence = []
        self.move_index = 0

        # NOTE: Move population and call-tree is now handled in start_animation

        # TODO: Implement video recording/export using QPixmap or QScreen.grabWindow

    def position_disks(self, rod_key):
        x_center = self.rod_positions[rod_key]
        for i, disk in enumerate(reversed(self.rods[rod_key])):
            disk.setRect(x_center - disk.rect().width() // 2,
                         self.scene.sceneRect().height() - DISK_HEIGHT * (i + 1),
                         disk.rect().width(),
                         DISK_HEIGHT)
            # Ensure disks are above rods and stacked correctly
            disk.setZValue(100 + i)

    # def generate_moves(self, n, source, target, auxiliary):
    #     if n == 1:
    #         self.move_sequence.append((source, target))
    #     else:
    #         self.generate_moves(n - 1, source, auxiliary, target)
    #         self.move_sequence.append((source, target))
    #         self.generate_moves(n - 1, auxiliary, target, source)

    def _collect_moves_tree(self, n: int, source: str, target: str, auxiliary: str, parent_item: QTreeWidgetItem, depth: int = 0) -> None:
        """Populate the recursion call-tree without mutating the move list.
        Uses self._tree_index to align nodes with precomputed move order and
        appends depths to self.depth_sequence in the same order.
        """
        color = QColor(_clamp(200 - depth * 15), 200, _clamp(200 + depth * 10))
        parent_item.setBackground(0, QBrush(color))

        node = QTreeWidgetItem(parent_item, [f"Call: move({n}, {source}->{target})"])
        if n == 1:
            idx = self._tree_index
            move_node = QTreeWidgetItem(node, [f"Move disk: {source} -> {target}"])
            move_node.setData(0, Qt.ItemDataRole.UserRole, idx)
            move_node.setBackground(0, QBrush(QColor(100, 255, 100)))
            self._move_items.append(move_node)
            self.depth_sequence.append(depth)
            self._tree_index += 1
        else:
            self._collect_moves_tree(n - 1, source, auxiliary, target, node, depth + 1)
            idx = self._tree_index
            move_node = QTreeWidgetItem(node, [f"Move disk: {source} -> {target}"])
            move_node.setData(0, Qt.ItemDataRole.UserRole, idx)
            move_node.setBackground(0, QBrush(QColor(255, 100, 100)))
            self._move_items.append(move_node)
            self.depth_sequence.append(depth)
            self._tree_index += 1
            self._collect_moves_tree(n - 1, auxiliary, target, source, node, depth + 1)

    def _prepare_run(self, restart_scene: bool = True) -> bool:
        """Build scene, moves, call tree, and depth plot without starting the timer.
        Returns True on success.
        """
        if restart_scene:
            self.init_disks()
        # Generate and validate moves
        self.move_sequence = generate_moves(self.num_disks, 'A', 'C', 'B')
        ok, err = validate_sequence(self.num_disks, self.move_sequence)
        if not ok:
            logger.error("Invalid move sequence: %s", err)
            self.move_sequence = []
            return False
        # Build call tree & depth chart
        self.call_tree.clear()
        self.depth_sequence = []
        self._move_items.clear()
        self._last_highlight = -1
        root = QTreeWidgetItem(self.call_tree, [f"Hanoi({self.num_disks})"])
        self._tree_index = 0
        self._collect_moves_tree(self.num_disks, 'A', 'C', 'B', root)
        self.call_tree.expandAll()

        self.depth_ax.clear()
        self.depth_ax.plot(self.depth_sequence, marker='o', linewidth=2.0, markersize=4.5)
        self.depth_ax.grid(True, alpha=0.3)
        self.depth_ax.margins(x=0.02)
        try:
            self.depth_ax.tick_params(labelsize=9)
        except Exception:
            pass
        self.depth_ax.set_title("Recursion Depth per Move", fontsize=11)
        self.depth_ax.set_xlabel("Move Index", fontsize=10)
        self.depth_ax.set_ylabel("Depth", fontsize=10)
        try:
            self.depth_fig.tight_layout(pad=0.4)
        except Exception:
            pass
        self.depth_canvas.draw()

        self.move_index = 0
        self._highlight_move(0)
        self._update_controls_state()
        return True

    def start_animation(self) -> None:
        if self.timer.isActive():
            self.timer.stop()
        if not self._prepare_run(restart_scene=True):
            return
        self.timer.start()
        self._update_controls_state()

    def perform_next_move(self) -> None:
        if self.move_index >= len(self.move_sequence):
            self.timer.stop()
            self._update_controls_state()
            return

        from_rod, to_rod = self.move_sequence[self.move_index]

        # Guard: cannot pop from empty rod
        if not self.rods[from_rod]:
            logger.error("Illegal move: source rod %s empty at index %d",
                         from_rod, self.move_index)
            self.timer.stop()
            self._update_controls_state()
            return

        # Safe to pop now
        disk = self.rods[from_rod].pop()

        # Defensive: disallow placing larger on smaller (future-proofing)
        if self.rods[to_rod] and disk.rect().width() > self.rods[to_rod][-1].rect().width():
            logger.error("Illegal move: larger on smaller (%s -> %s) at move %d",
                         from_rod, to_rod, self.move_index)
            self.rods[from_rod].append(disk)
            self.position_disks(from_rod)
            self.timer.stop()
            self._update_controls_state()
            return

        if self.num_disks <= 6 and not self.fast_forwarding:
            original_brush = disk.brush()
            highlight_color = QColor(255, 100, 100) if self.timer.isActive() else QColor(100, 255, 100)
            disk.setBrush(highlight_color)
            duration = max(100, int(self.timer.interval() * 0.45))

            def _restore_brush(disk_ref=disk, brush=original_brush):
                # Only restore if the disk still exists in our model (not cleared)
                if any(disk_ref is d for r in self.rods.values() for d in r):
                    disk_ref.setBrush(brush)

            QTimer.singleShot(duration, _restore_brush)

        self.rods[to_rod].append(disk)
        self.position_disks(from_rod)
        self.position_disks(to_rod)

        self.move_index += 1
        self.move_counter_label.setText(f"Move: {self.move_index}")
        # Status: which disk moved
        try:
            disk_no = int(disk.data(0) or 0)
            self.statusBar().showMessage(
                f"Move {self.move_index}: disk {disk_no} {from_rod} -> {to_rod}"
            )
        except Exception:
            pass
        # Highlight next move in the call tree
        self._highlight_move(self.move_index)

        if self.num_disks <= 6 and not self.fast_forwarding:
            self.capture_frame()
        self.update_3d_view()

    def adjust_speed(self, value: int) -> None:
        clamped = max(MIN_TIMER_INTERVAL, min(value, MAX_TIMER_INTERVAL))
        self.timer.setInterval(clamped)
        self.speed_label.setText(f"Speed: {clamped} ms")
        if clamped != value:
            self.speed_slider.setValue(clamped)

    def reset_board(self) -> None:
        """Reset animation state and rebuild the scene in one pass."""
        self.timer.stop()
        self.move_index = 0
        self.move_counter_label.setText("Move: 0")
        # Reinitialize scene, rods, and disks; moves rebuilt at start_animation
        self.init_disks()
        self.update_3d_view()
        self._update_controls_state()

    def change_disk_count(self, value: int) -> None:
        """Update disk count from UI and reset the board."""
        self.num_disks = value
        self.reset_board()

    def capture_frame(self) -> None:
        """Persist a frame to captures/ directory (no auto-delete)."""
        out_dir = os.path.join(os.getcwd(), 'captures')
        os.makedirs(out_dir, exist_ok=True)
        pixmap = self.view.grab()
        filename = os.path.join(out_dir, f"frame_{self.move_index:03d}.png")
        pixmap.save(filename)

    def update_3d_view(self) -> None:
        """Stable, normalized 3D view: rods at X=0.5/1.5/2.5, labeled A/B/C."""
        self.ax3d.clear()
        # Compute relative width scale against the widest disk
        all_disks = [d for r in self.rods.values() for d in r]
        try:
            max_w = max((d.rect().width() for d in all_disks)) if all_disks else 1.0
        except Exception:
            max_w = 1.0
        rod_x = {'A': 0.5, 'B': 1.5, 'C': 2.5}
        y_base = {'A': 0.2, 'B': 1.2, 'C': 2.2}
        dy = 0.6
        hz = 1.0 / max(1, self.num_disks)
        for rk in ('A', 'B', 'C'):
            x_center = rod_x[rk]
            y = y_base[rk]
            for level, disk in enumerate(self.rods[rk]):
                w_rel = 0.9 * (disk.rect().width() / max_w)
                z = level * hz
                self.ax3d.bar3d(x_center - w_rel / 2.0, y, z, w_rel, dy, hz, shade=True)
        # Fixed axes and aspect (no autoscale surprises)
        self.ax3d.set_xlim(0, 3)
        self.ax3d.set_ylim(0, 3)
        self.ax3d.set_yticks([0.5, 1.5, 2.5])
        try:
            self.ax3d.set_yticklabels(['A', 'B', 'C'])
        except Exception:
            pass
        self.ax3d.set_zlim(0, 1.0 + hz * 0.5)
        self.ax3d.set_box_aspect((3.0, 1.2, 1.2))
        try:
            self.ax3d.view_init(elev=22, azim=-55)
        except Exception:
            pass
        self.canvas3d.draw()

    def compute_rod_positions(self) -> None:
        """Set rod x-centers based on current scene width at 1/4, 1/2, 3/4."""
        w = self.scene.sceneRect().width()
        self.rod_positions = {'A': w / 4, 'B': w / 2, 'C': 3 * w / 4}

    def resizeEvent(self, e) -> None:
        """Keep scene rect, rods, and disks aligned with the view size."""
        vw = self.view.viewport().width()
        vh = self.view.viewport().height()
        # Make the scene big enough to contain rods + full disk stack.
        # If the viewport is smaller, QGraphicsView will scroll/align to bottom.
        min_h = ROD_HEIGHT + DISK_HEIGHT * (self.num_disks + 2)
        min_w = 420  # enough for three rods + margins
        self.scene.setSceneRect(0, 0, max(vw, min_w), max(vh, min_h))
        self.compute_rod_positions()
        self.position_rods()
        for k in ('A', 'B', 'C'):
            self.position_disks(k)
        # Apply responsive dock sizing after Qt processes the resize
        try:
            QTimer.singleShot(0, self._apply_responsive_layout)
        except Exception:
            pass
        super().resizeEvent(e)

    def _install_shortcuts(self) -> None:
        """Install keyboard shortcuts for common actions."""
        # Space => start/pause
        act_start_pause = QAction("Start/Pause", self)
        act_start_pause.setShortcut(QKeySequence(Qt.Key.Key_Space))
        def _toggle():
            if self.timer.isActive():
                self.timer.stop()
            else:
                self.start_animation()
        act_start_pause.triggered.connect(_toggle)
        self.addAction(act_start_pause)

        # N => step
        act_step = QAction("Step", self)
        act_step.setShortcut(QKeySequence(Qt.Key.Key_N))
        act_step.triggered.connect(self.step_once)
        self.addAction(act_step)

        # R => reset
        act_reset = QAction("Reset", self)
        act_reset.setShortcut(QKeySequence(Qt.Key.Key_R))
        act_reset.triggered.connect(self.reset_board)
        self.addAction(act_reset)

    def _build_menus(self, controls_dock, calltree_dock, depth_dock, mat3d_dock):
        """Create a View menu with toggle actions for docks."""
        bar = self.menuBar()
        view_menu = bar.addMenu("&View")
        for name, dock in (
            ("Controls", controls_dock),
            ("Call Tree", calltree_dock),
            ("Depth Chart", depth_dock),
            ("3D View", mat3d_dock),
        ):
            act = dock.toggleViewAction()
            act.setText(name)
            view_menu.addAction(act)
        # No fixed initial sizes; handled by responsive helper after show
        try:
            mat3d_dock.setMinimumHeight(220)
            depth_dock.setMinimumHeight(160)
        except Exception:
            pass

    def showEvent(self, e) -> None:
        """Apply initial responsive sizing after the window is shown."""
        super().showEvent(e)
        try:
            QTimer.singleShot(0, self._apply_responsive_layout)
            QTimer.singleShot(0, self._reflow_scene)
        except Exception:
            pass

    def _apply_responsive_layout(self) -> None:
        """Adjust dock sizes proportionally based on current window size."""
        w = max(640, self.width())
        h = max(480, self.height())
        # Horizontal split: left call tree vs right depth chart
        left_w = max(180, int(w * 0.26))
        right_w = max(260, int(w * 0.34))
        try:
            self.resizeDocks([self.calltree_dock, self.depth_dock], [left_w, right_w], Qt.Orientation.Horizontal)
        except Exception:
            pass
        # Bottom 3D dock: cap at 40% and ensure room for center/top
        bottom_cap = int(h * 0.40)
        must_leave_for_center = 360
        bottom_h = max(220, min(bottom_cap, h - must_leave_for_center))
        try:
            self.resizeDocks([self.mat3d_dock], [bottom_h], Qt.Orientation.Vertical)
            # Also cap maximum height so dragging cannot starve the center
            self.mat3d_dock.setMaximumHeight(max(220, h - must_leave_for_center))
        except Exception:
            pass
        # Compact mode tweaks for small windows
        try:
            small = (w < 980) or (h < 640)
            self.canvas3d.setMinimumHeight(220 if small else 260)
            self.depth_canvas.setMinimumSize(300 if small else 360, 160 if small else 200)
        except Exception:
            pass

        # After dock changes, reflow the scene to current viewport
        try:
            QTimer.singleShot(0, self._reflow_scene)
        except Exception:
            pass

    def _reflow_scene(self) -> None:
        """Recompute scene rect and reposition rods/disks to current viewport."""
        try:
            vw = self.view.viewport().width()
            vh = self.view.viewport().height()
            min_h = ROD_HEIGHT + DISK_HEIGHT * (self.num_disks + 2)
            min_w = 420
            self.scene.setSceneRect(0, 0, max(vw, min_w), max(vh, min_h))
            self.compute_rod_positions()
            self.position_rods()
            for k in ('A', 'B', 'C'):
                self.position_disks(k)
        except Exception:
            pass

    def _update_controls_state(self) -> None:
        """Reflect run/idle state in Start/Step controls."""
        running = self.timer.isActive() or getattr(self, "_ff_busy", False)
        self.start_button.setText("Restart" if self.timer.isActive() else "Start")
        self.step_button.setEnabled(not running)
        # Avoid racy updates during fast-forward/running
        self.disk_selector.setEnabled(not running)
        self.speed_slider.setEnabled(not getattr(self, "_ff_busy", False))

    def _highlight_move(self, idx: int) -> None:
        """Select and reveal the call-tree node for the given move index."""
        if 0 <= idx < len(self._move_items):
            it = self._move_items[idx]
            try:
                self.call_tree.setCurrentItem(it)
                self.call_tree.scrollToItem(it)
            except Exception:
                pass
            self._last_highlight = idx

    def step_once(self) -> None:
        """Perform a single move; prepare state if needed. No timer run."""
        if self.timer.isActive() or getattr(self, "_ff_busy", False):
            return
        if not self.move_sequence:
            if not self._prepare_run(restart_scene=True):
                return
        self.perform_next_move()

    def on_tree_item_clicked(self, item, _column) -> None:
        """Fast-forward to the move index represented by the clicked item.
        Guard against reentrancy from rapid clicks.
        """
        if getattr(self, "_ff_busy", False):
            return
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        if idx is None:
            return
        self._ff_busy = True
        self._update_controls_state()
        self.timer.stop()
        # Reset scene and ensure moves exist
        self.init_disks()
        if not self.move_sequence:
            self.move_sequence = generate_moves(self.num_disks, 'A', 'C', 'B')
        self.move_index = 0
        self.fast_forwarding = True
        try:
            while self.move_index <= idx and self.move_index < len(self.move_sequence):
                self.perform_next_move()
        finally:
            self.fast_forwarding = False
            self._ff_busy = False
            self._update_controls_state()

if __name__ == "__main__":
    # Optional Hi-DPI tweaks (Qt6-safe). Not strictly necessary; Qt6 scales well by default.
    from PyQt6.QtCore import Qt as _Qt
    from PyQt6.QtGui import QGuiApplication as _QGuiApplication
    if hasattr(_Qt, "HighDpiScaleFactorRoundingPolicy"):
        _QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            _Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    if hasattr(_Qt, "ApplicationAttribute") and hasattr(_Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(_Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    window = HanoiVisualizer()
    try:
        window.showMaximized()
    except Exception:
        window.show()
    sys.exit(app.exec())
