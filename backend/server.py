from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
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

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    structured_response: Optional[dict] = None

class ChatSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    title: str
    messages: List[dict] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SendMessageRequest(BaseModel):
    chat_id: Optional[str] = None
    message: str
    student_id: str

class SendMessageResponse(BaseModel):
    chat_id: str
    response: dict

# ACE System Prompt
ACE_SYSTEM_PROMPT = """You are ACE (Academic Clarity Engine), a personalized academic advisor assistant for Penn State University students. You provide calm, confident, and structured guidance on academic matters.

IMPORTANT RESPONSE FORMAT:
You MUST respond in valid JSON format with this exact structure:
{
  "direct_answer": "A short, calm, confidence-building response that directly addresses the student's question or concern",
  "next_steps": ["Step 1", "Step 2", "Step 3"],
  "sources_used": [
    {"vault_id": "PSU-XXX-001", "title": "Policy Title", "link": "https://..."}
  ],
  "risk_level": "low|medium|high",
  "advisor_needed": true|false,
  "clarifying_question": null
}

BEHAVIOR RULES:
1. Prefer understanding before answering - if intent is unclear, set clarifying_question to a single question
2. Treat policies as constraints, not commands
3. Never claim authority to perform official actions
4. Escalate clearly when risk is high (set advisor_needed: true)
5. Be helpful beyond predefined categories
6. Reference specific policies from the vault when applicable

AVAILABLE POLICY DATA:
""" + json.dumps(ace_vault['policies'], indent=2) + """

When referencing policies, use the exact vault_id, title, and link from the data above.

RISK ASSESSMENT:
- low: General questions, planning, informational queries
- medium: Deadlines within 1-2 weeks, grade concerns, course changes
- high: Immediate deadlines, academic standing issues, financial aid impact

Set advisor_needed to true for: academic probation, dismissal appeals, complex financial aid, degree audit discrepancies, or when student expresses significant stress.

Remember: You are a companion, not a gatekeeper. Be warm but professional."""

def generate_chat_title(message: str) -> str:
    """Generate a short title from the first message"""
    words = message.split()[:6]
    title = ' '.join(words)
    if len(message.split()) > 6:
        title += '...'
    return title

async def get_ai_response(message: str, chat_history: List[dict]) -> dict:
    """Get structured response from AI"""
    try:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            raise ValueError("EMERGENT_LLM_KEY not configured")
        
        chat = LlmChat(
            api_key=api_key,
            session_id=str(uuid.uuid4()),
            system_message=ACE_SYSTEM_PROMPT
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
            # Clean up response if needed
            response_text = response.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            parsed = json.loads(response_text.strip())
            return parsed
        except json.JSONDecodeError:
            # Fallback structure if JSON parsing fails
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

# Routes
@api_router.get("/")
async def root():
    return {"message": "ACE API is running"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks

@api_router.get("/student/profile")
async def get_student_profile():
    """Get mocked student profile"""
    return ace_vault['student_mock']

@api_router.get("/student/intelligence")
async def get_student_intelligence():
    """Get adaptive intelligence/status for student - single calm insight"""
    from datetime import date
    
    student = ace_vault['student_mock']
    policies = ace_vault['policies']
    
    # Get calendar policy for deadline calculations
    calendar = next((p for p in policies if p['vault_id'] == 'PSU-CAL-001'), None)
    
    # Context line data
    context = {
        "term": "Spring 2026",
        "level": student['year'],
        "status": student['enrollment_status']
    }
    
    # Calculate days until withdrawal deadline
    today = date.today()
    withdrawal_deadline = date(2026, 4, 3)
    days_until_withdrawal = (withdrawal_deadline - today).days
    
    # Determine single insight based on priority
    insight = None
    action = None
    urgency = "low"
    
    if days_until_withdrawal <= 7 and days_until_withdrawal > 0:
        # Urgent deadline
        urgency = "high"
        insight = f"Withdrawal deadline is in {days_until_withdrawal} day{'s' if days_until_withdrawal != 1 else ''}. Act now if you're considering dropping a course."
        action = {
            "label": "Ask about withdrawal",
            "prompt": "I need to understand my options for withdrawing from a course before the deadline."
        }
    elif days_until_withdrawal <= 21 and days_until_withdrawal > 7:
        # Approaching deadline
        urgency = "medium"
        insight = f"The course withdrawal deadline is April 3rd — {days_until_withdrawal} days away."
        action = {
            "label": "Review my options",
            "prompt": "What should I consider before the withdrawal deadline on April 3rd?"
        }
    elif student['gpa'] >= 3.5:
        # Reassurance for strong students
        urgency = "low"
        insight = f"You're doing well with a {student['gpa']} GPA. Stay on track this semester."
        action = None
    elif student['credits_completed'] >= 60 and student['credits_completed'] < 90:
        # Junior-year planning
        urgency = "low"
        insight = "As a junior, now is a good time to map out your remaining requirements."
        action = {
            "label": "Plan ahead",
            "prompt": "Help me plan my remaining semesters to graduate on time."
        }
    else:
        # Default calm reassurance
        urgency = "low"
        insight = "No urgent items right now. You're on track for Spring 2026."
        action = None
    
    return {
        "context": context,
        "insight": insight,
        "urgency": urgency,
        "action": action
    }

@api_router.get("/chats/{student_id}")
async def get_chat_sessions(student_id: str):
    """Get all chat sessions for a student"""
    sessions = await db.chat_sessions.find(
        {"student_id": student_id},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(100)
    
    for session in sessions:
        if isinstance(session.get('created_at'), str):
            session['created_at'] = datetime.fromisoformat(session['created_at'])
        if isinstance(session.get('updated_at'), str):
            session['updated_at'] = datetime.fromisoformat(session['updated_at'])
    
    return sessions

@api_router.get("/chat/{chat_id}")
async def get_chat_session(chat_id: str):
    """Get a specific chat session"""
    session = await db.chat_sessions.find_one(
        {"id": chat_id},
        {"_id": 0}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session

@api_router.post("/chat/send", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """Send a message and get AI response"""
    chat_id = request.chat_id
    
    if chat_id:
        # Get existing chat
        session = await db.chat_sessions.find_one({"id": chat_id}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        messages = session.get('messages', [])
    else:
        # Create new chat
        chat_id = str(uuid.uuid4())
        messages = []
        title = generate_chat_title(request.message)
        new_session = {
            "id": chat_id,
            "student_id": request.student_id,
            "title": title,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_sessions.insert_one(new_session)
    
    # Add user message
    user_msg = {
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    messages.append(user_msg)
    
    # Get AI response
    ai_response = await get_ai_response(request.message, messages)
    
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
        {
            "$set": {
                "messages": messages,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return SendMessageResponse(chat_id=chat_id, response=ai_response)

@api_router.delete("/chat/{chat_id}")
async def delete_chat_session(chat_id: str):
    """Delete a chat session"""
    result = await db.chat_sessions.delete_one({"id": chat_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"status": "deleted"}

@api_router.get("/policies")
async def get_policies():
    """Get all policies from the vault"""
    return ace_vault['policies']

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
