import time
import numpy as np
from typing import List, Dict, Tuple, Optional
from flow_manager import select_critical_flows_via_bridge

class NetworkState:
    """Represents the current state of the network including link utilization and flow metrics"""
    def __init__(self, link_utils: Dict[str, float], flow_latencies: Dict[str, float]):
        self.link_utils = link_utils
        self.flow_latencies = flow_latencies
    
    def to_array(self) -> np.ndarray:
        """Convert state to a flat numpy array for RL agent consumption"""
        # Concatenate link utilizations and flow latencies
        # NOTE: Keep a deterministic ordering when converting to array.
        # Caller (CloudSimSDNEnv) will typically create arrays in the
        # desired order; this fallback uses sorted keys.
        link_vals = np.array([self.link_utils[k] for k in sorted(self.link_utils.keys())])
        flow_vals = np.array([self.flow_latencies[k] for k in sorted(self.flow_latencies.keys())])
        return np.concatenate([link_vals, flow_vals])

class CloudSimSDNEnv:
    """
    RL environment wrapper that interfaces with the Java RLNetworkBridge.
    Implements OpenAI Gym-like interface with proper state/action spaces
    and reward calculation based on network performance metrics.
    """

    def __init__(self, bridge, window: float = 5.0, k: int = 10, max_reroute_ratio: float = 0.15):
        self.bridge = bridge
        self.window = window  # Time window for averaging metrics
        self.k = k  # Maximum flows to reroute per step
        self.max_reroute_ratio = max_reroute_ratio
        
        # Cache network structure
        # bridge.getAllLinkIds() returns a list of string ids (labels). Build
        # a mapping from label -> index so we can call getLinkAvgUtilization(index,...)
        raw_link_ids = list(self.bridge.getAllLinkIds())
        self.link_ids = raw_link_ids
        self.link_id_to_idx = {lid: i for i, lid in enumerate(self.link_ids)}
        self.n_links = len(self.link_ids)
        
        # Initialize metrics history
        self.prev_avg_latency = None
        self.baseline_congestion = None
        
        # Get initial flow IDs to establish space dimensions
        self.initial_flow_ids = sorted(str(x) for x in self.bridge.getFlowIds())
        self.n_flows = len(self.initial_flow_ids)
        
        # Define spaces
        self.observation_space_size = self.n_links + self.n_flows  # Link utils + flow latencies
        self.action_space_size = self.k  # Number of flows we can reroute
        
    def _normalize_value(self, value: float, is_utilization: bool = True) -> float:
        """Normalize values to valid ranges and handle invalid values"""
        if value is None or np.isnan(value) or np.isinf(value):
            return 0.0
        
        if is_utilization:
            # Utilization should be between 0 and 1
            return max(0.0, min(1.0, float(value)))
        else:
            # Latency should be non-negative, cap at large value if needed
            return max(0.0, min(1e6, float(value)))

    def _get_network_state(self) -> NetworkState:
        """Collect current network state from bridge"""
        link_utils = {}
        for link_id in self.link_ids:
            try:
                # Map label -> index and call Java bridge with the integer index
                idx = self.link_id_to_idx[link_id]
                util = self.bridge.getLinkAvgUtilization(int(idx), float(self.window))
                link_utils[link_id] = self._normalize_value(util, is_utilization=True)
            except Exception:
                # On error, assume no utilization
                link_utils[link_id] = 0.0
            
        flow_latencies = {}
        for flow_id in self.bridge.getFlowIds():
            try:
                fid = int(flow_id)
                latency = self.bridge.getFlowAvgLatency(int(fid), float(self.window))
                flow_latencies[fid] = self._normalize_value(latency, is_utilization=False)
            except Exception:
                # On error, assume zero latency
                flow_latencies[fid] = 0.0
            
        return NetworkState(link_utils, flow_latencies)
    
    def _calculate_reward(self, prev_state: NetworkState, curr_state: NetworkState) -> float:
        """
        Calculate reward based on:
        1. Reduction in average flow latency
        2. Reduction in maximum link utilization
        3. Penalty for excessive rerouting
        """
        try:
            # Get valid latency values (non-zero and finite)
            prev_latencies = [v for v in prev_state.flow_latencies.values() 
                            if v > 0 and np.isfinite(v)]
            curr_latencies = [v for v in curr_state.flow_latencies.values() 
                            if v > 0 and np.isfinite(v)]
            
            # Calculate latency improvement if we have valid values
            if prev_latencies and curr_latencies:
                prev_latency = np.mean(prev_latencies)
                curr_latency = np.mean(curr_latencies)
                latency_reward = prev_latency - curr_latency
            else:
                latency_reward = 0.0
            
            # Get valid utilization values
            prev_utils = [v for v in prev_state.link_utils.values() 
                        if v >= 0 and np.isfinite(v)]
            curr_utils = [v for v in curr_state.link_utils.values() 
                        if v >= 0 and np.isfinite(v)]
            
            # Calculate congestion reduction if we have valid values
            if prev_utils and curr_utils:
                prev_max_util = max(prev_utils)
                curr_max_util = max(curr_utils)
                congestion_reward = prev_max_util - curr_max_util
            else:
                congestion_reward = 0.0
            
            # Combine rewards with weights
            total_reward = (0.7 * latency_reward) + (0.3 * congestion_reward)
            
            # Ensure reward is finite and reasonable
            return float(max(-100.0, min(100.0, total_reward)))
            
        except Exception:
            # On any error, return zero reward
            return 0.0

    def step(self) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one RL environment step:
        1. Get current network state
        2. Select critical flows for potential rerouting
        3. Apply rerouting actions
        4. Calculate reward based on resulting state
        
        Returns:
            observation: Network state as numpy array
            reward: Float reward value
            done: Boolean indicating if episode is complete
            info: Additional step information
        """
        # Get pre-action state
        prev_state = self._get_network_state()
        
        # Select and reroute critical flows
        selected = select_critical_flows_via_bridge(
            self.bridge, 
            window=self.window,
            k=self.k,
            max_reroute_ratio=self.max_reroute_ratio
        )
        
        results = []
        for fid in selected:
            try:
                ok = self.bridge.rerouteFlow(int(fid))
                results.append({'flowId': int(fid), 'rerouted': bool(ok)})
            except Exception:
                results.append({'flowId': int(fid), 'rerouted': False})
        
        # Small delay to let changes propagate
        time.sleep(0.1)
        
        # Get post-action state
        curr_state = self._get_network_state()
        
        # Calculate reward
        reward = self._calculate_reward(prev_state, curr_state)

        # Convert state to observation array with fixed dimensionality
        link_array = np.array([curr_state.link_utils[lid] for lid in self.link_ids])
        
        # Use initial flow IDs to maintain consistent observation space
        flow_array = np.zeros(self.n_flows)
        for i, fid in enumerate(self.initial_flow_ids):
            if int(fid) in curr_state.flow_latencies:
                flow_array[i] = curr_state.flow_latencies[int(fid)]
        
        obs = np.concatenate([link_array, flow_array])

        # Check if simulation is complete
        done = not bool(self.bridge.isRunning())

        info = {
            'time': self.bridge.getTime(),
            'selected_flows': results,
            'avg_latency': np.mean(list(curr_state.flow_latencies.values())),
            'max_utilization': max(curr_state.link_utils.values())
        }

        return obs, reward, done, info

    def reset(self) -> np.ndarray:
        """Reset environment and return initial observation"""
        # Get initial state
        state = self._get_network_state()
        
        # Convert to observation array using same format as step()
        link_array = np.array([state.link_utils[lid] for lid in self.link_ids])
        
        flow_array = np.zeros(self.n_flows)
        for i, fid in enumerate(self.initial_flow_ids):
            if int(fid) in state.flow_latencies:
                flow_array[i] = state.flow_latencies[int(fid)]
        
        return np.concatenate([link_array, flow_array])
        """Reset environment state and return initial observation"""
        # Clear metric history
        self.prev_avg_latency = None
        self.baseline_congestion = None

        # Get initial state
        initial_state = self._get_network_state()
        link_array = np.array([initial_state.link_utils[lid] for lid in self.link_ids])
        flow_keys_sorted = sorted(initial_state.flow_latencies.keys())
        flow_array = np.array([initial_state.flow_latencies[fid] for fid in flow_keys_sorted])
        return np.concatenate([link_array, flow_array])
