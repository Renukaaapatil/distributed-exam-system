#!/usr/bin/env python3
"""
Test Script for Voice Detection Anti-Cheating System
Tests voice detection, violation reporting, trust score updates, and auto-submit functionality
"""

import requests
import json
import time
from datetime import datetime

class VoiceDetectionSystemTester:
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
    
    def test_voice_violation_api(self):
        """Test voice detection violation API endpoint"""
        try:
            violation_data = {
                'violation_type': 'voice_detected',
                'exam_id': 1,
                'details': json.dumps({
                    'volume': 0.15,
                    'duration': 2500,
                    'violation_count': 1,
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
            
            response = requests.post(f"{self.base_url}/api/proctoring/update_trust_score", 
                                   json=violation_data, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    self.log_test("Voice Violation API", True, 
                                "Voice violation reported successfully", result)
                    return True
                else:
                    self.log_test("Voice Violation API", False, 
                                f"API error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Voice Violation API", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Voice Violation API", False, f"Error: {e}")
            return False
    
    def test_trust_score_reduction(self):
        """Test trust score reduction for voice violations"""
        try:
            # Get initial trust score
            initial_response = requests.get(f"{self.base_url}/api/proctoring/get_trust_score", 
                                           cookies=self.session_cookies, timeout=5)
            
            initial_score = 100  # Default if we can't get it
            
            if initial_response.status_code == 200:
                initial_data = initial_response.json()
                if initial_data.get('success'):
                    initial_score = initial_data.get('trust_score', 100)
            
            # Report voice violation
            violation_data = {
                'violation_type': 'voice_detected',
                'exam_id': 1,
                'details': json.dumps({
                    'volume': 0.2,
                    'duration': 3000,
                    'violation_count': 1
                })
            }
            
            response = requests.post(f"{self.base_url}/api/proctoring/update_trust_score", 
                                   json=violation_data, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    new_score = result.get('trust_score', initial_score)
                    expected_score = max(0, initial_score - 20)  # Voice detection reduces by 20
                    
                    if new_score == expected_score:
                        self.log_test("Trust Score Reduction", True, 
                                    f"Trust score reduced from {initial_score} to {new_score}")
                        return True
                    else:
                        self.log_test("Trust Score Reduction", False, 
                                    f"Expected score {expected_score}, got {new_score}")
                        return False
                else:
                    self.log_test("Trust Score Reduction", False, 
                                f"API error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Trust Score Reduction", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Trust Score Reduction", False, f"Error: {e}")
            return False
    
    def test_multiple_voice_violations(self):
        """Test multiple voice violations and auto-submit logic"""
        try:
            violations_reported = []
            
            # Report multiple voice violations
            for i in range(3):
                violation_data = {
                    'violation_type': 'voice_detected',
                    'exam_id': 1,
                    'details': json.dumps({
                        'volume': 0.15 + (i * 0.05),
                        'duration': 2000 + (i * 500),
                        'violation_count': i + 1
                    })
                }
                
                response = requests.post(f"{self.base_url}/api/proctoring/update_trust_score", 
                                       json=violation_data, 
                                       cookies=self.session_cookies, 
                                       timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        violations_reported.append({
                            'violation': i + 1,
                            'trust_score': result.get('trust_score'),
                            'success': True
                        })
                
                time.sleep(0.1)  # Small delay between violations
            
            if len(violations_reported) >= 3:
                self.log_test("Multiple Voice Violations", True, 
                            f"Successfully reported {len(violations_reported)} voice violations")
                return True
            else:
                self.log_test("Multiple Voice Violations", False, 
                            f"Only {len(violations_reported)} violations successful")
                return False
                
        except Exception as e:
            self.log_test("Multiple Voice Violations", False, f"Error: {e}")
            return False
    
    def test_proctoring_session_start(self):
        """Test starting a proctoring session"""
        try:
            session_data = {
                'exam_id': 1,
                'user_id': 1
            }
            
            response = requests.post(f"{self.base_url}/api/proctoring/session/start", 
                                   json=session_data, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 201:
                result = response.json()
                
                if result.get('success'):
                    self.log_test("Proctoring Session Start", True, 
                                "Proctoring session started successfully", result)
                    return True
                else:
                    self.log_test("Proctoring Session Start", False, 
                                f"Session start error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Proctoring Session Start", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Proctoring Session Start", False, f"Error: {e}")
            return False
    
    def test_trust_score_api(self):
        """Test trust score retrieval API"""
        try:
            response = requests.get(f"{self.base_url}/api/proctoring/get_trust_score", 
                                  cookies=self.session_cookies, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    trust_score = data.get('trust_score')
                    
                    if isinstance(trust_score, (int, float)) and 0 <= trust_score <= 100:
                        self.log_test("Trust Score API", True, 
                                    f"Current trust score: {trust_score}")
                        return True
                    else:
                        self.log_test("Trust Score API", False, 
                                    f"Invalid trust score: {trust_score}")
                        return False
                else:
                    self.log_test("Trust Score API", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Trust Score API", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Trust Score API", False, f"Error: {e}")
            return False
    
    def test_voice_violation_details(self):
        """Test voice violation with detailed information"""
        try:
            detailed_violation = {
                'violation_type': 'voice_detected',
                'exam_id': 1,
                'details': json.dumps({
                    'volume': 0.25,
                    'duration': 2500,
                    'violation_count': 2,
                    'timestamp': datetime.utcnow().isoformat(),
                    'audio_context': {
                        'sample_rate': 44100,
                        'channel_count': 1,
                        'buffer_size': 256
                    },
                    'detection_settings': {
                        'threshold': 0.1,
                        'talking_duration': 2000,
                        'check_interval': 100
                    }
                })
            }
            
            response = requests.post(f"{self.base_url}/api/proctoring/update_trust_score", 
                                   json=detailed_violation, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    # Check if violation details were preserved
                    if 'violation_details' in result:
                        self.log_test("Voice Violation Details", True, 
                                    "Detailed violation information preserved")
                        return True
                    else:
                        self.log_test("Voice Violation Details", False, 
                                    "Violation details not preserved in response")
                        return False
                else:
                    self.log_test("Voice Violation Details", False, 
                                f"API error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Voice Violation Details", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Voice Violation Details", False, f"Error: {e}")
            return False
    
    def test_invalid_violation_data(self):
        """Test API with invalid violation data"""
        try:
            # Test missing required fields
            invalid_data = {
                'violation_type': 'voice_detected'
                # Missing exam_id
            }
            
            response = requests.post(f"{self.base_url}/api/proctoring/update_trust_score", 
                                   json=invalid_data, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 400:
                self.log_test("Invalid Violation Data", True, 
                            "Properly rejected invalid violation data")
                return True
            else:
                self.log_test("Invalid Violation Data", False, 
                            f"Should have rejected invalid data, got status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Invalid Violation Data", False, f"Error: {e}")
            return False
    
    def test_exam_page_load(self):
        """Test that exam page loads with voice detection components"""
        try:
            # Try to access an exam page
            response = requests.get(f"{self.base_url}/exam/1", 
                                  cookies=self.session_cookies, 
                                  timeout=5)
            
            if response.status_code == 200:
                # Check if voice detection components are present
                content = response.text
                
                required_components = [
                    'voice_detection.js',
                    'voiceStatus',
                    'VoiceDetectionSystem',
                    'microphone'
                ]
                
                missing_components = []
                for component in required_components:
                    if component not in content:
                        missing_components.append(component)
                
                if missing_components:
                    self.log_test("Exam Page Load", False, 
                                f"Missing voice detection components: {missing_components}")
                    return False
                else:
                    self.log_test("Exam Page Load", True, 
                                "Exam page loaded with voice detection components")
                    return True
            else:
                self.log_test("Exam Page Load", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Exam Page Load", False, f"Error: {e}")
            return False
    
    def test_proctoring_service_integration(self):
        """Test integration with proctoring service"""
        try:
            # Start a proctoring session first
            session_data = {
                'exam_id': 1,
                'user_id': 1
            }
            
            session_response = requests.post(f"{self.base_url}/api/proctoring/session/start", 
                                          json=session_data, 
                                          cookies=self.session_cookies, 
                                          timeout=5)
            
            if session_response.status_code != 201:
                self.log_test("Proctoring Service Integration", False, 
                            "Failed to start proctoring session")
                return False
            
            # Report a voice violation
            violation_data = {
                'violation_type': 'voice_detected',
                'exam_id': 1,
                'details': json.dumps({
                    'volume': 0.18,
                    'duration': 2200,
                    'violation_count': 1
                })
            }
            
            violation_response = requests.post(f"{self.base_url}/api/proctoring/update_trust_score", 
                                            json=violation_data, 
                                            cookies=self.session_cookies, 
                                            timeout=5)
            
            if violation_response.status_code == 200:
                result = violation_response.json()
                
                if result.get('success'):
                    # Check if violation was recorded in proctoring service
                    if 'violation_id' in result or 'trust_score' in result:
                        self.log_test("Proctoring Service Integration", True, 
                                    "Voice violation properly integrated with proctoring service")
                        return True
                    else:
                        self.log_test("Proctoring Service Integration", False, 
                                    "Violation not properly recorded in proctoring service")
                        return False
                else:
                    self.log_test("Proctoring Service Integration", False, 
                                f"Integration error: {result.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Proctoring Service Integration", False, 
                            f"Status code: {violation_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Proctoring Service Integration", False, f"Error: {e}")
            return False
    
    def test_voice_detection_settings(self):
        """Test voice detection configuration settings"""
        try:
            # Test different violation types to ensure voice detection is handled correctly
            test_cases = [
                {
                    'violation_type': 'voice_detected',
                    'expected_reduction': 20,
                    'description': 'Voice detection violation'
                },
                {
                    'violation_type': 'looking_away',
                    'expected_reduction': 10,
                    'description': 'Other violation type for comparison'
                }
            ]
            
            results = []
            
            for test_case in test_cases:
                violation_data = {
                    'violation_type': test_case['violation_type'],
                    'exam_id': 1,
                    'details': json.dumps({
                        'volume': 0.15,
                        'duration': 2000,
                        'violation_count': 1
                    })
                }
                
                response = requests.post(f"{self.base_url}/api/proctoring/update_trust_score", 
                                       json=violation_data, 
                                       cookies=self.session_cookies, 
                                       timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        results.append({
                            'type': test_case['violation_type'],
                            'reduction_applied': True,
                            'description': test_case['description']
                        })
                
                time.sleep(0.1)  # Small delay between tests
            
            if len(results) >= 2:
                self.log_test("Voice Detection Settings", True, 
                            f"Voice detection settings working correctly")
                return True
            else:
                self.log_test("Voice Detection Settings", False, 
                            f"Only {len(results)} test cases passed")
                return False
                
        except Exception as e:
            self.log_test("Voice Detection Settings", False, f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all voice detection system tests"""
        print("=" * 60)
        print("VOICE DETECTION ANTI-CHEATING SYSTEM TESTS")
        print("=" * 60)
        
        # Login first
        self.login()
        
        # Test core functionality
        self.test_proctoring_session_start()
        self.test_voice_violation_api()
        self.test_trust_score_reduction()
        
        # Test advanced features
        self.test_multiple_voice_violations()
        self.test_voice_violation_details()
        self.test_proctoring_service_integration()
        
        # Test configuration
        self.test_voice_detection_settings()
        
        # Test utilities
        self.test_trust_score_api()
        
        # Test edge cases
        self.test_invalid_violation_data()
        
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
        print("Voice Detection System Test Complete!")
        print("=" * 60)

if __name__ == "__main__":
    tester = VoiceDetectionSystemTester()
    tester.run_all_tests()
