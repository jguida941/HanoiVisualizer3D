

Phase 1  Hands-on interactivity (S–M)
	1.	Timeline scrubber (seek anywhere)
	•	UI: QSlider “Move 0…N-1”, plus play/pause.
	•	Hook: On slider change, rebuild from start and apply first k moves (your fast-forward already does 95% of this).
	•	Bonus: Bookmarks—right-click tree node → “Set breakpoint at this move.”
	2.	Breakpoints & conditional stops
	•	Rules: Stop when (depth == d), disk == k, from==A && to==C, or every m moves.
	•	UI: Small “Break on…” popover in Controls.
	•	Plumbing: Evaluate before calling perform_next_move().
	3.	Drag-to-move (human mode)
	•	UX: Enable dragging top disk only; on drop, validate (no larger on smaller), snap to rod; if illegal, animate snap-back.
	•	Why: Lets users “play” and compare to optimal algorithm.
	4.	Record toggle + GIF/MP4 export
	•	UI: CheckBox “Record”; Menu → Export → MP4/GIF.
	•	Impl: Keep your PNG capture; add an ffmpeg or imageio assembler (optional dep, gracefully disabled if missing).


Phase 2  Live analytics (M)
	5.	Metrics panel (always-on)
	•	Stats: n, 2^n−1 target, moves done, current depth, elapsed time, moves/sec, last move parity, disk move counts.
	•	UI: Right dock “Metrics”.
	•	Impl: Update every move; very cheap.
	6.	Streaming plots
	•	Depth vs move: you have it—make it live (append instead of full redraw).
	•	Call rate plot: moves/sec over time (10-sample EMA).
	•	Disk heatmap: rows=disks, cols=move index buckets; shows which disks are active when.
	7.	CSV/JSON run export
	•	Schema: header with parameters + per-move rows (idx, from, to, depth, disk_id, timestamp).
	•	One click from the toolbar.



Phase 3 — Algorithm lab (M–L)
	8.	Algorithm variants (side-by-side compare)
	•	Variants: classic recursive; iterative (stack); Gray-code mapping;
	•	UI: ComboBox “Algorithm”; “Compare 2” shows two 2D panes and diff stats (same N).
	•	Science: Demonstrates equivalence / different traversal orders.
	9.	4+ pegs (Reve’s puzzle) — Frame–Stewart
	•	Solver: dynamic programming for optimal split k (cache minimal counts + decomposition).
	•	UI: Peg count selector (3–6), results panel shows optimal k for each disk count.
	•	Plot: Moves vs n for K∈{3..6} (log scale option).
	10.	State-graph view (optional)
	•	Graph: nodes = states; edges = legal moves; current state highlighted.
	•	Mode: For n≤5 only (explodes fast); teach shortest-path minimality.



Phase 4 — Pedagogical overlays (S–M)
	11.	Invariants & proofs overlay
	•	Overlays: “Largest disk moves every 2^(k−1) moves,” “Parity flips each step,” “Minimality: 2^n−1.”
	•	UI: Toggle chips; brief inline proof snippets anchored to the tree.
	12.	Explanatory call-stack
	•	Panel: Live stack frame list (move(n, s, t, a)); highlight frame responsible for current move.



Phase 5 — Visualization polish (S–M)
	13.	Auto-layout that feels native
	•	Save/restore dock geometry; sensible first-run sizes (you added resizeDocks, keep it).
	•	“Reset layout” menu item.
	14.	Legible plots by default
	•	Reticle/grid; DPI-aware fonts; thicker strokes; night/day theme toggle.
	•	3D: labeled rods, adaptive view_init, throttle redraw (every k moves for large n).
	15.	Accessibility & keyboard
	•	Full keyboard map; high-contrast mode; focus ring on current move node.


Phase 6 — Performance & scale (M)
	16.	Render throttling for big n
	•	Param K for “update views every K moves” (auto-raise K when N grows).
	•	Use Matplotlib blitting on the depth chart to avoid full canvas redraws.
	17.	Profiling & counters
	•	Tiny “Performance” tab: cProfile top functions; peak recursion depth; memory at peak.



Phase 7 — Reproducibility & packaging (S)
	18.	Run presets & sharing
	•	Save a “run” (n, algorithm, speed, breakpoints) to a .hanoirun file; load & replay.
	•	CLI “headless” runner to export moves/plots for papers.
	19.	Docs + tutorials
	•	“Lab worksheets” mode: guided exercises (break at certain moves; questions; auto-check).



Concrete engineering notes
	•	Timeline: expose apply_prefix(k) that rebuilds & fast-forwards to move k; scrubber + breakpoints both call this.
	•	Human mode: set ItemIsMovable on only the top disk per rod; override itemChange → detect drop area, validate against rods model, then snap & update model.
	•	Gray-code variant: disk to move at step i is index of least significant set bit in i (1-based); direction depends on disk parity → super fast & fun to show.
	•	Frame–Stewart: precompute FS[n][k] minimal counts and optimal split; recursively emit moves using the split (DP table kept in hanoi_core).
	•	Live plots: avoid ax.clear(); keep Line2D handles and push new points; call line.set_data(...) + ax.relim(); ax.autoscale_view() + blit.


Order: 
	1.	Timeline scrubber + breakpoints
	2.	Live call-tree highlight (if not already merged)
	3.	Record toggle + export
	4.	Metrics panel + live depth/chart polish
	5.	Algorithm variants (recursive + iterative + Gray-code)
	6.	4-peg Frame–Stewart + comparison plot
	7.	Drag-to-move human mode
	8.	State graph (n≤5)

