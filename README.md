# AI Product Manager Agent

An intelligent, full-stack application that transforms raw product ideas into comprehensive Product Requirements Documents (PRDs), System Architectures, and actionable Development Tickets using Advanced AI.

## 🚀 Features

* **Instant PRD Generation**: Converts a single sentence idea into a structured Product Plan, Target Audience profile, and Success Metrics.
* **Architecture Blueprinting**: Automatically designs the Tech Stack, API Endpoints, and Database Schema for the proposed product.
* **Agile Ticket Creation**: Breaks down the project into Development Epics, User Stories, Acceptance Criteria, and estimated Tasks.
* **High-Performance LLM Integration**: Powered by Groq's blindingly fast Llama 3.1 8B inference engine.
* **Beautiful UI**: Modern, responsive React frontend with real-time markdown parsing and robust error handling.

## 🛠️ System Architecture

* **Frontend**: React, TypeScript, Tailwind CSS, Lucide Icons
* **Backend**: FastAPI (Python), Uvicorn
* **AI Engine**: Groq API (`llama-3.1-8b-instant`)

---

## 📄 Resume Snippets

If you are using this project for your portfolio or resume, here are a few professional bullet points you can use:

* *Architected a full-stack AI Product Manager application using React and FastAPI, leveraging Groq's Llama 3.1 model to dynamically generate structured Product Requirement Documents (PRDs) and system architectures from raw user inputs.*
* *Engineered a robust Natural Language Processing layer with deterministic JSON schema enforcement, resulting in a 0% failure rate for frontend data hydration and eliminating LLM hallucination crashes.*
* *Implemented an end-to-end agile workflow generator capable of instantly decomposing high-level product visions into technical epics, user stories, and actionable Jira-style development tickets.*

---

## 💻 Local Setup & Installation

### Prerequisites
* Node.js (v16+)
* Python (3.9+)
* A [Groq API Key](https://console.groq.com/keys)

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:
```env
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.1-8b-instant
PORT=8001
CORS_ORIGINS=http://localhost:3000
```

Start the FastAPI server:
```bash
uvicorn main:app --reload --port 8001
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm start
```

The application will now be running at `http://localhost:3000`.

## 🌐 Deployment Documentation

* **Backend**: Ready to be deployed on Render as a Web Service. Set the Build Command to `pip install -r requirements.txt` and Start Command to `uvicorn main:app --host 0.0.0.0 --port 10000`. Ensure you add your `GROQ_API_KEY` to the Render Environment Variables.
* **Frontend**: Ready to be deployed on Vercel. Ensure you set the `REACT_APP_API_URL` environment variable if your backend is hosted securely.
