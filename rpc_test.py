#!/usr/bin/env python3
"""
RPC Test Script for Distributed Exam System
Tests RPC communication between nodes
"""

import sys
import time
import json
from core.rpc_client import RPCClient, RPCManager, RPCError
from datetime import datetime

def test_single_node_rpc():
    """Test RPC communication with a single node"""
    print("Testing Single Node RPC Communication")
    print("=" * 50)
    
    # Test with Node A
    client = RPCClient('node_5001', 'http://127.0.0.1:5001', timeout=5, max_retries=2)
    
    try:
        # Test ping
        print("1. Testing ping...")
        response = client.call('node.ping')
        if response.is_success:
            print(f"   Ping successful: {response.result}")
        else:
            print(f"   Ping failed: {response.error_message}")
        
        # Test node status
        print("2. Testing node status...")
        response = client.call('node.status')
        if response.is_success:
            print(f"   Node status: {response.result}")
        else:
            print(f"   Node status failed: {response.error_message}")
        
        # Test exam data
        print("3. Testing exam data...")
        response = client.call('exam.get_data')
        if response.is_success:
            exams = response.result.get('exams', [])
            print(f"   Found {len(exams)} exams")
            for exam in exams[:3]:  # Show first 3
                print(f"   - {exam['title']} (ID: {exam['id']})")
        else:
            print(f"   Exam data failed: {response.error_message}")
        
        # Get statistics
        print("4. Getting RPC statistics...")
        stats = client.get_stats()
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Success rate: {stats['success_rate']:.2%}")
        print(f"   Avg response time: {stats['avg_response_time']:.3f}s")
        
    except RPCError as e:
        print(f"RPC Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def test_multi_node_rpc():
    """Test RPC communication with multiple nodes"""
    print("\nTesting Multi-Node RPC Communication")
    print("=" * 50)
    
    # Create RPC manager
    rpc_manager = RPCManager('test_client')
    
    # Add clients for all nodes
    nodes = {
        'node_5001': 'http://127.0.0.1:5001',
        'node_5002': 'http://127.0.0.1:5002',
        'node_5003': 'http://127.0.0.1:5003'
    }
    
    for node_id, url in nodes.items():
        rpc_manager.add_client(node_id, url, timeout=5, max_retries=2)
    
    try:
        # Test ping all nodes
        print("1. Pinging all nodes...")
        ping_results = rpc_manager.broadcast('node.ping')
        
        for node_id, response in ping_results.items():
            if response.is_success:
                print(f"   {node_id}: Online (Response: {response.result.get('pong')})")
            else:
                print(f"   {node_id}: Error - {response.error_message}")
        
        # Test node status all nodes
        print("2. Getting status from all nodes...")
        status_results = rpc_manager.broadcast('node.status')
        
        for node_id, response in status_results.items():
            if response.is_success:
                status = response.result
                print(f"   {node_id}: {status['total_users']} users, {status['total_exams']} exams")
            else:
                print(f"   {node_id}: Error - {response.error_message}")
        
        # Test exam data from first available node
        print("3. Getting exam data from available nodes...")
        for node_id in nodes:
            try:
                response = rpc_manager.call(node_id, 'exam.get_data')
                if response.is_success:
                    exams = response.result.get('exams', [])
                    print(f"   {node_id}: {len(exams)} exams available")
                    break
            except RPCError:
                continue
        
        # Get all statistics
        print("4. Getting RPC statistics for all nodes...")
        all_stats = rpc_manager.get_all_stats()
        for node_id, stats in all_stats.items():
            print(f"   {node_id}: {stats['total_requests']} requests, {stats['success_rate']:.2%} success")
        
    except Exception as e:
        print(f"Error: {e}")

def test_exam_workflow():
    """Test complete exam workflow using RPC"""
    print("\nTesting Exam Workflow via RPC")
    print("=" * 50)
    
    try:
        # Connect to Node A
        client = RPCClient('node_5001', 'http://127.0.0.1:5001', timeout=10, max_retries=3)
        
        # 1. Create a test user
        print("1. Creating test user...")
        user_params = {
            'name': 'RPC Test User',
            'email': 'rpc_test@example.com',
            'password': 'test123',
            'role': 'student'
        }
        
        response = client.call('user.create', user_params)
        if response.is_success:
            user_id = response.result['user_id']
            print(f"   User created: ID {user_id}")
        else:
            print(f"   User creation failed: {response.error_message}")
            return
        
        # 2. Get available exams
        print("2. Getting available exams...")
        response = client.call('exam.get_data')
        if response.is_success:
            exams = response.result.get('exams', [])
            if exams:
                exam_id = exams[0]['id']
                exam_title = exams[0]['title']
                print(f"   Found exam: {exam_title} (ID: {exam_id})")
            else:
                print("   No exams available")
                return
        else:
            print(f"   Failed to get exams: {response.error_message}")
            return
        
        # 3. Start exam session
        print("3. Starting exam session...")
        exam_params = {
            'user_id': user_id,
            'exam_id': exam_id
        }
        
        response = client.call('exam.start', exam_params)
        if response.is_success:
            session_info = response.result
            print(f"   Exam started: {session_info['exam_title']}")
            print(f"   Duration: {session_info['duration']} minutes")
            print(f"   Questions: {session_info['question_count']}")
        else:
            print(f"   Exam start failed: {response.error_message}")
            return
        
        # 4. Submit exam with sample answers
        print("4. Submitting exam...")
        submit_params = {
            'user_id': user_id,
            'exam_id': exam_id,
            'answers': {'1': 'A', '2': 'B', '3': 'C'}  # Sample answers
        }
        
        response = client.call('exam.submit', submit_params)
        if response.is_success:
            result = response.result
            print(f"   Exam submitted successfully!")
            print(f"   Score: {result['score']}/{result['total_questions']}")
            print(f"   Percentage: {result['percentage']}%")
            print(f"   Response ID: {result['response_id']}")
        else:
            print(f"   Exam submission failed: {response.error_message}")
        
        # 5. Test response sync
        print("5. Testing response sync...")
        sync_params = {
            'response_id': result['response_id'],
            'user_id': user_id,
            'exam_id': exam_id,
            'answers': {'1': 'A', '2': 'B', '3': 'C'},
            'score': result['score'],
            'submitted_at': datetime.utcnow().isoformat()
        }
        
        response = client.call('response.sync', sync_params)
        if response.is_success:
            print(f"   Response synced: {response.result['action']}")
        else:
            print(f"   Response sync failed: {response.error_message}")
        
    except RPCError as e:
        print(f"RPC Error during workflow: {e}")
    except Exception as e:
        print(f"Error during workflow: {e}")

def test_error_handling():
    """Test RPC error handling and retry mechanisms"""
    print("\nTesting Error Handling and Retry")
    print("=" * 50)
    
    # Test with invalid node (should fail and retry)
    print("1. Testing with invalid node...")
    client = RPCClient('invalid_node', 'http://127.0.0.1:9999', timeout=2, max_retries=2)
    
    try:
        response = client.call('node.ping')
        print("   Unexpected success!")
    except RPCError as e:
        print(f"   Expected failure: {e}")
    
    # Test with invalid method
    print("2. Testing invalid method...")
    client = RPCClient('node_5001', 'http://127.0.0.1:5001', timeout=5, max_retries=1)
    
    try:
        response = client.call('invalid.method')
        if not response.is_success:
            print(f"   Expected error: {response.error_message}")
        else:
            print("   Unexpected success!")
    except RPCError as e:
        print(f"   Expected failure: {e}")
    
    # Test with invalid parameters
    print("3. Testing invalid parameters...")
    try:
        response = client.call('user.create', {'name': 'Test'})  # Missing required fields
        if not response.is_success:
            print(f"   Expected error: {response.error_message}")
        else:
            print("   Unexpected success!")
    except RPCError as e:
        print(f"   Expected failure: {e}")

def main():
    """Main test function"""
    print("Distributed Exam System - RPC Test Suite")
    print("=" * 60)
    print("Testing RPC-style communication between nodes")
    print("Make sure the cluster is running before running these tests")
    print("Start with: python start_cluster.py")
    print("=" * 60)
    
    # Wait a moment for nodes to start
    print("Waiting for nodes to initialize...")
    time.sleep(3)
    
    try:
        # Run tests
        test_single_node_rpc()
        test_multi_node_rpc()
        test_exam_workflow()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("RPC Test Suite Completed!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error during tests: {e}")

if __name__ == '__main__':
    main()
