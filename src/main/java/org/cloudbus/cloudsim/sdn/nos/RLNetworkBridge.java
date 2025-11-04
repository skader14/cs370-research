package org.cloudbus.cloudsim.sdn.nos;

import org.cloudbus.cloudsim.core.CloudSim;

import java.util.ArrayList;
import java.util.List;

/**
 * Simple bridge class to expose lightweight NetworkOperatingSystem helper methods to Python RL code.
 * Methods are intentionally small and return primitive/list types friendly to Py4J.
 */
public class RLNetworkBridge {
    private final NetworkOperatingSystem nos;

    public RLNetworkBridge(NetworkOperatingSystem nos) {
        this.nos = nos;
    }

    public List<Integer> getFlowIds() {
        return nos.getFlowIds();
    }

    public double getFlowAvgLatency(int flowId, double windowSeconds) {
        return nos.getFlowAvgLatency(flowId, windowSeconds);
    }

    public List<String> getAllLinkIds() {
        return nos.getAllLinkIds();
    }

    public double getLinkAvgUtilization(int linkIndex, double windowSeconds) {
        return nos.getLinkAvgUtilization(linkIndex, windowSeconds);
    }

    public int[] getFlowPath(int flowId) {
        return nos.getFlowPath(flowId);
    }

    public int[] getFlowEndpoints(int flowId) {
        return nos.getFlowEndpoints(flowId);
    }

    public boolean rerouteFlow(int flowId) {
        return nos.rerouteFlow(flowId);
    }

    public double getExpectedLatency(int srcVm, int dstVm, int flowId) {
        return nos.calculateLatency(srcVm, dstVm, flowId);
    }

    public double getRequestedBandwidth(int flowId) {
        return nos.getRequestedBandwidth(flowId);
    }

    public double getTime() {
        return CloudSim.clock();
    }
}