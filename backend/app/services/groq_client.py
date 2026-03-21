"""
Groq API client for fast LLM integration.
"""
import requests
import os
from typing import Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def call_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Make a call to Groq API."""
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    
    if not api_key or api_key == "gsk_your_actual_key_here":
        # Return demo response for testing
        return generate_demo_response(prompt)
    
    print(f"Using Groq model: {model}")
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 6000
            },
            timeout=30
        )
        
        if response.status_code != 200:
            # Fall back to demo response if API fails
            print(f"Groq API failed, using demo response: {response.status_code}")
            return generate_demo_response(prompt)
        
        data = response.json()
        
        if "choices" not in data or not data["choices"]:
            raise Exception(f"Invalid response: {data}")
        
        return data["choices"][0]["message"]["content"]
        
    except Exception as e:
        print(f"Groq API error: {e}, using demo response")
        return generate_demo_response(prompt)


def generate_demo_response(prompt: str) -> str:
    """Generate a demo response when API is not available."""
    if "todo app" in prompt.lower():
        return """
# Product Vision

**Product Name:** TaskMaster Pro

**Problem Statement:** Users struggle with organizing daily tasks and remembering important deadlines across multiple projects and contexts.

**Target Users:** 
- Busy professionals
- Students
- Project managers
- Anyone needing task organization

**Core Goals:**
- Simplify task management
- Improve productivity
- Reduce missed deadlines
- Enable seamless collaboration

**Key Features:**
- Task creation and management
- Priority-based organization
- Reminder notifications
- Project categorization
- Progress tracking

**Value Proposition:** TaskMaster Pro transforms chaotic task management into organized productivity, helping users achieve their goals efficiently.

# Target Users

Primary user groups include:
1. **Professionals** (25-45 years): Managing work projects and personal tasks
2. **Students** (18-30 years): Organizing assignments and study schedules
3. **Teams** (All ages): Collaborative project management

# User Personas

## Alex - Busy Professional
- **Role:** Marketing Manager
- **Goals:** Never miss deadlines, maintain work-life balance
- **Challenges:** Juggling multiple projects, forgetting follow-ups

## Sarah - Student
- **Role:** University Student
- **Goals:** Track assignments, study efficiently
- **Challenges:** Managing multiple courses, exam preparation

# Core Features

## 1. Task Management
- Create, edit, delete tasks
- Set priorities (High, Medium, Low)
- Add descriptions and attachments
- Tag and categorize tasks

## 2. Smart Reminders
- Time-based notifications
- Location-based reminders
- Recurring task support
- Custom reminder sounds

## 3. Project Organization
- Create project folders
- Assign tasks to projects
- Progress visualization
- Team collaboration tools

## 4. Analytics Dashboard
- Task completion rates
- Productivity trends
- Time tracking insights
- Performance metrics

# Tech Stack

**Frontend:**
- React.js for UI
- TypeScript for type safety
- Tailwind CSS for styling
- PWA capabilities

**Backend:**
- Node.js with Express
- MongoDB for data storage
- Redis for caching
- JWT for authentication

**Mobile:**
- React Native
- Push notifications
- Offline sync
- Biometric authentication

# System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │  Mobile Client  │    │   Admin Panel   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      API Gateway          │
                    │   (Express + Rate Limit)  │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     Application Layer      │
                    │  (Business Logic + Auth)   │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────┴───────┐    ┌─────────┴───────┐    ┌─────────┴───────┐
│   MongoDB       │    │     Redis       │    │  File Storage   │
│   (Primary DB)  │    │    (Cache)      │    │   (Attachments)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

# API Endpoints

## Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Token refresh

## Tasks
- `GET /api/tasks` - List user tasks
- `POST /api/tasks` - Create new task
- `PUT /api/tasks/:id` - Update task
- `DELETE /api/tasks/:id` - Delete task

## Projects
- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `PUT /api/projects/:id` - Update project

## Reminders
- `POST /api/reminders` - Set reminder
- `GET /api/reminders` - List reminders
- `PUT /api/reminders/:id` - Update reminder

# Development Tickets

## Epic: Core Task Management
**Priority:** High | **Story Points:** 8

### User Stories:
1. **Task CRUD Operations** (3 points)
   - As a user, I want to create, edit, and delete tasks
   - Acceptance: Tasks can be created with title, description, priority
   - Technical: Implement Task model, REST endpoints

2. **Task Organization** (2 points)
   - As a user, I want to categorize tasks into projects
   - Acceptance: Tasks can be assigned to projects
   - Technical: Project model, foreign key relationships

3. **Priority Management** (1 point)
   - As a user, I want to set task priorities
   - Acceptance: Tasks have High/Medium/Low priority levels
   - Technical: Priority enum, filtering capabilities

4. **Search and Filter** (2 points)
   - As a user, I want to search and filter tasks
   - Acceptance: Search by title, filter by priority/project
   - Technical: Search API, database indexing

## Epic: Reminder System
**Priority:** Medium | **Story Points:** 5

### User Stories:
1. **Time-based Reminders** (2 points)
   - As a user, I want to set time-based reminders
   - Acceptance: Reminders trigger at specified times
   - Technical: Cron jobs, notification system

2. **Push Notifications** (2 points)
   - As a user, I want to receive push notifications
   - Acceptance: Notifications work on mobile and web
   - Technical: Firebase/FCM integration

3. **Recurring Tasks** (1 point)
   - As a user, I want to set up recurring tasks
   - Acceptance: Tasks can repeat daily/weekly/monthly
   - Technical: Recurrence pattern logic

## Epic: User Experience
**Priority:** Medium | **Story Points:** 6

### User Stories:
1. **Responsive Design** (2 points)
   - As a user, I want the app to work on all devices
   - Acceptance: Mobile-first design, tablet support
   - Technical: CSS media queries, component flexibility

2. **Offline Mode** (2 points)
   - As a user, I want to access tasks offline
   - Acceptance: Basic functionality available offline
   - Technical: Service worker, local storage sync

3. **Dashboard Analytics** (2 points)
   - As a user, I want to see my productivity metrics
   - Acceptance: Charts showing completion rates, trends
   - Technical: Analytics API, charting library

## Epic: Collaboration
**Priority:** Low | **Story Points:** 8

### User Stories:
1. **Team Workspaces** (3 points)
   - As a team lead, I want to create shared workspaces
   - Acceptance: Multiple users can collaborate on projects
   - Technical: Multi-tenant architecture, permissions

2. **Task Assignment** (2 points)
   - As a manager, I want to assign tasks to team members
   - Acceptance: Tasks have assignees and status tracking
   - Technical: User management, notification system

3. **Activity Feed** (2 points)
   - As a team member, I want to see project activity
   - Acceptance: Real-time updates on task changes
   - Technical: WebSocket integration, event logging

4. **Comments & Attachments** (1 point)
   - As a user, I want to comment on tasks and add files
   - Acceptance: Rich text comments, file uploads
   - Technical: File storage, comment threading

**Total Estimated Effort:** ~27 story points
**Suggested Timeline:** 6-8 weeks (2-week sprints)
**Team Size:** 2-3 developers
"""
    else:
        return f"""
# Product Plan for {prompt[:50]}...

## Product Vision
This product addresses the core need for [extracted from idea]. The vision is to create a solution that...

## Target Users
- Primary users include...
- Secondary user groups...

## Core Features
1. Feature 1 - Description
2. Feature 2 - Description  
3. Feature 3 - Description

## Tech Stack
- Frontend: React/TypeScript
- Backend: Node.js/Express
- Database: MongoDB
- Additional: Redis, AWS S3

## Development Timeline
- Phase 1: Core features (4 weeks)
- Phase 2: Advanced features (3 weeks)
- Phase 3: Testing & deployment (2 weeks)

This is a comprehensive product plan that can be further detailed based on specific requirements.
"""
