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

# Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)

**Copyright (c) 2025 Justin Guida**

This work is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License**.

You are free to:

**Share** — copy and redistribute the material in any medium or format  
**Adapt** — remix, transform, and build upon the material  

Under the following terms:

 **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made. Credit must include:
- Name: *Justin Guida*
- Year: *2025*
- GitHub: [https://github.com/jguida941](https://github.com/jguida941)

 **NonCommercial** — You may not use the material for **commercial purposes** without **explicit written permission** from the author.

Additional terms:

- **You may not sell**, rebrand, or redistribute this work for profit.  
- Educational institutions and students may freely use, adapt, and build upon this work **for non-commercial academic use**, including course materials and presentations.
- Derivative works must also credit the original author clearly.

---

To view the full license, visit:  
[https://creativecommons.org/licenses/by-nc/4.0](https://creativecommons.org/licenses/by-nc/4.0)
