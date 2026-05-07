![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![React](https://img.shields.io/badge/React-18.x-61dafb.svg)
![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey.svg)
![Google Calendar](https://img.shields.io/badge/Google_Calendar-API-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Agentic](https://img.shields.io/badge/AI-Agentic-red.svg)
[![code style](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
#  Academic Task Agent

An autonomous AI agent that helps students manage academic deadlines using real Operating System scheduling algorithms. The agent perceives tasks, autonomously decides priorities, acts by updating calendars, and adapts to user behavior.

## 🤖 Agentic Features
- **Autonomous Decision Making** - Uses MLFQ (Multilevel Feedback Queue), Priority Aging, and EDF (Earliest Deadline First) algorithms
- **Proactive Actions** - Automatically syncs tasks to Google Calendar and sends smart reminders
- **Adaptive Learning** - Increases priority of repeatedly delayed tasks (starvation prevention)
- **Task Decomposition** - Automatically breaks down complex tasks into manageable subtasks
- **Intelligent Scheduling** - Real-time replanning when conditions change

##  Tech Stack
- **Frontend**: React.js with modern hooks
- **Backend**: Flask (Python)
- **Scheduling**: Custom MLFQ + Aging + EDF implementation
- **Calendar**: Google Calendar API
- **Notifications**: Desktop alerts

##  OS Algorithms Implemented
1. **Multilevel Feedback Queue (MLFQ)** - 3 priority queues with time quanta (10/20/40 min)
2. **Priority with Aging** - Prevents task starvation
3. **Earliest Deadline First (EDF)** - Real-time deadline tracking

##  Use Case
Designed for overwhelmed students to automatically prioritize tasks based on deadlines, delays, and difficulty levels. The agent ensures no task remains undone indefinitely.

##  What Makes This Agentic
| Property | Implementation |
|----------|----------------|
| Perception | Reads deadlines, delays, priorities |
| Autonomous Decision | MLFQ/EDF algorithms choose next task |
| Action | Creates/updates Google Calendar, sends notifications |
| Adaptation | Aging increases priority of delayed tasks |

##  Project Status
✅ Fully functional production-ready agent
✅ Google Calendar integration working
✅ Auto-decomposition of complex tasks
✅ Persistent storage with save/load
✅ Real-time UI updates

## Installation
```
git clone https://github.com/[your-username]/academic-task-agent
cd academic-task-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd academic-agent-ui
npm install
npm start
````
## Main Dashboard
```
┌─────────────────────────────────────────────────────────────────┐
│  Academic Task Agent                                            │   
│  OS Scheduling: MLFQ + Aging + EDF + Google Calendar            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Why this order?                                         │    │
│  │ • Final Exam: Queue 0 | Delays: 0 | Priority: 2.5       │    │
│  │ • Quiz Prep: Queue 1 | Delays: 1 | Priority: 4.0        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  [ Add New Task]                                                │
│                                                                 │
│   Active Tasks (6 subtasks)                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Final Year Project        [3/6 subtasks done]          │    │
│  │    ↳ Final Year Project - Research                      │    │
│  │    ↳ Final Year Project - Implementation                │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
``` 
## Planned Enhancements

| Feature                              | Priority | Estimated Effort    |
|--------------------------------------|----------|---------------------|
| LLM-based natural language input     | High     | 2 hours             |
| Predictive deadline miss alerts      | High     | 3 hours             |
| Weekly email reports                 | Medium   | 2 hours             |
| Multi-agent collaboration system     | High     | 5 hours             |
| Mobile app (React Native)            | Low      | 1 week              |
| Dark/light theme toggle              | Low      | 1 hour              |
| Export tasks to CSV/PDF              | Medium   | 2 hours             |
|Team task assignment	                 | Medium	  | 4 hours             |

## Contributions
Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Commit changes (git commit -m 'Add amazing feature')
4. Push to branch (git push origin feature/amazing-feature)
5. Open a Pull Request

## 🎥 Demo Video
[https://github.com/user-attachments/assets/YOUR_VIDEO_ID](https://youtu.be/OH5lOPU8tdg)
https://youtu.be/ZwRIpkSjpW8

