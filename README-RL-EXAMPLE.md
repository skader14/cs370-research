# CloudSimSDN RL Example

This document describes how to run and verify the Reinforcement Learning (RL) traffic engineering example for CloudSimSDN.

## Prerequisites

- Java 8 or higher
- Maven
- Python 3.7+
- Py4J package (`pip install py4j`)

## Project Structure

```
cloudsimsdn/
├── src/main/java/.../RLMonitoringExample.java  # Main simulation runner
├── rl-physical.json                            # Physical topology definition
├── rl-virtual.json                             # Virtual topology definition  
└── RL/
    ├── rl_env.py                              # RL environment implementation
    ├── flow_manager.py                        # Flow selection and routing
    └── run_training.py                        # Training script
```

## Running the Example

1. Build the project:
```powershell
mvn "clean" "package" "-DskipTests"
```

2. Run the Java simulation:
```powershell
mvn "org.codehaus.mojo:exec-maven-plugin:3.0.0:java" "-Dexec.mainClass=org.cloudbus.cloudsim.sdn.example.RLMonitoringExample" "-Dexec.classpathScope=runtime"
```

The simulation will:
- Load the topology from JSON files
- Start a Py4J gateway (default port: 25333)
- Create test flows and run the simulation
- Generate monitoring data in CSV files

## Output Files

After running, you'll find several CSV files:
- `host_utilization.csv`: CPU/memory usage per host
- `link_utilization_up.csv`/`link_utilization_down.csv`: Network link utilization
- `vm_utilization.csv`: VM resource usage
- `sw_energy.csv`: Switch energy consumption

## Running Python Tests

To verify the Py4J bridge is working:

```powershell
cd RL/tests
python test_bridge.py
```

The test will connect to the Java gateway and verify:
- Flow ID retrieval
- Link statistics access
- Basic flow management operations

## Expected Results

1. Java Simulation Output:
   - "Starting CloudSimSDN..."
   - "Creating SDN datacenter..."
   - "Starting Py4J gateway on port 25333"
   - Flow creation and routing information
   - "CloudSimSDN finished!"

2. CSV Files:
   - Check `link_utilization_*.csv` for network load data
   - Review `host_utilization.csv` for compute resource usage

3. Python Test Output:
   - "Connected to Java gateway"
   - "Found X active flows"
   - "All tests passed"

## Troubleshooting

1. Py4J Connection Issues:
   - Ensure Java simulation is running before Python tests
   - Check port 25333 is not blocked/in use
   - Verify Python environment has Py4J installed

2. Simulation Errors:
   - Review logs for topology parsing errors
   - Ensure JSON files are valid and complete
   - Check VM/host capacity specifications

## Next Steps

1. To implement custom RL algorithms:
   - Extend `rl_env.py` with your environment logic
   - Modify reward calculation in `RLEnvironment` class
   - Adjust state/action spaces as needed

2. To modify network topology:
   - Edit `rl-physical.json` for infrastructure changes
   - Update `rl-virtual.json` for VM placement/flows
   - Ensure matching node IDs between files