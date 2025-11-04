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
            dc = new SDNDatacenter(
                "DC1", 
                characteristics, 
                vmFac.create(nos.getHostList()),
                storageList, 
                0,
                nos);
        } catch (Exception e) {
            System.err.println("Failed to create datacenter: " + e.getMessage());
            return;
        }

        // Add a few simple VMs and flows so the bridge has something to report
        for (int i = 0; i < 4; i++) {
            SDNVm vm = new SDNVm(i, 0, 1000, 1, 512, 1000L, 10000L, "None", null);
            nos.addVm(vm);
        }

        for (int i = 0; i < 3; i++) {
            FlowConfig f = new FlowConfig(i, i + 1, i + 1, (long) (BW / 2.0), LATENCY);
            nos.addFlow(f);
        }

        RLNetworkBridge bridge = new RLNetworkBridge(nos);
        GatewayServer server = new GatewayServer(bridge);
        server.start();
        System.out.println("Py4J gateway started on port: " + server.getListeningPort());

        Log.printLine("Starting simulation...");
        double finish = CloudSim.startSimulation();
        CloudSim.stopSimulation();
        Log.printLine(finish + ": simulation finished");

        Log.printLine("Flows reported by NOS: " + nos.getFlowIds().size());

        server.shutdown();
    }
}