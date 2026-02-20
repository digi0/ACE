# ACE (Academic Clarity Engine) - PRD

## Original Problem Statement
Build a desktop-first web application called ACE for Penn State students only. ACE is a personalized, conversation-first academic advisor assistant that helps students navigate urgent academic situations, long-term planning, and university policies. It should feel like a persistent academic companion (Jarvis-style), not a generic chatbot.

## User Personas
- **Primary**: Penn State undergraduate/graduate students seeking academic guidance
- **Use Cases**: Course withdrawal questions, deadline inquiries, academic planning, policy clarification

## Core Requirements

### Phase 1 (Initial Build - Completed)
1. ✅ Two-column desktop layout (320px left sidebar + fluid right workspace)
2. ✅ AI-powered conversational assistant using OpenAI GPT-5.2
3. ✅ Structured responses (direct answer, next steps, sources, risk indicator)
4. ✅ Student profile display
5. ✅ Intelligence card with adaptive notifications
6. ✅ Chat history persistence in MongoDB
7. ✅ Quick-access conversation starters
8. ✅ Policy vault with PSU academic policies
9. ✅ Penn State branding (navy blue accents)

### Phase 2 (Dynamic Features - Completed)
1. ✅ Dynamic Intelligence Card with context line, primary insight, action button
2. ✅ Quick Access Panel with customizable tools (up to 3)
3. ✅ Collapsible left sidebar with toggle button
4. ✅ Mobile responsive layout

### Phase 3 (Authentication & Core Logic - Completed)
1. ✅ Email/password authentication with bcrypt hashing
2. ✅ Google OAuth via Emergent-managed auth
3. ✅ Bearer token authentication (localStorage + axios interceptors)
4. ✅ Multi-step onboarding wizard (Campus/Major, Academic Standing, Additional Info)
5. ✅ Profile completion check and route protection
6. ✅ User profile context passed to AI in every conversation
7. ✅ Risk classification layer (Low/Medium/High based on triggers)
8. ✅ Updated AI system prompt with tone guidelines
9. ✅ Admin interface for policy vault management (scaffolded)

## What's Been Implemented (Feb 20, 2026)

### Backend (FastAPI + MongoDB)
- User authentication (email/password + Google OAuth)
- Session management with Bearer tokens
- User profile storage and onboarding
- AI chat with GPT-5.2 via Emergent LLM key
- Risk classification for AI responses
- Policy vault with CRUD operations
- Admin endpoints for policy management

### Frontend (React + Tailwind CSS + Shadcn UI)
- Login/Signup pages with form validation
- Google OAuth callback handler
- 3-step onboarding wizard
- Main assistant with collapsible sidebar
- Dynamic intelligence card
- Quick access tools panel
- Chat workspace with structured AI responses
- Chat history management
- Route protection and auth state management

## Architecture
```
/app/
├── backend/
│   ├── server.py          # FastAPI with all endpoints
│   ├── ace_vault.json     # Policy data with modular entries
│   ├── requirements.txt
│   └── .env               # EMERGENT_LLM_KEY, MONGO_URL, CORS_ORIGINS
└── frontend/
    ├── src/
    │   ├── utils/
    │   │   └── api.js     # Axios with Bearer token interceptors
    │   ├── pages/
    │   │   ├── LoginPage.jsx
    │   │   ├── SignupPage.jsx
    │   │   ├── OnboardingPage.jsx
    │   │   ├── AuthCallback.jsx
    │   │   ├── MainAssistant.jsx
    │   │   └── AdminPage.jsx
    │   └── components/
    │       ├── LeftSidebar.jsx
    │       ├── ChatWorkspace.jsx
    │       └── ACEResponse.jsx
    └── .env               # REACT_APP_BACKEND_URL
```

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Email/password signup
- `POST /api/auth/login` - Email/password login
- `POST /api/auth/session` - Google OAuth session exchange
- `GET /api/auth/me` - Get current user (Bearer token)
- `POST /api/auth/logout` - Logout user

### User Profile
- `GET /api/user/profile` - Get user profile
- `POST /api/user/profile` - Update profile (onboarding)
- `GET /api/user/profile-options` - Get options for profile fields

### Intelligence & Chat
- `GET /api/student/intelligence` - Adaptive status card
- `GET /api/chats` - Get user's chat sessions
- `GET /api/chat/{chat_id}` - Get specific chat
- `POST /api/chat/send` - Send message & get AI response
- `DELETE /api/chat/{chat_id}` - Delete chat session

### Policies & Admin
- `GET /api/policies` - Get all policies
- `GET /api/admin/policies` - Admin: Get policies
- `POST /api/admin/policies` - Admin: Add policy
- `PUT /api/admin/policies/{vault_id}` - Admin: Update policy
- `DELETE /api/admin/policies/{vault_id}` - Admin: Delete policy

## Database Schema

### users Collection
```json
{
  "user_id": "user_xxx",
  "email": "student@psu.edu",
  "name": "John Doe",
  "password_hash": "bcrypt_hash",
  "picture": "url",
  "profile_complete": true,
  "profile": {
    "campus": "University Park",
    "major": "Computer Science",
    "academic_level": "Junior (60-89 credits)",
    "credit_load": "Full-time (12+ credits)",
    "financial_aid_status": "Receiving aid",
    "international_student": false,
    "expected_graduation": "Spring 2026",
    "current_semester": "Spring 2026"
  },
  "is_admin": false,
  "auth_provider": "email|google",
  "created_at": "ISO_DATE"
}
```

### user_sessions Collection
```json
{
  "user_id": "user_xxx",
  "session_token": "session_xxx",
  "expires_at": "ISO_DATE",
  "created_at": "ISO_DATE"
}
```

### chat_sessions Collection
```json
{
  "id": "uuid",
  "user_id": "user_xxx",
  "title": "Chat title",
  "messages": [
    {
      "role": "user|assistant",
      "content": "message text",
      "timestamp": "ISO_DATE",
      "structured_response": {}
    }
  ],
  "created_at": "ISO_DATE",
  "updated_at": "ISO_DATE"
}
```

## Prioritized Backlog

### P0 (Critical) - Completed ✅
- Core chat functionality
- Authentication (email/password + Google OAuth)
- Onboarding flow
- User profile context in AI
- Risk classification

### P1 (High Priority)
- File upload support for document analysis
- Admin interface full implementation and testing
- Real-time deadline calculations
- Academic calendar integration

### P2 (Nice to Have)
- Profile settings modal
- Export chat history
- Voice input support
- Dark mode option
- Push notifications for deadlines
- Multi-language support

## Next Tasks
1. Implement file upload functionality in chat
2. Complete admin interface testing
3. Add "Profile & Memory" settings modal
4. Connect Quick Access tools to external PSU links
5. Implement conversation search

## 3rd Party Integrations
- **OpenAI GPT-5.2**: Text generation via Emergent LLM Key
- **Emergent Google Auth**: Google OAuth authentication

## Test Credentials
```
Email: test@psu.edu
Password: testpass123
```
