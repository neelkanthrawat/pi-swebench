import json
import subprocess
from pathlib import Path
import argparse
import time

from datasets import load_dataset

# INPUTS
# TASK_ID = "django__django-14373"
# IMAGE = "pi-swebench-django-14373"


# GET TASK
def get_task(TASK_ID):
    dataset = load_dataset(
        "SWE-bench/SWE-bench_Verified",
        split="test",
    )

    task = next(
        task for task in dataset
        if task["instance_id"] == TASK_ID
    )

    return task["problem_statement"]


# RUN PI ONCE
def run_pi(task, task_id, image, run_number):

    run_folder = (
        Path.cwd()
        / "experiments_openai_2"
        / task_id
        / f"run_{run_number}"
    )

    run_folder.mkdir(parents=True, exist_ok=True)

    process = subprocess.Popen(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "-e",
            "OPENAI_API_KEY",
            "-v",
            f"{run_folder}:/pi-sessions",
            image,
            "pi",
            "--mode",
            "rpc", # i need to understand what exactly is this rpc mode really is. 
            "--session-dir",# some kind of folder mounting
            "/pi-sessions",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
    )

    prompt = {
        "type": "prompt",
        "message": (
            "Solve this SWE-bench task.\n\n"
            "Work directly in the repository at /testbed.\n"
            "Use `/opt/miniconda3/envs/testbed/bin/python` for all Python commands "
            "and tests. Do not install or modify benchmark dependencies unless required "
            "by the task.\n\n"
            f"Task:\n{task}"
        ),
    }

    process.stdin.write(json.dumps(prompt) + "\n")
    process.stdin.flush()

    print(f"\n========== RUN {run_number} ==========\n")

    for line in process.stdout:
        print(line, end="", flush=True)

        # if '"type":"agent_settled"' in line:
        #     break
        if '"type":"agent_settled"' in line:
            process.stdin.write(
                json.dumps({
                    "id": "stats",
                    "type": "get_session_stats",
                }) + "\n"
            )
            process.stdin.flush()
            continue
        try:
            response = json.loads(line)
        except json.JSONDecodeError:
            continue

        if response.get("id") == "stats":
            stats_file = run_folder / "pi_session_stats.json"

            with stats_file.open("w", encoding="utf-8") as f:
                json.dump(
                    response.get("data", {}),
                    f,
                    indent=4,
                )

            print(f"\nPi statistics saved to: {stats_file}")
            break
        # till here I did things

    process.terminate()
    process.wait()

    print(f"\n========== RUN {run_number} FINISHED ==========\n")


# MAIN
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-experiments", type=int, default=1)
    parser.add_argument("--task-id", type=str, default="django__django-14373")
    parser.add_argument("--image", type=str, default="pi-swebench-django-14373")
    args = parser.parse_args()

    print(f"Task ID: {args.task_id}")
    print(f"Image: {args.image}")
    print(f"Number of experiments: {args.n_experiments}")

    # Load the problem statement ONCE.
    task = get_task(args.task_id) # the problem statement

    print("\nTask loaded successfully.")
    print("\nStarting experiments...")

    for run_number in range(1, args.n_experiments + 1):
        run_pi(task, args.task_id, args.image, run_number)
        if run_number < args.n_experiments:
            print("\nWaiting 10 seconds before the next run...")
            time.sleep(10)

    print("\nAll experiments finished.")


if __name__ == "__main__":
    main()