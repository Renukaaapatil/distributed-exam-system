#!/usr/bin/env python3
"""
Cluster Management Tool for Distributed Exam System
Provides utilities to manage and monitor the distributed cluster
"""

import requests
import json
import time
from datetime import datetime
import argparse

class ClusterManagerCLI:
    """Command-line interface for cluster management"""
    
    def __init__(self):
        self.nodes = {
            'Node A': {'port': 5001, 'url': 'http://127.0.0.1:5001'},
            'Node B': {'port': 5002, 'url': 'http://127.0.0.1:5002'},
            'Node C': {'port': 5003, 'url': 'http://127.0.0.1:5003'}
        }
    
    def check_node_status(self, node_name):
        """Check status of a specific node"""
        node = self.nodes[node_name]
        try:
            response = requests.get(f"{node['url']}/node/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'HTTP {response.status_code}'}
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
    
    def check_all_nodes(self):
        """Check status of all nodes"""
        print("Cluster Status Report")
        print("=" * 60)
        
        all_online = True
        for node_name in self.nodes:
            status = self.check_node_status(node_name)
            
            if 'error' in status:
                print(f"{node_name}: OFFLINE - {status['error']}")
                all_online = False
            else:
                print(f"{node_name}: ONLINE")
                print(f"  Node ID: {status.get('node_id')}")
                print(f"  Port: {status.get('port')}")
                print(f"  Active Nodes: {status.get('active_nodes')}")
                print(f"  Total Exams: {status.get('total_exams')}")
                print(f"  Total Responses: {status.get('total_responses')}")
                print(f"  Last Updated: {status.get('timestamp')}")
                print()
        
        print("=" * 60)
        if all_online:
            print("Status: All nodes are online and healthy")
        else:
            print("Status: Some nodes are offline")
        
        return all_online
    
    def sync_nodes(self):
        """Trigger synchronization between nodes"""
        print("Triggering node synchronization...")
        
        for node_name in self.nodes:
            node = self.nodes[node_name]
            try:
                # Get data from this node
                response = requests.post(f"{node['url']}/node/sync/full", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    print(f"{node_name}: Sync successful")
                    print(f"  Exams: {len(data.get('exams', []))}")
                    print(f"  Questions: {len(data.get('questions', []))}")
                    print(f"  Responses: {len(data.get('responses', []))}")
                else:
                    print(f"{node_name}: Sync failed - HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"{node_name}: Sync failed - {e}")
            print()
    
    def broadcast_exam(self, exam_id, user_id):
        """Broadcast exam start to all nodes"""
        print(f"Broadcasting exam start (Exam ID: {exam_id}, User ID: {user_id})")
        
        broadcast_data = {
            'exam_id': exam_id,
            'user_id': user_id,
            'node_id': 'manager',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        successful_nodes = []
        for node_name in self.nodes:
            node = self.nodes[node_name]
            try:
                response = requests.post(f"{node['url']}/node/exam/start", 
                                       json=broadcast_data, timeout=5)
                if response.status_code == 200:
                    successful_nodes.append(node_name)
                    print(f"{node_name}: Broadcast successful")
                else:
                    print(f"{node_name}: Broadcast failed - HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"{node_name}: Broadcast failed - {e}")
        
        print(f"\nBroadcast completed. Successful nodes: {len(successful_nodes)}/{len(self.nodes)}")
        return successful_nodes
    
    def test_communication(self):
        """Test communication between all nodes"""
        print("Testing inter-node communication...")
        print("=" * 60)
        
        # Test each node's heartbeat endpoint
        heartbeat_data = {
            'node_id': 'test_manager',
            'port': 9999,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        results = {}
        for node_name in self.nodes:
            node = self.nodes[node_name]
            try:
                response = requests.post(f"{node['url']}/node/heartbeat", 
                                       json=heartbeat_data, timeout=5)
                if response.status_code == 200:
                    results[node_name] = 'OK'
                    print(f"{node_name}: Heartbeat OK")
                else:
                    results[node_name] = f'HTTP {response.status_code}'
                    print(f"{node_name}: Heartbeat failed - HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                results[node_name] = str(e)
                print(f"{node_name}: Heartbeat failed - {e}")
        
        print("=" * 60)
        
        # Test data synchronization
        print("Testing data synchronization...")
        for node_name in self.nodes:
            node = self.nodes[node_name]
            try:
                response = requests.get(f"{node['url']}/node/exams", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    exam_count = len(data.get('exams', []))
                    print(f"{node_name}: {exam_count} exams available")
                else:
                    print(f"{node_name}: Failed to get exams - HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"{node_name}: Failed to get exams - {e}")
        
        return results
    
    def monitor_cluster(self, duration=60):
        """Monitor cluster for specified duration"""
        print(f"Monitoring cluster for {duration} seconds...")
        print("Press Ctrl+C to stop monitoring early")
        print("=" * 60)
        
        start_time = time.time()
        try:
            while time.time() - start_time < duration:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{timestamp}] Cluster Check")
                
                online_count = 0
                for node_name in self.nodes:
                    status = self.check_node_status(node_name)
                    if 'error' not in status:
                        online_count += 1
                        active_nodes = status.get('active_nodes', 0)
                        print(f"  {node_name}: Online (Active peers: {active_nodes})")
                    else:
                        print(f"  {node_name}: Offline")
                
                print(f"  Cluster Health: {online_count}/{len(self.nodes)} nodes online")
                
                time.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        
        print("Monitoring completed")
    
    def test_rpc_communication(self):
        """Test RPC communication between nodes"""
        print("Testing RPC Communication")
        print("=" * 60)
        
        from core.rpc_client import RPCClient, RPCError
        
        # Test RPC calls to each node
        for node_name in self.nodes:
            node = self.nodes[node_name]
            print(f"\nTesting RPC with {node_name}:")
            
            try:
                client = RPCClient(node_name, node['url'], timeout=5, max_retries=2)
                
                # Test ping
                try:
                    response = client.call('node.ping')
                    if response.is_success:
                        print(f"  Ping: OK")
                    else:
                        print(f"  Ping: Failed - {response.error_message}")
                except RPCError as e:
                    print(f"  Ping: Error - {e}")
                
                # Test node status
                try:
                    response = client.call('node.status')
                    if response.is_success:
                        status = response.result
                        print(f"  Status: {status['total_users']} users, {status['total_exams']} exams")
                    else:
                        print(f"  Status: Failed - {response.error_message}")
                except RPCError as e:
                    print(f"  Status: Error - {e}")
                
                # Test exam data
                try:
                    response = client.call('exam.get_data')
                    if response.is_success:
                        exams = response.result.get('exams', [])
                        print(f"  Exams: {len(exams)} available")
                    else:
                        print(f"  Exams: Failed - {response.error_message}")
                except RPCError as e:
                    print(f"  Exams: Error - {e}")
                
                # Show statistics
                stats = client.get_stats()
                print(f"  Stats: {stats['total_requests']} requests, {stats['success_rate']:.2%} success")
                
            except Exception as e:
                print(f"  Connection failed: {e}")
    
    def ping_all_nodes_rpc(self):
        """Ping all nodes using RPC"""
        print("Pinging All Nodes via RPC")
        print("=" * 60)
        
        from core.rpc_client import RPCManager
        
        rpc_manager = RPCManager('cluster_manager')
        
        # Add all nodes
        for node_name, node in self.nodes.items():
            rpc_manager.add_client(node_name, node['url'], timeout=3, max_retries=1)
        
        # Broadcast ping
        try:
            results = rpc_manager.broadcast('node.ping')
            
            for node_name, response in results.items():
                if response.is_success:
                    result = response.result
                    print(f"{node_name}: Online ({result.get('node_id', 'Unknown')})")
                else:
                    print(f"{node_name}: Error - {response.error_message}")
                    
        except Exception as e:
            print(f"RPC ping failed: {e}")
    
    def show_rpc_statistics(self):
        """Show RPC statistics for all nodes"""
        print("RPC Statistics")
        print("=" * 60)
        
        from core.rpc_client import RPCManager
        
        rpc_manager = RPCManager('cluster_manager')
        
        # Add all nodes
        for node_name, node in self.nodes.items():
            rpc_manager.add_client(node_name, node['url'], timeout=3, max_retries=1)
        
        # Get statistics from each node
        for node_name in self.nodes:
            print(f"\n{node_name}:")
            
            try:
                client = rpc_manager.clients[node_name]
                stats = client.get_stats()
                
                print(f"  Total Requests: {stats['total_requests']}")
                print(f"  Successful: {stats['successful_requests']}")
                print(f"  Failed: {stats['failed_requests']}")
                print(f"  Success Rate: {stats['success_rate']:.2%}")
                print(f"  Avg Response Time: {stats['avg_response_time']:.3f}s")
                print(f"  Retry Count: {stats['retry_count']}")
                
            except Exception as e:
                print(f"  Error getting stats: {e}")
    
    def show_fault_tolerance_status(self):
        """Show fault tolerance status for all nodes"""
        print("Fault Tolerance Status")
        print("=" * 60)
        
        from core.rpc_client import RPCManager
        
        rpc_manager = RPCManager('cluster_manager')
        
        # Add all nodes
        for node_name, node in self.nodes.items():
            rpc_manager.add_client(node_name, node['url'], timeout=5, max_retries=2)
        
        for node_name in self.nodes:
            print(f"\n{node_name}:")
            
            try:
                response = rpc_manager.call(node_name, 'node.get_fault_tolerance_status')
                if response.is_success:
                    ft_status = response.result
                    
                    # Heartbeat status
                    heartbeat = ft_status.get('heartbeat_status', {})
                    print(f"  Heartbeat Monitoring: {heartbeat.get('monitoring_active', False)}")
                    print(f"  Monitored Nodes: {heartbeat.get('monitored_nodes', 0)}")
                    print(f"  Active Nodes: {heartbeat.get('active_nodes', 0)}")
                    
                    # Leader election
                    leader = ft_status.get('leader_election', {})
                    print(f"  Current Leader: {leader.get('current_leader', 'None')}")
                    print(f"  Node State: {leader.get('node_state', 'unknown')}")
                    print(f"  Election in Progress: {leader.get('election_in_progress', False)}")
                    
                    # Data replication
                    replication = ft_status.get('data_replication', {})
                    print(f"  Data Replication: {replication.get('enabled', False)}")
                    print(f"  Replication Active: {replication.get('active', False)}")
                    
                    # Failover
                    failover = ft_status.get('failover', {})
                    print(f"  Failover Active: {failover.get('active', False)}")
                    print(f"  Failed Nodes: {failover.get('failed_nodes', [])}")
                    
                    # Failure summary
                    failure_summary = ft_status.get('failure_summary', {})
                    print(f"  Total Failures: {failure_summary.get('total_failures', 0)}")
                    
                else:
                    print(f"  Error: {response.error_message}")
                    
            except Exception as e:
                print(f"  Error getting status: {e}")
    
    def test_fault_tolerance(self):
        """Test fault tolerance mechanisms"""
        print("Testing Fault Tolerance Mechanisms")
        print("=" * 60)
        
        try:
            # Run the fault tolerance test suite
            from fault_tolerance_test import FaultToleranceTester
            tester = FaultToleranceTester()
            
            print("Running comprehensive fault tolerance tests...")
            tester.run_all_tests()
            
        except ImportError:
            print("Fault tolerance test module not available")
            print("Please ensure fault_tolerance_test.py exists")
        except Exception as e:
            print(f"Error running fault tolerance tests: {e}")
    
    def show_leader_info(self):
        """Show leader election information"""
        print("Leader Election Information")
        print("=" * 60)
        
        from core.rpc_client import RPCManager
        
        rpc_manager = RPCManager('cluster_manager')
        
        # Add all nodes
        for node_name, node in self.nodes.items():
            rpc_manager.add_client(node_name, node['url'], timeout=5, max_retries=2)
        
        leader_info = {}
        
        for node_name in self.nodes:
            try:
                response = rpc_manager.call(node_name, 'node.get_leader_info')
                if response.is_success:
                    info = response.result
                    leader_info[node_name] = info
                    
                    print(f"\n{node_name}:")
                    print(f"  Current Leader: {info.get('current_leader', 'None')}")
                    print(f"  Node State: {info.get('node_state', 'unknown')}")
                    print(f"  Node Priority: {info.get('node_priority', 0)}")
                    print(f"  Election in Progress: {info.get('election_in_progress', False)}")
                    
                    if info.get('last_election_time'):
                        print(f"  Last Election: {info.get('last_election_time')}")
                else:
                    print(f"\n{node_name}: Error - {response.error_message}")
                    
            except Exception as e:
                print(f"\n{node_name}: Error - {e}")
        
        # Check consensus
        leaders = set()
        for node_name, info in leader_info.items():
            leader = info.get('current_leader')
            if leader:
                leaders.add(leader)
        
        print(f"\nLeader Consensus:")
        if len(leaders) == 1:
            leader = list(leaders)[0]
            print(f"  All nodes agree on leader: {leader}")
        elif len(leaders) == 0:
            print(f"  No leader elected")
        else:
            print(f"  Nodes disagree on leader: {leaders}")
    
    def test_failover_mechanism(self):
        """Test failover mechanism"""
        print("Testing Failover Mechanism")
        print("=" * 60)
        
        from core.rpc_client import RPCManager
        
        rpc_manager = RPCManager('cluster_manager')
        
        # Add all nodes
        for node_name, node in self.nodes.items():
            rpc_manager.add_client(node_name, node['url'], timeout=5, max_retries=2)
        
        print("1. Getting current cluster state...")
        
        current_leader = None
        cluster_state = {}
        
        for node_name in self.nodes:
            try:
                response = rpc_manager.call(node_name, 'node.get_fault_tolerance_status')
                if response.is_success:
                    ft_status = response.result
                    cluster_state[node_name] = ft_status
                    
                    leader = ft_status.get('leader_election', {}).get('current_leader')
                    if leader and not current_leader:
                        current_leader = leader
                    
                    print(f"  {node_name}: Leader = {leader}")
            except Exception as e:
                print(f"  {node_name}: Error - {e}")
        
        if current_leader:
            print(f"\nCurrent leader: {current_leader}")
            
            print("\n2. Simulating leader failure...")
            print("   In a real scenario, this would be a node crash")
            print("   For testing, we'll trigger a new election...")
            
            # Find highest priority node
            highest_priority_node = max(self.nodes.keys(), key=lambda x: int(x.split('_')[1]))
            
            if highest_priority_node != current_leader:
                print(f"   Triggering election on {highest_priority_node}...")
                
                try:
                    election_params = {
                        'type': 'election',
                        'candidate_id': highest_priority_node,
                        'priority': int(highest_priority_node.split('_')[1]),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    response = rpc_manager.call(highest_priority_node, 'node.handle_election', election_params)
                    if response.is_success:
                        print(f"   Election triggered successfully")
                    else:
                        print(f"   Election trigger failed: {response.error_message}")
                        
                except Exception as e:
                    print(f"   Failed to trigger election: {e}")
            else:
                print(f"   {current_leader} is already highest priority node")
            
            print("\n3. Waiting for election to complete...")
            time.sleep(10)
            
            print("\n4. Checking new leader...")
            
            new_leader = None
            for node_name in self.nodes:
                try:
                    response = rpc_manager.call(node_name, 'node.get_leader_info')
                    if response.is_success:
                        info = response.result
                        leader = info.get('current_leader')
                        if leader and not new_leader:
                            new_leader = leader
                        print(f"  {node_name}: Leader = {leader}")
                except Exception as e:
                    print(f"  {node_name}: Error - {e}")
            
            if new_leader and new_leader != current_leader:
                print(f"\nFailover successful: {current_leader} -> {new_leader}")
            elif new_leader == current_leader:
                print(f"\nLeader unchanged: {new_leader}")
            else:
                print(f"\nFailover incomplete or failed")
        else:
            print("No current leader found")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Distributed Exam System Cluster Manager')
    parser.add_argument('command', choices=[
        'status', 'sync', 'test', 'monitor', 'broadcast', 'rpc-test', 'ping', 'rpc-stats',
        'ft-status', 'ft-test', 'leader-info', 'failover-test'
    ], help='Command to execute')
    parser.add_argument('--exam-id', type=int, help='Exam ID for broadcast')
    parser.add_argument('--user-id', type=int, help='User ID for broadcast')
    parser.add_argument('--duration', type=int, default=60, 
                       help='Monitoring duration in seconds (default: 60)')
    
    args = parser.parse_args()
    
    manager = ClusterManagerCLI()
    
    if args.command == 'status':
        manager.check_all_nodes()
    elif args.command == 'sync':
        manager.sync_nodes()
    elif args.command == 'test':
        manager.test_communication()
    elif args.command == 'monitor':
        manager.monitor_cluster(args.duration)
    elif args.command == 'broadcast':
        if not args.exam_id or not args.user_id:
            print("Error: --exam-id and --user-id required for broadcast")
            return
        manager.broadcast_exam(args.exam_id, args.user_id)
    elif args.command == 'rpc-test':
        manager.test_rpc_communication()
    elif args.command == 'ping':
        manager.ping_all_nodes_rpc()
    elif args.command == 'rpc-stats':
        manager.show_rpc_statistics()
    elif args.command == 'ft-status':
        manager.show_fault_tolerance_status()
    elif args.command == 'ft-test':
        manager.test_fault_tolerance()
    elif args.command == 'leader-info':
        manager.show_leader_info()
    elif args.command == 'failover-test':
        manager.test_failover_mechanism()

if __name__ == '__main__':
    main()
