#!/usr/bin/env python3
"""
Test Script for Offline Mode + Sync System
Tests offline detection, local storage, synchronization, and data integrity
"""

import requests
import json
import time
from datetime import datetime

class OfflineSyncSystemTester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.test_results = []
        self.session_cookies = None
    
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
    
    def login(self):
        """Login to get session cookies"""
        try:
            login_data = {
                'email': 'admin@example.com',  # Default admin user
                'password': 'admin123'
            }
            
            response = requests.post(f"{self.base_url}/login", data=login_data, allow_redirects=False)
            
            if response.status_code == 302:
                self.session_cookies = response.cookies
                print("Login successful")
                return True
            else:
                print("Login failed - trying without authentication")
                return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def test_sync_endpoint(self):
        """Test sync_exam endpoint functionality"""
        try:
            # Test sync with exam answers
            sync_data = {
                'type': 'exam_answers',
                'data': {
                    'examId': 1,
                    'answers': {
                        '1': 'A',
                        '2': 'B',
                        '3': 'C'
                    }
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(f"{self.base_url}/sync_exam", 
                                   json=sync_data, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    self.log_test("Sync Endpoint", True, 
                                "Exam answers synced successfully", result)
                    return True
                else:
                    self.log_test("Sync Endpoint", False, 
                                f"Sync error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Sync Endpoint", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Endpoint", False, f"Error: {e}")
            return False
    
    def test_sync_metadata(self):
        """Test syncing exam metadata"""
        try:
            sync_data = {
                'type': 'exam_metadata',
                'data': {
                    'examId': 1,
                    'metadata': {
                        'startTime': datetime.utcnow().isoformat(),
                        'browser': 'test_browser',
                        'screenResolution': '1920x1080'
                    }
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(f"{self.base_url}/sync_exam", 
                                   json=sync_data, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    self.log_test("Sync Metadata", True, 
                                "Exam metadata synced successfully")
                    return True
                else:
                    self.log_test("Sync Metadata", False, 
                                f"Metadata sync error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Sync Metadata", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Metadata", False, f"Error: {e}")
            return False
    
    def test_sync_progress(self):
        """Test syncing exam progress"""
        try:
            sync_data = {
                'type': 'exam_progress',
                'data': {
                    'examId': 1,
                    'progress': {
                        'currentQuestion': 5,
                        'totalQuestions': 10,
                        'timeSpent': 1200,
                        'answersCount': 3
                    }
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(f"{self.base_url}/sync_exam", 
                                   json=sync_data, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    self.log_test("Sync Progress", True, 
                                "Exam progress synced successfully")
                    return True
                else:
                    self.log_test("Sync Progress", False, 
                                f"Progress sync error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Sync Progress", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Progress", False, f"Error: {e}")
            return False
    
    def test_sync_status(self):
        """Test sync status endpoint"""
        try:
            response = requests.get(f"{self.base_url}/sync_status", 
                                  cookies=self.session_cookies, 
                                  timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    sync_info = data.get('sync_info', {})
                    required_fields = ['last_sync', 'recent_syncs', 'pending_count', 'sync_enabled']
                    missing_fields = [field for field in required_fields if field not in sync_info]
                    
                    if missing_fields:
                        self.log_test("Sync Status", False, 
                                    f"Missing status fields: {missing_fields}")
                        return False
                    
                    self.log_test("Sync Status", True, 
                                "Sync status retrieved successfully", sync_info)
                    return True
                else:
                    self.log_test("Sync Status", False, 
                                f"Status error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Sync Status", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Status", False, f"Error: {e}")
            return False
    
    def test_force_sync(self):
        """Test force sync endpoint"""
        try:
            response = requests.post(f"{self.base_url}/force_sync", 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    self.log_test("Force Sync", True, 
                                "Force sync initiated successfully")
                    return True
                else:
                    self.log_test("Force Sync", False, 
                                f"Force sync error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Force Sync", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Force Sync", False, f"Error: {e}")
            return False
    
    def test_sync_health(self):
        """Test sync health check endpoint"""
        try:
            response = requests.get(f"{self.base_url}/sync_health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and data.get('status') == 'healthy':
                    self.log_test("Sync Health", True, 
                                "Sync system is healthy", data)
                    return True
                else:
                    self.log_test("Sync Health", False, 
                                f"Sync system unhealthy: {data.get('status', 'Unknown')}")
                    return False
            else:
                self.log_test("Sync Health", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Health", False, f"Error: {e}")
            return False
    
    def test_invalid_sync_data(self):
        """Test sync endpoint with invalid data"""
        try:
            # Test missing required fields
            invalid_data = {
                'type': 'exam_answers'
                # Missing 'data' field
            }
            
            response = requests.post(f"{self.base_url}/sync_exam", 
                                   json=invalid_data, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 400:
                self.log_test("Invalid Sync Data", True, 
                            "Properly rejected invalid sync data")
                return True
            else:
                self.log_test("Invalid Sync Data", False, 
                            f"Should have rejected invalid data, got status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Invalid Sync Data", False, f"Error: {e}")
            return False
    
    def test_unknown_sync_type(self):
        """Test sync endpoint with unknown sync type"""
        try:
            sync_data = {
                'type': 'unknown_type',
                'data': {
                    'test': 'data'
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(f"{self.base_url}/sync_exam", 
                                   json=sync_data, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 400:
                self.log_test("Unknown Sync Type", True, 
                            "Properly rejected unknown sync type")
                return True
            else:
                self.log_test("Unknown Sync Type", False, 
                            f"Should have rejected unknown type, got status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Unknown Sync Type", False, f"Error: {e}")
            return False
    
    def test_clear_offline_data(self):
        """Test clearing offline data"""
        try:
            response = requests.post(f"{self.base_url}/clear_offline_data", 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    self.log_test("Clear Offline Data", True, 
                                "Offline data cleared successfully")
                    return True
                else:
                    self.log_test("Clear Offline Data", False, 
                                f"Clear error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Clear Offline Data", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Clear Offline Data", False, f"Error: {e}")
            return False
    
    def test_exam_page_load(self):
        """Test that exam page loads with offline sync components"""
        try:
            # Try to access an exam page
            response = requests.get(f"{self.base_url}/exam/1", 
                                  cookies=self.session_cookies, 
                                  timeout=5)
            
            if response.status_code == 200:
                # Check if offline sync components are present
                content = response.text
                
                required_components = [
                    'offline_sync.js',
                    'connectionStatus',
                    'OfflineSyncManager',
                    'localStorage'
                ]
                
                missing_components = []
                for component in required_components:
                    if component not in content:
                        missing_components.append(component)
                
                if missing_components:
                    self.log_test("Exam Page Load", False, 
                                f"Missing offline sync components: {missing_components}")
                    return False
                else:
                    self.log_test("Exam Page Load", True, 
                                "Exam page loaded with offline sync components")
                    return True
            else:
                self.log_test("Exam Page Load", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Exam Page Load", False, f"Error: {e}")
            return False
    
    def test_multiple_sync_operations(self):
        """Test multiple sync operations in sequence"""
        try:
            sync_operations = []
            
            # Perform multiple sync operations
            for i in range(3):
                sync_data = {
                    'type': 'exam_answers',
                    'data': {
                        'examId': 1,
                        'answers': {
                            str(i): chr(65 + i)  # 'A', 'B', 'C'
                        }
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                response = requests.post(f"{self.base_url}/sync_exam", 
                                       json=sync_data, 
                                       cookies=self.session_cookies, 
                                       timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    sync_operations.append({
                        'operation': i + 1,
                        'success': result.get('success', False),
                        'data': result
                    })
                
                # Small delay between operations
                time.sleep(0.1)
            
            successful_ops = len([op for op in sync_operations if op['success']])
            
            if successful_ops >= 2:
                self.log_test("Multiple Sync Operations", True, 
                            f"Successfully completed {successful_ops}/3 sync operations")
                return True
            else:
                self.log_test("Multiple Sync Operations", False, 
                            f"Only {successful_ops}/3 operations successful")
                return False
                
        except Exception as e:
            self.log_test("Multiple Sync Operations", False, f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all offline sync system tests"""
        print("=" * 60)
        print("OFFLINE MODE + SYNC SYSTEM TESTS")
        print("=" * 60)
        
        # Login first
        self.login()
        
        # Test core sync functionality
        self.test_sync_endpoint()
        self.test_sync_metadata()
        self.test_sync_progress()
        
        # Test status and health
        self.test_sync_status()
        self.test_sync_health()
        
        # Test edge cases
        self.test_invalid_sync_data()
        self.test_unknown_sync_type()
        
        # Test utilities
        self.test_force_sync()
        self.test_clear_offline_data()
        
        # Test multiple operations
        self.test_multiple_sync_operations()
        
        # Test UI integration
        self.test_exam_page_load()
        
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
        
        print("\nTest Results:")
        for result in self.test_results:
            status = "PASS" if result['success'] else "FAIL"
            print(f"  [{status}] {result['test']}")
        
        print("\n" + "=" * 60)
        print("Offline Sync System Test Complete!")
        print("=" * 60)

if __name__ == "__main__":
    tester = OfflineSyncSystemTester()
    tester.run_all_tests()
