"""
ACE (Academic Clarity Engine) - Backend API Tests
Tests authentication, profile management, and chat functionality
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials
TEST_EMAIL = f"test_user_{uuid.uuid4().hex[:8]}@psu.edu"
TEST_PASSWORD = "testpass123"
TEST_NAME = "Test User ACE"

class TestHealthAndBasicEndpoints:
    """Test basic API health and public endpoints"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "ACE API is running" in data["message"]
        print(f"SUCCESS: API root returns: {data}")
    
    def test_profile_options(self):
        """Test profile options endpoint (public)"""
        response = requests.get(f"{BASE_URL}/api/user/profile-options")
        assert response.status_code == 200
        data = response.json()
        assert "campuses" in data
        assert "academic_levels" in data
        assert "credit_loads" in data
        assert "financial_aid_statuses" in data
        assert len(data["campuses"]) > 0
        print(f"SUCCESS: Profile options - {len(data['campuses'])} campuses, {len(data['academic_levels'])} levels")
    
    def test_policies_endpoint(self):
        """Test policies endpoint (public)"""
        response = requests.get(f"{BASE_URL}/api/policies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check policy structure
        policy = data[0]
        assert "vault_id" in policy
        assert "title" in policy
        assert "summary" in policy
        print(f"SUCCESS: Policies endpoint returns {len(data)} policies")


class TestSignupFlow:
    """Test user signup flow"""
    
    def test_signup_new_user(self):
        """Test creating a new user via signup"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        }
        response = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        
        # Should return 200 for successful signup
        assert response.status_code == 200, f"Signup failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "user_id" in data
        assert "email" in data
        assert "name" in data
        assert "session_token" in data
        assert "profile_complete" in data
        
        # Verify values
        assert data["email"] == TEST_EMAIL
        assert data["name"] == TEST_NAME
        assert data["profile_complete"] == False
        assert data["session_token"].startswith("session_")
        
        print(f"SUCCESS: Signup created user {data['user_id']} with session token")
        
        # Store for later tests
        pytest.signup_session_token = data["session_token"]
        pytest.signup_user_id = data["user_id"]
    
    def test_signup_duplicate_email(self):
        """Test signup with duplicate email fails"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        }
        response = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        
        # Should return 400 for duplicate email
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "already registered" in data["detail"].lower()
        print(f"SUCCESS: Duplicate email correctly rejected")


class TestLoginFlow:
    """Test user login flow"""
    
    def test_login_valid_credentials(self):
        """Test login with valid credentials"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "user_id" in data
        assert "email" in data
        assert "name" in data
        assert "session_token" in data
        assert "profile_complete" in data
        
        # Verify values
        assert data["email"] == TEST_EMAIL
        assert data["session_token"].startswith("session_")
        
        print(f"SUCCESS: Login successful, session token received")
        
        # Store for later tests
        pytest.login_session_token = data["session_token"]
    
    def test_login_invalid_password(self):
        """Test login with invalid password"""
        payload = {
            "email": TEST_EMAIL,
            "password": "wrongpassword"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        print(f"SUCCESS: Invalid password correctly rejected")
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent user"""
        payload = {
            "email": "nonexistent@psu.edu",
            "password": "anypassword"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code == 401
        print(f"SUCCESS: Non-existent user correctly rejected")


class TestBearerTokenAuth:
    """Test Bearer token authentication"""
    
    def test_auth_me_with_bearer_token(self):
        """Test /auth/me with Bearer token"""
        token = getattr(pytest, 'login_session_token', None)
        if not token:
            pytest.skip("No session token available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        data = response.json()
        
        assert "user_id" in data
        assert "email" in data
        assert "name" in data
        assert "profile_complete" in data
        assert data["email"] == TEST_EMAIL
        
        print(f"SUCCESS: Bearer token auth works for /auth/me")
    
    def test_auth_me_without_token(self):
        """Test /auth/me without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 401
        print(f"SUCCESS: Unauthenticated request correctly rejected")
    
    def test_auth_me_with_invalid_token(self):
        """Test /auth/me with invalid token returns 401"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 401
        print(f"SUCCESS: Invalid token correctly rejected")


class TestProfileManagement:
    """Test user profile management (onboarding)"""
    
    def test_get_profile_before_completion(self):
        """Test getting profile before completion"""
        token = getattr(pytest, 'login_session_token', None)
        if not token:
            pytest.skip("No session token available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/user/profile", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["profile_complete"] == False
        print(f"SUCCESS: Profile shows incomplete before onboarding")
    
    def test_update_profile(self):
        """Test updating user profile (onboarding)"""
        token = getattr(pytest, 'login_session_token', None)
        if not token:
            pytest.skip("No session token available")
        
        headers = {"Authorization": f"Bearer {token}"}
        profile_data = {
            "campus": "University Park",
            "major": "Computer Science",
            "academic_level": "Junior (60-89 credits)",
            "credit_load": "Full-time (12-18 credits)",
            "financial_aid_status": "Receiving aid",
            "international_student": False,
            "expected_graduation": "Spring 2027",
            "current_semester": "Spring 2026"
        }
        
        response = requests.post(f"{BASE_URL}/api/user/profile", json=profile_data, headers=headers)
        
        assert response.status_code == 200, f"Profile update failed: {response.text}"
        data = response.json()
        
        assert data["profile_complete"] == True
        assert "profile" in data
        assert data["profile"]["campus"] == "University Park"
        assert data["profile"]["major"] == "Computer Science"
        
        print(f"SUCCESS: Profile updated successfully")
    
    def test_get_profile_after_completion(self):
        """Test getting profile after completion"""
        token = getattr(pytest, 'login_session_token', None)
        if not token:
            pytest.skip("No session token available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/user/profile", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["profile_complete"] == True
        assert data["profile"]["campus"] == "University Park"
        print(f"SUCCESS: Profile shows complete after onboarding")


class TestStudentIntelligence:
    """Test student intelligence/insights endpoint"""
    
    def test_get_intelligence(self):
        """Test getting student intelligence"""
        token = getattr(pytest, 'login_session_token', None)
        if not token:
            pytest.skip("No session token available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/student/intelligence", headers=headers)
        
        assert response.status_code == 200, f"Intelligence failed: {response.text}"
        data = response.json()
        
        assert "context" in data
        assert "insight" in data
        assert "urgency" in data
        
        print(f"SUCCESS: Intelligence endpoint returns insight: {data['insight'][:50]}...")


class TestChatFunctionality:
    """Test chat functionality with AI"""
    
    def test_get_chats_empty(self):
        """Test getting chat sessions (initially empty)"""
        token = getattr(pytest, 'login_session_token', None)
        if not token:
            pytest.skip("No session token available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/chats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Chats endpoint returns {len(data)} sessions")
    
    def test_send_message_new_chat(self):
        """Test sending a message to create new chat"""
        token = getattr(pytest, 'login_session_token', None)
        if not token:
            pytest.skip("No session token available")
        
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "message": "What are the requirements for changing my major?"
        }
        
        response = requests.post(f"{BASE_URL}/api/chat/send", json=payload, headers=headers, timeout=60)
        
        assert response.status_code == 200, f"Chat send failed: {response.text}"
        data = response.json()
        
        assert "chat_id" in data
        assert "response" in data
        
        # Check AI response structure
        ai_response = data["response"]
        assert "direct_answer" in ai_response
        assert "next_steps" in ai_response
        assert "risk_level" in ai_response
        
        print(f"SUCCESS: Chat created with ID {data['chat_id']}")
        print(f"AI Response: {ai_response['direct_answer'][:100]}...")
        
        pytest.chat_id = data["chat_id"]
    
    def test_get_chat_session(self):
        """Test getting a specific chat session"""
        token = getattr(pytest, 'login_session_token', None)
        chat_id = getattr(pytest, 'chat_id', None)
        if not token or not chat_id:
            pytest.skip("No session token or chat_id available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/chat/{chat_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == chat_id
        assert "messages" in data
        assert len(data["messages"]) >= 2  # User message + AI response
        
        print(f"SUCCESS: Chat session retrieved with {len(data['messages'])} messages")
    
    def test_send_followup_message(self):
        """Test sending a follow-up message to existing chat"""
        token = getattr(pytest, 'login_session_token', None)
        chat_id = getattr(pytest, 'chat_id', None)
        if not token or not chat_id:
            pytest.skip("No session token or chat_id available")
        
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "chat_id": chat_id,
            "message": "What forms do I need to fill out?"
        }
        
        response = requests.post(f"{BASE_URL}/api/chat/send", json=payload, headers=headers, timeout=60)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["chat_id"] == chat_id
        assert "response" in data
        
        print(f"SUCCESS: Follow-up message sent to chat {chat_id}")
    
    def test_delete_chat_session(self):
        """Test deleting a chat session"""
        token = getattr(pytest, 'login_session_token', None)
        chat_id = getattr(pytest, 'chat_id', None)
        if not token or not chat_id:
            pytest.skip("No session token or chat_id available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.delete(f"{BASE_URL}/api/chat/{chat_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        
        print(f"SUCCESS: Chat session {chat_id} deleted")
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/api/chat/{chat_id}", headers=headers)
        assert response.status_code == 404


class TestLogout:
    """Test logout functionality"""
    
    def test_logout(self):
        """Test logout endpoint"""
        token = getattr(pytest, 'login_session_token', None)
        if not token:
            pytest.skip("No session token available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        print(f"SUCCESS: Logout successful")


class TestProtectedRoutes:
    """Test that protected routes require authentication"""
    
    def test_profile_requires_auth(self):
        """Test /user/profile requires authentication"""
        response = requests.get(f"{BASE_URL}/api/user/profile")
        assert response.status_code == 401
        print(f"SUCCESS: /user/profile requires auth")
    
    def test_chats_requires_auth(self):
        """Test /chats requires authentication"""
        response = requests.get(f"{BASE_URL}/api/chats")
        assert response.status_code == 401
        print(f"SUCCESS: /chats requires auth")
    
    def test_chat_send_requires_auth(self):
        """Test /chat/send requires authentication"""
        response = requests.post(f"{BASE_URL}/api/chat/send", json={"message": "test"})
        assert response.status_code == 401
        print(f"SUCCESS: /chat/send requires auth")
    
    def test_intelligence_requires_auth(self):
        """Test /student/intelligence requires authentication"""
        response = requests.get(f"{BASE_URL}/api/student/intelligence")
        assert response.status_code == 401
        print(f"SUCCESS: /student/intelligence requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
