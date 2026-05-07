"""
Academic Deadline & Task Prioritization Agent
COMPLETE OS SCHEDULING ALGORITHMS:
1. Priority with Aging (prevents starvation)
2. Earliest Deadline First (EDF) - respects deadlines
3. Multilevel Feedback Queue (MLFQ) - used in modern OS
"""

import heapq
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time

class Task:
    """Represents a single academic task"""
    
    def __init__(self, task_id, name, deadline, user_priority=5, difficulty=3, energy_level="medium"):
        self.id = task_id
        self.name = name
        self.deadline = deadline
        self.user_priority = user_priority  # User's input priority
        self.delay_count = 0
        self.difficulty = difficulty
        self.energy_level = energy_level
        self.status = "pending"
        self.created_at = datetime.now()
        
        # MLFQ attributes
        self.current_queue = 0  # 0=highest priority, 1,2=lower queues
        self.time_quantum = 10  # minutes allocated for this queue
        self.time_used = 0  # minutes used in current session
        self.times_through_queue = 0  # how many times it's been demoted
        
        # Priority algorithms
        self.aging_priority = user_priority
        self.edf_priority = 0
        self.combined_priority = 0
        self.mlfq_priority = 0
        self.final_priority = 0
        
        self.update_priorities()
    
    def calculate_edf_priority(self):
        """Earliest Deadline First: Closer deadline = higher priority"""
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
        """Delay aging: each delay increases priority"""
        aging_boost = min(self.delay_count, 7)
        new_priority = max(1, self.user_priority - aging_boost)
        self.aging_priority = new_priority
        return self.aging_priority
    
    def apply_mlfq_demotion(self):
        """MLFQ: If task uses its full time quantum, it moves to lower queue"""
        if self.time_used >= self.time_quantum and self.current_queue < 2:
            self.current_queue += 1
            self.time_used = 0
            self.times_through_queue += 1
            return True
        return False
    
    def update_priorities(self):
        """Recalculate all priority components"""
        self.edf_priority = self.calculate_edf_priority()
        self.apply_aging()
        
        # Combined priority from Aging + EDF
        self.combined_priority = (self.aging_priority + self.edf_priority) / 2
        
        # MLFQ adjustment: lower queue = higher priority number (less urgent)
        mlfq_penalty = self.current_queue * 2  # Queue 0: +0, Queue 1: +2, Queue 2: +4
        self.mlfq_priority = self.combined_priority + mlfq_penalty
        
        # Final priority for scheduling
        self.final_priority = self.mlfq_priority
        
        # Aging can override MLFQ queue if delayed enough
        if self.delay_count >= 3 and self.current_queue > 0:
            self.current_queue = max(0, self.current_queue - 1)
    
    def delay(self):
        """Mark task as delayed"""
        self.delay_count += 1
        self.status = "delayed"
        
        # Aging boost: high delays can move task to higher queue
        if self.delay_count >= 3 and self.current_queue > 0:
            self.current_queue -= 1
            print(f"   ⬆️ MLFQ: Task moved to higher priority queue (Queue {self.current_queue})")
        
        self.update_priorities()
    
    def complete(self):
        self.status = "done"
    
    def execute_time_slice(self, minutes=10):
        """Simulate working on task for a time slice"""
        self.time_used += minutes
        demoted = self.apply_mlfq_demotion()
        self.update_priorities()
        return demoted
    
    def __lt__(self, other):
        return self.final_priority < other.final_priority
    
    def get_priority_display(self):
        return f"A:{self.aging_priority:.0f} | E:{self.edf_priority} | C:{self.combined_priority:.0f} | Q{self.current_queue}"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "deadline": self.deadline.strftime("%Y-%m-%d %H:%M"),
            "delay_count": self.delay_count,
            "current_queue": self.current_queue,
            "status": self.status
        }


class MLFQScheduler:
    """
    Multilevel Feedback Queue Scheduler
    Queues: Q0 (highest priority, smallest time quantum)
            Q1 (medium priority, medium quantum)
            Q2 (lowest priority, largest quantum)
    
    Rules:
    - New tasks start in Q0
    - If task uses full quantum → demoted to next queue
    - Delayed tasks → aging increases priority, can move up queues
    """
    
    def __init__(self):
        self.tasks: Dict[int, Task] = {}
        self.next_id = 1
        
        # Three priority queues
        self.queue0 = []  # Highest priority
        self.queue1 = []  # Medium priority
        self.queue2 = []  # Lowest priority
        
        self.time_quanta = {0: 10, 1: 20, 2: 40}  # minutes per queue
    
    def add_task(self, name, deadline_str, user_priority=5, difficulty=3, energy_level="medium"):
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
            
            task = Task(self.next_id, name, deadline, user_priority, difficulty, energy_level)
            task.current_queue = 0  # Start in highest priority queue
            task.time_quantum = self.time_quanta[0]
            task.update_priorities()
            
            self.tasks[self.next_id] = task
            self._add_to_queue(task)
            self.next_id += 1
            
            print(f"\n✅ Task '{name}' added to MLFQ Queue 0 (Highest Priority)")
            print(f"   📅 Deadline: {deadline.strftime('%Y-%m-%d %H:%M')}")
            print(f"   ⏱️  Time quantum: {task.time_quantum} minutes")
            return task.id
        except ValueError:
            print("❌ Invalid date format! Use: YYYY-MM-DD HH:MM")
            return None
    
    def _add_to_queue(self, task):
        """Add task to appropriate queue based on current_queue value"""
        if task.current_queue == 0:
            heapq.heappush(self.queue0, task)
        elif task.current_queue == 1:
            heapq.heappush(self.queue1, task)
        else:
            heapq.heappush(self.queue2, task)
    
    def _reheap_all_queues(self):
        """Rebuild all queues after priority changes"""
        self.queue0 = []
        self.queue1 = []
        self.queue2 = []
        
        for task in self.tasks.values():
            if task.status != "done":
                self._add_to_queue(task)
    
    def get_next_task(self) -> Optional[Task]:
        """MLFQ scheduling: Always pick from highest non-empty queue"""
        if self.queue0:
            return self.queue0[0]
        elif self.queue1:
            return self.queue1[0]
        elif self.queue2:
            return self.queue2[0]
        return None
    
    def execute_task_slice(self, task_id, minutes=None):
        """Simulate working on a task for a time slice"""
        if task_id not in self.tasks:
            print("❌ Task not found")
            return
        
        task = self.tasks[task_id]
        if task.status == "done":
            print("❌ Task already completed")
            return
        
        if minutes is None:
            minutes = task.time_quantum
        
        print(f"\n⏰ Executing '{task.name}' for {minutes} minutes...")
        demoted = task.execute_time_slice(minutes)
        
        if demoted:
            print(f"   ⬇️ MLFQ: Task used full quantum → Demoted to Queue {task.current_queue}")
            print(f"   ⏱️  New time quantum: {task.time_quantum} minutes")
        
        self._reheap_all_queues()
        return demoted
    
    def delay_task(self, task_id):
        if task_id in self.tasks and self.tasks[task_id].status != "done":
            task = self.tasks[task_id]
            old_queue = task.current_queue
            task.delay()
            new_queue = task.current_queue
            self._reheap_all_queues()
            
            print(f"\n⚠️  Task '{task.name}' delayed!")
            print(f"   Delay count: {task.delay_count}")
            if new_queue < old_queue:
                print(f"   ⬆️ MLFQ: Moved from Queue {old_queue} → {new_queue} (due to aging)")
        else:
            print(f"❌ Task ID {task_id} not found or already completed")
    
    def complete_task(self, task_id):
        if task_id in self.tasks and self.tasks[task_id].status != "done":
            task = self.tasks[task_id]
            task.complete()
            self._reheap_all_queues()
            print(f"\n✅ Task '{task.name}' completed! Great job!")
        else:
            print(f"❌ Task ID {task_id} not found or already done")
    
    def get_sorted_tasks(self):
        """Return all tasks organized by queue"""
        all_tasks = []
        for task in self.tasks.values():
            if task.status != "done":
                all_tasks.append(task)
        all_tasks.sort(key=lambda t: (t.current_queue, t.final_priority))
        return all_tasks
    
    def print_schedule(self):
        if not self.tasks:
            print("\n📭 No tasks yet. Add some tasks first!\n")
            return
        
        print("\n" + "="*90)
        print("📋 MLFQ SCHEDULE (Multilevel Feedback Queue - Used in Modern OS)")
        print("="*90)
        
        # Show each queue
        queues_info = [
            ("🔴 QUEUE 0 (Highest Priority)", self.queue0, "10 min quantum"),
            ("🟡 QUEUE 1 (Medium Priority)", self.queue1, "20 min quantum"),
            ("🟢 QUEUE 2 (Lowest Priority)", self.queue2, "40 min quantum")
        ]
        
        for queue_name, queue, quantum in queues_info:
            print(f"\n{queue_name} - {quantum}")
            print("-"*90)
            if not queue:
                print("   (empty)")
            else:
                print(f"{'ID':<4} {'Task Name':<22} {'Deadline':<17} {'Delays':<8} {'Used/Quantum':<14}")
                for task in sorted(queue, key=lambda t: t.final_priority):
                    deadline_str = task.deadline.strftime("%m-%d %H:%M")
                    print(f"{task.id:<4} {task.name[:21]:<22} {deadline_str:<17} {task.delay_count:<8} {task.time_used}/{task.time_quantum}min")
        
        print("\n" + "="*90)
        
        next_task = self.get_next_task()
        if next_task:
            print(f"🎯 NEXT TASK: {next_task.name} (Queue {next_task.current_queue})")
            hours_left = (next_task.deadline - datetime.now()).total_seconds() / 3600
            if hours_left < 48:
                print(f"   ⚠️  URGENT: {hours_left:.0f} hours until deadline!")
            if next_task.delay_count > 0:
                print(f"   📈 Has been delayed {next_task.delay_count} time(s) → aging active")
        print("="*90 + "\n")
    
    def explain_mlfq(self):
        print("\n" + "🔬"*35)
        print("HOW MULTILEVEL FEEDBACK QUEUE (MLFQ) WORKS")
        print("🔬"*35)
        print("""
MLFQ is used in Windows, macOS, and Linux kernels.

QUEUES:
┌─────────────────────────────────────────────────────────────┐
│ Queue 0 │ Highest Priority │ 10 min quantum │ New tasks start here │
│ Queue 1 │ Medium Priority  │ 20 min quantum │ Demoted if quantum used│
│ Queue 2 │ Lowest Priority  │ 40 min quantum │ CPU-bound tasks end here│
└─────────────────────────────────────────────────────────────┘

RULES:
1. New task → Queue 0
2. Use full quantum → Demoted to next queue
3. Aging (delayed tasks) → Can move UP queues
4. Always run tasks from highest non-empty queue

WHY THIS WORKS FOR STUDENTS:
- Short tasks finish quickly in Queue 0
- Long tasks don't block others (demoted)
- Delayed tasks become urgent (move up queues)
- NO TASK STAYS UNDONE FOREVER
        """)
        print("🔬"*35 + "\n")
        input("Press Enter to continue...")


def show_menu():
    print("\n" + "="*60)
    print("🎓 ACADEMIC TASK AGENT - COMPLETE OS SCHEDULER")
    print("   Algorithms: MLFQ + Aging + EDF")
    print("="*60)
    print("1. ➕ Add a new task")
    print("2. 📋 View MLFQ schedule")
    print("3. 🎯 Get next task recommendation")
    print("4. ⏰ Execute time slice (simulate working)")
    print("5. ⚠️  Delay a task (triggers aging)")
    print("6. ✅ Complete a task")
    print("7. 💡 Explain MLFQ algorithm")
    print("8. 🚪 Exit")
    print("="*60)


def get_task_input():
    print("\n📝 NEW TASK DETAILS:\n")
    
    name = input("Task name: ").strip()
    if not name:
        print("❌ Task name cannot be empty!")
        return None
    
    print("\nDate format: YYYY-MM-DD HH:MM")
    deadline = input("Deadline: ").strip()
    
    print("\nPriority (1=Highest, 10=Lowest)")
    try:
        priority = int(input("Priority (1-10) [default=5]: ").strip() or "5")
        if priority < 1 or priority > 10:
            priority = 5
    except ValueError:
        priority = 5
    
    return {"name": name, "deadline": deadline, "priority": priority}


def main():
    scheduler = MLFQScheduler()
    
    print("\n" + "🎯"*30)
    print("WELCOME TO YOUR COMPLETE OS-INSPIRED ACADEMIC AGENT")
    print("🎯"*30)
    print("""
This agent uses the MULTILEVEL FEEDBACK QUEUE (MLFQ) algorithm
— the same scheduler used in Windows, macOS, and Linux!

Key features:
  • 3 priority queues with different time quanta
  • Tasks start in highest queue
  • Use full quantum → demoted
  • Delayed tasks → aging moves them UP queues
  • No task ever starves
    """)
    
    while True:
        show_menu()
        choice = input("Choose (1-8): ").strip()
        
        if choice == '1':
            data = get_task_input()
            if data:
                scheduler.add_task(data["name"], data["deadline"], data["priority"])
        
        elif choice == '2':
            scheduler.print_schedule()
        
        elif choice == '3':
            next_task = scheduler.get_next_task()
            if next_task:
                print(f"\n🎯 RECOMMENDED: {next_task.name} (Queue {next_task.current_queue})")
            else:
                print("\n📭 No pending tasks!\n")
        
        elif choice == '4':
            scheduler.print_schedule()
            tasks = scheduler.get_sorted_tasks()
            if tasks:
                try:
                    task_id = int(input("\nTask ID to work on: "))
                    minutes = input("Minutes (Enter for default quantum): ")
                    minutes = int(minutes) if minutes else None
                    scheduler.execute_task_slice(task_id, minutes)
                except ValueError:
                    print("❌ Invalid input")
        
        elif choice == '5':
            scheduler.print_schedule()
            if scheduler.get_sorted_tasks():
                try:
                    task_id = int(input("\nTask ID to DELAY: "))
                    scheduler.delay_task(task_id)
                except ValueError:
                    print("❌ Invalid input")
        
        elif choice == '6':
            scheduler.print_schedule()
            if scheduler.get_sorted_tasks():
                try:
                    task_id = int(input("\nTask ID to COMPLETE: "))
                    scheduler.complete_task(task_id)
                except ValueError:
                    print("❌ Invalid input")
        
        elif choice == '7':
            scheduler.explain_mlfq()
        
        elif choice == '8':
            print("\n👋 Goodbye! Your agent used REAL OS scheduling algorithms.\n")
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()