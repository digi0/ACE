import requests
import sys
import json
import uuid
from datetime import datetime

class ACEAPITester:
    def __init__(self, base_url="https://penn-state-clarity.preview.emergentagent.com/api"):
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
        return self.run_test("Root API", "GET", "", 200, use_session=False)

    def test_signup(self):
        """Test user signup"""
        signup_data = {
            "name": "Test User",
            "email": self.test_email,
            "password": self.test_password
        }
        
        success, response = self.run_test("User Signup", "POST", "auth/signup", 200, signup_data)
        if success:
            expected_fields = ['user_id', 'email', 'name', 'profile_complete']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in signup response: {missing_fields}")
            else:
                print(f"✅ Signup response contains all expected fields")
                print(f"   User: {response.get('name')} ({response.get('email')})")
                self.user_data = response
        return success, response

    def test_login(self):
        """Test user login"""
        login_data = {
            "email": self.test_email,
            "password": self.test_password
        }
        
        success, response = self.run_test("User Login", "POST", "auth/login", 200, login_data)
        if success:
            expected_fields = ['user_id', 'email', 'name', 'profile_complete']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in login response: {missing_fields}")
            else:
                print(f"✅ Login response contains all expected fields")
                print(f"   User: {response.get('name')} ({response.get('email')})")
                self.user_data = response
        return success, response

    def test_get_me(self):
        """Test get current user"""
        success, response = self.run_test("Get Current User", "GET", "auth/me", 200)
        if success:
            expected_fields = ['user_id', 'email', 'name', 'profile_complete']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in user response: {missing_fields}")
            else:
                print(f"✅ User response contains all expected fields")
        return success, response

    def test_profile_options(self):
        """Test profile options endpoint"""
        success, response = self.run_test("Profile Options", "GET", "user/profile-options", 200, use_session=False)
        if success:
            expected_fields = ['campuses', 'academic_levels', 'credit_loads', 'financial_aid_statuses']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in profile options: {missing_fields}")
            else:
                print(f"✅ Profile options contains all expected fields")
                print(f"   Campuses: {len(response.get('campuses', []))}")
                print(f"   Academic levels: {len(response.get('academic_levels', []))}")
        return success, response

    def test_update_profile(self):
        """Test profile update (onboarding)"""
        profile_data = {
            "campus": "University Park",
            "major": "Computer Science",
            "academic_level": "Junior (60-89 credits)",
            "credit_load": "Full-time (12-18 credits)",
            "financial_aid_status": "Receiving aid (grants/scholarships)",
            "international_student": False,
            "expected_graduation": "Spring 2026",
            "current_semester": "Spring 2026"
        }
        
        success, response = self.run_test("Update Profile", "POST", "user/profile", 200, profile_data)
        if success:
            expected_fields = ['message', 'profile_complete', 'profile']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in profile update response: {missing_fields}")
            else:
                print(f"✅ Profile update response contains all expected fields")
                print(f"   Profile complete: {response.get('profile_complete')}")
        return success, response

    def test_student_intelligence(self):
        """Test student intelligence endpoint"""
        success, response = self.run_test("Student Intelligence", "GET", "student/intelligence", 200)
        if success:
            expected_fields = ['context', 'insight', 'urgency']
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in intelligence: {missing_fields}")
            else:
                print(f"✅ Intelligence contains all expected fields")
                print(f"   Urgency: {response.get('urgency')}")
        return success, response

    def test_chat_send(self):
        """Test chat send endpoint"""
        test_message = "What are the withdrawal deadlines for this semester?"
        test_data = {
            "chat_id": None,
            "message": test_message
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
        """Test get chats for current user"""
        return self.run_test("Get Chats", "GET", "chats", 200)

    def test_policies(self):
        """Test policies endpoint"""
        success, response = self.run_test("Get Policies", "GET", "policies", 200, use_session=False)
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} policies")
            if len(response) > 0:
                first_policy = response[0]
                expected_fields = ['vault_id', 'title', 'category', 'summary', 'risk_category', 'source_link']
                missing_fields = [field for field in expected_fields if field not in first_policy]
                if missing_fields:
                    print(f"⚠️  Missing fields in policy: {missing_fields}")
                else:
                    print(f"✅ Policy structure is correct")
                    print(f"   First policy: {first_policy.get('title')} (Risk: {first_policy.get('risk_category')})")
        return success, response

    def test_logout(self):
        """Test user logout"""
        return self.run_test("User Logout", "POST", "auth/logout", 200)

def main():
    print("🚀 Starting ACE API Testing...")
    print("=" * 50)
    
    tester = ACEAPITester()
    
    # Run all tests in order (authentication flow first)
    tests = [
        tester.test_root_endpoint,
        tester.test_policies,  # Public endpoint
        tester.test_profile_options,  # Public endpoint
        tester.test_signup,
        tester.test_login,
        tester.test_get_me,
        tester.test_update_profile,
        tester.test_student_intelligence,
        tester.test_get_chats,
        tester.test_chat_send,  # This one might take longer due to AI processing
        tester.test_logout,
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