package org.cloudbus.cloudsim.sdn.example;

import org.junit.Test;
import static org.junit.Assert.*;

import java.util.List;
import py4j.GatewayServer;
import org.cloudbus.cloudsim.core.CloudSim;
import org.cloudbus.cloudsim.sdn.nos.RLNetworkBridge;

public class RLIntegrationTest {
    
    @Test
    public void testRLMonitoringExample() throws Exception {
        // Create and run example
        RLMonitoringExample example = new RLMonitoringExample();
        
        // Start simulation
        example.start();
        
        // Get bridge instance and verify it's working
        RLNetworkBridge bridge = example.getBridge();
        assertNotNull("Bridge should be initialized", bridge);
        
        // Test basic bridge methods
        List<Integer> flowIds = bridge.getFlowIds();
        assertNotNull("Should get flow IDs", flowIds);
        assertFalse("Should have at least one flow", flowIds.isEmpty());
        
        List<String> linkIds = bridge.getAllLinkIds();
        assertNotNull("Should get link IDs", linkIds);
        assertFalse("Should have at least one link", linkIds.isEmpty());
        
        // Let simulation warm up
        Thread.sleep(2000);

        // Test metrics access
        boolean hasValidMetrics = false;
        for (int attempt = 0; attempt < 3; attempt++) {
            try {
                for (Integer flowId : flowIds) {
                    double latency = bridge.getFlowAvgLatency(flowId, 1.0);
                    if (latency >= 0.0) {
                        hasValidMetrics = true;
                        break;
                    }
                }
                if (hasValidMetrics) break;
                Thread.sleep(1000);
            } catch (Exception e) {
                // Ignore and retry
            }
        }
        assertTrue("Should get valid metrics after warmup", hasValidMetrics);
        
        for (String linkId : linkIds) {
            double util = bridge.getLinkAvgUtilization(Integer.parseInt(linkId), 1.0);
            assertTrue("Utilization should be between 0 and 1", util >= 0.0 && util <= 1.0);
        }
        
        // Let simulation run briefly
        Thread.sleep(1000);
        
        // Clean up
        example.stop();
        
        // Verify simulation stopped
        Thread.sleep(100); // Give time for cleanup
        assertEquals("Simulation should be stopped", false, CloudSim.running());
    }
}