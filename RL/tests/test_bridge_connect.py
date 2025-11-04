import os
import time
import sys

try:
    from py4j.java_gateway import JavaGateway, GatewayParameters
except Exception as e:
    print("py4j is required to run this test. Install with: pip install py4j")
    raise

PORT = int(os.environ.get('PY4J_PORT', '25333'))

if __name__ == '__main__':
    print(f"Attempting to connect to Py4J gateway on port {PORT}...")
    try:
        gw = JavaGateway(gateway_parameters=GatewayParameters(port=PORT))
        bridge = gw.entry_point

        print('Connected. Querying bridge...')
        flow_ids = bridge.getFlowIds()
        link_ids = bridge.getAllLinkIds()
        now = bridge.getTime()

        print('flow_ids ->', flow_ids)
        print('link_ids ->', link_ids)
        print('sim time ->', now)

        assert flow_ids is not None
        assert link_ids is not None

        # If there are flows, call a per-flow API
        if len(flow_ids) > 0:
            fid = int(flow_ids[0])
            lat = bridge.getFlowAvgLatency(fid, 5.0)
            print(f'flow {fid} avg latency (5s):', lat)

        print('Bridge smoke test passed')
        gw.close()
    except Exception as e:
        print('Failed to connect or query the bridge:', e)
        print('Make sure the Java example is running and that PY4J_PORT is set correctly (default 25333).')
        sys.exit(2)
