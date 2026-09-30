import json
import argparse
from pathlib import Path
from generate_simple_graph import generate_figure

def extract_trajectory(session_file):
    trajectory = []
    step = 0

    with session_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "message":
                continue

            message = entry.get("message", {})
            role = message.get("role")

            
            # Assistant tool calls
            

            if role == "assistant":
                content = message.get("content", [])

                if not isinstance(content, list):
                    continue

                for block in content:
                    if not isinstance(block, dict):
                        continue

                    if block.get("type") != "toolCall":
                        continue

                    tool = block.get("name")
                    arguments = block.get("arguments", {})

                    action = {
                        "step": step,
                        "action": tool,
                        "tool": tool,
                        "file": [],
                        "command": None,
                        "success": None,
                    }

                    if tool in {"read", "write", "edit"}:
                        path = arguments.get("path")

                        if path:
                            action["file"].append(path)

                    elif tool == "bash":
                        action["command"] = arguments.get("command")

                    trajectory.append(action)
                    step += 1

            
            # Tool results
            

            elif role == "toolResult":
                if not trajectory:
                    continue

                trajectory[-1]["success"] = not message.get(
                    "isError",
                    False,
                )

            
            # Bash executions
            

            elif role == "bashExecution":
                action = {
                    "step": step,
                    "action": "bash",
                    "tool": "bash",
                    "file": [],
                    "command": message.get("command"),
                    "success": (
                        message.get("exitCode") == 0
                        if message.get("exitCode") is not None
                        else None
                    ),
                }

                trajectory.append(action)
                step += 1

    return trajectory


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "session_file",
        help="Path to the Pi session JSONL file.",
    )
    parser.add_argument(
        "--generate-figure",
        action="store_true",
        default=False
    )

    args = parser.parse_args()

    session_file = Path(args.session_file)

    if not session_file.exists():
        print(f"File does not exist: {session_file}")
        return

    trajectory = extract_trajectory(session_file)

    output_file = session_file.parent / "graph.jsonl"

    with output_file.open("w", encoding="utf-8") as f:
        for node in trajectory:
            f.write(json.dumps(node) + "\n")

    print(f"Trajectory saved to: {output_file}")
    print(f"Number of actions: {len(trajectory)}")
    if args.generate_figure:
        generate_figure(output_file)
        print(f"figure generated and saved")


if __name__ == "__main__":
    main()