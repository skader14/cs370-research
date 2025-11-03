import json
import random
import os

def reroute_link(virtual_file, src_vm, current_dst, all_vms):
    """
    Randomly reroute a link from src_vm to another destination.
    Returns the name of the updated JSON file.
    """
    with open(virtual_file, "r") as f:
        data = json.load(f)

    # Pick a new destination different from current_dst and src_vm
    candidates = [v for v in all_vms if v not in [current_dst, src_vm]]
    new_dst = random.choice(candidates)

    # Find link to modify
    for link in data["links"]:
        if link["source"] == src_vm and link["destination"] == current_dst:
            print(f"[ACTION] Rerouting {src_vm} → {current_dst} → {new_dst}")
            link["destination"] = new_dst
            link["name"] = f"{src_vm}-{new_dst}"
            break

    # Save updated version
    output_file = os.path.join(os.path.dirname(virtual_file), "fat-tree-virtual-temp.json")
    updated_file = output_file
    with open(updated_file, "w") as f:
        json.dump(data, f, indent=2)

    return updated_file, f"{src_vm}-{new_dst}"
