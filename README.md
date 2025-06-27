# HanoiVisualizer3D

An interactive Tower of Hanoi visualizer built with PyQt6, featuring both 2D and 3D animated views, a recursion call tree, and a depth chart.

## Features

* **2D Animation**: Watch disks move in real time on a QGraphicsView.
* **3D Visualization**: Currently uses Matplotlib 3D bar charts for visualization (Qt3D support planned for future).
* **Recursion Call Tree**: Expandable tree view of recursive calls and disk moves.
* **Depth Chart**: Matplotlib chart plotting recursion depth over each move.
* **Controls**:
  * **Start**: Run full animation automatically.
  * **Step**: Perform one move at a time.
  * **Speed Slider**: Adjust animation interval between moves.
  * **Move Counter**: Track current move number.
  * **Reset**: Clear the board and start over.
  * **Disk Selector**: Choose number of disks (1–10).

## Dependencies

* Python 3.10 or higher
* PyQt6
* Matplotlib
* mpl_toolkits

Install with:

```bash
pip install PyQt6 matplotlib
# for future 3D support:
# pip install PyQt6-Qt3D
```

## Screenshots

2D View:

![2D View](screenshots/2d_view.png)

3D View:

![3D View](screenshots/3d_view.png)

Recursion Call Tree:

![Call Tree](screenshots/call_tree.png)

Depth Chart:

![Depth Chart](screenshots/depth_chart.png)


## Usage

```bash
git clone https://github.com/jguida941/HanoiVisualizer3D.git
cd HanoiVisualizer3D
python main.py
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details. 
