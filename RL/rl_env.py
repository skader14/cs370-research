import os
import subprocess
import numpy as np
from metrics_parser import extract_state, count_packet_failures
from routing_actions import reroute_link

class CloudSimSDNEnv:
    def __init__(self, sim_path, physical_file, virtual_file, workload_file):
        # Use the actual parameter, not the string literal
        self.sim_path = sim_path  

        # Ensure the files are joined relative to the sim_path
        self.physical_file = os.path.join(sim_path, physical_file)
        self.virtual_file = os.path.join(sim_path, virtual_file)
        self.workload_file = os.path.join(sim_path, workload_file)

        # Derived attributes
        self.vms = [f"vm0{i+1}" for i in range(8)]  # adapt if you change topology
        self.state_size = 14
        self.action_size = len(self.vms)
        self.current_state = np.zeros(self.state_size)


    def run_simulation(self):
        """Runs the CloudSimSDN Java simulation synchronously."""
        cmd = [
            "java",
            "-cp",
            "target/classes;target/dependency/*",
            "org.cloudbus.cloudsim.sdn.example.SimpleExample",
            "LFF",
            self.physical_file,
            self.virtual_file,
            self.workload_file,
        ]
        print(f"[RUN] Launching simulation with {self.virtual_file}")
        subprocess.run(cmd, cwd=self.sim_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def get_state(self):
        """Reads metrics and returns new state vector."""
        state = extract_state(self.sim_path)
        self.current_state = state
        return state

    def compute_reward(self):
        """Computes reward based on failures + energy efficiency."""
        failures = count_packet_failures(self.sim_path)

        sw_energy_path = os.path.join(self.sim_path, "sw_energy.csv")
        if os.path.exists(sw_energy_path):
            energy = np.sum(np.loadtxt(sw_energy_path, delimiter=",", skiprows=1, usecols=[1]))
        else:
            energy = 0

        # Reward: penalize failures and high energy
        reward = -3 * failures - 0.005 * energy
        print(f"[REWARD] Failures={failures}, Energy={energy:.2f}, Reward={reward:.3f}")
        return reward

    def step(self, action_index):
        """
        Performs one RL step:
        1. Modify the topology based on the action
        2. Rerun CloudSimSDN
        3. Compute new state + reward
        """
        src_vm = "vm01"
        current_dst = "vm05"
        new_dst = self.vms[action_index % len(self.vms)]

        updated_virtual, _ = reroute_link(self.virtual_file, src_vm, current_dst, self.vms)
        self.virtual_file = updated_virtual

        self.run_simulation()
        next_state = self.get_state()
        reward = self.compute_reward()
        done = True  # one sim per step for now

        return next_state, reward, done, {}

    def reset(self):
        """Resets environment for next episode."""
        self.current_state = np.zeros(self.state_size)
        return self.current_state
