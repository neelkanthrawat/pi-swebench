import argparse
import json
from pathlib import Path

from plot_trajectory_info import plot_tool_call_distributions


def save_tool_call_positions(task_folder, distribution_style=1):
	task_folder = Path(task_folder)
	if not task_folder.is_dir():
		raise NotADirectoryError(f"Task folder does not exist: {task_folder}")

	run_folders = sorted(
		(
			path for path in task_folder.glob("run_*")
			if path.is_dir() and path.name.removeprefix("run_").isdigit()
		),
		key=lambda path: int(path.name.removeprefix("run_")),
	)
	positions_by_run = []
	for run_folder in run_folders:
		run_number = run_folder.name.removeprefix("run_")
		statistics_file = run_folder / f"statistics_{run_number}.json"
		run_positions = {}
		if statistics_file.is_file():
			with statistics_file.open("r", encoding="utf-8") as file:
				statistics = json.load(file)
			run_tool_positions = statistics.get("tools", {}).get("tool_call_position", {})
			if isinstance(run_tool_positions, dict):
				for tool_name, positions in run_tool_positions.items():
					if not isinstance(positions, list):
						continue
					tool_positions = []
					for position in positions:
						if isinstance(position, str):
							position = position.split("_", 1)
						if not isinstance(position, (list, tuple)) or len(position) != 2:
							continue
						try:
							jsonl_element, call_order = map(int, position)
						except (TypeError, ValueError):
							continue
						tool_positions.append([jsonl_element, call_order])
					run_positions[tool_name] = tool_positions
		positions_by_run.append(run_positions)

	tool_names = dict.fromkeys(
		tool_name
		for run_positions in positions_by_run
		for tool_name in run_positions
	)
	tool_call_positions = {
		tool_name: [run_positions.get(tool_name, []) for run_positions in positions_by_run]
		for tool_name in tool_names
	}

	output_file = task_folder / "tool_call_positions.json"
	with output_file.open("w", encoding="utf-8") as file:
		json.dump(tool_call_positions, file, indent=4)
		file.write("\n")
	plot_tool_call_distributions(task_folder, tool_call_positions, distribution_style)
	plot_tool_call_distributions(
		task_folder,
		tool_call_positions,
		distribution_style,
		fine_grained=True,
	)
	return output_file


def main():
	parser = argparse.ArgumentParser(
		description="Collect tool-call positions from every run in a task folder."
	)
	parser.add_argument(
		"task_folder",
		help="Folder containing run_N subfolders.",
	)
	parser.add_argument(
		"--distribution-style",
		type=int,
		choices=(1, 2),
		default=1,
		help="Combined histogram style: 1 for outlines, 2 for translucent fills.",
	)
	args = parser.parse_args()
	output_file = save_tool_call_positions(args.task_folder, args.distribution_style)
	print(f"Saved {output_file}")


if __name__ == "__main__":
	main()