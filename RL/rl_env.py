import time
from typing import List, Dict
from .flow_manager import select_critical_flows_via_bridge


class CloudSimSDNEnv:
    """
    Lightweight environment wrapper that talks to the Java RLNetworkBridge.
    It implements a small step() that queries averaged observed latencies,
    compares them to expected latencies, selects top-K critical flows and
    asks the NOS to reroute them.
    """

    def __init__(self, bridge, window: float = 5.0, k: int = 10, max_reroute_ratio: float = 0.15):
        self.bridge = bridge
        self.window = window
        self.k = k
        self.max_reroute_ratio = max_reroute_ratio

    def step(self) -> Dict:
        """Perform one monitoring-based decision step.
        Returns a simple report dictionary with selected flows and timestamp.
        """
        t = self.bridge.getTime()
        selected = select_critical_flows_via_bridge(self.bridge, window=self.window, k=self.k, max_reroute_ratio=self.max_reroute_ratio)
        results = []
        for fid in selected:
            try:
                ok = self.bridge.rerouteFlow(int(fid))
            except Exception:
                ok = False
            results.append({'flowId': int(fid), 'rerouted': bool(ok)})

        return {
            'time': t,
            'selected_flows': results
        }

    def reset(self):
        # No internal state in this minimal wrapper
        return {}
