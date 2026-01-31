# ACE (Academic Clarity Engine) - PRD

## Original Problem Statement
Build a desktop-first web application called ACE for Penn State students only. ACE is a personalized, conversation-first academic advisor assistant that helps students navigate urgent academic situations, long-term planning, and university policies. It should feel like a persistent academic companion (Jarvis-style), not a generic chatbot.

## User Personas
- **Primary**: Penn State undergraduate/graduate students seeking academic guidance
- **Use Cases**: Course withdrawal questions, deadline inquiries, academic planning, policy clarification

## Core Requirements (Static)
1. ✅ Mocked Penn State SSO login
2. ✅ Two-column desktop layout (320px left sidebar + fluid right workspace)
3. ✅ AI-powered conversational assistant using OpenAI GPT-5.2
4. ✅ Structured responses (direct answer, next steps, sources, risk indicator)
5. ✅ Student profile display with mocked data
6. ✅ Intelligence card with adaptive notifications
7. ✅ Chat history persistence in MongoDB
8. ✅ Quick-access conversation starters
9. ✅ Policy vault with PSU academic policies
10. ✅ Penn State branding (navy blue accents, Merriweather font)

## What's Been Implemented (Jan 31, 2026)
- **Backend**: FastAPI with OpenAI GPT-5.2 integration via Emergent LLM key
- **Frontend**: React with Tailwind CSS and Shadcn UI components
- **Database**: MongoDB for chat session persistence
- **AI Features**: 
  - Structured JSON responses with policy citations
  - Clarifying questions when intent unclear
  - Risk assessment (low/medium/high)
  - Advisor escalation recommendations
- **Policy Vault**: 8 PSU policies (calendar, withdrawal, tuition, grading, etc.)

## Architecture
```
/app/
├── backend/
│   ├── server.py          # FastAPI with AI chat endpoints
│   ├── ace_vault.json     # Policy data
│   └── .env               # EMERGENT_LLM_KEY
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── LoginPage.jsx
    │   │   └── MainAssistant.jsx
    │   └── components/
    │       ├── LeftSidebar.jsx
    │       ├── ChatWorkspace.jsx
    │       └── ACEResponse.jsx
    └── .env
```

## API Endpoints
- `GET /api/student/profile` - Mocked student data
- `GET /api/student/intelligence` - Adaptive status card
- `GET /api/chats/{student_id}` - Chat history
- `POST /api/chat/send` - Send message & get AI response
- `GET /api/policies` - Policy vault data

## Prioritized Backlog

### P0 (Critical) - Completed
- ✅ Core chat functionality
- ✅ Structured AI responses
- ✅ Policy citations

### P1 (High Priority)
- File upload support (+ button is stubbed)
- Real-time deadline calculations
- Academic calendar integration
- Profile settings modal

### P2 (Nice to Have)
- Dark mode option
- Export chat history
- Voice input support
- Multi-language support
- Push notifications for deadlines

## Next Tasks
1. Implement file upload for document analysis
2. Add real Penn State SSO integration
3. Create profile settings modal
4. Add more sophisticated deadline tracking
5. Implement conversation search
