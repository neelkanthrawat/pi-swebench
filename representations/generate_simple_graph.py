import json
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx


# Visual style for each action type

ACTION_STYLE = {
    "read": {
        "color": "skyblue",
        "shape": "o",
    },
    "write": {
        "color": "lightgreen",
        "shape": "s",
    },
    "edit": {
        "color": "gold",
        "shape": "d",
    },
    "bash": {
        "color": "lightcoral",
        "shape": "^",
    },
}


def generate_figure(trajectory_file):
    trajectory_file = Path(trajectory_file)

    
    # Load trajectory JSONL
    

    trajectory = []

    with trajectory_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            trajectory.append(json.loads(line))

    
    # Create graph
    

    graph = nx.DiGraph()

    for node in trajectory:
        step = node["step"]
        action = node["action"]

        graph.add_node(
            step,
            action=action,
        )

    
    # Connect consecutive actions
    

    for i in range(len(trajectory) - 1):
        current_step = trajectory[i]["step"]
        next_step = trajectory[i + 1]["step"]

        graph.add_edge(
            current_step,
            next_step,
        )

    
    # Chronological layout
    #
    # step 0 -> step 1 -> step 2 -> ...
    

    pos = {
        node: (node, 0)
        for node in graph.nodes
    }

    
    # Draw
    

    plt.figure(
        figsize=(max(12, len(trajectory) * 1.5), 5)
    )

    # Draw edges first so they appear behind nodes.
    nx.draw_networkx_edges(
        graph,
        pos=pos,
        arrows=True,
        arrowsize=20,
    )

    
    # Draw nodes grouped by action type
    

    for action, style in ACTION_STYLE.items():

        nodes = [
            node
            for node in graph.nodes
            if graph.nodes[node]["action"] == action
        ]

        if not nodes:
            continue

        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=nodes,
            node_color=style["color"],
            node_shape=style["shape"],
            node_size=2500,
        )

    
    # Handle unknown action types
    

    known_actions = set(ACTION_STYLE)

    unknown_nodes = [
        node
        for node in graph.nodes
        if graph.nodes[node]["action"] not in known_actions
    ]

    if unknown_nodes:
        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=unknown_nodes,
            node_color="lightgray",
            node_shape="o",
            node_size=2500,
        )

    
    # Labels
    #
    # Only show the tool/action name.
    

    labels = {
        node: f"{node}\n{graph.nodes[node]['action']}"
        for node in graph.nodes
    }

    nx.draw_networkx_labels(
        graph,
        pos,
        labels=labels,
        font_size=8,
    )

    plt.axis("off")
    plt.tight_layout()

    
    # Save
    

    output_dir = (
        Path.cwd()
        / "graphs"
        / "simplest_graphs"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / f"{trajectory_file.stem}.png"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close()

    print(f"Graph saved to: {output_file}")


# Command-line interface

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "trajectory_file",
        help="Path to the trajectory JSONL file.",
    )

    args = parser.parse_args()

    trajectory_file = Path(args.trajectory_file)

    if not trajectory_file.exists():
        print(f"File does not exist: {trajectory_file}")
        return

    generate_figure(trajectory_file)


if __name__ == "__main__":
    main()