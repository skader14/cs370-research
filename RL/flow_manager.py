"""
Flow Manager for RL-based Traffic Engineering in CloudSimSDN.
Handles critical flow selection and flow table updates.
"""

import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class FlowStats:
    """Statistics for a single flow"""
    flow_id: str
    src_id: str
    dst_id: str
    bandwidth: float
    current_path: List[str]
    latency: float
    queue_lengths: Dict[str, float]

@dataclass
class LinkStats:
    """Statistics for a single link"""
    link_id: str
    utilization: float
    capacity: float
    current_flows: List[str]
    queue_length: float

class RLFlowManager:
    """Manages flow statistics and updates for RL-based traffic engineering"""
    
    def __init__(self, max_reroute_ratio: float = 0.15):
        self.max_reroute_ratio = max_reroute_ratio
        self.flow_stats: Dict[str, FlowStats] = {}
        self.link_stats: Dict[str, LinkStats] = {}
        self.last_update_time = 0.0
        self.update_interval = 1.0  # 1 second default
        
    def update_flow_stats(self, flow_id: str, stats: FlowStats) -> None:
        """Update statistics for a single flow"""
        self.flow_stats[flow_id] = stats
        
    def update_link_stats(self, link_id: str, stats: LinkStats) -> None:
        """Update statistics for a single link"""
        self.link_stats[link_id] = stats
        
    def calculate_congestion_impact(self, flow_id: str) -> float:
        """
        Calculate how much a flow contributes to network congestion.
        Based on Zhang et al.'s approach.
        """
        flow = self.flow_stats.get(flow_id)
        if not flow:
            return 0.0
            
        impact = 0.0
        # Sum the utilization of links along flow's path
        for link_id in flow.current_path:
            link = self.link_stats.get(link_id)
            if link:
                # Higher impact if link is more utilized
                impact += link.utilization / link.capacity
                # Additional impact from queue buildup
                impact += link.queue_length / link.capacity
                
        return impact * flow.bandwidth
        
    def select_critical_flows(self, current_time: float, k: int = 10) -> List[str]:
        """
        Select top K flows that most contribute to congestion,
        while respecting the maximum reroute ratio.
        """
        # Check if enough time has passed since last update
        if current_time - self.last_update_time < self.update_interval:
            return []
            
        # Calculate congestion impact for all flows
        flow_impacts = {
            flow_id: self.calculate_congestion_impact(flow_id)
            for flow_id in self.flow_stats.keys()
        }
        
        # Sort flows by impact
        sorted_flows = sorted(
            flow_impacts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Limit number of flows to reroute
        max_flows = int(len(self.flow_stats) * self.max_reroute_ratio)
        k = min(k, max_flows)
        
        selected_flows = [flow_id for flow_id, _ in sorted_flows[:k]]
        self.last_update_time = current_time
        
        return selected_flows
        
    def get_flow_state(self) -> Dict:
        """Get current network state for RL environment"""
        return {
            'flows': self.flow_stats,
            'links': self.link_stats,
            'max_utilization': max(
                (link.utilization for link in self.link_stats.values()),
                default=0.0
            ),
            'avg_latency': np.mean([
                flow.latency for flow in self.flow_stats.values()
            ])
        }


def select_critical_flows_via_bridge(bridge, window: float = 5.0, k: int = 10, max_reroute_ratio: float = 0.15):
    """
    Helper that queries the Java bridge for basic metrics and selects critical flows.
    Strategy: compute latency_ratio = (observed - expected) / expected and multiply by requested bandwidth.
    Returns a list of flowIds to reroute.
    """
    flow_ids = bridge.getFlowIds()
    if flow_ids is None:
        return []

    scores = []
    for fid in flow_ids:
        try:
            obs = bridge.getFlowAvgLatency(int(fid), window)
            endpoints = bridge.getFlowEndpoints(int(fid))
            if endpoints is None:
                continue
            src = int(endpoints[0])
            dst = int(endpoints[1])
            exp = bridge.getExpectedLatency(src, dst, int(fid))
            bw = bridge.getRequestedBandwidth(int(fid))
            if obs <= 0 or exp <= 0:
                ratio = 0.0
            else:
                ratio = (obs - exp) / exp
            score = ratio * max(1.0, float(bw))
            scores.append((fid, score))
        except Exception:
            continue

    # sort and pick top-K while respecting max_reroute_ratio
    scores.sort(key=lambda x: x[1], reverse=True)
    if len(scores) == 0:
        return []

    max_flows = max(1, int(len(scores) * max_reroute_ratio))
    k = min(k, max_flows)
    selected = [int(fid) for fid, _ in scores[:k] if _ > 0]
    return selected