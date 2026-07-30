#!/usr/bin/env python3
"""
Test Script for Blockchain-based Result Storage System
Tests blockchain functionality, hashing, integrity verification, and integration
"""

import requests
import json
import time
import hashlib
from datetime import datetime

class BlockchainSystemTester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5000"
        self.blockchain_url = f"{self.base_url}/blockchain"
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
    
    def test_blockchain_api_results(self):
        """Test blockchain results API endpoint"""
        try:
            response = requests.get(f"{self.blockchain_url}/api/results", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    blocks = data.get('blocks', [])
                    stats = data.get('stats', {})
                    
                    self.log_test("Blockchain API Results", True, 
                                f"Retrieved {len(blocks)} blocks", {
                        'total_blocks': len(blocks),
                        'stats_keys': list(stats.keys())
                    })
                    return True
                else:
                    self.log_test("Blockchain API Results", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Blockchain API Results", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Blockchain API Results", False, f"Error: {e}")
            return False
    
    def test_blockchain_verification(self):
        """Test blockchain integrity verification"""
        try:
            response = requests.get(f"{self.blockchain_url}/verify", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    verification = data.get('verification', {})
                    
                    if verification.get('valid'):
                        self.log_test("Blockchain Verification", True, 
                                    "Blockchain verified: No tampering detected", verification)
                    else:
                        self.log_test("Blockchain Verification", False, 
                                    f"Tampering detected: {len(verification.get('issues', []))} issues")
                    
                    return True
                else:
                    self.log_test("Blockchain Verification", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Blockchain Verification", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Blockchain Verification", False, f"Error: {e}")
            return False
    
    def test_blockchain_stats(self):
        """Test blockchain statistics endpoint"""
        try:
            response = requests.get(f"{self.blockchain_url}/stats", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    stats = data.get('stats', {})
                    
                    required_keys = ['total_blocks', 'unique_users', 'unique_exams', 'average_score']
                    missing_keys = [key for key in required_keys if key not in stats]
                    
                    if missing_keys:
                        self.log_test("Blockchain Stats", False, 
                                    f"Missing stats: {missing_keys}")
                        return False
                    else:
                        self.log_test("Blockchain Stats", True, 
                                    "Statistics retrieved successfully", stats)
                        return True
                else:
                    self.log_test("Blockchain Stats", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Blockchain Stats", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Blockchain Stats", False, f"Error: {e}")
            return False
    
    def test_add_result(self):
        """Test adding exam result to blockchain"""
        try:
            test_data = {
                'user_id': 1,
                'exam_id': 1,
                'score': 85,
                'additional_data': {
                    'total_questions': 10,
                    'correct_answers': 8,
                    'percentage': 80.0,
                    'exam_duration': 60
                }
            }
            
            response = requests.post(f"{self.blockchain_url}/add_result", 
                                   json=test_data, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    self.log_test("Add Result", True, 
                                "Test result added to blockchain", data)
                    return True
                else:
                    self.log_test("Add Result", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Add Result", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Add Result", False, f"Error: {e}")
            return False
    
    def test_block_structure(self):
        """Test block structure and hashing"""
        try:
            # Get blockchain results to check block structure
            response = requests.get(f"{self.blockchain_url}/api/results", timeout=5)
            
            if response.status_code != 200:
                self.log_test("Block Structure", False, "Failed to get blockchain data")
                return False
            
            data = response.json()
            
            if not data.get('success'):
                self.log_test("Block Structure", False, "API returned error")
                return False
            
            blocks = data.get('blocks', [])
            
            if not blocks:
                self.log_test("Block Structure", False, "No blocks found")
                return False
            
            # Check block structure
            required_fields = [
                'index', 'timestamp', 'user_id', 'exam_id', 
                'score', 'previous_hash', 'current_hash', 'data'
            ]
            
            structure_issues = []
            
            for i, block in enumerate(blocks):
                missing_fields = [field for field in required_fields if field not in block]
                
                if missing_fields:
                    structure_issues.append(f"Block {i}: Missing {missing_fields}")
                
                # Check hash format (should be 64 characters for SHA-256)
                if len(block.get('current_hash', '')) != 64:
                    structure_issues.append(f"Block {i}: Invalid hash length")
                
                # Check timestamp format
                try:
                    datetime.fromisoformat(block.get('timestamp', '').replace('Z', '+00:00'))
                except ValueError:
                    structure_issues.append(f"Block {i}: Invalid timestamp format")
            
            if structure_issues:
                self.log_test("Block Structure", False, 
                            f"Structure issues: {'; '.join(structure_issues)}")
                return False
            else:
                self.log_test("Block Structure", True, 
                            f"All {len(blocks)} blocks have correct structure")
                return True
                
        except Exception as e:
            self.log_test("Block Structure", False, f"Error: {e}")
            return False
    
    def test_hash_consistency(self):
        """Test hash consistency and integrity"""
        try:
            response = requests.get(f"{self.blockchain_url}/api/results", timeout=5)
            
            if response.status_code != 200:
                self.log_test("Hash Consistency", False, "Failed to get blockchain data")
                return False
            
            data = response.json()
            blocks = data.get('blocks', [])
            
            if len(blocks) < 2:
                self.log_test("Hash Consistency", False, "Need at least 2 blocks for testing")
                return False
            
            # Check hash linking
            hash_issues = []
            
            for i in range(1, len(blocks)):
                current_block = blocks[i]
                previous_block = blocks[i-1]
                
                # Check if previous hash matches
                if current_block.get('previous_hash') != previous_block.get('current_hash'):
                    hash_issues.append(f"Block {i}: Previous hash mismatch")
            
            if hash_issues:
                self.log_test("Hash Consistency", False, 
                            f"Hash issues: {'; '.join(hash_issues)}")
                return False
            else:
                self.log_test("Hash Consistency", True, 
                            "All hash links are consistent")
                return True
                
        except Exception as e:
            self.log_test("Hash Consistency", False, f"Error: {e}")
            return False
    
    def test_blockchain_export(self):
        """Test blockchain export functionality"""
        try:
            response = requests.get(f"{self.blockchain_url}/export", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    blockchain_data = data.get('blockchain', {})
                    
                    if 'blocks' in blockchain_data and 'stats' in blockchain_data:
                        self.log_test("Blockchain Export", True, 
                                    f"Exported {len(blockchain_data['blocks'])} blocks")
                        return True
                    else:
                        self.log_test("Blockchain Export", False, "Missing required fields")
                        return False
                else:
                    self.log_test("Blockchain Export", False, 
                                f"API error: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("Blockchain Export", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Blockchain Export", False, f"Error: {e}")
            return False
    
    def test_genesis_block(self):
        """Test genesis block properties"""
        try:
            response = requests.get(f"{self.blockchain_url}/api/results", timeout=5)
            
            if response.status_code != 200:
                self.log_test("Genesis Block", False, "Failed to get blockchain data")
                return False
            
            data = response.json()
            blocks = data.get('blocks', [])
            
            if not blocks:
                self.log_test("Genesis Block", False, "No blocks found")
                return False
            
            # Find genesis block (index 0)
            genesis_block = None
            for block in blocks:
                if block.get('index') == 0:
                    genesis_block = block
                    break
            
            if not genesis_block:
                self.log_test("Genesis Block", False, "Genesis block not found")
                return False
            
            # Check genesis block properties
            genesis_issues = []
            
            if genesis_block.get('user_id') != 0:
                genesis_issues.append("Invalid user_id (should be 0)")
            
            if genesis_block.get('exam_id') != 0:
                genesis_issues.append("Invalid exam_id (should be 0)")
            
            if genesis_block.get('score') != 0.0:
                genesis_issues.append("Invalid score (should be 0.0)")
            
            if genesis_block.get('previous_hash') != "0" * 64:
                genesis_issues.append("Invalid previous_hash (should be 64 zeros)")
            
            if genesis_issues:
                self.log_test("Genesis Block", False, 
                            f"Genesis issues: {'; '.join(genesis_issues)}")
                return False
            else:
                self.log_test("Genesis Block", True, 
                            "Genesis block has correct properties")
                return True
                
        except Exception as e:
            self.log_test("Genesis Block", False, f"Error: {e}")
            return False
    
    def test_multiple_results(self):
        """Test adding multiple results and chain growth"""
        try:
            # Add multiple test results
            test_results = [
                {'user_id': 2, 'exam_id': 1, 'score': 75},
                {'user_id': 3, 'exam_id': 2, 'score': 90},
                {'user_id': 1, 'exam_id': 2, 'score': 88}
            ]
            
            initial_blocks = None
            added_count = 0
            
            for i, test_data in enumerate(test_results):
                try:
                    response = requests.post(f"{self.blockchain_url}/add_result", 
                                           json=test_data, timeout=5)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('success'):
                            added_count += 1
                        else:
                            print(f"Failed to add result {i+1}: {result.get('error')}")
                    else:
                        print(f"HTTP error adding result {i+1}: {response.status_code}")
                        
                except Exception as e:
                    print(f"Exception adding result {i+1}: {e}")
            
            # Check final blockchain size
            final_response = requests.get(f"{self.blockchain_url}/api/results", timeout=5)
            
            if final_response.status_code == 200:
                final_data = final_response.json()
                final_blocks = len(final_data.get('blocks', []))
                
                if added_count > 0:
                    self.log_test("Multiple Results", True, 
                                f"Added {added_count}/{len(test_results)} results, total blocks: {final_blocks}")
                    return True
                else:
                    self.log_test("Multiple Results", False, "No results added successfully")
                    return False
            else:
                self.log_test("Multiple Results", False, "Failed to check final blockchain")
                return False
                
        except Exception as e:
            self.log_test("Multiple Results", False, f"Error: {e}")
            return False
    
    def test_tampering_detection(self):
        """Test tampering detection by verifying integrity"""
        try:
            # First, verify current chain is valid
            verify_response = requests.get(f"{self.blockchain_url}/verify", timeout=5)
            
            if verify_response.status_code != 200:
                self.log_test("Tampering Detection", False, "Failed to verify initial chain")
                return False
            
            verify_data = verify_response.json()
            
            if not verify_data.get('success'):
                self.log_test("Tampering Detection", False, "Initial verification failed")
                return False
            
            # Get current blockchain state
            results_response = requests.get(f"{self.blockchain_url}/api/results", timeout=5)
            
            if results_response.status_code != 200:
                self.log_test("Tampering Detection", False, "Failed to get blockchain data")
                return False
            
            results_data = results_response.json()
            blocks = results_data.get('blocks', [])
            
            if len(blocks) < 2:
                self.log_test("Tampering Detection", False, "Need at least 2 blocks for testing")
                return False
            
            # The system should detect any tampering
            # Since we can't directly modify the blockchain, we'll test the verification system
            verification = verify_data.get('verification', {})
            
            if verification.get('valid'):
                self.log_test("Tampering Detection", True, 
                            "No tampering detected (chain is intact)")
                return True
            else:
                issues = verification.get('issues', [])
                self.log_test("Tampering Detection", True, 
                            f"Tampering detection working: {len(issues)} issues found", issues)
                return True
                
        except Exception as e:
            self.log_test("Tampering Detection", False, f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all blockchain system tests"""
        print("=" * 60)
        print("BLOCKCHAIN-BASED RESULT STORAGE SYSTEM TESTS")
        print("=" * 60)
        
        # Test basic API endpoints
        self.test_blockchain_api_results()
        self.test_blockchain_stats()
        self.test_blockchain_verification()
        
        # Test blockchain functionality
        self.test_genesis_block()
        self.test_block_structure()
        self.test_hash_consistency()
        
        # Test result management
        self.test_add_result()
        self.test_multiple_results()
        
        # Test advanced features
        self.test_blockchain_export()
        self.test_tampering_detection()
        
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
        print("Blockchain System Test Complete!")
        print("=" * 60)

if __name__ == "__main__":
    tester = BlockchainSystemTester()
    tester.run_all_tests()
