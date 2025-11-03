# CloudSimSDN AI Assistant Instructions

CloudSimSDN is a Software-Defined Networking (SDN) extension for CloudSim that simulates utilization of hosts and networks, and response times of requests in SDN-enabled cloud data centers. The project includes a reinforcement learning (RL)-based traffic engineering component for dynamic routing optimization.

## Project Goals

The primary objective is to implement intelligent traffic engineering using reinforcement learning to:
- Dynamically adjust routing parameters to optimize network utilization
- Minimize latency while maintaining network stability
- Selectively reroute critical flows that contribute most to congestion
- Achieve near-optimal load balancing with minimal traffic disruption

## Project Architecture

### Core Components

1. **Network Operating System (`org.cloudbus.cloudsim.sdn.nos`)**
   - Core component that simulates SDN Controller functionality
   - Manages channels between switches and packet routing
   - Key file: `NetworkOperatingSystem.java`

2. **Physical Components (`org.cloudbus.cloudsim.sdn.physicalcomponents`)**
   - Implements SDN-enabled infrastructure:
     - Nodes, Links, Physical Topology
     - Switches (Aggregation, Core, Edge, Gateway)
     - Extended DataCenter and Host classes

3. **Virtual Components (`org.cloudbus.cloudsim.sdn.virtualcomponents`)**
   - Manages virtual network mapping and flow configurations
   - Handles VM allocation and channel management

### Critical Files

- Configuration: `src/main/java/org/cloudbus/cloudsim/sdn/Configuration.java`
- Main examples: `src/main/java/org/cloudbus/cloudsim/sdn/example/SimpleExample.java`
- Topology definitions: JSON files in project root (e.g., `*-physical.json`, `*-virtual.json`)

## Development Workflows

### Building the Project

1. CloudSim Integration (Required):
   ```xml
   <dependency>
       <groupId>org.cloudbus.cloudsim</groupId>
       <artifactId>cloudsim</artifactId>
       <version>4.0</version>
   </dependency>
   ```

2. Build command:
   ```powershell
   mvn clean install
   ```

### Running Simulations

Basic simulation requires three files:
1. Physical topology (JSON)
2. Virtual topology (JSON)
3. Workload file(s) (CSV)

Example command structure:
```powershell
java <MainClass> <Policy> <physical.json> <virtual.json> [workload.csv...]
```

Common policies: LFF (Least Full First), MFF (Most Full First)

## Key Integration Points

1. **VM Allocation Policies**
   - Extend `VmAllocationPolicy` class
   - Implement in `org.cloudbus.cloudsim.sdn.policies.vmallocation`
   - Example: `VmAllocationPolicyCombinedLeastFullFirst`

2. **Link Selection Policies**
   - Implement `LinkSelectionPolicy` interface
   - Define in `org.cloudbus.cloudsim.sdn.policies.selectlink`
   - Example: `LinkSelectionPolicyDestinationAddress`

3. **Service Function Chaining (SFC)**
   - Configuration in `example-sfc` folder
   - Auto-scaling support via `ServiceFunctionAutoScaler`
   - Enable with `Configuration.SFC_AUTOSCALE_ENABLE`

## Project-Specific Patterns

1. **Resource Monitoring**
   - Regular monitoring intervals defined in `Configuration.java`
   - Utilization tracked through `Monitor` classes
   - Results output to CSV files (e.g., `host_utilization.csv`)

2. **Topology Format**
   - Physical topology: Network infrastructure definition
   - Virtual topology: Application deployment configuration
   - Workload: Traffic patterns and request specifications

3. **Logging & Output**
   - Use `Log.printLine()` for console output
   - Results stored in `<experimentName>log.out.txt`
   - CSV files generated for various metrics

## RL-Based Traffic Engineering

### Core Components

1. **Environment Integration (`RL/rl_env.py`)**
   - Interfaces with CloudSimSDN's `NetworkOperatingSystem` 
   - Monitors flow statistics via `Monitor` classes
   - Calculates congestion metrics per-link and per-flow
   - Implements reward function based on network state
   - Updates flow tables for selected critical flows

2. **Flow Management (`RL/flow_manager.py`)**
   - Identifies critical flows contributing to congestion
   - Maintains flow statistics and history
   - Implements flow table update mechanisms
   - Interfaces with CloudSimSDN's channel management
   - Example usage:
     ```java
     // In NetworkOperatingSystem
     @Override
     protected void processFlowTableUpdate(SimEvent ev) {
         if (RLFlowManager.shouldUpdateFlows()) {
             List<FlowConfig> criticalFlows = RLFlowManager.selectCriticalFlows();
             for (FlowConfig flow : criticalFlows) {
                 updateChannelPath(flow);
             }
         }
     }
     ```

3. **Critical Flow Selection (`RL/flow_selection.py`)**
   - Implements Zhang et al.'s critical flow identification
   - Uses network state to rank flows by congestion impact
   - Selects top K flows for rerouting while limiting disruption
   - Example selection logic:
     ```python
     def select_critical_flows(self, flow_stats, K=10):
         # Rank flows by their contribution to congestion
         congestion_scores = {}
         for flow in flow_stats:
             score = self.calculate_congestion_impact(flow)
             congestion_scores[flow.id] = score
             
         # Select top K flows while respecting rerouting limits
         return self.filter_top_flows(congestion_scores, K)
     ```

### Key Integration Points

1. **State Representation**
   ```java
   class NetworkState {
       Map<Link, Double> linkUtilization;  // Current link loads
       Map<Flow, Double> flowThroughput;   // Per-flow metrics
       Map<Link, Double> queueLengths;     // Switch queue status
       double maxLinkUtil;                 // For reward calculation
   }
   ```

2. **Action Space**
   ```java
   class FlowAction {
       String flowId;           // Flow to reroute
       List<Node> newPath;      // Updated routing path
       double expectedImprovement;  // Predicted congestion reduction
   }
   ```

3. **Runtime Integration**
   - Monitor intervals: Sync with CloudSimSDN's simulation ticks
   - Flow updates: Triggered by NetworkOperatingSystem events
   - State collection: Integrated with existing monitoring
   - Example configuration:
     ```java
     // In Configuration.java
     public static final double RL_MONITOR_INTERVAL = 1.0;  // 1 second
     public static final int RL_UPDATE_FREQUENCY = 5;       // Every 5 monitors
     public static final double MAX_REROUTE_RATIO = 0.15;   // Max 15% flows
     ```

## Common Operations

1. **Adding New VM Allocation Strategy**
```java
vmAllocationFac = new VmAllocationPolicyFactory() {
    public VmAllocationPolicy create(List<? extends Host> list) {
        return new YourCustomVmAllocationPolicy(list);
    }
};
```

2. **Defining Network Topology**
```json
{
    "nodes": [...],
    "links": [...]
}
```

3. **Running RL Training**
```powershell
python RL/run_training.py --episodes 1000 --monitoring-interval 5
```