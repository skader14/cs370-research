import numpy as np
import os
from rl_env import CloudSimSDNEnv
import matplotlib.pyplot as plt

if __name__ == "__main__":
    env = CloudSimSDNEnv(
        sim_path=r"C:\Users\saifk\CS370\Code\cloudsimsdn",
        physical_file="fat-tree-physical.json",
        virtual_file="fat-tree-virtual.json",
        workload_file="fat-tree-workload-heuristic.csv",
    )
    print("Working directory:", os.getcwd())
    print("Physical file:", env.physical_file)
    print("Virtual file:", env.virtual_file)
    print("Workload file:", env.workload_file)


    episodes = 3
    rewards = []
    for ep in range(episodes):
        print(f"\n===== EPISODE {ep+1} =====")
        state = env.reset()
        action = np.random.randint(0, env.action_size)
        next_state, reward, done, _ = env.step(action)
        rewards.append(reward)
        print(f"[EP {ep+1}] Action={action}, Reward={reward:.3f}")

    
    plt.plot(rewards)
    plt.title("Reward over episodes")
    plt.savefig("training_rewards.png")
    plt.close()
    print("Training completed. Rewards plot saved as training_rewards.png")

    

