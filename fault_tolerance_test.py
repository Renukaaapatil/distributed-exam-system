#!/usr/bin/env python3
"""
Fault Tolerance Test Suite for Distributed Exam System
Tests heartbeat monitoring, leader election, and failover mechanisms
"""

import sys
import time
import json
import threading
from datetime import datetime
from core.rpc_client import RPCClient, RPCManager, RPCError

class FaultToleranceTester:
    """Test suite for fault tolerance features"""
    
    def __init__(self):
        self.rpc_manager = RPCManager('fault_tolerance_tester')
        self.nodes = {
            'node_5001': 'http://127.0.0.1:5001',
            'node_5002': 'http://127.0.0.1:5002',
            'node_5003': 'http://127.0.0.1:5003'
        }
        
        # Add RPC clients
        for node_id, url in self.nodes.items():
            self.rpc_manager.add_client(node_id, url, timeout=5, max_retries=2)
    
    def test_heartbeat_monitoring(self):
        """Test heartbeat monitoring between nodes"""
        print("\nTesting Heartbeat Monitoring")
        print("=" * 50)
        
        print("1. Checking initial heartbeat status...")
        
        for node_id in self.nodes:
            try:
                response = self.rpc_manager.call(node_id, 'node.get_fault_tolerance_status')
                if response.is_success:
                    ft_status = response.result
                    heartbeat_status = ft_status.get('heartbeat_status', {})
                    print(f"   {node_id}:")
                    print(f"     Monitoring: {heartbeat_status.get('monitoring_active', False)}")
                    print(f"     Monitored nodes: {heartbeat_status.get('monitored_nodes', 0)}")
                    print(f"     Active nodes: {heartbeat_status.get('active_nodes', 0)}")
                    
                    # Show node states
                    node_states = heartbeat_status.get('node_states', [])
                    for state in node_states:
                        if state.get('node_id') != node_id:  # Skip self
                            print(f"     {state.get('node_id')}: {state.get('state', 'unknown')}")
                else:
                    print(f"   {node_id}: Failed to get status - {response.error_message}")
            except RPCError as e:
                print(f"   {node_id}: Error - {e}")
        
        print("\n2. Testing heartbeat responsiveness...")
        
        # Test ping responses
        ping_results = self.rpc_manager.broadcast('node.ping')
        for node_id, response in ping_results.items():
            if response.is_success:
                print(f"   {node_id}: Responsive")
            else:
                print(f"   {node_id}: Unresponsive - {response.error_message}")
        
        print("\n3. Monitoring heartbeat patterns for 15 seconds...")
        
        # Monitor heartbeat patterns
        start_time = time.time()
        heartbeat_log = {}
        
        while time.time() - start_time < 15:
            current_time = datetime.now().strftime("%H:%M:%S")
            
            for node_id in self.nodes:
                try:
                    response = self.rpc_manager.call(node_id, 'node.get_fault_tolerance_status')
                    if response.is_success:
                        ft_status = response.result
                        heartbeat_status = ft_status.get('heartbeat_status', {})
                        active_count = heartbeat_status.get('active_nodes', 0)
                        
                        if node_id not in heartbeat_log:
                            heartbeat_log[node_id] = []
                        heartbeat_log[node_id].append((current_time, active_count))
                        
                except RPCError:
                    if node_id not in heartbeat_log:
                        heartbeat_log[node_id] = []
                    heartbeat_log[node_id].append((current_time, -1))
            
            time.sleep(2)
        
        # Show heartbeat patterns
        print("   Heartbeat patterns:")
        for node_id, logs in heartbeat_log.items():
            print(f"   {node_id}:")
            for timestamp, active_count in logs[-3:]:  # Show last 3 entries
                status = f"{active_count} active" if active_count >= 0 else "error"
                print(f"     {timestamp}: {status}")
    
    def test_leader_election(self):
        """Test Bully algorithm leader election"""
        print("\nTesting Leader Election (Bully Algorithm)")
        print("=" * 50)
        
        print("1. Checking current leader status...")
        
        current_leaders = {}
        for node_id in self.nodes:
            try:
                response = self.rpc_manager.call(node_id, 'node.get_leader_info')
                if response.is_success:
                    leader_info = response.result
                    current_leaders[node_id] = leader_info
                    print(f"   {node_id}:")
                    print(f"     Current leader: {leader_info.get('current_leader', 'None')}")
                    print(f"     Node state: {leader_info.get('node_state', 'unknown')}")
                    print(f"     Node priority: {leader_info.get('node_priority', 0)}")
                    print(f"     Election in progress: {leader_info.get('election_in_progress', False)}")
                else:
                    print(f"   {node_id}: Failed to get leader info - {response.error_message}")
            except RPCError as e:
                print(f"   {node_id}: Error - {e}")
        
        # Check if all nodes agree on leader
        leaders = set(info.get('current_leader') for info in current_leaders.values() if info.get('current_leader'))
        if len(leaders) == 1:
            leader = list(leaders)[0]
            print(f"\n   All nodes agree on leader: {leader}")
        else:
            print(f"\n   Nodes disagree on leader: {leaders}")
        
        print("\n2. Testing leader election trigger...")
        
        # Find current leader
        current_leader = None
        for node_id, info in current_leaders.items():
            if info.get('current_leader'):
                current_leader = info.get('current_leader')
                break
        
        if current_leader:
            print(f"   Current leader is {current_leader}")
            
            # Simulate leader failure by stopping heartbeat monitoring on leader
            print(f"   Simulating leader failure on {current_leader}...")
            
            try:
                # This would normally be done by stopping the node, but for testing
                # we'll trigger an election manually
                highest_priority_node = max(self.nodes.keys(), key=lambda x: int(x.split('_')[1]))
                
                if highest_priority_node != current_leader:
                    print(f"   Triggering election on {highest_priority_node}...")
                    
                    # Start election on highest priority node
                    election_params = {
                        'type': 'election',
                        'candidate_id': highest_priority_node,
                        'priority': int(highest_priority_node.split('_')[1]),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    response = self.rpc_manager.call(highest_priority_node, 'node.handle_election', election_params)
                    if response.is_success:
                        print(f"   Election triggered successfully")
                    else:
                        print(f"   Election trigger failed: {response.error_message}")
                else:
                    print(f"   {current_leader} is already highest priority node")
                
            except RPCError as e:
                print(f"   Failed to trigger election: {e}")
        else:
            print("   No current leader found")
        
        print("\n3. Waiting for election to complete...")
        time.sleep(10)
        
        print("\n4. Checking new leader status...")
        
        new_leaders = {}
        for node_id in self.nodes:
            try:
                response = self.rpc_manager.call(node_id, 'node.get_leader_info')
                if response.is_success:
                    leader_info = response.result
                    new_leaders[node_id] = leader_info
                    print(f"   {node_id}: Leader = {leader_info.get('current_leader', 'None')}")
            except RPCError as e:
                print(f"   {node_id}: Error - {e}")
        
        # Verify election results
        new_leader_set = set(info.get('current_leader') for info in new_leaders.values() if info.get('current_leader'))
        if len(new_leader_set) == 1:
            new_leader = list(new_leader_set)[0]
            if new_leader != current_leader:
                print(f"\n   Leader successfully changed: {current_leader} -> {new_leader}")
            else:
                print(f"\n   Leader unchanged: {new_leader}")
        else:
            print(f"\n   Leader election incomplete or failed: {new_leader_set}")
    
    def test_failover_mechanism(self):
        """Test automatic failover mechanism"""
        print("\nTesting Failover Mechanism")
        print("=" * 50)
        
        print("1. Getting initial cluster state...")
        
        cluster_state = {}
        for node_id in self.nodes:
            try:
                response = self.rpc_manager.call(node_id, 'node.get_fault_tolerance_status')
                if response.is_success:
                    ft_status = response.result
                    cluster_state[node_id] = ft_status
                    
                    leader_info = ft_status.get('leader_election', {})
                    heartbeat_info = ft_status.get('heartbeat_status', {})
                    
                    print(f"   {node_id}:")
                    print(f"     Leader: {leader_info.get('current_leader', 'None')}")
                    print(f"     State: {leader_info.get('node_state', 'unknown')}")
                    print(f"     Active peers: {heartbeat_info.get('active_nodes', 0)}")
                    print(f"     Failed nodes: {ft_status.get('failover', {}).get('failed_nodes', [])}")
                else:
                    print(f"   {node_id}: Failed to get status")
            except RPCError as e:
                print(f"   {node_id}: Error - {e}")
        
        print("\n2. Simulating node failure...")
        
        # Find a non-leader node to "fail"
        leader_nodes = set()
        for node_id, status in cluster_state.items():
            leader = status.get('leader_election', {}).get('current_leader')
            if leader:
                leader_nodes.add(leader)
        
        # Find a node that's not the leader
        node_to_fail = None
        for node_id in self.nodes:
            if node_id not in leader_nodes:
                node_to_fail = node_id
                break
        
        if node_to_fail:
            print(f"   Simulating failure of {node_to_fail}...")
            
            # In a real scenario, this would be a node crash
            # For testing, we'll just observe how other nodes detect the failure
            
            print("   Monitoring failure detection for 20 seconds...")
            
            failure_detection_log = {}
            start_time = time.time()
            
            while time.time() - start_time < 20:
                current_time = datetime.now().strftime("%H:%M:%S")
                
                for observer_id in self.nodes:
                    if observer_id != node_to_fail:
                        try:
                            response = self.rpc_manager.call(observer_id, 'node.get_fault_tolerance_status')
                            if response.is_success:
                                ft_status = response.result
                                heartbeat_info = ft_status.get('heartbeat_status', {})
                                node_states = heartbeat_info.get('node_states', [])
                                
                                # Find state of failed node
                                failed_node_state = "unknown"
                                for state in node_states:
                                    if state.get('node_id') == node_to_fail:
                                        failed_node_state = state.get('state', 'unknown')
                                        break
                                
                                if observer_id not in failure_detection_log:
                                    failure_detection_log[observer_id] = []
                                failure_detection_log[observer_id].append((current_time, failed_node_state))
                                
                        except RPCError:
                            if observer_id not in failure_detection_log:
                                failure_detection_log[observer_id] = []
                            failure_detection_log[observer_id].append((current_time, "error"))
                
                time.sleep(3)
            
            # Show failure detection results
            print("   Failure detection results:")
            for observer_id, logs in failure_detection_log.items():
                print(f"   {observer_id} observing {node_to_fail}:")
                for timestamp, state in logs:
                    print(f"     {timestamp}: {state}")
        else:
            print("   Could not find a non-leader node to fail")
        
        print("\n3. Testing data replication during failure...")
        
        # Test data replication
        try:
            # Get backup data from a healthy node
            healthy_node = None
            for node_id in self.nodes:
                if node_id != node_to_fail:
                    healthy_node = node_id
                    break
            
            if healthy_node:
                print(f"   Testing data replication from {healthy_node}...")
                
                backup_response = self.rpc_manager.call(healthy_node, 'data.backup')
                if backup_response.is_success:
                    backup_data = backup_response.result
                    print(f"   Backup successful: {backup_data.get('backup_size', 0)} bytes")
                    
                    # Test restore to another node
                    target_node = None
                    for node_id in self.nodes:
                        if node_id != healthy_node and node_id != node_to_fail:
                            target_node = node_id
                            break
                    
                    if target_node:
                        restore_response = self.rpc_manager.call(target_node, 'data.restore', {'backup_data': backup_data})
                        if restore_response.is_success:
                            result = restore_response.result
                            print(f"   Restore to {target_node} successful")
                            print(f"   Restored: {result.get('counts', {})}")
                        else:
                            print(f"   Restore failed: {restore_response.error_message}")
                else:
                    print(f"   Backup failed: {backup_response.error_message}")
        except RPCError as e:
            print(f"   Data replication test failed: {e}")
    
    def test_recovery_mechanism(self):
        """Test node recovery mechanism"""
        print("\nTesting Node Recovery Mechanism")
        print("=" * 50)
        
        print("1. Checking current failed nodes...")
        
        failed_nodes = set()
        for node_id in self.nodes:
            try:
                response = self.rpc_manager.call(node_id, 'node.get_fault_tolerance_status')
                if response.is_success:
                    ft_status = response.result
                    failed = ft_status.get('failover', {}).get('failed_nodes', [])
                    failed_nodes.update(failed)
                    
                    print(f"   {node_id}: Failed nodes = {failed}")
            except RPCError as e:
                print(f"   {node_id}: Error - {e}")
        
        print(f"\n   Total failed nodes detected: {failed_nodes}")
        
        print("\n2. Simulating node recovery...")
        
        # In a real scenario, a failed node would restart and rejoin the cluster
        # For testing, we'll check how nodes handle a recovered node
        
        if failed_nodes:
            recovered_node = list(failed_nodes)[0]
            print(f"   Simulating recovery of {recovered_node}...")
            
            # Test how other nodes handle the recovery
            print("   Monitoring recovery handling for 15 seconds...")
            
            recovery_log = {}
            start_time = time.time()
            
            while time.time() - start_time < 15:
                current_time = datetime.now().strftime("%H:%M:%S")
                
                for observer_id in self.nodes:
                    if observer_id != recovered_node:
                        try:
                            response = self.rpc_manager.call(observer_id, 'node.get_fault_tolerance_status')
                            if response.is_success:
                                ft_status = response.result
                                heartbeat_info = ft_status.get('heartbeat_status', {})
                                node_states = heartbeat_info.get('node_states', [])
                                
                                # Find state of recovered node
                                recovered_node_state = "unknown"
                                for state in node_states:
                                    if state.get('node_id') == recovered_node:
                                        recovered_node_state = state.get('state', 'unknown')
                                        break
                                
                                if observer_id not in recovery_log:
                                    recovery_log[observer_id] = []
                                recovery_log[observer_id].append((current_time, recovered_node_state))
                                
                        except RPCError:
                            if observer_id not in recovery_log:
                                recovery_log[observer_id] = []
                            recovery_log[observer_id].append((current_time, "error"))
                
                time.sleep(3)
            
            # Show recovery results
            print("   Recovery handling results:")
            for observer_id, logs in recovery_log.items():
                print(f"   {observer_id} observing {recovered_node}:")
                for timestamp, state in logs:
                    print(f"     {timestamp}: {state}")
        else:
            print("   No failed nodes to recover")
        
        print("\n3. Testing data synchronization after recovery...")
        
        # Test data sync to recovered node
        try:
            # Get data from a healthy node
            source_node = None
            for node_id in self.nodes:
                if node_id not in failed_nodes:
                    source_node = node_id
                    break
            
            if source_node and failed_nodes:
                recovered_node = list(failed_nodes)[0]
                
                print(f"   Testing data sync from {source_node} to {recovered_node}...")
                
                backup_response = self.rpc_manager.call(source_node, 'data.backup')
                if backup_response.is_success:
                    backup_data = backup_response.result
                    
                    restore_response = self.rpc_manager.call(recovered_node, 'data.restore', {'backup_data': backup_data})
                    if restore_response.is_success:
                        result = restore_response.result
                        print(f"   Data sync successful")
                        print(f"   Synced: {result.get('counts', {})}")
                    else:
                        print(f"   Data sync failed: {restore_response.error_message}")
                else:
                    print(f"   Backup failed: {backup_response.error_message}")
        except RPCError as e:
            print(f"   Data sync test failed: {e}")
    
    def test_failure_logging(self):
        """Test comprehensive failure logging"""
        print("\nTesting Failure Logging System")
        print("=" * 50)
        
        print("1. Checking failure logs from all nodes...")
        
        for node_id in self.nodes:
            try:
                response = self.rpc_manager.call(node_id, 'node.get_fault_tolerance_status')
                if response.is_success:
                    ft_status = response.result
                    failure_summary = ft_status.get('failure_summary', {})
                    
                    print(f"   {node_id}:")
                    print(f"     Total failures: {failure_summary.get('total_failures', 0)}")
                    
                    # Show failures by type
                    by_type = failure_summary.get('by_type', {})
                    if by_type:
                        print(f"     By type:")
                        for failure_type, count in by_type.items():
                            print(f"       {failure_type}: {count}")
                    
                    # Show failures by severity
                    by_severity = failure_summary.get('by_severity', {})
                    if by_severity:
                        print(f"     By severity:")
                        for severity, count in by_severity.items():
                            print(f"       {severity}: {count}")
                    
                    # Show failures by node
                    by_node = failure_summary.get('by_node', {})
                    if by_node:
                        print(f"     By node:")
                        for failed_node, count in by_node.items():
                            print(f"       {failed_node}: {count}")
                else:
                    print(f"   {node_id}: Failed to get failure logs")
            except RPCError as e:
                print(f"   {node_id}: Error - {e}")
        
        print("\n2. Testing failure event generation...")
        
        # Generate some test failures by simulating network issues
        print("   Generating test failure events...")
        
        for node_id in self.nodes:
            try:
                # Make a call with very short timeout to generate timeout failures
                client = RPCClient(node_id, self.nodes[node_id], timeout=0.001, max_retries=1)
                try:
                    response = client.call('node.ping')
                except RPCError:
                    pass  # Expected to fail
                
                print(f"   Generated test failures for {node_id}")
            except Exception as e:
                print(f"   Failed to generate test failures for {node_id}: {e}")
        
        print("\n3. Checking updated failure logs...")
        
        time.sleep(2)  # Wait for logs to be processed
        
        for node_id in self.nodes:
            try:
                response = self.rpc_manager.call(node_id, 'node.get_fault_tolerance_status')
                if response.is_success:
                    ft_status = response.result
                    failure_summary = ft_status.get('failure_summary', {})
                    
                    print(f"   {node_id}: {failure_summary.get('total_failures', 0)} total failures")
            except RPCError as e:
                print(f"   {node_id}: Error - {e}")
    
    def run_all_tests(self):
        """Run all fault tolerance tests"""
        print("Distributed Exam System - Fault Tolerance Test Suite")
        print("=" * 60)
        print("Testing fault tolerance mechanisms including:")
        print("- Heartbeat monitoring")
        print("- Leader election (Bully algorithm)")
        print("- Automatic failover")
        print("- Node recovery")
        print("- Failure logging")
        print("=" * 60)
        
        try:
            # Wait for nodes to initialize
            print("Waiting for nodes to initialize...")
            time.sleep(3)
            
            # Run tests
            self.test_heartbeat_monitoring()
            self.test_leader_election()
            self.test_failover_mechanism()
            self.test_recovery_mechanism()
            self.test_failure_logging()
            
            print("\n" + "=" * 60)
            print("Fault Tolerance Test Suite Completed!")
            print("=" * 60)
            
        except KeyboardInterrupt:
            print("\nTests interrupted by user")
        except Exception as e:
            print(f"\nUnexpected error during tests: {e}")

def main():
    """Main function"""
    tester = FaultToleranceTester()
    tester.run_all_tests()

if __name__ == '__main__':
    main()
