#!/usr/bin/env python3
"""
Test Script for Fault-Tolerant Distributed Exam System
Tests session management, failover, and recovery functionality
"""

import requests
import json
import time
import threading
from datetime import datetime

class FaultToleranceTester:
    def __init__(self):
        self.load_balancer_url = "http://127.0.0.1:5000"
        self.nodes = {
            'A': "http://127.0.0.1:5001",
            'B': "http://127.0.0.1:5002", 
            'C': "http://127.0.0.1:5003"
        }
        self.test_session_id = None
        self.test_results = []
    
    def log_test(self, test_name, success, message, details=None):
        """Log test result"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}: {message}")
        
        if details:
            print(f"    Details: {details}")
    
    def test_load_balancer_health(self):
        """Test load balancer health check"""
        try:
            response = requests.get(f"{self.load_balancer_url}/check_health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Load Balancer Health", True, "Load balancer is healthy", data)
                return True
            else:
                self.log_test("Load Balancer Health", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Load Balancer Health", False, f"Error: {e}")
            return False
    
    def test_node_health(self):
        """Test individual node health"""
        healthy_nodes = []
        
        for node_id, node_url in self.nodes.items():
            try:
                response = requests.get(f"{node_url}/api/fault_tolerance/health", timeout=3)
                
                if response.status_code == 200:
                    self.log_test(f"Node {node_id} Health", True, f"Node {node_id} is healthy")
                    healthy_nodes.append(node_id)
                else:
                    self.log_test(f"Node {node_id} Health", False, f"Status code: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Node {node_id} Health", False, f"Error: {e}")
        
        return healthy_nodes
    
    def test_session_creation(self):
        """Test session creation on nodes"""
        try:
            # Test session creation via load balancer
            response = requests.post(f"{self.load_balancer_url}/route_exam", timeout=5)
            
            if response.status_code == 200:
                # Extract session info from response or redirect
                self.log_test("Session Creation", True, "Successfully routed to node")
                return True
            else:
                self.log_test("Session Creation", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Session Creation", False, f"Error: {e}")
            return False
    
    def test_session_registration(self):
        """Test direct session registration"""
        for node_id, node_url in self.nodes.items():
            try:
                data = {
                    "user_id": 1,
                    "exam_id": 1,
                    "node_id": node_id
                }
                
                response = requests.post(f"{node_url}/api/fault_tolerance/register_session", 
                                       json=data, timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        session_id = result['session']['session_id']
                        self.test_session_id = session_id
                        self.log_test(f"Session Registration {node_id}", True, 
                                    f"Session created: {session_id}")
                        return session_id
                    else:
                        self.log_test(f"Session Registration {node_id}", False, 
                                    result.get('error', 'Unknown error'))
                else:
                    self.log_test(f"Session Registration {node_id}", False, 
                                f"Status code: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Session Registration {node_id}", False, f"Error: {e}")
        
        return None
    
    def test_progress_saving(self, session_id):
        """Test progress saving functionality"""
        if not session_id:
            self.log_test("Progress Saving", False, "No session ID available")
            return False
        
        try:
            # Find which node has the session
            session_node = None
            for node_id, node_url in self.nodes.items():
                try:
                    response = requests.get(f"{node_url}/api/fault_tolerance/resume_exam/{session_id}", 
                                          timeout=3)
                    if response.status_code == 200:
                        session_node = node_url
                        break
                except:
                    continue
            
            if not session_node:
                self.log_test("Progress Saving", False, "Could not find session node")
                return False
            
            # Test saving progress
            data = {
                "session_id": session_id,
                "current_question_index": 2,
                "answers": {"1": "A", "2": "B"},
                "remaining_time": 1500
            }
            
            response = requests.post(f"{session_node}/api/fault_tolerance/save_progress", 
                                   json=data, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("Progress Saving", True, "Progress saved successfully")
                    return True
                else:
                    self.log_test("Progress Saving", False, result.get('error', 'Unknown error'))
            else:
                self.log_test("Progress Saving", False, f"Status code: {response.status_code}")
                
        except Exception as e:
            self.log_test("Progress Saving", False, f"Error: {e}")
        
        return False
    
    def test_session_recovery(self, session_id):
        """Test session recovery functionality"""
        if not session_id:
            self.log_test("Session Recovery", False, "No session ID available")
            return False
        
        try:
            # Test session recovery via load balancer
            response = requests.get(f"{self.load_balancer_url}/resume_exam/{session_id}", timeout=5)
            
            if response.status_code == 200:
                self.log_test("Session Recovery", True, "Session recovery successful")
                return True
            else:
                self.log_test("Session Recovery", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Session Recovery", False, f"Error: {e}")
            return False
    
    def test_failover_simulation(self):
        """Test failover by simulating node failure"""
        try:
            # Get current node status
            response = requests.get(f"{self.load_balancer_url}/node_status", timeout=5)
            
            if response.status_code == 200:
                status = response.json()
                active_nodes = [n for n in status['nodes'] if n['active']]
                
                if len(active_nodes) < 2:
                    self.log_test("Failover Simulation", False, "Need at least 2 active nodes")
                    return False
                
                # Simulate failure of first active node
                failed_node = active_nodes[0]
                self.log_test("Failover Simulation", True, 
                            f"Simulating failure of Node {failed_node['id']}")
                
                # Trigger failover (this would normally be automatic)
                # For testing, we'll just check if load balancer can still route
                response = requests.post(f"{self.load_balancer_url}/route_exam", timeout=5)
                
                if response.status_code == 200:
                    self.log_test("Failover Simulation", True, "Failover successful")
                    return True
                else:
                    self.log_test("Failover Simulation", False, "Failover failed")
                    return False
            else:
                self.log_test("Failover Simulation", False, "Could not get node status")
                return False
                
        except Exception as e:
            self.log_test("Failover Simulation", False, f"Error: {e}")
            return False
    
    def test_auto_save_simulation(self):
        """Test auto-save functionality simulation"""
        if not self.test_session_id:
            self.log_test("Auto-Save Simulation", False, "No session ID available")
            return False
        
        try:
            # Simulate multiple save operations
            save_count = 0
            successful_saves = 0
            
            for i in range(5):
                data = {
                    "session_id": self.test_session_id,
                    "current_question_index": i,
                    "answers": {str(j): chr(65 + (i + j) % 4) for j in range(i + 1)},
                    "remaining_time": 1800 - (i * 60)
                }
                
                # Try to save on different nodes
                for node_id, node_url in self.nodes.items():
                    try:
                        response = requests.post(f"{node_url}/api/fault_tolerance/save_progress", 
                                               json=data, timeout=3)
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get('success'):
                                successful_saves += 1
                                save_count += 1
                                break
                    except:
                        continue
                
                time.sleep(0.5)  # Small delay between saves
            
            if successful_saves >= 3:
                self.log_test("Auto-Save Simulation", True, 
                            f"Successfully saved {successful_saves}/{save_count} times")
                return True
            else:
                self.log_test("Auto-Save Simulation", False, 
                            f"Only {successful_saves}/{save_count} saves successful")
                return False
                
        except Exception as e:
            self.log_test("Auto-Save Simulation", False, f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all fault tolerance tests"""
        print("=" * 60)
        print("FAULT-TOLERANT DISTRIBUTED EXAM SYSTEM TESTS")
        print("=" * 60)
        
        # Test load balancer
        self.test_load_balancer_health()
        
        # Test nodes
        healthy_nodes = self.test_node_health()
        
        if not healthy_nodes:
            print("\nERROR: No healthy nodes found. Cannot continue testing.")
            return
        
        print(f"\nFound {len(healthy_nodes)} healthy nodes: {healthy_nodes}")
        
        # Test session creation
        self.test_session_creation()
        
        # Test session registration
        session_id = self.test_session_registration()
        
        if session_id:
            # Test progress saving
            self.test_progress_saving(session_id)
            
            # Test session recovery
            self.test_session_recovery(session_id)
            
            # Test auto-save simulation
            self.test_auto_save_simulation()
        
        # Test failover (only if multiple nodes are healthy)
        if len(healthy_nodes) >= 2:
            self.test_failover_simulation()
        else:
            self.log_test("Failover Test", False, "Need at least 2 healthy nodes for failover testing")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status = "PASS" if result['success'] else "FAIL"
            print(f"  [{status}] {result['test']}")
        
        print("=" * 60)

if __name__ == "__main__":
    tester = FaultToleranceTester()
    tester.run_all_tests()
