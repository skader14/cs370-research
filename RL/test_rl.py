#!/usr/bin/env python3

import time
import argparse
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
from py4j.java_gateway import JavaGateway, GatewayParameters
import numpy as np
from rl_env import CloudSimSDNEnv

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EpisodeMetrics:
    """Track metrics for a single episode"""
    rewards: List[float]
    max_utilizations: List[float]
    avg_latencies: List[float]
    step_times: List[float]
    
    def add_step(self, reward: float, info: Dict[str, Any]):
        """Add metrics from a single step"""
        self.rewards.append(reward)
        self.max_utilizations.append(info['max_utilization'])
        self.avg_latencies.append(info['avg_latency'])
        self.step_times.append(info['time'])
    
    def print_summary(self):
        """Print episode statistics"""
        logger.info("Episode Summary:")
        logger.info(f"Total steps: {len(self.rewards)}")
        logger.info(f"Average reward: {np.mean(self.rewards):.4f}")
        logger.info(f"Final max utilization: {self.max_utilizations[-1]:.4f}")
        logger.info(f"Final avg latency: {self.avg_latencies[-1]:.4f}")
        logger.info(f"Simulation time: {self.step_times[-1]:.2f}s")


def connect_gateway(port=25333, retries=20, delay=1.0):
    """Try to connect to the Java gateway with retries."""
    last_exc = None
    logger.info(f"Attempting to connect to Java gateway on port {port}")
    
    for attempt in range(retries):
        try:
            gateway = JavaGateway(gateway_parameters=GatewayParameters(port=port))
            # Test the connection by calling a simple method
            gateway.jvm.System.currentTimeMillis()
            logger.info("Successfully connected to Java gateway")
            return gateway
        except Exception as e:
            last_exc = e
            if attempt < retries - 1:  # Don't sleep on last attempt
                logger.debug(f"Connection attempt {attempt + 1} failed, retrying in {delay}s...")
                time.sleep(delay)
    
    logger.error(f"Failed to connect to Java gateway after {retries} attempts")
    logger.error(f"Last error: {last_exc}")
    raise last_exc


def validate_observation(obs: np.ndarray, expected_shape: tuple):
    """Validate observation array"""
    assert obs is not None, "Observation cannot be None"
    assert isinstance(obs, np.ndarray), "Observation must be numpy array"
    assert obs.shape == expected_shape, f"Expected shape {expected_shape}, got {obs.shape}"
    assert not np.any(np.isnan(obs)), "Observation contains NaN values"
    assert np.all(np.isfinite(obs)), "Observation contains infinite values"
    assert np.all(obs >= 0), "Utilization/latency values must be non-negative"
    assert np.all(obs <= 1.0), "Utilization values must be <= 1.0"

def test_rl_environment(no_shutdown: bool = False, n_steps: int = 20):
    """Run a test episode of the RL environment with validation"""
    # Connect to the Java gateway
    gateway = connect_gateway()
    logger.info("Connected to Java gateway")

    try:
        # Get the bridge instance and create environment
        bridge = gateway.entry_point
        env = CloudSimSDNEnv(bridge)
        logger.info("Created RL environment")

        # Track episode metrics
        metrics = EpisodeMetrics([], [], [], [])

        # Reset environment (guarded)
        try:
            initial_state = env.reset()
            logger.info(f"Initial state shape: {initial_state.shape}")
            validate_observation(initial_state, (env.observation_space_size,))
        except Exception as e:
            logger.error(f"Error during reset: {e}")
            return

        # Run episode steps with validation
        prev_time = 0.0
        for i in range(n_steps):
            logger.info(f"\nStep {i+1}:")
            try:
                # Execute step
                obs, reward, done, info = env.step()
                
                # Validate observation
                validate_observation(obs, (env.observation_space_size,))
                
                # Validate info dict
                assert all(k in info for k in ['time', 'max_utilization', 'avg_latency']), \
                    "Missing required info fields"
                
                # Validate simulation progress
                curr_time = info['time']
                assert curr_time > prev_time, "Simulation time must increase"
                prev_time = curr_time
                
                # Track metrics
                metrics.add_step(reward, info)
                
                # Log step info
                logger.info(f"Observation shape: {obs.shape}")
                logger.info(f"Reward: {reward:.4f}")
                logger.info(f"Max utilization: {info['max_utilization']:.4f}")
                logger.info(f"Avg latency: {info['avg_latency']:.4f}")
                logger.info(f"Simulation time: {info['time']:.2f}s")
                
            except Exception as e:
                logger.error(f"Error during step {i+1}: {e}")
                break

            if done:
                logger.info("Episode finished")
                break

            # Small delay between steps for stability
            time.sleep(0.5)
        
        # Print episode summary
        metrics.print_summary()

    finally:
        if not no_shutdown:
            try:
                gateway.shutdown()
                print("Gateway shut down")
            except Exception:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-shutdown", dest="no_shutdown", action="store_true",
                        help="Do not call gateway.shutdown() at the end (leave Java gateway running)")
    parser.add_argument("--steps", type=int, default=20,
                        help="Number of steps to run in test episode")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    test_rl_environment(no_shutdown=args.no_shutdown, n_steps=args.steps)