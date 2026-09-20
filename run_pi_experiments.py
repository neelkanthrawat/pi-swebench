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
        / "experiments_2"
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
            "GWDG_API_KEY",
            "-v",
            f"{run_folder}:/pi-sessions",
            image,
            "pi",
            "--mode",
            "rpc",
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
            print("\nWaiting 60 seconds before the next run...")
            time.sleep(60)

    print("\nAll experiments finished.")


if __name__ == "__main__":
    main()













####################
# import json
# import subprocess
# from pathlib import Path

# from datasets import load_dataset


# TASK_ID = "django__django-14373"
# IMAGE = "pi-swebench-django-14373"
# N_EXPERIMENTS = 3

# PROJECT_DIR = Path(__file__).resolve().parent
# OUTPUT_ROOT = PROJECT_DIR / "experiments"


# def load_task(task_id):
#     dataset = load_dataset(
#         "SWE-bench/SWE-bench_Verified",
#         split="test",
#     )

#     return next(
#         task for task in dataset
#         if task["instance_id"] == task_id
#     )


# def next_experiment_dir(task_id, output_root):
#     task_output_dir = output_root / task_id
#     task_output_dir.mkdir(parents=True, exist_ok=True)

#     experiment_number = 1
#     while True:
#         experiment_dir = task_output_dir / f"experiment_{experiment_number:03d}"
#         if not experiment_dir.exists():
#             experiment_dir.mkdir()
#             return experiment_dir
#         experiment_number += 1


# def start_pi(task_id, image, task, session_dir):
#     process = subprocess.Popen(
#         [
#             "docker",
#             "run",
#             "--rm",
#             "-i",
#             "-e",
#             "GWDG_API_KEY",
#             "-v",
#             f"{session_dir}:/pi-sessions",
#             image,
#             "pi",
#             "--mode",
#             "rpc",
#             "--session-dir",
#             "/pi-sessions",
#         ],
#         stdin=subprocess.PIPE,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         text=True,
#         bufsize=1,
#         encoding="utf-8",
#     )

#     prompt = {
#         "type": "prompt",
#         "message": (
#             "Solve this SWE-bench task.\n\n"
#             "Work directly in the repository at /testbed.\n"
#             f"Task: \n{task['problem_statement']}"
#         ),
#     }

#     process.stdin.write(json.dumps(prompt) + "\n")
#     process.stdin.flush()
#     process.stdin.close()

#     return process


# def run_experiments(task_id, image, task, n_experiments, output_root=OUTPUT_ROOT):
#     for experiment_number in range(1, n_experiments + 1):
#         session_dir = next_experiment_dir(task_id, output_root)
#         print(
#             f"Starting experiment {experiment_number}/{n_experiments}: "
#             f"{session_dir}"
#         )

#         process = start_pi(task_id, image, task, session_dir)
#         try:
#             for line in process.stdout:
#                 print(line, end="", flush=True)
#                 if '"type":"agent_settled"' in line:
#                     break
#         finally:
#             process.terminate()
#             process.wait()

#         print(f"Finished experiment {experiment_number}: {session_dir}")


# def main():
#     task = load_task(TASK_ID)
#     print(f"Task: {TASK_ID}")
#     print(f"Running {N_EXPERIMENTS} experiments")

#     run_experiments(TASK_ID, IMAGE, task, N_EXPERIMENTS)


# if __name__ == "__main__":
#     main()
