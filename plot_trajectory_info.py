import argparse
import json
import math
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


def get_tool_call_curves(statistics):
	tool_positions = statistics.get("tools", {}).get("tool_call_position", {})
	calls = []

	if not isinstance(tool_positions, dict):
		return {}

	for tool_name, positions in tool_positions.items():
		if not isinstance(positions, list):
			continue

		for position in positions:
			if isinstance(position, str):
				position = position.split("_", 1)
			if not isinstance(position, (list, tuple)) or len(position) != 2:
				continue
			try:
				jsonl_element, call_index = map(int, position)
			except (TypeError, ValueError):
				continue
			calls.append((jsonl_element, call_index, tool_name))

	calls.sort(key=lambda call: (call[0], call[1]))
	calls_per_element = Counter(call[0] for call in calls)
	if not calls:
		return {}

	call_positions = {
		(jsonl_element, call_index): (
			jsonl_element + call_index / (calls_per_element[jsonl_element] + 1)
		)
		for jsonl_element, call_index, _ in calls
	}
	end_position = max(
		max(call_positions.values()),
		statistics.get("counts", {}).get("total_entries", 0),
	)
	calls_by_tool = {}
	for jsonl_element, call_index, tool_name in calls:
		calls_by_tool.setdefault(tool_name, []).append((jsonl_element, call_index))

	curves = {}
	for tool_name, positions in calls_by_tool.items():
		x_values = [0]
		cumulative_calls = [0]
		for call_position in positions:
			x_values.append(call_positions[call_position])
			cumulative_calls.append(cumulative_calls[-1] + 1)
		if x_values[-1] < end_position:
			x_values.append(end_position)
			cumulative_calls.append(cumulative_calls[-1])
		curves[tool_name] = (x_values, cumulative_calls)

	return curves


def _plot_fine_grained_stems(axis, positions, tool_name, color_index):
	frequencies = Counter(positions)
	unique_positions = sorted(frequencies)
	position_values = [element + call_order / 10 for element, call_order in unique_positions]
	frequency_values = [frequencies[position] for position in unique_positions]
	color_number = color_index % 10
	axis.stem(
		position_values,
		frequency_values,
		linefmt=f"C{color_number}-",
		markerfmt=f"C{color_number}o",
		basefmt=" ",
		label=tool_name,
	)


def plot_tool_call_distributions(
	task_folder,
	tool_call_positions,
	distribution_style=1,
	fine_grained=False,
):
	if distribution_style not in (1, 2):
		raise ValueError("distribution_style must be 1 (outline) or 2 (filled)")

	positions_by_tool = {}
	for tool_name, run_positions in tool_call_positions.items():
		if not isinstance(run_positions, list):
			continue
		positions_by_tool[tool_name] = []
		for positions in run_positions:
			if not isinstance(positions, list):
				continue
			for position in positions:
				if not isinstance(position, (list, tuple)) or len(position) != 2:
					continue
				try:
					positions_by_tool[tool_name].append(
						(int(position[0]), int(position[1]))
					)
				except (TypeError, ValueError):
					continue

	elements_by_tool = {
		tool_name: [
			element + call_order / 10 if fine_grained else element
			for element, call_order in positions
		]
		for tool_name, positions in positions_by_tool.items()
	}

	all_elements = [
		element
		for elements in elements_by_tool.values()
		for element in elements
	]
	if all_elements and not fine_grained:
		bin_edges = range(min(all_elements), max(all_elements) + 2)
	else:
		bin_edges = range(2)

	output_folder = Path(task_folder)
	filename_suffix = "_finegrained" if fine_grained else ""
	combined_output = output_folder / (
		f"tool_call_position_distribution_all_tools{filename_suffix}.png"
	)
	figure, axis = plt.subplots(figsize=(11, 6))
	histogram_style = (
		{"histtype": "step", "linewidth": 1.8}
		if distribution_style == 1
		else {"histtype": "stepfilled", "alpha": 0.35, "linewidth": 1}
	)
	for color_index, (tool_name, elements) in enumerate(elements_by_tool.items()):
		if not elements:
			continue
		if fine_grained:
			_plot_fine_grained_stems(
				axis,
				positions_by_tool[tool_name],
				tool_name,
				color_index,
			)
		else:
			axis.hist(
				elements,
				bins=bin_edges,
				density=True,
				label=tool_name,
				**histogram_style,
			)
	if fine_grained:
		axis.axhline(0, color="black", linewidth=0.8)
	if elements_by_tool and all_elements:
		axis.legend(title="Tool")
	else:
		axis.text(0.5, 0.5, "No tool calls recorded", ha="center", va="center", transform=axis.transAxes)
	plot_title = (
		"Frequency of Tool Calls by Position"
		if fine_grained
		else "Distribution of Tool Calls Across JSONL Elements"
	)
	if fine_grained:
		plot_title += " (Fine-Grained)"
	axis.set_title(plot_title)
	axis.set_xlabel(
		"JSONL element index + call order / 10"
		if fine_grained
		else "JSONL element index (first position value)"
	)
	axis.set_ylabel("Frequency" if fine_grained else "Probability density")
	if fine_grained:
		axis.xaxis.set_major_locator(MaxNLocator(nbins=12))
	else:
		axis.xaxis.set_major_locator(MaxNLocator(integer=True))
	axis.grid(True, linestyle="--", alpha=0.35)
	figure.tight_layout()
	figure.savefig(combined_output, dpi=200, bbox_inches="tight")
	plt.close(figure)

	tool_names = list(elements_by_tool)
	if tool_names:
		columns = math.ceil(math.sqrt(len(tool_names)))
		rows = math.ceil(len(tool_names) / columns)
		figure, axes = plt.subplots(
			rows,
			columns,
			figsize=(5 * columns, 3.5 * rows),
			squeeze=False,
		)
		for color_index, (axis, tool_name) in enumerate(zip(axes.flat, tool_names)):
			elements = elements_by_tool[tool_name]
			if elements:
				if fine_grained:
					_plot_fine_grained_stems(
						axis,
						positions_by_tool[tool_name],
						tool_name,
						color_index,
					)
				else:
					axis.hist(elements, bins=bin_edges, density=True, color="tab:blue", alpha=0.8)
			else:
				axis.text(0.5, 0.5, "No tool calls recorded", ha="center", va="center", transform=axis.transAxes)
			axis.set_title(tool_name)
			axis.set_xlabel(
				"JSONL element index + call order / 10"
				if fine_grained
				else "JSONL element index"
			)
			axis.set_ylabel("Frequency" if fine_grained else "Probability density")
			if fine_grained:
				axis.xaxis.set_major_locator(MaxNLocator(nbins=12))
			else:
				axis.xaxis.set_major_locator(MaxNLocator(integer=True))
			axis.grid(True, linestyle="--", alpha=0.35)
		for axis in list(axes.flat)[len(tool_names):]:
			axis.set_visible(False)
		if fine_grained:
			for axis in axes.flat:
				if axis.get_visible():
					axis.axhline(0, color="black", linewidth=0.8)
	else:
		figure, axis = plt.subplots(figsize=(7, 4))
		axis.text(0.5, 0.5, "No tool calls recorded", ha="center", va="center", transform=axis.transAxes)
		axis.set_axis_off()
	figure.suptitle(
		"Tool Call Position Distributions by Tool"
		+ (" (Fine-Grained)" if fine_grained else "")
	)
	figure.tight_layout()
	subplots_output = output_folder / (
		f"tool_call_position_distribution_by_tool{filename_suffix}.png"
	)
	figure.savefig(subplots_output, dpi=200, bbox_inches="tight")
	plt.close(figure)
	return combined_output, subplots_output


def plot_run(run_folder, statistics_file):
	with statistics_file.open("r", encoding="utf-8") as file:
		statistics = json.load(file)

	curves = get_tool_call_curves(statistics)

	figure, axis = plt.subplots(figsize=(10, 5))
	for tool_name, (x_values, cumulative_calls) in curves.items():
		axis.step(
			x_values,
			cumulative_calls,
			where="post",
			marker="o",
			markersize=3,
			linewidth=2,
			label=tool_name,
		)
	axis.set_title(f"Cumulative Tool Calls by Type: {run_folder.name}")
	axis.set_xlabel("JSONL element (fractional position is call order)")
	axis.set_ylabel("Cumulative tool calls")
	axis.xaxis.set_major_locator(MaxNLocator(integer=True))
	axis.grid(True, linestyle="--", alpha=0.35)
	if curves:
		axis.legend(title="Tool")
	else:
		axis.text(0.5, 0.5, "No tool calls recorded", ha="center", va="center", transform=axis.transAxes)
	figure.tight_layout()

	output_file = run_folder / "tool_call_cumulative.png"
	figure.savefig(output_file, dpi=200, bbox_inches="tight")
	plt.close(figure)
	print(f"Saved {output_file}")


def main():
	parser = argparse.ArgumentParser(
		description="Plot cumulative tool calls for every run in a task folder."
	)
	parser.add_argument(
		"task_folder",
		help="Folder containing run_N subfolders.",
	)
	args = parser.parse_args()

	task_folder = Path(args.task_folder)
	if not task_folder.is_dir():
		parser.error(f"Task folder does not exist: {task_folder}")

	run_folders = sorted(
		(
			path for path in task_folder.glob("run_*")
			if path.is_dir() and path.name.removeprefix("run_").isdigit()
		),
		key=lambda path: int(path.name.removeprefix("run_")),
	)

	for run_folder in run_folders:
		run_number = run_folder.name.removeprefix("run_")
		statistics_file = run_folder / f"statistics_{run_number}.json"
		if not statistics_file.is_file():
			print(f"Skipping {run_folder}: {statistics_file.name} not found")
			continue
		plot_run(run_folder, statistics_file)


if __name__ == "__main__":
	main()
