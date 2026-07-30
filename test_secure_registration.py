#!/usr/bin/env python3
"""
Test Script for Secure Registration System
Tests that users cannot register as admin and security measures are working
"""

import requests
import json
import time
from datetime import datetime

class SecureRegistrationTester:
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
    
    def test_registration_page_load(self):
        """Test that registration page loads without admin option"""
        try:
            response = requests.get(f"{self.base_url}/register", timeout=5)
            
            if response.status_code == 200:
                content = response.text
                
                # Check that admin option is NOT present
                if 'Administrator' not in content and 'admin' not in content.lower():
                    self.log_test("Registration Page Load", True, 
                                "Registration page loads without admin option")
                    return True
                else:
                    self.log_test("Registration Page Load", False, 
                                "Admin option still present in registration form")
                    return False
            else:
                self.log_test("Registration Page Load", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Registration Page Load", False, f"Error: {e}")
            return False
    
    def test_student_registration(self):
        """Test normal student registration works"""
        try:
            # Generate unique student data
            timestamp = int(time.time())
            student_data = {
                'name': f'Test Student {timestamp}',
                'email': f'student{timestamp}@test.com',
                'password': 'testpass123',
                'confirm_password': 'testpass123',
                'role': 'student'
            }
            
            response = requests.post(f"{self.base_url}/register", 
                                   data=student_data, 
                                   allow_redirects=False, 
                                   timeout=5)
            
            if response.status_code == 302:
                # Check if redirected to login (successful registration)
                if 'login' in response.headers.get('Location', ''):
                    self.log_test("Student Registration", True, 
                                "Student registration successful")
                    return True
                else:
                    self.log_test("Student Registration", False, 
                                "Unexpected redirect after registration")
                    return False
            else:
                self.log_test("Student Registration", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Student Registration", False, f"Error: {e}")
            return False
    
    def test_admin_registration_blocked(self):
        """Test that admin registration is blocked"""
        try:
            # Try to register as admin by manipulating form data
            timestamp = int(time.time())
            admin_data = {
                'name': f'Hacker Admin {timestamp}',
                'email': f'hacker{timestamp}@test.com',
                'password': 'hackpass123',
                'confirm_password': 'hackpass123',
                'role': 'admin'  # Try to set admin role
            }
            
            response = requests.post(f"{self.base_url}/register", 
                                   data=admin_data, 
                                   allow_redirects=False, 
                                   timeout=5)
            
            if response.status_code == 302:
                # Check if redirected to login (registration appeared successful)
                if 'login' in response.headers.get('Location', ''):
                    # Now check if user was actually created as admin
                    # Try to login as admin
                    login_data = {
                        'email': admin_data['email'],
                        'password': admin_data['password']
                    }
                    
                    login_response = requests.post(f"{self.base_url}/login", 
                                                data=login_data, 
                                                allow_redirects=False, 
                                                timeout=5)
                    
                    if login_response.status_code == 302:
                        # Check dashboard to see user role
                        dashboard_response = requests.get(f"{self.base_url}/dashboard", 
                                                       cookies=login_response.cookies, 
                                                       timeout=5)
                        
                        if dashboard_response.status_code == 200:
                            content = dashboard_response.text
                            
                            # Check if user has admin access
                            if 'Administrator' in content or 'Admin Panel' in content:
                                self.log_test("Admin Registration Blocked", False, 
                                            "User was able to register as admin - SECURITY BREACH!")
                                return False
                            else:
                                # User was created but as student
                                self.log_test("Admin Registration Blocked", True, 
                                            "Admin registration blocked - user created as student")
                                return True
                        else:
                            self.log_test("Admin Registration Blocked", False, 
                                        f"Could not check user dashboard: {dashboard_response.status_code}")
                            return False
                    else:
                        self.log_test("Admin Registration Blocked", False, 
                                    f"Login failed after registration: {login_response.status_code}")
                        return False
                else:
                    self.log_test("Admin Registration Blocked", False, 
                                "Unexpected redirect after registration")
                    return False
            else:
                self.log_test("Admin Registration Blocked", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Admin Registration Blocked", False, f"Error: {e}")
            return False
    
    def test_default_admin_exists(self):
        """Test that default admin account exists"""
        try:
            # Try to login with default admin credentials
            admin_data = {
                'email': 'admin@example.com',
                'password': 'admin123'
            }
            
            response = requests.post(f"{self.base_url}/login", 
                                   data=admin_data, 
                                   allow_redirects=False, 
                                   timeout=5)
            
            if response.status_code == 302:
                # Check if redirected to dashboard (successful login)
                if 'dashboard' in response.headers.get('Location', ''):
                    # Check dashboard for admin features
                    dashboard_response = requests.get(f"{self.base_url}/dashboard", 
                                                   cookies=response.cookies, 
                                                   timeout=5)
                    
                    if dashboard_response.status_code == 200:
                        content = dashboard_response.text
                        
                        if 'Administrator' in content or 'Admin Panel' in content:
                            self.log_test("Default Admin Exists", True, 
                                        "Default admin account exists and has admin access")
                            return True
                        else:
                            self.log_test("Default Admin Exists", False, 
                                        "Default admin account exists but lacks admin features")
                            return False
                    else:
                        self.log_test("Default Admin Exists", False, 
                                    f"Could not access dashboard: {dashboard_response.status_code}")
                        return False
                else:
                    self.log_test("Default Admin Exists", False, 
                                "Login successful but not redirected to dashboard")
                    return False
            else:
                self.log_test("Default Admin Exists", False, f"Login failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Default Admin Exists", False, f"Error: {e}")
            return False
    
    def test_duplicate_email_prevention(self):
        """Test that duplicate email registration is prevented"""
        try:
            # Try to register with existing admin email
            duplicate_data = {
                'name': 'Duplicate User',
                'email': 'admin@example.com',  # Use existing admin email
                'password': 'newpass123',
                'confirm_password': 'newpass123',
                'role': 'student'
            }
            
            response = requests.post(f"{self.base_url}/register", 
                                   data=duplicate_data, 
                                   allow_redirects=False, 
                                   timeout=5)
            
            if response.status_code == 200:
                # If returned to registration page, it means registration failed (good)
                self.log_test("Duplicate Email Prevention", True, 
                            "Duplicate email registration prevented")
                return True
            else:
                self.log_test("Duplicate Email Prevention", False, 
                            f"Unexpected status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Duplicate Email Prevention", False, f"Error: {e}")
            return False
    
    def test_password_validation(self):
        """Test password validation requirements"""
        try:
            # Test with short password
            short_password_data = {
                'name': 'Short Password User',
                'email': 'shortpass@test.com',
                'password': '123',  # Too short
                'confirm_password': '123',
                'role': 'student'
            }
            
            response = requests.post(f"{self.base_url}/register", 
                                   data=short_password_data, 
                                   allow_redirects=False, 
                                   timeout=5)
            
            if response.status_code == 200:
                # If returned to registration page, it means registration failed (good)
                self.log_test("Password Validation", True, 
                            "Short password validation working")
                return True
            else:
                self.log_test("Password Validation", False, 
                            f"Password validation not working: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Password Validation", False, f"Error: {e}")
            return False
    
    def test_required_fields_validation(self):
        """Test that required fields are validated"""
        try:
            # Test with missing name
            missing_field_data = {
                'name': '',  # Missing name
                'email': 'missing@test.com',
                'password': 'testpass123',
                'confirm_password': 'testpass123',
                'role': 'student'
            }
            
            response = requests.post(f"{self.base_url}/register", 
                                   data=missing_field_data, 
                                   allow_redirects=False, 
                                   timeout=5)
            
            if response.status_code == 200:
                # If returned to registration page, it means validation failed (good)
                self.log_test("Required Fields Validation", True, 
                            "Required fields validation working")
                return True
            else:
                self.log_test("Required Fields Validation", False, 
                            f"Required fields validation not working: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Required Fields Validation", False, f"Error: {e}")
            return False
    
    def test_csrf_protection(self):
        """Test that CSRF protection is working"""
        try:
            # Try to register without CSRF token
            no_csrf_data = {
                'name': 'No CSRF User',
                'email': 'csrf@test.com',
                'password': 'testpass123',
                'confirm_password': 'testpass123',
                'role': 'student'
            }
            
            response = requests.post(f"{self.base_url}/register", 
                                   data=no_csrf_data, 
                                   allow_redirects=False, 
                                   timeout=5)
            
            if response.status_code == 400 or response.status_code == 200:
                # If blocked or returned to form, CSRF is working
                self.log_test("CSRF Protection", True, 
                            "CSRF protection appears to be working")
                return True
            else:
                self.log_test("CSRF Protection", False, 
                            f"CSRF protection may not be working: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("CSRF Protection", False, f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all secure registration tests"""
        print("=" * 60)
        print("SECURE REGISTRATION SYSTEM TESTS")
        print("=" * 60)
        
        # Test frontend security
        self.test_registration_page_load()
        
        # Test backend security
        self.test_student_registration()
        self.test_admin_registration_blocked()
        
        # Test admin account
        self.test_default_admin_exists()
        
        # Test validation
        self.test_duplicate_email_prevention()
        self.test_password_validation()
        self.test_required_fields_validation()
        
        # Test security features
        self.test_csrf_protection()
        
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
        print("Secure Registration System Test Complete!")
        print("=" * 60)

if __name__ == "__main__":
    tester = SecureRegistrationTester()
    tester.run_all_tests()
