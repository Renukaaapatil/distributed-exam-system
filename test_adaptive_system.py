#!/usr/bin/env python3
"""
Test Script for Adaptive Exam System
Tests adaptive difficulty adjustment, question fetching, and exam flow
"""

import requests
import json
import time
from datetime import datetime

class AdaptiveSystemTester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.adaptive_url = f"{self.base_url}/adaptive"
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
                # Get session cookies
                self.session_cookies = response.cookies
                print("Login successful")
                return True
            else:
                print("Login failed - trying without authentication")
                return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def test_adaptive_exam_start(self, exam_id=1):
        """Test starting adaptive exam"""
        try:
            response = requests.get(f"{self.adaptive_url}/start_exam/{exam_id}", 
                                  cookies=self.session_cookies, timeout=5)
            
            if response.status_code == 200:
                # Check if page loaded successfully
                if "Adaptive Exam" in response.text:
                    self.log_test("Adaptive Exam Start", True, 
                                f"Successfully started adaptive exam {exam_id}")
                    return True
                else:
                    self.log_test("Adaptive Exam Start", False, "Page content invalid")
                    return False
            else:
                self.log_test("Adaptive Exam Start", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Adaptive Exam Start", False, f"Error: {e}")
            return False
    
    def test_answer_submission(self, exam_id=1):
        """Test answer submission with adaptive logic"""
        try:
            # First start an exam
            start_response = requests.get(f"{self.adaptive_url}/start_exam/{exam_id}", 
                                        cookies=self.session_cookies, timeout=5)
            
            if start_response.status_code != 200:
                self.log_test("Answer Submission", False, "Failed to start exam")
                return False
            
            # Submit a test answer
            answer_data = {
                'question_id': 1,  # Assuming question 1 exists
                'selected_answer': 'A'
            }
            
            response = requests.post(f"{self.adaptive_url}/submit_answer", 
                                   json=answer_data, 
                                   cookies=self.session_cookies, 
                                   timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    required_fields = ['is_correct', 'points_earned', 'current_score', 'current_difficulty']
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if missing_fields:
                        self.log_test("Answer Submission", False, 
                                    f"Missing fields: {missing_fields}")
                        return False
                    
                    # Check difficulty adjustment logic
                    current_difficulty = data.get('current_difficulty')
                    if current_difficulty in [1, 2, 3]:
                        self.log_test("Answer Submission", True, 
                                    f"Answer processed, new difficulty: {current_difficulty}", data)
                        return True
                    else:
                        self.log_test("Answer Submission", False, 
                                    f"Invalid difficulty: {current_difficulty}")
                        return False
                else:
                    self.log_test("Answer Submission", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Answer Submission", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Answer Submission", False, f"Error: {e}")
            return False
    
    def test_session_state(self):
        """Test session state management"""
        try:
            response = requests.get(f"{self.adaptive_url}/session_state", 
                                  cookies=self.session_cookies, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    session_state = data.get('session_state', {})
                    required_fields = ['current_difficulty', 'score', 'question_index', 'accuracy']
                    missing_fields = [field for field in required_fields if field not in session_state]
                    
                    if missing_fields:
                        self.log_test("Session State", False, 
                                    f"Missing session fields: {missing_fields}")
                        return False
                    
                    # Check difficulty range
                    difficulty = session_state.get('current_difficulty')
                    if difficulty not in [1, 2, 3]:
                        self.log_test("Session State", False, 
                                    f"Invalid difficulty in session: {difficulty}")
                        return False
                    
                    self.log_test("Session State", True, 
                                "Session state retrieved successfully", session_state)
                    return True
                else:
                    self.log_test("Session State", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Session State", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Session State", False, f"Error: {e}")
            return False
    
    def test_adaptive_logic(self):
        """Test adaptive difficulty adjustment logic"""
        try:
            # Test multiple answer submissions to see difficulty progression
            difficulty_progression = []
            
            for i in range(5):  # Submit 5 answers
                answer_data = {
                    'question_id': 1,  # Use same question for testing
                    'selected_answer': 'A' if i % 2 == 0 else 'B'  # Alternate correct/incorrect
                }
                
                response = requests.post(f"{self.adaptive_url}/submit_answer", 
                                       json=answer_data, 
                                       cookies=self.session_cookies, 
                                       timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        difficulty_progression.append(data.get('current_difficulty'))
                else:
                    break
            
            if len(difficulty_progression) >= 3:
                self.log_test("Adaptive Logic", True, 
                            f"Difficulty progression: {difficulty_progression}")
                return True
            else:
                self.log_test("Adaptive Logic", False, 
                            f"Insufficient progression data: {difficulty_progression}")
                return False
                
        except Exception as e:
            self.log_test("Adaptive Logic", False, f"Error: {e}")
            return False
    
    def test_exam_completion(self, exam_id=1):
        """Test exam completion flow"""
        try:
            # Start exam
            start_response = requests.get(f"{self.adaptive_url}/start_exam/{exam_id}", 
                                        cookies=self.session_cookies, timeout=5)
            
            if start_response.status_code != 200:
                self.log_test("Exam Completion", False, "Failed to start exam")
                return False
            
            # End exam
            response = requests.post(f"{self.adaptive_url}/end_exam", 
                                   cookies=self.session_cookies, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    required_fields = ['total_questions', 'correct_answers', 'score', 'accuracy']
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if missing_fields:
                        self.log_test("Exam Completion", False, 
                                    f"Missing result fields: {missing_fields}")
                        return False
                    
                    self.log_test("Exam Completion", True, 
                                f"Exam completed successfully", data)
                    return True
                else:
                    self.log_test("Exam Completion", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Exam Completion", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Exam Completion", False, f"Error: {e}")
            return False
    
    def test_exam_statistics(self, exam_id=1):
        """Test exam statistics endpoint"""
        try:
            response = requests.get(f"{self.adaptive_url}/exam_stats/{exam_id}", 
                                  cookies=self.session_cookies, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    stats = data.get('stats', {})
                    required_fields = ['total_questions', 'difficulty_distribution']
                    missing_fields = [field for field in required_fields if field not in stats]
                    
                    if missing_fields:
                        self.log_test("Exam Statistics", False, 
                                    f"Missing stats fields: {missing_fields}")
                        return False
                    
                    # Check difficulty distribution
                    difficulty_dist = stats.get('difficulty_distribution', {})
                    expected_levels = [1, 2, 3]
                    missing_levels = [level for level in expected_levels if level not in difficulty_dist]
                    
                    if missing_levels:
                        self.log_test("Exam Statistics", False, 
                                    f"Missing difficulty levels: {missing_levels}")
                        return False
                    
                    self.log_test("Exam Statistics", True, 
                                f"Statistics retrieved successfully", stats)
                    return True
                else:
                    self.log_test("Exam Statistics", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Exam Statistics", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Exam Statistics", False, f"Error: {e}")
            return False
    
    def test_question_fetching(self, exam_id=1):
        """Test question fetching by difficulty"""
        try:
            # Test getting current question
            response = requests.get(f"{self.adaptive_url}/get_question", 
                                  cookies=self.session_cookies, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    question = data.get('question', {})
                    required_fields = ['id', 'text', 'options', 'difficulty', 'difficulty_name']
                    missing_fields = [field for field in required_fields if field not in question]
                    
                    if missing_fields:
                        self.log_test("Question Fetching", False, 
                                    f"Missing question fields: {missing_fields}")
                        return False
                    
                    # Check difficulty validity
                    difficulty = question.get('difficulty')
                    if difficulty not in [1, 2, 3]:
                        self.log_test("Question Fetching", False, 
                                    f"Invalid question difficulty: {difficulty}")
                        return False
                    
                    # Check options structure
                    options = question.get('options', {})
                    if not isinstance(options, dict) or len(options) != 4:
                        self.log_test("Question Fetching", False, 
                                    "Invalid question options structure")
                        return False
                    
                    self.log_test("Question Fetching", True, 
                                f"Question fetched successfully", {
                        'difficulty': difficulty,
                        'options_count': len(options)
                    })
                    return True
                else:
                    self.log_test("Question Fetching", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Question Fetching", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Question Fetching", False, f"Error: {e}")
            return False
    
    def test_score_weighting(self):
        """Test score weighting based on difficulty"""
        try:
            # Submit answers for different difficulty levels
            score_tests = []
            
            for difficulty in [1, 2, 3]:  # Test all difficulty levels
                answer_data = {
                    'question_id': 1,
                    'selected_answer': 'A'  # Assume this is correct
                }
                
                response = requests.post(f"{self.adaptive_url}/submit_answer", 
                                       json=answer_data, 
                                       cookies=self.session_cookies, 
                                       timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and data.get('is_correct'):
                        points = data.get('points_earned', 0)
                        score_tests.append({
                            'difficulty': difficulty,
                            'points': points
                        })
                
                # Small delay between requests
                time.sleep(0.1)
            
            # Check if scoring follows the expected pattern
            expected_weights = {1: 1, 2: 2, 3: 3}
            weight_correct = True
            
            for test in score_tests:
                expected_points = expected_weights.get(test['difficulty'], 2)
                if test['points'] != expected_points:
                    weight_correct = False
                    break
            
            if weight_correct and len(score_tests) >= 2:
                self.log_test("Score Weighting", True, 
                            f"Score weighting working correctly", score_tests)
                return True
            else:
                self.log_test("Score Weighting", False, 
                            f"Score weighting incorrect: {score_tests}")
                return False
                
        except Exception as e:
            self.log_test("Score Weighting", False, f"Error: {e}")
            return False
    
    def test_session_reset(self):
        """Test session reset functionality"""
        try:
            # Reset session
            response = requests.post(f"{self.adaptive_url}/reset_session", 
                                   cookies=self.session_cookies, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    # Check if session is actually cleared
                    session_response = requests.get(f"{self.adaptive_url}/session_state", 
                                                   cookies=self.session_cookies, timeout=5)
                    
                    if session_response.status_code == 404:
                        self.log_test("Session Reset", True, 
                                    "Session reset successfully")
                        return True
                    else:
                        self.log_test("Session Reset", False, 
                                    "Session still active after reset")
                        return False
                else:
                    self.log_test("Session Reset", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Session Reset", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Session Reset", False, f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all adaptive system tests"""
        print("=" * 60)
        print("ADAPTIVE EXAM SYSTEM TESTS")
        print("=" * 60)
        
        # Login first
        self.login()
        
        # Test core functionality
        self.test_adaptive_exam_start()
        self.test_session_state()
        self.test_question_fetching()
        
        # Test adaptive logic
        self.test_answer_submission()
        self.test_adaptive_logic()
        self.test_score_weighting()
        
        # Test exam flow
        self.test_exam_completion()
        self.test_exam_statistics()
        
        # Test utilities
        self.test_session_reset()
        
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
        print("Adaptive System Test Complete!")
        print("=" * 60)

if __name__ == "__main__":
    tester = AdaptiveSystemTester()
    tester.run_all_tests()
