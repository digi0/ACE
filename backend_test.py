import requests
import sys
import json
import uuid
from datetime import datetime

class ACEAPITester:
    def __init__(self, base_url="https://ace-advisor.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.user_data = None
        self.test_email = f"test_{uuid.uuid4().hex[:8]}@psu.edu"
        self.test_password = "TestPass123!"

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, use_session=True):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            client = self.session if use_session else requests
            
            if method == 'GET':
                response = client.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = client.post(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = client.delete(url, headers=headers, timeout=30)
            elif method == 'PUT':
                response = client.put(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response preview: {str(response_data)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.failed_tests.append({
                    'test': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:200]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                'test': name,
                'error': str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_student_profile(self):
        """Test student profile endpoint"""
        success, response = self.run_test("Student Profile", "GET", "student/profile", 200)
        if success:
            # Verify expected fields
            expected_fields = ['id', 'psu_id', 'name', 'email', 'major']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in profile: {missing_fields}")
            else:
                print(f"✅ Profile contains all expected fields")
                print(f"   Student: {response.get('name')} ({response.get('psu_id')})")
        return success, response

    def test_student_intelligence(self):
        """Test student intelligence endpoint"""
        success, response = self.run_test("Student Intelligence", "GET", "student/intelligence", 200)
        if success:
            expected_fields = ['type', 'title', 'description', 'urgency']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in intelligence: {missing_fields}")
            else:
                print(f"✅ Intelligence contains all expected fields")
        return success, response

    def test_chat_send(self):
        """Test chat send endpoint"""
        test_message = "What are the withdrawal deadlines for this semester?"
        test_data = {
            "chat_id": None,
            "message": test_message,
            "student_id": "abc123456"
        }
        
        success, response = self.run_test("Chat Send", "POST", "chat/send", 200, test_data)
        if success:
            # Verify response structure
            expected_fields = ['chat_id', 'response']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in chat response: {missing_fields}")
                return False, response
            
            # Check structured response
            ai_response = response.get('response', {})
            expected_ai_fields = ['direct_answer', 'next_steps', 'sources_used', 'risk_level']
            missing_ai_fields = [field for field in expected_ai_fields if field not in ai_response]
            if missing_ai_fields:
                print(f"⚠️  Missing fields in AI response: {missing_ai_fields}")
            else:
                print(f"✅ AI response contains all expected fields")
                print(f"   Direct answer: {ai_response.get('direct_answer', '')[:100]}...")
                print(f"   Risk level: {ai_response.get('risk_level')}")
                print(f"   Next steps count: {len(ai_response.get('next_steps', []))}")
                print(f"   Sources count: {len(ai_response.get('sources_used', []))}")
        
        return success, response

    def test_get_chats(self):
        """Test get chats for student"""
        student_id = "abc123456"
        return self.run_test("Get Chats", "GET", f"chats/{student_id}", 200)

    def test_policies(self):
        """Test policies endpoint"""
        success, response = self.run_test("Get Policies", "GET", "policies", 200)
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} policies")
            if len(response) > 0:
                first_policy = response[0]
                expected_fields = ['vault_id', 'title', 'category', 'content', 'link']
                missing_fields = [field for field in expected_fields if field not in first_policy]
                if missing_fields:
                    print(f"⚠️  Missing fields in policy: {missing_fields}")
                else:
                    print(f"✅ Policy structure is correct")
        return success, response

def main():
    print("🚀 Starting ACE API Testing...")
    print("=" * 50)
    
    tester = ACEAPITester()
    
    # Run all tests
    tests = [
        tester.test_root_endpoint,
        tester.test_student_profile,
        tester.test_student_intelligence,
        tester.test_policies,
        tester.test_get_chats,
        tester.test_chat_send,  # This one might take longer due to AI processing
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            tester.failed_tests.append({'test': test.__name__, 'error': str(e)})
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.failed_tests:
        print("\n❌ Failed Tests:")
        for failure in tester.failed_tests:
            print(f"   - {failure.get('test', 'Unknown')}: {failure.get('error', failure.get('actual', 'Unknown error'))}")
    
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"\n📈 Success Rate: {success_rate:.1f}%")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())