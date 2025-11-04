package org.cloudbus.cloudsim.sdn.example;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;

import org.cloudbus.cloudsim.DatacenterCharacteristics;
import org.cloudbus.cloudsim.Host;
import org.cloudbus.cloudsim.Log;
import org.cloudbus.cloudsim.Storage;
import org.cloudbus.cloudsim.core.CloudSim;
import org.cloudbus.cloudsim.sdn.HostFactory;
import org.cloudbus.cloudsim.sdn.HostFactorySimple;
import org.cloudbus.cloudsim.sdn.nos.NetworkOperatingSystem;
import org.cloudbus.cloudsim.sdn.nos.NetworkOperatingSystemSimple;
import org.cloudbus.cloudsim.sdn.nos.RLNetworkBridge;
import org.cloudbus.cloudsim.sdn.parsers.PhysicalTopologyParser;
import org.cloudbus.cloudsim.sdn.physicalcomponents.SDNDatacenter;
import org.cloudbus.cloudsim.sdn.virtualcomponents.FlowConfig;
import org.cloudbus.cloudsim.sdn.virtualcomponents.SDNVm;
import org.cloudbus.cloudsim.sdn.example.SimpleExampleInterCloud.VmAllocationPolicyFactory;
import org.cloudbus.cloudsim.sdn.policies.selectlink.LinkSelectionPolicy;
import org.cloudbus.cloudsim.sdn.policies.selectlink.LinkSelectionPolicyBandwidthAllocation;
import org.cloudbus.cloudsim.sdn.policies.vmallocation.VmAllocationPolicyCombinedLeastFullFirst;

import py4j.GatewayServer;

/**
 * Lightweight example runner that builds a small datacenter from a physical
 * topology JSON (using existing helpers), starts the RL Py4J bridge and
 * creates a few test VMs/flows so the bridge can be exercised from Python.
 */
public class RLMonitoringExample {
    private static final String PHYSICAL = "rl-physical.json";
    private static final double BW = 100000; // 100Mbps
    private static final double LATENCY = 0.1;

    private NetworkOperatingSystem nos;
    private RLNetworkBridge bridge;
    private GatewayServer server;
    private SDNDatacenter datacenter;
    private boolean isRunning;

    public void start() throws Exception {
        setupSimulation();
        createDatacenter();
        createVmsAndFlows();
        startBridge();
        startSimulation();
    }

    public void stop() {
        if (server != null) {
            server.shutdown();
        }
        if (isRunning) {
            CloudSim.stopSimulation();
            isRunning = false;
        }
    }

    public RLNetworkBridge getBridge() {
        return bridge;
    }

    private void setupSimulation() {
        int numUser = 1;
        Calendar calendar = Calendar.getInstance();
        boolean traceFlag = false;
        CloudSim.init(numUser, calendar, traceFlag);

        // Create network operating system
        nos = new NetworkOperatingSystemSimple();
        
        // Set up host factory and link selection policy
        HostFactory hostFactory = new HostFactorySimple();
        LinkSelectionPolicy linkSelect = new LinkSelectionPolicyBandwidthAllocation();
        nos.setLinkSelectionPolicy(linkSelect);
    }

    private void createDatacenter() throws Exception {
        // Load physical topology
        PhysicalTopologyParser.loadPhysicalTopologySingleDC(PHYSICAL, nos, new HostFactorySimple());

        // Create VM allocation policy
        VmAllocationPolicyFactory vmFac = new VmAllocationPolicyFactory() {
            @Override
            public org.cloudbus.cloudsim.VmAllocationPolicy create(List<? extends Host> list) {
                return new VmAllocationPolicyCombinedLeastFullFirst(list);
            }
        };

        // Create datacenter characteristics
        String arch = "x86";
        String os = "Linux";
        String vmm = "Xen";
        double time_zone = 10.0;
        double cost = 3.0;
        double costPerMem = 0.05;
        double costPerStorage = 0.001;
        double costPerBw = 0.0;
        
        DatacenterCharacteristics characteristics = new DatacenterCharacteristics(
            arch, os, vmm, nos.getHostList(), time_zone, cost, costPerMem, 
            costPerStorage, costPerBw);

        List<Storage> storageList = new ArrayList<Storage>();
        
        datacenter = new SDNDatacenter(
            "DC1", characteristics, vmFac.create(nos.getHostList()),
            storageList, 0, nos);
    }

    private void createVmsAndFlows() {
        // Add VMs
        for (int i = 0; i < 4; i++) {
            SDNVm vm = new SDNVm(i, 0, 1000, 1, 512, 1000L, 10000L, "None", null);
            nos.addVm(vm);
        }

        // Add flows between VMs
        for (int i = 0; i < 3; i++) {
            FlowConfig f = new FlowConfig(i, i + 1, i + 1, (long) (BW / 2.0), LATENCY);
            nos.addFlow(f);
        }
    }

    private void startBridge() {
        bridge = new RLNetworkBridge(nos);
        server = new GatewayServer(bridge);
        server.start();
        System.out.println("Py4J gateway started on port: " + server.getListeningPort());
    }

    private void startSimulation() {
        // Run the simulation in a background thread so the Py4J gateway can
        // remain available for Python clients while the simulation runs.
        Thread simThread = new Thread(new Runnable() {
            @Override
            public void run() {
                Log.printLine("Starting simulation...");
                isRunning = true;
                CloudSim.startSimulation();
                isRunning = false;
                Log.printLine("Simulation finished (background thread).");
            }
        });
        simThread.setDaemon(false);
        simThread.start();
    }

    public static void main(String[] args) {
        int numUser = 1;
        Calendar calendar = Calendar.getInstance();
        boolean traceFlag = false;
        CloudSim.init(numUser, calendar, traceFlag);

        // Create network operating system for the datacenter
        NetworkOperatingSystem nos = new NetworkOperatingSystemSimple();
        
        // Set up host factory and link selection policy
        HostFactory hostFactory = new HostFactorySimple();
        LinkSelectionPolicy linkSelect = new LinkSelectionPolicyBandwidthAllocation();
        nos.setLinkSelectionPolicy(linkSelect);

        // Create VM allocation policy
        VmAllocationPolicyFactory vmFac = new VmAllocationPolicyFactory() {
            @Override
            public org.cloudbus.cloudsim.VmAllocationPolicy create(List<? extends Host> list) {
                return new VmAllocationPolicyCombinedLeastFullFirst(list);
            }
        };
        
        // Load physical topology using the simpler single DC approach
        PhysicalTopologyParser.loadPhysicalTopologySingleDC(PHYSICAL, nos, hostFactory);

        // Create SDN datacenter
        List<Storage> storageList = new ArrayList<Storage>();
        
        // Create datacenter characteristics
        String arch = "x86";
        String os = "Linux";
        String vmm = "Xen";
        double time_zone = 10.0;
        double cost = 3.0;
        double costPerMem = 0.05;
        double costPerStorage = 0.001;
        double costPerBw = 0.0;
        DatacenterCharacteristics characteristics = new DatacenterCharacteristics(
            arch, os, vmm, nos.getHostList(), time_zone, cost, costPerMem, costPerStorage, costPerBw);

        SDNDatacenter dc = null;
        try {
            RLMonitoringExample example = new RLMonitoringExample();
            example.start();

            // If user passed --wait, keep the gateway open until ENTER is pressed.
            boolean waitForInput = false;
            for (String a : args) {
                if ("--wait".equals(a) || "-w".equals(a)) {
                    waitForInput = true;
                    break;
                }
            }

            if (waitForInput) {
                System.out.println("Gateway and simulation running. Press ENTER to stop...");
                System.in.read();
            } else {
                // Default: give the simulation a short amount of time to run
                Thread.sleep(5000);
            }

            example.stop();
            Log.printLine("Example completed successfully");

        } catch (Exception e) {
            System.err.println("Failed to run example: " + e.getMessage());
            e.printStackTrace();
        }
    }
}