from flask import Flask, request, jsonify
from flask_cors import CORS
from full_agent import MLFQScheduler
from datetime import datetime
import threading

app = Flask(__name__)
CORS(app)

# Initialize your agent
scheduler = MLFQScheduler()

def fix_date_format(date_str):
    """Convert from '2026-05-15T14:30' to '2026-05-15 14:30'"""
    if 'T' in date_str:
        return date_str.replace('T', ' ')
    return date_str

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks with their current priorities"""
    tasks = []
    for task in scheduler.tasks.values():
        tasks.append({
            'id': task.id,
            'name': task.name,
            'deadline': task.deadline.isoformat(),
            'status': task.status,
            'delay_count': task.delay_count,
            'current_queue': task.current_queue,
            'final_priority': round(task.final_priority, 1),
            'aging_priority': round(task.aging_priority, 1),
            'edf_priority': task.edf_priority,
            'parent_id': getattr(task, 'parent_id', None),
            'is_parent': getattr(task, 'is_parent', False)
        })
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    """Add a new task"""
    try:
        data = request.json
        print(f"📥 Received task: {data}")
        
        # Fix the date format
        deadline_str = fix_date_format(data['deadline'])
        print(f"📅 Converted deadline: {deadline_str}")
        
        task_id = scheduler.add_task(
            name=data['name'],
            deadline_str=deadline_str,
            user_priority=data.get('priority', 5),
            parent_id=data.get('parent_id', None)
        )
        
        if task_id:
            print(f"✅ Task created with ID: {task_id}")
            return jsonify({'success': True, 'task_id': task_id, 'calendar_synced': True})
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/delay', methods=['POST'])
def delay_task(task_id):
    """Delay a task (triggers aging)"""
    scheduler.delay_task(task_id)
    return jsonify({'success': True})

@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Complete a task"""
    scheduler.complete_task(task_id)
    return jsonify({'success': True})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    success = scheduler.delete_task(task_id)
    return jsonify({'success': success})

@app.route('/api/tasks/<int:task_id>/deadline', methods=['PUT'])
def update_deadline(task_id):
    """Update a task deadline"""
    data = request.json
    deadline_str = fix_date_format(data['deadline'])
    success = scheduler.update_deadline(task_id, deadline_str)
    return jsonify({'success': success})

@app.route('/api/tasks/completed', methods=['DELETE'])
def clear_completed_tasks():
    """Clear all completed tasks"""
    count = scheduler.clear_completed_tasks()
    return jsonify({'success': True, 'count': count})

@app.route('/api/tasks/<int:task_id>/execute', methods=['POST'])
def execute_task(task_id):
    """Execute a time slice on a task"""
    data = request.json
    minutes = data.get('minutes', 10)
    scheduler.execute_task_slice(task_id, minutes)
    return jsonify({'success': True})

@app.route('/api/next-task', methods=['GET'])
def get_next_task():
    """Get the recommended next task"""
    task = scheduler.get_next_task()
    if task:
        return jsonify({
            'id': task.id,
            'name': task.name,
            'deadline': task.deadline.isoformat(),
            'final_priority': round(task.final_priority, 1)
        })
    return jsonify(None)

@app.route('/api/explain', methods=['GET'])
def explain_schedule():
    """Get explanation of current schedule"""
    pending = scheduler.get_sorted_tasks()
    explanations = []
    for task in pending[:3]:
        explanations.append({
            'name': task.name,
            'reason': f"Queue {task.current_queue} | Delays: {task.delay_count} | Priority: {task.final_priority}"
        })
    return jsonify(explanations)

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get productivity analytics"""
    try:
        data = scheduler.get_analytics()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/email', methods=['POST'])
def send_email_report():
    """Send an email report"""
    try:
        data = request.json
        to_email = data.get('email')
        if not to_email:
            return jsonify({"error": "Email address is required"}), 400
            
        success, message = scheduler.send_email_report(to_email)
        if success:
            return jsonify({"message": message})
        else:
            return jsonify({"error": message}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Academic Agent Backend...")
    print("📍 API running at http://localhost:5000")
    print("📍 Connect React app to this address")
    app.run(port=5000, debug=True)