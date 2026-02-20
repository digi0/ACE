from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import httpx
import uuid
import bcrypt
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Load policy vault
with open(ROOT_DIR / 'ace_vault.json', 'r') as f:
    ace_vault = json.load(f)

# Create the main app
app = FastAPI()

# Create routers
api_router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class UserProfile(BaseModel):
    campus: str
    major: str
    academic_level: str
    credit_load: str
    financial_aid_status: str
    international_student: bool
    expected_graduation: str
    current_semester: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    profile_complete: bool = False
    profile: Optional[UserProfile] = None
    is_admin: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdate(BaseModel):
    campus: str
    major: str
    academic_level: str
    credit_load: str
    financial_aid_status: str
    international_student: bool
    expected_graduation: str
    current_semester: str

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    structured_response: Optional[dict] = None

class ChatSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    messages: List[dict] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SendMessageRequest(BaseModel):
    chat_id: Optional[str] = None
    message: str

class PolicyUpdate(BaseModel):
    vault_id: str
    title: str
    summary: str
    category: str
    tags: List[str]
    risk_category: str
    content: str
    source_link: str

# ==================== AUTH HELPERS ====================

async def get_current_user(request: Request) -> User:
    """Extract and validate user from session token"""
    # Check cookie first, then Authorization header
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    return User(**user_doc)

async def get_admin_user(request: Request) -> User:
    """Get current user and verify admin status"""
    user = await get_current_user(request)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/signup")
async def signup(data: UserSignup, request: Request, response: Response):
    """Email/password signup"""
    # Check if user exists
    existing = await db.users.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user_doc = {
        "user_id": user_id,
        "email": data.email,
        "name": data.name,
        "password_hash": hash_password(data.password),
        "picture": None,
        "profile_complete": False,
        "profile": None,
        "is_admin": False,
        "auth_provider": "email",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    # Create session
    session_token = f"session_{uuid.uuid4().hex}"
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie - use secure settings for production URLs
    is_secure = "localhost" not in str(request.url) and "127.0.0.1" not in str(request.url)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=is_secure,
        samesite="lax" if not is_secure else "none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    return {
        "user_id": user_id,
        "email": data.email,
        "name": data.name,
        "profile_complete": False
    }

@api_router.post("/auth/login")
async def login(data: UserLogin, request: Request, response: Response):
    """Email/password login"""
    user_doc = await db.users.find_one({"email": data.email}, {"_id": 0})
    
    if not user_doc or "password_hash" not in user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(data.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create session
    session_token = f"session_{uuid.uuid4().hex}"
    session_doc = {
        "user_id": user_doc["user_id"],
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    is_secure = "localhost" not in str(request.url) and "127.0.0.1" not in str(request.url)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=is_secure,
        samesite="lax" if not is_secure else "none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    return {
        "user_id": user_doc["user_id"],
        "email": user_doc["email"],
        "name": user_doc["name"],
        "profile_complete": user_doc.get("profile_complete", False),
        "is_admin": user_doc.get("is_admin", False)
    }

@api_router.post("/auth/session")
async def process_oauth_session(request: Request, response: Response):
    """Process Google OAuth session from Emergent Auth"""
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # Exchange session_id for user data
    async with httpx.AsyncClient() as client:
        auth_response = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
    
    if auth_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    auth_data = auth_response.json()
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": auth_data["email"]}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": auth_data["name"],
                "picture": auth_data.get("picture")
            }}
        )
        profile_complete = existing_user.get("profile_complete", False)
        is_admin = existing_user.get("is_admin", False)
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "email": auth_data["email"],
            "name": auth_data["name"],
            "picture": auth_data.get("picture"),
            "profile_complete": False,
            "profile": None,
            "is_admin": False,
            "auth_provider": "google",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc)
        profile_complete = False
        is_admin = False
    
    # Create session
    session_token = f"session_{uuid.uuid4().hex}"
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    is_secure = "localhost" not in str(request.url) and "127.0.0.1" not in str(request.url)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=is_secure,
        samesite="lax" if not is_secure else "none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    return {
        "user_id": user_id,
        "email": auth_data["email"],
        "name": auth_data["name"],
        "picture": auth_data.get("picture"),
        "profile_complete": profile_complete,
        "is_admin": is_admin
    }

@api_router.get("/auth/me")
async def get_me(request: Request):
    """Get current authenticated user"""
    user = await get_current_user(request)
    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "profile_complete": user.profile_complete,
        "profile": user.profile.model_dump() if user.profile else None,
        "is_admin": user.is_admin
    }

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out"}

# ==================== USER PROFILE ROUTES ====================

@api_router.get("/user/profile")
async def get_user_profile(request: Request):
    """Get user profile"""
    user = await get_current_user(request)
    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "profile_complete": user.profile_complete,
        "profile": user.profile.model_dump() if user.profile else None
    }

@api_router.post("/user/profile")
async def update_user_profile(data: ProfileUpdate, request: Request):
    """Update user profile (onboarding)"""
    user = await get_current_user(request)
    
    profile_dict = data.model_dump()
    
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {
            "profile": profile_dict,
            "profile_complete": True
        }}
    )
    
    return {
        "message": "Profile updated",
        "profile_complete": True,
        "profile": profile_dict
    }

@api_router.get("/user/profile-options")
async def get_profile_options():
    """Get options for profile fields"""
    return {
        "campuses": ace_vault["campuses"],
        "academic_levels": ace_vault["academic_levels"],
        "credit_loads": ace_vault["credit_loads"],
        "financial_aid_statuses": ace_vault["financial_aid_statuses"]
    }

# ==================== INTELLIGENCE ROUTES ====================

@api_router.get("/student/intelligence")
async def get_student_intelligence(request: Request):
    """Get adaptive intelligence/status for student"""
    user = await get_current_user(request)
    
    if not user.profile_complete or not user.profile:
        return {
            "context": {"term": "Unknown", "level": "Unknown", "status": "Unknown"},
            "insight": "Complete your profile to receive personalized insights.",
            "urgency": "low",
            "action": None
        }
    
    from datetime import date
    profile = user.profile
    
    context = {
        "term": profile.current_semester,
        "level": profile.academic_level.split(" ")[0],
        "status": profile.credit_load.split(" ")[0]
    }
    
    # Calculate days until withdrawal deadline
    today = date.today()
    withdrawal_deadline = date(2026, 4, 3)
    days_until_withdrawal = (withdrawal_deadline - today).days
    
    insight = None
    action = None
    urgency = "low"
    
    # Check for high-risk situations
    if profile.international_student:
        urgency = "medium"
        insight = "As an international student, any enrollment changes require prior approval from Global Programs."
        action = {
            "label": "Check requirements",
            "prompt": "What do I need to know as an international student about enrollment changes?"
        }
    elif days_until_withdrawal <= 7 and days_until_withdrawal > 0:
        urgency = "high"
        insight = f"Withdrawal deadline is in {days_until_withdrawal} day{'s' if days_until_withdrawal != 1 else ''}. Act now if considering dropping a course."
        action = {
            "label": "Ask about withdrawal",
            "prompt": "I need to understand my options for withdrawing from a course before the deadline."
        }
    elif days_until_withdrawal <= 21 and days_until_withdrawal > 7:
        urgency = "medium"
        insight = f"The course withdrawal deadline is April 3rd — {days_until_withdrawal} days away."
        action = {
            "label": "Review options",
            "prompt": "What should I consider before the withdrawal deadline on April 3rd?"
        }
    elif "aid" in profile.financial_aid_status.lower() and "receiving" in profile.financial_aid_status.lower():
        urgency = "low"
        insight = "Remember: Enrollment changes may affect your financial aid. Check before making changes."
        action = {
            "label": "Learn more",
            "prompt": "How do enrollment changes affect my financial aid?"
        }
    else:
        insight = f"You're on track for {profile.current_semester}. No urgent items right now."
        action = None
    
    return {
        "context": context,
        "insight": insight,
        "urgency": urgency,
        "action": action
    }

# ==================== CHAT ROUTES ====================

# Risk triggers for classification
RISK_TRIGGERS = {
    "high": ["withdrawal", "dismiss", "probation", "financial aid", "visa", "international", 
             "status change", "deadline missed", "enrollment status", "expelled", "suspended",
             "immigration", "F-1", "distress", "failing", "academic warning"],
    "medium": ["deadline", "grade concern", "registration", "graduation", "leave of absence", 
               "appeal", "overload", "prerequisite", "hold"],
    "low": ["general", "information", "planning", "advising", "schedule", "course", "major"]
}

def classify_risk(message: str, response_content: str) -> tuple:
    """Classify risk level based on message content and response"""
    combined = (message + " " + response_content).lower()
    
    # Check for high risk triggers
    for trigger in RISK_TRIGGERS["high"]:
        if trigger in combined:
            return "high", True
    
    # Check for medium risk triggers
    for trigger in RISK_TRIGGERS["medium"]:
        if trigger in combined:
            return "medium", False
    
    return "low", False

# Updated system prompt
ACE_SYSTEM_PROMPT = """You are ACE, a Penn State–focused academic decision-support assistant.
You provide structured, policy-grounded guidance to PSU students in a tone that is friendly but academic.
You are not an official PSU advising office.
You do not make final decisions.
You explain options, consequences, and next steps clearly.

IMPORTANT: You MUST respond in valid JSON format with this exact structure:
{
  "direct_answer": "Clear, structured, calm explanation addressing the student's question",
  "next_steps": ["Step 1", "Step 2", "Step 3"],
  "sources_used": [
    {"vault_id": "PSU-XXX-001", "title": "Policy Title", "link": "https://..."}
  ],
  "risk_level": "low|medium|high",
  "advisor_needed": true|false,
  "clarifying_question": null
}

If information is missing, ask no more than two clarifying questions before advising. Set clarifying_question to your question if needed.

If the issue involves:
- missed deadlines
- enrollment status change
- financial aid impact
- international student implications
- academic warning, probation, or dismissal
You MUST set advisor_needed to true and recommend advisor confirmation.

Always incorporate the student's stored profile context when relevant.

Tone:
- Professional but approachable
- No slang
- No emojis
- No dramatic language
- No over-reassurance
- No authoritative commands

If uncertain, state uncertainty clearly and recommend verification.

AVAILABLE POLICY DATA:
"""

def get_system_prompt_with_policies():
    """Get system prompt with current policies"""
    policies_summary = []
    for p in ace_vault["policies"]:
        policies_summary.append({
            "vault_id": p["vault_id"],
            "title": p["title"],
            "summary": p["summary"],
            "category": p["category"],
            "risk_category": p["risk_category"],
            "source_link": p["source_link"],
            "last_reviewed": p["last_reviewed"]
        })
    return ACE_SYSTEM_PROMPT + json.dumps(policies_summary, indent=2)

def get_user_context(user: User) -> str:
    """Generate user context string for AI"""
    if not user.profile_complete or not user.profile:
        return "Student profile not yet completed."
    
    p = user.profile
    context = f"""
STUDENT PROFILE CONTEXT:
- Name: {user.name}
- Campus: {p.campus}
- Major: {p.major}
- Academic Level: {p.academic_level}
- Credit Load: {p.credit_load}
- Financial Aid Status: {p.financial_aid_status}
- International Student: {"Yes" if p.international_student else "No"}
- Expected Graduation: {p.expected_graduation}
- Current Semester: {p.current_semester}
"""
    return context

def generate_chat_title(message: str) -> str:
    """Generate a short title from the first message"""
    words = message.split()[:6]
    title = ' '.join(words)
    if len(message.split()) > 6:
        title += '...'
    return title

async def get_ai_response(message: str, chat_history: List[dict], user: User) -> dict:
    """Get structured response from AI with user context"""
    try:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            raise ValueError("EMERGENT_LLM_KEY not configured")
        
        # Build system prompt with user context
        system_prompt = get_system_prompt_with_policies()
        user_context = get_user_context(user)
        full_system_prompt = system_prompt + "\n\n" + user_context
        
        chat = LlmChat(
            api_key=api_key,
            session_id=str(uuid.uuid4()),
            system_message=full_system_prompt
        ).with_model("openai", "gpt-5.2")
        
        # Build context from history (last 10 messages)
        context = ""
        for msg in chat_history[-10:]:
            role = "Student" if msg['role'] == 'user' else "ACE"
            context += f"{role}: {msg['content']}\n"
        
        full_message = f"{context}\nStudent: {message}\n\nRespond in the exact JSON format specified."
        
        user_message = UserMessage(text=full_message)
        response = await chat.send_message(user_message)
        
        # Parse JSON response
        try:
            response_text = response.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            parsed = json.loads(response_text.strip())
            
            # Apply risk classification override if needed
            detected_risk, advisor_needed = classify_risk(message, parsed.get("direct_answer", ""))
            if detected_risk == "high":
                parsed["risk_level"] = "high"
                parsed["advisor_needed"] = True
            elif detected_risk == "medium" and parsed.get("risk_level") == "low":
                parsed["risk_level"] = "medium"
            
            return parsed
        except json.JSONDecodeError:
            return {
                "direct_answer": response,
                "next_steps": [],
                "sources_used": [],
                "risk_level": "low",
                "advisor_needed": False,
                "clarifying_question": None
            }
    except Exception as e:
        logger.error(f"AI response error: {e}")
        return {
            "direct_answer": "I apologize, but I'm having trouble processing your request right now. Please try again or contact your academic advisor directly.",
            "next_steps": ["Try rephrasing your question", "Contact your advisor at advising@psu.edu"],
            "sources_used": [{"vault_id": "PSU-ADV-001", "title": "Academic Advising Services", "link": "https://advising.psu.edu/"}],
            "risk_level": "low",
            "advisor_needed": False,
            "clarifying_question": None
        }

@api_router.get("/chats")
async def get_chat_sessions(request: Request):
    """Get all chat sessions for current user"""
    user = await get_current_user(request)
    
    sessions = await db.chat_sessions.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(100)
    
    return sessions

@api_router.get("/chat/{chat_id}")
async def get_chat_session(chat_id: str, request: Request):
    """Get a specific chat session"""
    user = await get_current_user(request)
    
    session = await db.chat_sessions.find_one(
        {"id": chat_id, "user_id": user.user_id},
        {"_id": 0}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session

@api_router.post("/chat/send")
async def send_message(data: SendMessageRequest, request: Request):
    """Send a message and get AI response"""
    user = await get_current_user(request)
    
    if not user.profile_complete:
        raise HTTPException(status_code=400, detail="Please complete your profile first")
    
    chat_id = data.chat_id
    
    if chat_id:
        session = await db.chat_sessions.find_one(
            {"id": chat_id, "user_id": user.user_id},
            {"_id": 0}
        )
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        messages = session.get('messages', [])
    else:
        chat_id = str(uuid.uuid4())
        messages = []
        title = generate_chat_title(data.message)
        new_session = {
            "id": chat_id,
            "user_id": user.user_id,
            "title": title,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_sessions.insert_one(new_session)
    
    # Add user message
    user_msg = {
        "role": "user",
        "content": data.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    messages.append(user_msg)
    
    # Get AI response with user context
    ai_response = await get_ai_response(data.message, messages, user)
    
    # Add assistant message
    assistant_msg = {
        "role": "assistant",
        "content": ai_response.get('direct_answer', ''),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "structured_response": ai_response
    }
    messages.append(assistant_msg)
    
    # Update chat session
    await db.chat_sessions.update_one(
        {"id": chat_id},
        {"$set": {
            "messages": messages,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"chat_id": chat_id, "response": ai_response}

@api_router.delete("/chat/{chat_id}")
async def delete_chat_session(chat_id: str, request: Request):
    """Delete a chat session"""
    user = await get_current_user(request)
    
    result = await db.chat_sessions.delete_one(
        {"id": chat_id, "user_id": user.user_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"status": "deleted"}

# ==================== POLICY ROUTES ====================

@api_router.get("/policies")
async def get_policies():
    """Get all policies from the vault"""
    return ace_vault['policies']

# ==================== ADMIN ROUTES ====================

@admin_router.get("/policies")
async def admin_get_policies(request: Request):
    """Get all policies for admin"""
    await get_admin_user(request)
    return ace_vault['policies']

@admin_router.put("/policies/{vault_id}")
async def admin_update_policy(vault_id: str, data: PolicyUpdate, request: Request):
    """Update a policy entry"""
    await get_admin_user(request)
    
    # Find and update policy in vault
    for i, policy in enumerate(ace_vault['policies']):
        if policy['vault_id'] == vault_id:
            ace_vault['policies'][i].update({
                "title": data.title,
                "summary": data.summary,
                "category": data.category,
                "tags": data.tags,
                "risk_category": data.risk_category,
                "content": data.content,
                "source_link": data.source_link,
                "last_reviewed": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            })
            
            # Save to file
            with open(ROOT_DIR / 'ace_vault.json', 'w') as f:
                json.dump(ace_vault, f, indent=2)
            
            return {"message": "Policy updated", "policy": ace_vault['policies'][i]}
    
    raise HTTPException(status_code=404, detail="Policy not found")

@admin_router.post("/policies")
async def admin_add_policy(data: PolicyUpdate, request: Request):
    """Add a new policy entry"""
    await get_admin_user(request)
    
    # Check if vault_id exists
    for policy in ace_vault['policies']:
        if policy['vault_id'] == data.vault_id:
            raise HTTPException(status_code=400, detail="Policy with this vault_id already exists")
    
    new_policy = {
        "vault_id": data.vault_id,
        "title": data.title,
        "summary": data.summary,
        "category": data.category,
        "tags": data.tags,
        "risk_category": data.risk_category,
        "content": data.content,
        "source_link": data.source_link,
        "last_reviewed": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    }
    
    ace_vault['policies'].append(new_policy)
    
    # Save to file
    with open(ROOT_DIR / 'ace_vault.json', 'w') as f:
        json.dump(ace_vault, f, indent=2)
    
    return {"message": "Policy added", "policy": new_policy}

@admin_router.delete("/policies/{vault_id}")
async def admin_delete_policy(vault_id: str, request: Request):
    """Delete a policy entry"""
    await get_admin_user(request)
    
    for i, policy in enumerate(ace_vault['policies']):
        if policy['vault_id'] == vault_id:
            deleted = ace_vault['policies'].pop(i)
            
            # Save to file
            with open(ROOT_DIR / 'ace_vault.json', 'w') as f:
                json.dump(ace_vault, f, indent=2)
            
            return {"message": "Policy deleted", "vault_id": vault_id}
    
    raise HTTPException(status_code=404, detail="Policy not found")

@admin_router.post("/make-admin/{user_id}")
async def make_admin(user_id: str, request: Request):
    """Make a user an admin (super admin only)"""
    admin = await get_admin_user(request)
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"is_admin": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User {user_id} is now an admin"}

# ==================== GENERAL ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "ACE API is running"}

# Include routers
app.include_router(api_router)
app.include_router(admin_router)

# Get allowed origins
cors_origins_str = os.environ.get('CORS_ORIGINS', 'http://localhost:3000')
allowed_origins = [origin.strip() for origin in cors_origins_str.split(',')]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
