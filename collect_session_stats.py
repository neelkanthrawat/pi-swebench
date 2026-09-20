import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def parse_timestamp(timestamp):
    if not timestamp:
        return None

    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def collect_statistics(session_file):
    entries = []

    with session_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    entry_type_counts = Counter()
    role_counts = Counter()
    tool_counts = Counter()
    compaction_tokens = 0
    branch_summary_tokens = 0
    compaction_cost = 0
    branch_summary_cost = 0

    files_read = set()
    files_modified = set()

    bash_commands = []
    tool_errors = []

    models = set()
    providers = set()

    input_tokens = 0
    output_tokens = 0
    cache_read_tokens = 0
    cache_write_tokens = 0
    total_tokens = 0

    input_cost = 0
    output_cost = 0
    cache_read_cost = 0
    cache_write_cost = 0
    total_cost = 0

    timestamps = []

    for entry in entries:
        entry_type = entry.get("type")
        entry_type_counts[entry_type] += 1

        timestamp = parse_timestamp(entry.get("timestamp"))
        
        if entry_type in {"compaction", "branch_summary"}:
            usage = entry.get("usage", {})

            total = usage.get("totalTokens", 0) or 0
            cost = usage.get("cost", {}).get("total", 0) or 0

            if entry_type == "compaction":
                compaction_tokens += total
                compaction_cost += cost

            elif entry_type == "branch_summary":
                branch_summary_tokens += total
                branch_summary_cost += cost

        if timestamp:
            timestamps.append(timestamp)

        # Session header
        if entry_type == "session":
            session_id = entry.get("id")
            session_timestamp = entry.get("timestamp")
            session_cwd = entry.get("cwd")
            session_version = entry.get("version")

        # Messages
        if entry_type != "message":
            continue

        message = entry.get("message", {})
        role = message.get("role")

        if role:
            role_counts[role] += 1

        # ---------------------------------------------------------
        # Assistant messages
        # ---------------------------------------------------------

        if role == "assistant":
            model = message.get("model")
            provider = message.get("provider")

            if model:
                models.add(model)

            if provider:
                providers.add(provider)

            usage = message.get("usage", {})

            input_tokens += usage.get("input", 0) or 0
            output_tokens += usage.get("output", 0) or 0
            cache_read_tokens += usage.get("cacheRead", 0) or 0
            cache_write_tokens += usage.get("cacheWrite", 0) or 0
            total_tokens += usage.get("totalTokens", 0) or 0

            cost = usage.get("cost", {})

            input_cost += cost.get("input", 0) or 0
            output_cost += cost.get("output", 0) or 0
            cache_read_cost += cost.get("cacheRead", 0) or 0
            cache_write_cost += cost.get("cacheWrite", 0) or 0
            total_cost += cost.get("total", 0) or 0

            # Look for tool calls inside assistant message
            content = message.get("content", [])

            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue

                    if block.get("type") != "toolCall":
                        continue

                    tool_name = block.get("name")

                    if not tool_name:
                        continue

                    tool_counts[tool_name] += 1

                    arguments = block.get("arguments", {})

                    if not isinstance(arguments, dict):
                        continue

                    # Files explicitly accessed through Pi's tools
                    if tool_name == "read":
                        path = arguments.get("path")

                        if path:
                            files_read.add(str(path))

                    elif tool_name in {"write", "edit"}:
                        path = arguments.get("path")

                        if path:
                            files_modified.add(str(path))

        # ---------------------------------------------------------
        # Tool results
        # ---------------------------------------------------------

        if role == "toolResult":
            if message.get("isError"):
                tool_errors.append(
                    {
                        "tool": message.get("toolName"),
                    }
                )

        # ---------------------------------------------------------
        # Bash executions
        # ---------------------------------------------------------

        if role == "bashExecution":
            command = message.get("command")

            if command:
                bash_commands.append(command)

        # ---------------------------------------------------------
        # File information stored in details
        # ---------------------------------------------------------

        details = message.get("details", {})

        if isinstance(details, dict):
            for path in details.get("readFiles", []):
                files_read.add(str(path))

            for path in details.get("modifiedFiles", []):
                files_modified.add(str(path))

    total_tokens += compaction_tokens + branch_summary_tokens
    total_cost += compaction_cost + branch_summary_cost

    # -------------------------------------------------------------
    # Session duration
    # -------------------------------------------------------------

    duration_seconds = None

    if len(timestamps) >= 2:
        duration_seconds = (
            max(timestamps) - min(timestamps)
        ).total_seconds()

    # -------------------------------------------------------------
    # Build statistics object
    # -------------------------------------------------------------

    statistics = {
        "session_file": session_file.name,

        "session": {
            "id": session_id if "session_id" in locals() else None,
            "timestamp": (
                session_timestamp
                if "session_timestamp" in locals()
                else None
            ),
            "cwd": session_cwd if "session_cwd" in locals() else None,
            "version": (
                session_version
                if "session_version" in locals()
                else None
            ),
        },

        "counts": {
            "total_entries": len(entries),
            "entry_types": dict(entry_type_counts),
            "messages_by_role": dict(role_counts),
            "assistant_messages": role_counts.get("assistant", 0),
            "user_messages": role_counts.get("user", 0),
            "tool_result_messages": role_counts.get("toolResult", 0),
            "bash_executions": len(bash_commands),
            "compactions": entry_type_counts.get("compaction", 0),
            "branch_summaries": entry_type_counts.get(
                "branch_summary",
                0,
            ),
        },

        "tools": {
            "total_calls": sum(tool_counts.values()),
            "distinct_tools": len(tool_counts),
            "frequency": dict(tool_counts),
            "errors": len(tool_errors),
            "error_details": tool_errors,
        },

        "files": {
            "read": sorted(files_read),
            "modified": sorted(files_modified),
            "number_of_files_read": len(files_read),
            "number_of_files_modified": len(files_modified),
        },

        "bash": {
            "number_of_commands": len(bash_commands),
            "commands": bash_commands,
        },

        "model": {
            "models": sorted(models),
            "providers": sorted(providers),
        },

        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "cache_read": cache_read_tokens,
            "cache_write": cache_write_tokens,
            "total": total_tokens,
            "compaction": compaction_tokens,
            "branch_summary": branch_summary_tokens,
        },

        "cost": {
            "input": input_cost,
            "output": output_cost,
            "cache_read": cache_read_cost,
            "cache_write": cache_write_cost,
            "total": total_cost,
            "compaction": compaction_cost,
            "branch_summary": branch_summary_cost,
        },

        "duration_seconds": duration_seconds,
    }

    return statistics


def process_task_folder(task_folder):
    run_folders = sorted(
        path
        for path in task_folder.glob("run_*")
        if path.is_dir()
    )

    if not run_folders:
        print(f"No run folders found in {task_folder}")
        return

    for run_folder in run_folders:
        session_files = list(run_folder.glob("*.jsonl"))

        if not session_files:
            print(f"[SKIP] No JSONL file found in {run_folder}")
            continue

        if len(session_files) > 1:
            print(
                f"[WARNING] Multiple JSONL files found in {run_folder}. "
                f"Using the first one."
            )

        session_file = session_files[0]

        print(f"Processing {session_file}")

        statistics = collect_statistics(session_file)

        output_file = run_folder / "statistics.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(
                statistics,
                f,
                indent=4,
            )

        print(f"  -> {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Collect statistics from Pi session JSONL files."
    )

    parser.add_argument(
        "task_folder",
        help="Path to the experiment task folder.",
    )

    args = parser.parse_args()

    task_folder = Path(args.task_folder)

    if not task_folder.exists():
        print(f"Folder does not exist: {task_folder}")
        return

    process_task_folder(task_folder)


if __name__ == "__main__":
    main()