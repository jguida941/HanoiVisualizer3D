import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QPushButton, QLabel, QSlider, QSpinBox,
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QSplitter, QDockWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
import os
import glob


# Qt3D imports for upcoming 3D visualization (may require PyQt6-Qt3D package)
try:
    from PyQt6.Qt3DCore import QEntity
    from PyQt6.Qt3DExtras import (
        Qt3DWindow, QCylinderMesh, QPhongMaterial, QOrbitCameraController
    )
    from PyQt6.Qt3DRender import QPointLight
    from PyQt6.Qt3DCore import QTransform
    from PyQt6.QtGui import QVector3D
    qt3d_available = True
except ModuleNotFoundError:
    qt3d_available = False
    print("Warning: PyQt6.Qt3D modules not found; 3D visualization disabled.")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D


NUMBER_OF_DISKS = 3
DISK_HEIGHT = 20
DISK_WIDTH_STEP = 30
BASE_DISK_WIDTH = 60
ROD_WIDTH = 10
ROD_HEIGHT = 200
VIEW_WIDTH = 600
VIEW_HEIGHT = 400

MIN_TIMER_INTERVAL = 100
MAX_TIMER_INTERVAL = 2000

class HanoiVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tower of Hanoi Visualizer")
        self.setGeometry(100, 100, VIEW_WIDTH, VIEW_HEIGHT)

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
        self.step_button.clicked.connect(self.perform_next_move)
        controls_layout.addWidget(self.step_button)

        # Speed controls
        self.speed_label = QLabel("Speed")
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
        self.disk_selector.setValue(NUMBER_OF_DISKS)
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

        # Splitter for 2D and 3D views
        splitter = QSplitter(Qt.Orientation.Horizontal)
        # 2D graphics view
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        splitter.addWidget(self.view)
        # 3D Matplotlib view (with toolbar)
        if qt3d_available:
            view3d_container = QWidget()
            view3d_layout = QVBoxLayout(view3d_container)
            view3d_layout.setContentsMargins(0, 0, 0, 0)
            view3d_layout.addWidget(self.toolbar)
            view3d_layout.addWidget(self.canvas3d)
            splitter.addWidget(view3d_container)
        self.setCentralWidget(splitter)

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

        # Depth chart
        self.depth_fig = plt.figure(figsize=(4, 2))
        self.depth_ax = self.depth_fig.add_subplot(111)
        self.depth_canvas = FigureCanvas(self.depth_fig)
        # Dock the depth chart
        depth_dock = QDockWidget("Depth Chart", self)
        depth_dock.setWidget(self.depth_canvas)
        depth_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, depth_dock)

        # 3D Matplotlib view dock
        self.fig3d = plt.figure()
        self.ax3d = self.fig3d.add_subplot(111, projection='3d')
        self.canvas3d = FigureCanvas(self.fig3d)
        mat3d_dock = QDockWidget("3D View", self)
        mat3d_dock.setWidget(self.canvas3d)
        mat3d_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, mat3d_dock)

        self.rods = {'A': [], 'B': [], 'C': []}
        self.rod_positions = {
            'A': VIEW_WIDTH // 4,
            'B': VIEW_WIDTH // 2,
            'C': 3 * VIEW_WIDTH // 4
        }

        self.init_disks()

    def init_rods(self):
        for x in self.rod_positions.values():
            rod = QGraphicsRectItem(x - ROD_WIDTH // 2, VIEW_HEIGHT - ROD_HEIGHT, ROD_WIDTH, ROD_HEIGHT)
            rod.setBrush(QColor("black"))
            self.scene.addItem(rod)

    def init_disks(self):
        # Completely reset scene and rod lists
        self.scene.clear()
        self.rods = {'A': [], 'B': [], 'C': []}
        self.init_rods()

        max_total_width = VIEW_WIDTH // 3 - 20  # keep margin from rod
        max_disk_width = min(BASE_DISK_WIDTH + (NUMBER_OF_DISKS - 1) * DISK_WIDTH_STEP, max_total_width)
        width_step = max(max_disk_width // NUMBER_OF_DISKS, 10)

        for i in range(NUMBER_OF_DISKS, 0, -1):
            width = width_step * i
            disk = QGraphicsRectItem(0, 0, width, DISK_HEIGHT)
            disk.setBrush(QColor(100 + i * 15, 100, 255))
            self.scene.addItem(disk)
            self.rods['A'].append(disk)

        self.position_disks('A')
        self.update_3d_view()

        # Animation and button setup
        self.move_sequence = []
        self.move_index = 0

        self.timer = QTimer()
        self.timer.setInterval(600)
        self.timer.timeout.connect(self.perform_next_move)

        # NOTE: Move population and call-tree is now handled in start_animation

        # TODO: Implement video recording/export using QPixmap or QScreen.grabWindow

    def position_disks(self, rod_key):
        x_center = self.rod_positions[rod_key]
        for i, disk in enumerate(reversed(self.rods[rod_key])):
            disk.setRect(x_center - disk.rect().width() // 2,
                         VIEW_HEIGHT - DISK_HEIGHT * (i + 1),
                         disk.rect().width(),
                         DISK_HEIGHT)

    # def generate_moves(self, n, source, target, auxiliary):
    #     if n == 1:
    #         self.move_sequence.append((source, target))
    #     else:
    #         self.generate_moves(n - 1, source, auxiliary, target)
    #         self.move_sequence.append((source, target))
    #         self.generate_moves(n - 1, auxiliary, target, source)

    def _collect_moves(self, n, source, target, auxiliary, parent_item, depth=0):
        """
        Recursively collect moves and populate the call-tree under parent_item.
        """
        # Color recursion nodes by depth
        color = QColor(200 - depth*15, 200, 200 + depth*10)
        parent_item.setBackground(0, color)

        # Add a tree node for this call
        node = QTreeWidgetItem(parent_item, [f"Call: move({n}, {source}->{target})"])
        if n == 1:
            idx = len(self.move_sequence)
            move_node = QTreeWidgetItem(node, [f"Move disk: {source} -> {target}"])
            move_node.setData(0, Qt.ItemDataRole.UserRole, idx)
            move_node.setBackground(0, QColor(100, 255, 100))  # base moves green
            self.move_sequence.append((source, target))
            self.depth_sequence.append(depth)
        else:
            # Recurse to move n-1 from source to auxiliary
            self._collect_moves(n-1, source, auxiliary, target, node, depth+1)
            idx = len(self.move_sequence)
            move_node = QTreeWidgetItem(node, [f"Move disk: {source} -> {target}"])
            move_node.setData(0, Qt.ItemDataRole.UserRole, idx)
            move_node.setBackground(0, QColor(255, 100, 100))  # top-level moves red
            self.move_sequence.append((source, target))
            self.depth_sequence.append(depth)
            # Recurse to move n-1 from auxiliary to target
            self._collect_moves(n-1, auxiliary, target, source, node, depth+1)

    def start_animation(self):
        # Clear previous call-tree and moves
        self.call_tree.clear()
        self.move_sequence = []
        self.depth_sequence = []
        # Create root tree item
        root = QTreeWidgetItem(self.call_tree, [f"Hanoi({NUMBER_OF_DISKS})"])
        # Collect moves and build tree
        self._collect_moves(NUMBER_OF_DISKS, 'A', 'C', 'B', root)
        self.call_tree.expandAll()
        # Plot depth over move index
        self.depth_ax.clear()
        self.depth_ax.plot(self.depth_sequence, marker='o')
        self.depth_ax.set_title("Recursion Depth per Move")
        self.depth_ax.set_xlabel("Move Index")
        self.depth_ax.set_ylabel("Depth")
        self.depth_canvas.draw()
        # Reset move index and start timer
        self.move_index = 0
        self.timer.start()

    def perform_next_move(self):
        if self.move_index >= len(self.move_sequence):
            self.timer.stop()
            return

        from_rod, to_rod = self.move_sequence[self.move_index]
        if self.rods[from_rod]:
            disk = self.rods[from_rod].pop()

            if NUMBER_OF_DISKS <= 6:
                # Highlight the moving disk
                original_brush = disk.brush()
                # choose highlight color based on full animation vs manual step
                if self.timer.isActive():
                    highlight_color = QColor(255, 100, 100)
                else:
                    highlight_color = QColor(100, 255, 100)
                disk.setBrush(highlight_color)
                QTimer.singleShot(300, lambda d=disk, b=original_brush: d.setBrush(b))

            self.rods[to_rod].append(disk)
            self.position_disks(from_rod)
            self.position_disks(to_rod)

            self.move_index += 1
            self.move_counter_label.setText(f"Move: {self.move_index}")

            if NUMBER_OF_DISKS <= 6:
                self.capture_frame()
            self.update_3d_view()

    def adjust_speed(self, value):
        clamped = max(MIN_TIMER_INTERVAL, min(value, MAX_TIMER_INTERVAL))
        self.timer.setInterval(clamped)
        if clamped != value:
            self.speed_slider.setValue(clamped)

    def reset_board(self):
        # clear out any previously recorded frames
        for f in glob.glob("frame_*.png"):
            try:
                os.remove(f)
            except OSError:
                pass
        self.timer.stop()
        self.scene.clear()
        self.rods = {'A': [], 'B': [], 'C': []}

        for rod in self.rods.values():
            rod.clear()

        self.move_index = 0
        self.move_counter_label.setText("Move: 0")
        # Move sequence and call-tree will be populated at animation start
        self.init_rods()
        self.init_disks()
        self.update_3d_view()

    def change_disk_count(self, value):
        global NUMBER_OF_DISKS
        NUMBER_OF_DISKS = value
        self.reset_board()

    def capture_frame(self):
        # Make sure window is visible and fully rendered
        self.raise_()
        self.activateWindow()
        QApplication.processEvents()  # Process any pending events
        
        # Create screenshots directory if it doesn't exist
        os.makedirs("screenshots", exist_ok=True)
        
        # Capture individual frame
        pixmap = self.view.grab()
        filename = f"screenshots/frame_{self.move_index:03d}.png"
        pixmap.save(filename)
        
        # Save specific frames as screenshots for README
        if self.move_index in [1, len(self.move_sequence)//2, len(self.move_sequence)-1]:
            if self.move_index == 1:
                # Capture the entire main window for 2D view
                QTimer.singleShot(100, lambda: self.capture_full_window("screenshots/2d_view.png"))
            elif self.move_index == len(self.move_sequence)//2:
                # Capture specific widgets
                QTimer.singleShot(100, lambda: self.depth_canvas.grab().save("screenshots/depth_chart.png"))
                QTimer.singleShot(100, lambda: self.call_tree.grab().save("screenshots/call_tree.png"))
            else:
                QTimer.singleShot(100, lambda: self.canvas3d.grab().save("screenshots/3d_view.png"))
                
    def capture_full_window(self, filename):
        """Capture the entire application window"""
        self.raise_()
        self.activateWindow()
        QApplication.processEvents()
        full_pixmap = self.grab()
        full_pixmap.save(filename)
        print(f"Full window screenshot saved to {filename}")

    def update_3d_view(self):
        self.ax3d.clear()
        # positions: A=0, B=1, C=2
        for idx, rod_key in enumerate(('A', 'B', 'C')):
            for level, disk in enumerate(self.rods[rod_key]):
                width = disk.rect().width()
                height = DISK_HEIGHT
                # center x
                x = idx * (BASE_DISK_WIDTH + DISK_WIDTH_STEP)
                y = 0
                z = level * height
                # draw as a flat bar
                self.ax3d.bar3d(x - width/2, y, z, width, 0.5, height, shade=True)
        self.ax3d.set_xlim(-BASE_DISK_WIDTH, 3*(BASE_DISK_WIDTH+DISK_WIDTH_STEP))
        self.ax3d.set_ylim(-1, 1)
        self.ax3d.set_zlim(0, NUMBER_OF_DISKS * DISK_HEIGHT + 10)
        self.canvas3d.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HanoiVisualizer()
    window.show()
    sys.exit(app.exec())