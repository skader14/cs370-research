import os
import pandas as pd
import numpy as np

def extract_state(sim_path):
    """
    Reads CloudSimSDN output CSVs and produces a normalized state vector.
    """
    link_file = os.path.join(sim_path, "link_utilization_up.csv")
    sw_file = os.path.join(sim_path, "sw_energy.csv")

    if not os.path.exists(link_file) or not os.path.exists(sw_file):
        print("[WARN] Missing metrics files, returning zeros.")
        return np.zeros(14)

    link_df = pd.read_csv(link_file)
    sw_df = pd.read_csv(sw_file)

    # Extract average utilization per link
    if "Utilization" in link_df.columns:
        link_util = link_df["Utilization"].values
    else:
        link_util = link_df.iloc[:, -1].values  # fallback to last column

    # Extract energy consumption per switch
    if "Energy" in sw_df.columns:
        sw_energy = sw_df["Energy"].values
    else:
        sw_energy = sw_df.iloc[:, -1].values

    # Normalize
    link_util = link_util / np.max(link_util) if np.max(link_util) > 0 else link_util
    sw_energy = sw_energy / np.max(sw_energy) if np.max(sw_energy) > 0 else sw_energy

    # Concatenate as state vector
    state = np.concatenate([link_util, sw_energy])
    return state[:14]  # limit for consistent state size


def count_packet_failures(sim_path):
    """
    Counts number of 'Packet failed' messages in the CloudSimSDN output log.
    """
    log_file = os.path.join(sim_path, "result_fat-tree-workload-heuristic.csv")
    count = 0
    if not os.path.exists(log_file):
        return 0

    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "Packet failed" in line:
                count += 1
    return count
