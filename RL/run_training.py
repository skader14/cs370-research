import argparse
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import matplotlib.pyplot as plt
from rl_env import CloudSimSDNEnv

def parse_args():
    parser = argparse.ArgumentParser(
        description='Train RL agent for CloudSimSDN traffic engineering'
    )
    parser.add_argument(
        '--episodes',
        type=int,
        default=1000,
        help='Number of training episodes'
    )
    parser.add_argument(
        '--monitoring-interval',
        type=float,
        default=1.0,
        help='Interval between monitoring updates (seconds)'
    )
    parser.add_argument(
        '--max-reroute-ratio',
        type=float,
        default=0.15,
        help='Maximum fraction of flows to reroute'
    )
    parser.add_argument(
        '--model-path',
        type=str,
        default='rl_model',
        help='Path to save/load model'
    )
    return parser.parse_args()

def create_env(nos):
    """Create and configure the RL environment"""
    return CloudSimSDNEnv(
        nos=nos,
        max_flows=100,  # Adjust based on your topology
        max_links=50,   # Adjust based on your topology
        update_interval=1.0,
        max_reroute_ratio=0.15
    )


def train(env, args):
    """Train the RL agent"""
    # Create vectorized environment
    vec_env = DummyVecEnv([lambda: env])
    
    # Initialize PPO agent
    model = PPO(
        "MultiInputPolicy",
        vec_env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        tensorboard_log="./tensorboard_logs/"
    )
    
    # Training loop
    total_timesteps = args.episodes * env.max_flows
    rewards = []
    
    print(f"Starting training for {args.episodes} episodes...")
    model.learn(total_timesteps=total_timesteps)
    
    # Save the trained model
    model.save(args.model_path)
    print(f"Model saved to {args.model_path}")
    
    # Plot rewards
    plt.figure(figsize=(10, 5))
    plt.plot(rewards)
    plt.title("Training Rewards")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.savefig("training_rewards.png")
    plt.close()
    
def evaluate(env, model_path, num_episodes=10):
    """Evaluate the trained agent"""
    model = PPO.load(model_path)
    rewards = []
    
    for episode in range(num_episodes):
        obs = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, _ = env.step(action)
            episode_reward += reward
            
        rewards.append(episode_reward)
        print(f"Episode {episode + 1} reward: {episode_reward:.3f}")
    
    mean_reward = np.mean(rewards)
    std_reward = np.std(rewards)
    print(f"\nEvaluation over {num_episodes} episodes:")
    print(f"Mean reward: {mean_reward:.3f} ± {std_reward:.3f}")
    
def main():
    # Parse command line arguments
    args = parse_args()
    
    # Get NetworkOperatingSystem instance
    # This would be set up by CloudSimSDN before training
    nos = get_network_operating_system()
    
    # Create and configure environment
    env = create_env(nos)
    
    # Train the agent
    print("Starting training...")
    train(env, args)
    
    # Evaluate the trained agent
    print("\nStarting evaluation...")
    evaluate(env, args.model_path)

if __name__ == "__main__":
    main()

    

