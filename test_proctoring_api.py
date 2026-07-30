#!/usr/bin/env python3
"""
Test script for proctoring API endpoints
"""

import requests
import json

def test_proctoring_endpoints():
    """Test all proctoring API endpoints"""
    base_url = "http://127.0.0.1:5000/api/proctoring"
    
    print("Testing Proctoring API Endpoints...")
    print("=" * 50)
    
    # Test 1: Get trust score
    print("\n1. Testing GET /get_trust_score")
    try:
        response = requests.get(f"{base_url}/get_trust_score?exam_id=1")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("SUCCESS: get_trust_score endpoint working")
        else:
            print("FAILED: get_trust_score endpoint not working")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 2: Update trust score
    print("\n2. Testing POST /update_trust_score")
    try:
        data = {
            "violation_type": "looking_away",
            "exam_id": 1
        }
        response = requests.post(f"{base_url}/update_trust_score", 
                               json=data,
                               headers={'Content-Type': 'application/json'})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("SUCCESS: update_trust_score endpoint working")
        else:
            print("FAILED: update_trust_score endpoint not working")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 3: Auto submit exam
    print("\n3. Testing POST /auto_submit")
    try:
        data = {"exam_id": 1}
        response = requests.post(f"{base_url}/auto_submit", 
                               json=data,
                               headers={'Content-Type': 'application/json'})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("SUCCESS: auto_submit endpoint working")
        else:
            print("FAILED: auto_submit endpoint not working")
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("Proctoring API testing completed!")

if __name__ == "__main__":
    test_proctoring_endpoints()
