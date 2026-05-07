"""
COMPLETE ACADEMIC TASK AGENT
OS Scheduling: MLFQ + Aging + EDF
Features: Google Calendar Integration + Smart Reminders
"""
import re
from typing import Optional, List, Dict
import heapq
import pickle
import os
from dotenv import load_dotenv
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from plyer import notification

load_dotenv()

# Google Calendar imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If running on Windows without GUI, uncomment:
# import warnings
# warnings.filterwarnings("ignore")

SCOPES = ['https://www.googleapis.com/auth/calendar']


class Task:
    """Represents a single academic task"""
    
    def __init__(self, task_id, name, deadline, user_priority=5, difficulty=3, energy_level="medium", parent_id=None):
        self.id = task_id
        self.name = name
        self.deadline = deadline
        self.user_priority = user_priority
        self.delay_count = 0
        self.difficulty = difficulty
        self.energy_level = energy_level
        self.status = "pending"
        self.created_at = datetime.now()
        self.completed_at = None
        self.calendar_event_id = None  # Store Google Calendar event ID

        self.parent_id = parent_id  # Link to parent task
        self.is_parent = False      # Flag for tasks that have children
        
        # MLFQ attributes
        self.current_queue = 0
        self.time_quantum = 10
        self.time_used = 0
        self.times_through_queue = 0
        self.last_reminder_sent = None
        
        # Priority components
        self.aging_priority = user_priority
        self.edf_priority = 0
        self.combined_priority = 0
        self.mlfq_priority = 0
        self.final_priority = 0
        
        self.update_priorities()
    
    def calculate_edf_priority(self):
        now = datetime.now()
        hours_until_deadline = max(0, (self.deadline - now).total_seconds() / 3600)
        
        if hours_until_deadline <= 24:
            return 1
        elif hours_until_deadline <= 72:
            return 2
        elif hours_until_deadline <= 168:
            return 4
        elif hours_until_deadline <= 336:
            return 6
        else:
            return 8
    
    def apply_aging(self):
        aging_boost = min(self.delay_count, 7)
        new_priority = max(1, self.user_priority - aging_boost)
        self.aging_priority = new_priority
        return self.aging_priority
    
    def apply_mlfq_demotion(self):
        if self.time_used >= self.time_quantum and self.current_queue < 2:
            self.current_queue += 1
            self.time_used = 0
            self.times_through_queue += 1
            return True
        return False
    
    def update_priorities(self):
        self.edf_priority = self.calculate_edf_priority()
        self.apply_aging()
        self.combined_priority = (self.aging_priority + self.edf_priority) / 2
        mlfq_penalty = self.current_queue * 2
        self.mlfq_priority = self.combined_priority + mlfq_penalty
        self.final_priority = self.mlfq_priority
        
        if self.delay_count >= 3 and self.current_queue > 0:
            self.current_queue = max(0, self.current_queue - 1)
    
    def delay(self):
        self.delay_count += 1
        self.status = "delayed"
        if self.delay_count >= 3 and self.current_queue > 0:
            self.current_queue -= 1
        self.update_priorities()
        self._send_delay_notification()
    
    def complete(self):
        self.status = "done"
        self.completed_at = datetime.now()
        self._send_completion_notification()
    
    def _send_delay_notification(self):
        notification.notify(
            title=f"⚠️ Task Delayed: {self.name}",
            message=f"Delay #{self.delay_count}. Priority increased to {self.aging_priority:.0f}/10",
            timeout=5
        )
    
    def _send_completion_notification(self):
        notification.notify(
            title=f"✅ Task Completed: {self.name}",
            message="Great job! Keep the momentum going!",
            timeout=5
        )
    
    def execute_time_slice(self, minutes=10):
        self.time_used += minutes
        demoted = self.apply_mlfq_demotion()
        self.update_priorities()
        return demoted
    
    def __lt__(self, other):
        return self.final_priority < other.final_priority
    
    def get_priority_display(self):
        return f"A:{self.aging_priority:.0f} | E:{self.edf_priority} | Q{self.current_queue}"
    
    def should_send_reminder(self):
        """Check if task needs a reminder"""
        if self.status == "done":
            return False
        
        hours_until = (self.deadline - datetime.now()).total_seconds() / 3600
        
        # Reminder conditions
        if hours_until <= 24 and hours_until > 23:
            return "tomorrow"
        elif hours_until <= 6 and hours_until > 5:
            return "6hours"
        elif hours_until <= 1 and hours_until > 0.5:
            return "1hour"
        elif self.delay_count >= 2 and self.status == "delayed":
            return "delayed"
        
        return None


class GoogleCalendarManager:
    """Handles all Google Calendar operations"""
    
    def __init__(self):
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Google Calendar API"""
        creds = None
        
        # Token file stores user's access and refresh tokens
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    print("\n⚠️  Google Calendar setup required!")
                    print("   1. Go to https://console.cloud.google.com/")
                    print("   2. Enable Google Calendar API")
                    print("   3. Download credentials.json to this folder")
                    print("\n❌ Calendar features disabled. Continuing without calendar...\n")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('calendar', 'v3', credentials=creds)
        print("✅ Google Calendar connected!")
        return True
    
    def add_task_to_calendar(self, task: Task) -> Optional[str]:
        """Add a task as a calendar event"""
        if not self.service:
            return None
        
        event = {
            'summary': f"📚 {task.name}",
            'description': f"Priority: {task.user_priority}/10 | Difficulty: {task.difficulty}/5\n"
                          f"Delay count: {task.delay_count}\n"
                          f"Status: {task.status}",
            'start': {
                'dateTime': task.deadline.isoformat(),
                'timeZone': 'Asia/Karachi',  # Change to your timezone
            },
            'end': {
                'dateTime': (task.deadline + timedelta(hours=1)).isoformat(),
                'timeZone': 'Asia/Karachi',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 60},  # 1 hour before
                ],
            },
            'colorId': '11',  # Red for urgent tasks
        }
        
        try:
            event = self.service.events().insert(calendarId='primary', body=event).execute()
            print(f"   📅 Added to Google Calendar: {event.get('htmlLink')}")
            return event.get('id')
        except Exception as e:
            print(f"   ⚠️ Could not add to calendar: {e}")
            return None
    
    def update_calendar_event(self, task: Task):
        """Update calendar event when task changes"""
        if not self.service or not task.calendar_event_id:
            return
        
        try:
            # Update event color based on urgency
            event = self.service.events().get(calendarId='primary', eventId=task.calendar_event_id).execute()
            
            if task.final_priority <= 3:  # Very urgent
                event['colorId'] = '11'  # Red
            elif task.delay_count > 0:
                event['colorId'] = '6'  # Orange
            
            event['description'] = f"Priority: {task.final_priority:.1f}/10 | Delays: {task.delay_count}"
            
            self.service.events().update(calendarId='primary', eventId=task.calendar_event_id, body=event).execute()
        except:
            pass
    
    def delete_calendar_event(self, event_id: str):
        """Remove task from calendar when completed"""
        if self.service and event_id:
            try:
                self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            except:
                pass


class MotivationManager:
    """Sends motivational messages based on progress"""
    
    def __init__(self):
        self.messages = {
            "good_start": [
                "🌟 Great start! You're making progress!",
                "💪 One task at a time. You've got this!",
                "🎯 Keep going! Every task completed is a win."
            ],
            "urgent": [
                "⏰ Deadline approaching! Focus on this task now.",
                "🚨 This task is urgent! Let's get it done.",
                "⚡ Time is running out. You can do this!"
            ],
            "delayed": [
                "⚠️ This task has been delayed. Let's tackle it now!",
                "📈 Priority increased due to delay. Time to work on it!",
                "🎯 Don't let this task fall behind. Start now!"
            ],
            "completed": [
                "🏆 Amazing! Another task completed!",
                "🎉 You're crushing it! Keep the momentum!",
                "✨ Task done! Celebrate this small win!"
            ],
            "streak": [
                "🔥 You're on a roll! Keep completing tasks!",
                "💎 Consistency is key. Great job staying on track!",
                "📈 Your productivity is improving!"
            ]
        }
        self.streak = 0
    
    def get_message(self, category: str) -> str:
        import random
        return random.choice(self.messages.get(category, self.messages["good_start"]))
    
    def send_motivation(self, category: str):
        message = self.get_message(category)
        notification.notify(
            title="🎓 Academic Agent",
            message=message,
            timeout=4
        )
        print(f"\n💡 MOTIVATION: {message}\n")
    
    def record_completion(self):
        self.streak += 1
        if self.streak % 3 == 0:  # Every 3 completions
            self.send_motivation("streak")
    
    def reset_streak(self):
        self.streak = 0

class TaskDecomposer:
    """
    Autonomous Task Decomposer
    Breaks large tasks into manageable subtasks automatically
    """
    
    # Common task decomposition patterns
    DECOMPOSITION_RULES = {
        "essay": ["Research", "Outline", "Write Introduction", "Write Body", "Write Conclusion", "Proofread", "Submit"],
        "project": ["Requirements Analysis", "Design", "Implementation", "Testing", "Documentation", "Presentation"],
        "exam": ["Review Notes", "Practice Problems", "Past Papers", "Weak Areas", "Final Review"],
        "coding": ["Setup Environment", "Design Architecture", "Write Core Logic", "Debug", "Testing", "Documentation"],
        "presentation": ["Research Content", "Create Slides", "Practice Delivery", "Prepare Q&A", "Final Rehearsal"],
        "paper": ["Literature Review", "Methodology", "Experiments", "Results Analysis", "Write Draft", "Revisions"],
        "reading": ["Abstract/Skim", "Key Points", "Detailed Reading", "Summarize", "Apply/Analyze"],
        "assignment": ["Understand Requirements", "Research", "Draft", "Review", "Final Polish", "Submit"],
    }
    
    def __init__(self, parent_scheduler):
        self.scheduler = parent_scheduler
        self.decomposition_history = {}  # Track which tasks were decomposed
    
    def should_decompose(self, task) -> bool:
        """Determine if a task needs decomposition"""
        # Decompose if:
        # 1. Difficulty is high (4 or 5)
        # 2. Time to deadline is more than 3 days
        # 3. Task name suggests complexity
        if task.difficulty >= 4:
            return True
        
        # Check if task name indicates complexity
        complex_keywords = ['project', 'essay', 'research', 'thesis', 'report', 'analysis', 'implementation']
        if any(keyword in task.name.lower() for keyword in complex_keywords):
            return True
        
        return False
    
    def detect_task_type(self, task_name: str) -> str:
        """Detect what kind of task this is"""
        task_lower = task_name.lower()
        
        for task_type, keywords in {
            'essay': ['essay', 'paper', 'write-up', 'article'],
            'project': ['project', 'major', 'big'],
            'exam': ['exam', 'final', 'test', 'quiz'],
            'coding': ['code', 'program', 'develop', 'software'],
            'presentation': ['presentation', 'slides', 'talk', 'demo'],
            'reading': ['read', 'chapter', 'book', 'article'],
            'assignment': ['assignment', 'homework', 'exercise']
        }.items():
            if any(keyword in task_lower for keyword in keywords):
                return task_type
        
        return 'assignment'  # default
    
    def generate_subtasks(self, task) -> List[Dict]:
        """Generate subtasks automatically"""
        task_type = self.detect_task_type(task.name)
        
        # Get template subtasks
        subtasks = self.DECOMPOSITION_RULES.get(task_type, 
            ["Planning", "Execution", "Review", "Finalize"])
        
        # Calculate deadline distribution
        total_days = max(1, (task.deadline - datetime.now()).days)
        days_per_subtask = total_days / len(subtasks)
        
        # Create subtasks with staggered deadlines
        generated = []
        for i, subtask_name in enumerate(subtasks):
            # Personalize subtask name
            full_name = f"{task.name} - {subtask_name}"
            
            # Calculate deadline for this subtask
            subtask_deadline = task.deadline - timedelta(days=(len(subtasks) - i - 1) * 2)
            subtask_deadline = max(subtask_deadline, datetime.now() + timedelta(days=1))
            
            # Priority is slightly higher than parent (to ensure progression)
            subtask_priority = max(1, task.user_priority - 1)
            
            generated.append({
                'name': full_name,
                'deadline': subtask_deadline.strftime("%Y-%m-%d %H:%M"),
                'priority': subtask_priority,
                'difficulty': max(1, task.difficulty - 1),
                'parent_id': task.id
            })
        
        return generated
    
    def decompose_task(self, task) -> bool:
        """Main decomposition method"""
        if not self.should_decompose(task):
            return False
        
        # Check if already decomposed
        if task.id in self.decomposition_history:
            return False
        
        # ⭐ Mark the parent task ⭐
        task.is_parent = True

        print(f"\n🔨 AUTONOMOUS TASK DECOMPOSITION:")
        print(f"   Detected complex task: {task.name}")
        print(f"   Difficulty: {task.difficulty}/5")
        print(f"   Deadline: {task.deadline.strftime('%Y-%m-%d %H:%M')}")
        
        # Generate subtasks
        subtasks = self.generate_subtasks(task)
        
        print(f"   Breaking into {len(subtasks)} subtasks...")
        
        # Add subtasks to scheduler
        added_ids = []
        for subtask_data in subtasks:
            subtask_id = self.scheduler.add_task(
                name=subtask_data['name'],
                deadline_str=subtask_data['deadline'],
                user_priority=subtask_data['priority'],
                difficulty=subtask_data['difficulty'],
                parent_id=subtask_data['parent_id']
            )
            if subtask_id:
                added_ids.append(subtask_id)
                print(f"      ✓ Created: {subtask_data['name']}")
        
        # Mark as decomposed
        self.decomposition_history[task.id] = {
            'subtasks': added_ids,
            'decomposed_at': datetime.now()
        }
        
        # Optional: Archive the original task or mark as parent
        task.is_parent = True
        task.difficulty = 2  # Reduce difficulty since it's now broken down
        
        print(f"   ✅ Task decomposition complete!")
        print(f"   💡 Tip: Complete subtasks one by one\n")
        
        return True
    
    def get_decomposition_status(self, task_id):
        """Check decomposition status"""
        if task_id in self.decomposition_history:
            return self.decomposition_history[task_id]
        return None

class MLFQScheduler:
    """Complete scheduler with all OS algorithms"""
   
    def add_decomposer_method(self):
      pass
    
    def __init__(self):
        self.tasks: Dict[int, Task] = {}
        self.next_id = 1
        self.queue0 = []
        self.queue1 = []
        self.queue2 = []
        self.time_quanta = {0: 10, 1: 20, 2: 40}
        
        self.calendar = GoogleCalendarManager()
        self.motivation = MotivationManager()

        self.decomposer = TaskDecomposer(self)  # Initialize decomposer
        
        self.load_data()  # Load saved tasks
    
    def _add_to_queue(self, task):
        if task.current_queue == 0:
            heapq.heappush(self.queue0, task)
        elif task.current_queue == 1:
            heapq.heappush(self.queue1, task)
        else:
            heapq.heappush(self.queue2, task)
    
    def _reheap_all_queues(self):
        self.queue0 = []
        self.queue1 = self.queue2 = []
        for task in self.tasks.values():
            if task.status != "done":
                self._add_to_queue(task)
    
    def add_task(self, name, deadline_str, user_priority=5, difficulty=3, energy_level="medium", parent_id=None):
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
            
             # ⭐ Pass parent_id to Task constructor ⭐
            task = Task(self.next_id, name, deadline, user_priority, difficulty, energy_level, parent_id)
            task.current_queue = 0
            task.time_quantum = self.time_quanta[0]
            task.update_priorities()

            # Add to Google Calendar
            event_id = self.calendar.add_task_to_calendar(task)
            task.calendar_event_id = event_id
            
            self.tasks[self.next_id] = task
            self._add_to_queue(task)
            self.next_id += 1
            
            self.save_data()  # Auto-save
            
            print(f"\n✅ Task '{name}' added to Queue 0")
            print(f"   📅 Deadline: {deadline.strftime('%Y-%m-%d %H:%M')}")
            if event_id:
                print(f"   📆 Synced to Google Calendar")
            
            # Auto-decompose if it's a complex task and not already a subtask
            if parent_id is None and difficulty >= 4:
                self.decomposer.decompose_task(task)

            return task.id
        except ValueError:
            print("❌ Invalid date format! Use: YYYY-MM-DD HH:MM")
            return None
    
    def get_next_task(self) -> Optional[Task]:
        if self.queue0:
            return self.queue0[0]
        elif self.queue1:
            return self.queue1[0]
        elif self.queue2:
            return self.queue2[0]
        return None
    
    def delay_task(self, task_id):
        if task_id in self.tasks and self.tasks[task_id].status != "done":
            task = self.tasks[task_id]
            old_queue = task.current_queue
            task.delay()
            new_queue = task.current_queue
            
            # Update calendar
            self.calendar.update_calendar_event(task)
            
            self._reheap_all_queues()
            self.save_data()
            
            print(f"\n⚠️ Task '{task.name}' delayed!")
            print(f"   Delay count: {task.delay_count}")
            
            if new_queue < old_queue:
                print(f"   ⬆️ Moved to Queue {new_queue} (aging boost)")
            
            # Send motivational reminder about delayed task
            self.motivation.send_motivation("delayed")
        else:
            print(f"❌ Task ID {task_id} not found")
    
    def complete_task(self, task_id):
        if task_id in self.tasks and self.tasks[task_id].status != "done":
            task = self.tasks[task_id]
            task.complete()
            
            # Remove from calendar
            self.calendar.delete_calendar_event(task.calendar_event_id)
            
            self._reheap_all_queues()
            self.save_data()
            
            self.motivation.record_completion()
            self.motivation.send_motivation("completed")
            
            print(f"\n✅ Task '{task.name}' completed!")
        else:
            print(f"❌ Task ID {task_id} not found")
            
    def delete_task(self, task_id):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.calendar_event_id:
                self.calendar.delete_calendar_event(task.calendar_event_id)
            del self.tasks[task_id]
            self._reheap_all_queues()
            self.save_data()
            print(f"\n🗑️ Task deleted!")
            return True
        return False
        
    def update_deadline(self, task_id, new_deadline_str):
        if task_id in self.tasks and self.tasks[task_id].status != "done":
            try:
                new_deadline = datetime.strptime(new_deadline_str, "%Y-%m-%d %H:%M")
                task = self.tasks[task_id]
                task.deadline = new_deadline
                task.update_priorities()
                self.calendar.update_calendar_event(task)
                self._reheap_all_queues()
                self.save_data()
                print(f"\n📅 Task '{task.name}' deadline updated to {new_deadline_str}!")
                return True
            except ValueError:
                print("❌ Invalid date format!")
                return False
        return False
        
    def clear_completed_tasks(self):
        to_delete = [t.id for t in self.tasks.values() if t.status == "done"]
        for task_id in to_delete:
            del self.tasks[task_id]
        if to_delete:
            self.save_data()
            print(f"\n🧹 Cleared {len(to_delete)} completed tasks!")
        return len(to_delete)

    def get_analytics(self):
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks.values() if t.status == "done"])
        pending_tasks = total_tasks - completed_tasks
        delayed_tasks = len([t for t in self.tasks.values() if t.delay_count > 0 and t.status != "done"])
        
        # Queue distribution
        q_dist = [0, 0, 0]
        for t in self.tasks.values():
            if t.status != "done":
                q_dist[t.current_queue] += 1
                
        # Completion by day (last 7 days)
        last_7_days = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        completions_by_day = {day: 0 for day in last_7_days}
        for t in self.tasks.values():
            if t.status == "done" and getattr(t, 'completed_at', None):
                day_str = t.completed_at.strftime("%Y-%m-%d")
                if day_str in completions_by_day:
                    completions_by_day[day_str] += 1
                    
        return {
            "total": total_tasks,
            "completed": completed_tasks,
            "pending": pending_tasks,
            "delayed": delayed_tasks,
            "queue_distribution": q_dist,
            "completions_by_day": list(completions_by_day.values()),
            "days": [d.split('-')[1] + '/' + d.split('-')[2] for d in last_7_days] # format MM/DD
        }

    def send_email_report(self, to_email):
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_PASSWORD")
        
        if not sender_email or not sender_password:
            return False, "Email credentials not configured in .env file."
            
        analytics = self.get_analytics()
        subject = "📊 Academic Task Agent - Weekly Productivity Report"
        
        contents = [
            f"<h2>Your Productivity Report</h2>",
            f"<ul>",
            f"<li><b>Total Tasks:</b> {analytics['total']}</li>",
            f"<li><b>Completed Tasks:</b> {analytics['completed']}</li>",
            f"<li><b>Pending Tasks:</b> {analytics['pending']}</li>",
            f"<li><b>Delayed Tasks:</b> {analytics['delayed']}</li>",
            f"</ul>",
            f"<h3>Tasks by Queue</h3>",
            f"<ul>",
            f"<li>Queue 0 (Highest): {analytics['queue_distribution'][0]}</li>",
            f"<li>Queue 1 (Medium): {analytics['queue_distribution'][1]}</li>",
            f"<li>Queue 2 (Lowest): {analytics['queue_distribution'][2]}</li>",
            f"</ul>",
            f"<p>Keep up the great work!</p>"
        ]
        
        print("\n" + "="*50)
        print(f"📧 [SIMULATED] Weekly Report Sent to: {to_email}")
        print("-"*50)
        print("Here is what would be emailed:\n")
        # print(your_report_text) # <-- Print your report
        print("✅ Report generation successful!")
        print("(In production, this would be delivered to your inbox)")
        print("="*50 + "\n")

        # Return success to the frontend
        return True, "Report generated successfully (demo mode). Check the backend console."

    
    def execute_task_slice(self, task_id, minutes=None):
        if task_id not in self.tasks:
            print("❌ Task not found")
            return
        
        task = self.tasks[task_id]
        if task.status == "done":
            print("❌ Task already completed")
            return
        
        if minutes is None:
            minutes = task.time_quantum
        
        print(f"\n⏰ Working on '{task.name}' for {minutes} minutes...")
        demoted = task.execute_time_slice(minutes)
        
        if demoted:
            print(f"   ⬇️ Demoted to Queue {task.current_queue}")
            print(f"   ⏱️  New quantum: {task.time_quantum} minutes")
        
        self.calendar.update_calendar_event(task)
        self._reheap_all_queues()
        self.save_data()
    
    def check_reminders(self):
        """Automatically send reminders for urgent tasks"""
        for task in self.tasks.values():
            if task.status != "done":
                reminder_type = task.should_send_reminder()
                
                if reminder_type and (task.last_reminder_sent is None or 
                    (datetime.now() - task.last_reminder_sent).seconds > 3600):
                    
                    if reminder_type == "tomorrow":
                        self.motivation.send_motivation("urgent")
                        notification.notify(
                            title=f"⏰ Deadline Tomorrow: {task.name}",
                            message=f"Due: {task.deadline.strftime('%Y-%m-%d %H:%M')}",
                            timeout=5
                        )
                    elif reminder_type == "6hours":
                        notification.notify(
                            title=f"🚨 URGENT: {task.name}",
                            message=f"Due in 6 hours! Priority: {task.final_priority:.1f}",
                            timeout=5
                        )
                    elif reminder_type == "delayed":
                        notification.notify(
                            title=f"⚠️ Delayed Task: {task.name}",
                            message=f"Priority increased to {task.aging_priority:.0f}. Time to work on it!",
                            timeout=5
                        )
                    
                    task.last_reminder_sent = datetime.now()
    
    def get_sorted_tasks(self):
        all_tasks = [t for t in self.tasks.values() if t.status != "done"]
        all_tasks.sort(key=lambda t: (t.current_queue, t.final_priority))
        return all_tasks
    
    def print_schedule(self):
        if not self.tasks:
            print("\n📭 No tasks yet. Add some!\n")
            return
        
        print("\n" + "="*90)
        print("📋 COMPLETE SCHEDULE (MLFQ + Aging + EDF + Calendar)")
        print("="*90)
        
        queues = [
            ("🔴 QUEUE 0", self.queue0, "10min"),
            ("🟡 QUEUE 1", self.queue1, "20min"),
            ("🟢 QUEUE 2", self.queue2, "40min")
        ]
        
        for name, queue, quantum in queues:
            print(f"\n{name} - {quantum} quantum")
            print("-"*90)
            if not queue:
                print("   (empty)")
            else:
                print(f"{'ID':<4} {'Task':<22} {'Deadline':<17} {'Delays':<8} {'Priority'}")
                for task in sorted(queue, key=lambda t: t.final_priority):
                    dl = task.deadline.strftime("%m-%d %H:%M")
                    print(f"{task.id:<4} {task.name[:21]:<22} {dl:<17} {task.delay_count:<8} {task.get_priority_display()}")
        
        print("\n" + "="*90)
        next_task = self.get_next_task()
        if next_task:
            print(f"🎯 NEXT: {next_task.name}")
            hours_left = (next_task.deadline - datetime.now()).total_seconds() / 3600
            if hours_left < 48:
                print(f"   ⚠️ {hours_left:.0f} hours until deadline!")
        print("="*90 + "\n")
    
    def save_data(self):
        """Save tasks to file for persistence"""
        try:
            data = []
            for task in self.tasks.values():
                data.append({
                    "id": task.id,
                    "name": task.name,
                    "deadline": task.deadline.isoformat(),
                    "user_priority": task.user_priority,
                    "delay_count": task.delay_count,
                    "status": task.status,
                    "current_queue": task.current_queue,
                    "calendar_event_id": task.calendar_event_id,
                    "parent_id": getattr(task, 'parent_id', None),
                    "is_parent": getattr(task, 'is_parent', False)
                })
            with open("tasks_backup.pkl", "wb") as f:
                pickle.dump(data, f)
        except:
            pass
    
    def load_data(self):
        """Load tasks from backup"""
        try:
            if os.path.exists("tasks_backup.pkl"):
                with open("tasks_backup.pkl", "rb") as f:
                    data = pickle.load(f)
                for task_data in data:
                    deadline = datetime.fromisoformat(task_data["deadline"])
                    task = Task(
                        task_data["id"], task_data["name"], deadline,
                        task_data["user_priority"]
                    )
                    task.delay_count = task_data["delay_count"]
                    task.status = task_data["status"]
                    task.current_queue = task_data["current_queue"]
                    task.calendar_event_id = task_data.get("calendar_event_id")
                    task.parent_id = task_data.get("parent_id")
                    task.is_parent = task_data.get("is_parent", False)
                    task.update_priorities()
                    self.tasks[task.id] = task
                    self._add_to_queue(task)
                    self.next_id = max(self.next_id, task.id + 1)
                if data:
                    print(f"📂 Loaded {len(data)} saved tasks")
        except:
            pass


def reminder_thread(scheduler):
    """Background thread for automatic reminders"""
    while True:
        scheduler.check_reminders()
        time.sleep(1800)  # Check every 30 minutes


def show_menu():
    print("\n" + "="*55)
    print("🎓 COMPLETE ACADEMIC AGENT")
    print("   MLFQ + Aging + EDF + Google Calendar")
    print("="*55)
    print("1. ➕ Add task")
    print("2. 📋 View schedule")
    print("3. 🎯 Get next task")
    print("4. ⏰ Work on task (time slice)")
    print("5. ⚠️ Delay task")
    print("6. ✅ Complete task")
    print("7. 💡 Explain algorithms")
    print("8. 🚪 Exit")
    print("="*55)


def main():
    scheduler = MLFQScheduler()
    
    # Start reminder thread
    reminder_t = threading.Thread(target=reminder_thread, args=(scheduler,), daemon=True)
    reminder_t.start()
    
    print("\n" + "🎯"*30)
    print("YOUR COMPLETE OS-INSPIRED ACADEMIC AGENT IS RUNNING")
    print("🎯"*30)
    print("""
Features active:
  ✅ MLFQ scheduling (3 queues with time quanta)
  ✅ Priority aging (no task starves)
  ✅ EDF deadline tracking
  ✅ Google Calendar sync
  ✅ Smart reminders + motivation
  ✅ Auto-save tasks
    """)
    
    while True:
        show_menu()
        choice = input("Choose (1-8): ").strip()
        
        if choice == '1':
            name = input("Task name: ").strip()
            deadline = input("Deadline (YYYY-MM-DD HH:MM): ").strip()
            priority = input("Priority (1-10) [5]: ").strip()
            priority = int(priority) if priority else 5
            scheduler.add_task(name, deadline, priority)
        
        elif choice == '2':
            scheduler.print_schedule()
        
        elif choice == '3':
            task = scheduler.get_next_task()
            if task:
                print(f"\n🎯 NEXT: {task.name} (Queue {task.current_queue})")
            else:
                print("\n📭 No tasks!\n")
        
        elif choice == '4':
            scheduler.print_schedule()
            if scheduler.get_sorted_tasks():
                try:
                    tid = int(input("Task ID: "))
                    scheduler.execute_task_slice(tid)
                except:
                    print("❌ Invalid")
        
        elif choice == '5':
            scheduler.print_schedule()
            if scheduler.get_sorted_tasks():
                try:
                    tid = int(input("Task ID to DELAY: "))
                    scheduler.delay_task(tid)
                except:
                    print("❌ Invalid")
        
        elif choice == '6':
            scheduler.print_schedule()
            if scheduler.get_sorted_tasks():
                try:
                    tid = int(input("Task ID to COMPLETE: "))
                    scheduler.complete_task(tid)
                except:
                    print("❌ Invalid")
        
        elif choice == '7':
            print("\n" + "="*50)
            print("MLFQ: Used in Windows, macOS, Linux")
            print("Aging: Prevents starvation")
            print("EDF: Real-time deadline guarantee")
            print("="*50 + "\n")
            input("Press Enter...")
        
        elif choice == '8':
            scheduler.save_data()
            print("\n👋 Goodbye! Tasks saved.\n")
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()