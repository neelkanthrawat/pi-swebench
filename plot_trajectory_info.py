import argparse
import json
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
