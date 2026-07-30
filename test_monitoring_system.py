#!/usr/bin/env python3
"""
Test Script for Live Exam Monitoring Dashboard
Tests admin monitoring functionality, API endpoints, and real-time updates
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta

class MonitoringSystemTester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.admin_url = f"{self.base_url}/admin"
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
    
    def test_admin_dashboard_access(self):
        """Test admin dashboard access"""
        try:
            response = requests.get(f"{self.admin_url}/dashboard", timeout=5)
            
            if response.status_code == 200:
                self.log_test("Admin Dashboard Access", True, "Dashboard accessible")
                return True
            elif response.status_code == 302:
                self.log_test("Admin Dashboard Access", False, "Redirected (likely not logged in)")
                return False
            else:
                self.log_test("Admin Dashboard Access", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Admin Dashboard Access", False, f"Error: {e}")
            return False
    
    def test_live_sessions_api(self):
        """Test live sessions API endpoint"""
        try:
            response = requests.get(f"{self.admin_url}/live_sessions", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    sessions = data.get('sessions', [])
                    self.log_test("Live Sessions API", True, 
                                f"Retrieved {len(sessions)} active sessions", data)
                    return True
                else:
                    self.log_test("Live Sessions API", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Live Sessions API", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Live Sessions API", False, f"Error: {e}")
            return False
    
    def test_violations_api(self):
        """Test violations API endpoint"""
        try:
            response = requests.get(f"{self.admin_url}/violations", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    violations = data.get('violations', [])
                    self.log_test("Violations API", True, 
                                f"Retrieved {len(violations)} recent violations", data)
                    return True
                else:
                    self.log_test("Violations API", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Violations API", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Violations API", False, f"Error: {e}")
            return False
    
    def test_snapshots_api(self):
        """Test snapshots API endpoint"""
        try:
            # Test without session ID (should return all snapshots)
            response = requests.get(f"{self.admin_url}/snapshots/test_session_id", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    snapshots = data.get('snapshots', [])
                    self.log_test("Snapshots API", True, 
                                f"Retrieved {len(snapshots)} snapshots", data)
                    return True
                else:
                    self.log_test("Snapshots API", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Snapshots API", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Snapshots API", False, f"Error: {e}")
            return False
    
    def test_statistics_api(self):
        """Test statistics API endpoint"""
        try:
            response = requests.get(f"{self.admin_url}/statistics", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    stats = data.get('statistics', {})
                    self.log_test("Statistics API", True, 
                                f"Retrieved statistics", stats)
                    return True
                else:
                    self.log_test("Statistics API", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Statistics API", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Statistics API", False, f"Error: {e}")
            return False
    
    def test_snapshot_upload(self):
        """Test snapshot upload functionality"""
        try:
            # Create a test image file (1x1 pixel PNG)
            test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
            
            files = {'image': ('test_snapshot.png', test_image_data, 'image/png')}
            data = {
                'session_id': 'test_session_id',
                'violation_detected': 'false'
            }
            
            response = requests.post(f"{self.admin_url}/upload_snapshot", 
                                   files=files, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    self.log_test("Snapshot Upload", True, 
                                "Test snapshot uploaded successfully", result)
                    return True
                else:
                    self.log_test("Snapshot Upload", False, 
                                f"Upload error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Snapshot Upload", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Snapshot Upload", False, f"Error: {e}")
            return False
    
    def test_real_time_updates(self):
        """Test real-time update simulation"""
        try:
            print("\nTesting real-time updates (3 iterations)...")
            
            for i in range(3):
                print(f"  Update {i+1}/3...")
                
                # Fetch live data
                sessions_response = requests.get(f"{self.admin_url}/live_sessions", timeout=5)
                violations_response = requests.get(f"{self.admin_url}/violations", timeout=5)
                
                if sessions_response.status_code == 200 and violations_response.status_code == 200:
                    sessions_data = sessions_response.json()
                    violations_data = violations_response.json()
                    
                    print(f"    Sessions: {len(sessions_data.get('sessions', []))}")
                    print(f"    Violations: {len(violations_data.get('violations', []))}")
                else:
                    self.log_test("Real-time Updates", False, f"Failed on iteration {i+1}")
                    return False
                
                # Wait between updates (simulating real-time behavior)
                time.sleep(2)
            
            self.log_test("Real-time Updates", True, "Successfully simulated real-time updates")
            return True
            
        except Exception as e:
            self.log_test("Real-time Updates", False, f"Error: {e}")
            return False
    
    def test_dashboard_components(self):
        """Test dashboard UI components"""
        try:
            response = requests.get(f"{self.admin_url}/dashboard", timeout=5)
            
            if response.status_code != 200:
                self.log_test("Dashboard Components", False, "Dashboard not accessible")
                return False
            
            html_content = response.text
            
            # Check for key components
            components = {
                'Statistics Cards': 'stat-card',
                'Sessions Table': 'sessionsTableBody',
                'Violations Feed': 'violationsFeed',
                'Snapshots Grid': 'snapshotsGrid',
                'Refresh Indicator': 'refreshIndicator'
            }
            
            missing_components = []
            
            for component_name, component_id in components.items():
                if component_id not in html_content:
                    missing_components.append(component_name)
            
            if missing_components:
                self.log_test("Dashboard Components", False, 
                            f"Missing components: {', '.join(missing_components)}")
                return False
            else:
                self.log_test("Dashboard Components", True, "All dashboard components found")
                return True
                
        except Exception as e:
            self.log_test("Dashboard Components", False, f"Error: {e}")
            return False
    
    def test_api_response_format(self):
        """Test API response format consistency"""
        try:
            endpoints = [
                '/admin/live_sessions',
                '/admin/violations',
                '/admin/statistics'
            ]
            
            format_issues = []
            
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check for required fields
                        if endpoint == '/admin/live_sessions':
                            required_fields = ['success', 'sessions', 'total_active', 'timestamp']
                        elif endpoint == '/admin/violations':
                            required_fields = ['success', 'violations', 'total_violations', 'timestamp']
                        elif endpoint == '/admin/statistics':
                            required_fields = ['success', 'statistics']
                        
                        missing_fields = [field for field in required_fields if field not in data]
                        
                        if missing_fields:
                            format_issues.append(f"{endpoint}: Missing {missing_fields}")
                        
                    else:
                        format_issues.append(f"{endpoint}: Status {response.status_code}")
                        
                except Exception as e:
                    format_issues.append(f"{endpoint}: {str(e)}")
            
            if format_issues:
                self.log_test("API Response Format", False, 
                            f"Format issues: {'; '.join(format_issues)}")
                return False
            else:
                self.log_test("API Response Format", True, "All API responses properly formatted")
                return True
                
        except Exception as e:
            self.log_test("API Response Format", False, f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all monitoring system tests"""
        print("=" * 60)
        print("LIVE EXAM MONITORING DASHBOARD TESTS")
        print("=" * 60)
        
        # Test API endpoints
        self.test_live_sessions_api()
        self.test_violations_api()
        self.test_snapshots_api()
        self.test_statistics_api()
        
        # Test functionality
        self.test_snapshot_upload()
        self.test_real_time_updates()
        
        # Test UI components
        self.test_admin_dashboard_access()
        self.test_dashboard_components()
        
        # Test data consistency
        self.test_api_response_format()
        
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
        print("Monitoring System Test Complete!")
        print("=" * 60)

if __name__ == "__main__":
    tester = MonitoringSystemTester()
    tester.run_all_tests()
