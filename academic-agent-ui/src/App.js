import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FaPlus, FaCheck, FaClock, FaPause, FaCalendarAlt, FaTrash, FaEdit, FaSave, FaChartBar, FaEnvelope } from 'react-icons/fa';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import './App.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const API_URL = 'http://localhost:5000/api';

function App() {
  const [tasks, setTasks] = useState([]);
  const [nextTask, setNextTask] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTask, setNewTask] = useState({ name: '', deadline: '', priority: 5, difficulty: 3 });
  const [explanations, setExplanations] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [decomposedTasks, setDecomposedTasks] = useState({});
  const [editingDeadlineId, setEditingDeadlineId] = useState(null);
  const [editDeadlineValue, setEditDeadlineValue] = useState('');
  const [expandedTaskIds, setExpandedTaskIds] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [emailAddress, setEmailAddress] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);

  const toggleExpand = (id) => {
    setExpandedTaskIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const showToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  const fetchData = async () => {
    try {
      const [tasksRes, nextRes, explainRes, analyticsRes] = await Promise.all([
        axios.get(`${API_URL}/tasks`),
        axios.get(`${API_URL}/next-task`),
        axios.get(`${API_URL}/explain`),
        axios.get(`${API_URL}/analytics`)
      ]);

      // Build parent-child relationship
      const decomposed = {};
      const parentIds = new Set();

      // First, find all parent IDs (tasks that have children)
      tasksRes.data.forEach(task => {
        if (task.parent_id) {
          parentIds.add(task.parent_id);
        }
      });

      // Then, group children under their parents
      tasksRes.data.forEach(task => {
        if (task.parent_id) {
          if (!decomposed[task.parent_id]) {
            decomposed[task.parent_id] = [];
          }
          decomposed[task.parent_id].push(task);
        }
      });

      // Mark parent tasks
      const tasksWithParentFlag = tasksRes.data.map(task => ({
        ...task,
        is_parent: parentIds.has(task.id) && decomposed[task.id]?.length > 0
      }));

      setDecomposedTasks(decomposed);
      setTasks(tasksWithParentFlag);
      setNextTask(nextRes.data);
      setExplanations(explainRes.data);
      setAnalytics(analyticsRes.data);

      console.log("Decomposed tasks:", decomposed); // Debug log

    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const addTask = async () => {
    if (!newTask.name || !newTask.deadline) return;
    try {
      const res = await axios.post(`${API_URL}/tasks`, newTask);
      let toastMsg = `Task '${newTask.name}' added successfully!`;
      if (res.data.calendar_synced) {
        toastMsg += ' 📅 Synced with Google Calendar.';
      } else {
        toastMsg += ' ⚠️ Calendar sync skipped.';
      }
      showToast(toastMsg, 'success');
      setNewTask({ name: '', deadline: '', priority: '' });
      setShowAddForm(false);
      fetchData();
    } catch (e) {
      showToast('Error adding task', 'error');
    }
  };

  const delayTask = async (id) => {
    const task = tasks.find(t => t.id === id);
    await axios.post(`${API_URL}/tasks/${id}/delay`);
    showToast(`Task '${task?.name}' delayed! Priority has increased.`, 'warning');
    fetchData();
  };

  const completeTask = async (id) => {
    const task = tasks.find(t => t.id === id);
    await axios.post(`${API_URL}/tasks/${id}/complete`);
    showToast(`Task '${task?.name}' completed! Great job!`, 'success');
    fetchData();
  };

  const sendEmailReport = async () => {
    if (!emailAddress) {
      showToast('Please enter an email address', 'warning');
      return;
    }
    setSendingEmail(true);
    try {
      const res = await axios.post(`${API_URL}/reports/email`, { email: emailAddress });
      showToast(res.data.message || 'Report sent successfully!', 'success');
      setShowEmailModal(false);
    } catch (e) {
      showToast(e.response?.data?.error || 'Failed to send email report', 'error');
    } finally {
      setSendingEmail(false);
    }
  };

  const executeTask = async (id) => {
    await axios.post(`${API_URL}/tasks/${id}/execute`, { minutes: 10 });
    fetchData();
  };

  const deleteTask = async (id) => {
    if (window.confirm("Are you sure you want to delete this task?")) {
      await axios.delete(`${API_URL}/tasks/${id}`);
      showToast('Task deleted successfully!', 'info');
      fetchData();
    }
  };

  const updateTaskDeadline = async (id) => {
    if (!editDeadlineValue) return;
    try {
      await axios.put(`${API_URL}/tasks/${id}/deadline`, { deadline: editDeadlineValue });
      showToast('Deadline updated successfully!', 'success');
      setEditingDeadlineId(null);
      fetchData();
    } catch (e) {
      showToast('Error updating deadline', 'error');
    }
  };

  const clearCompletedTasks = async () => {
    if (window.confirm("Are you sure you want to clear all completed tasks?")) {
      const res = await axios.delete(`${API_URL}/tasks/completed`);
      showToast(`Cleared ${res.data.count} completed tasks!`, 'info');
      fetchData();
    }
  };

  const getQueueColor = (queue) => {
    switch (queue) {
      case 0: return '#ff4444';
      case 1: return '#ffaa44';
      default: return '#44ff44';
    }
  };

  const getStatusIcon = (status) => {
    if (status === 'done') return '✅';
    if (status === 'delayed') return '⚠️';
    return '⏳';
  };

  return (
    <div className="App">
      {/* Toast Notifications Container */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast toast-${toast.type}`}>
            {toast.message}
          </div>
        ))}
      </div>

      <header className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>🎓 Academic Task Agent</h1>
        </div>
        <button className="email-report-btn" onClick={() => setShowEmailModal(true)}>
          <FaEnvelope /> Email Weekly Report
        </button>
      </header>

      {analytics && (
        <div className="analytics-dashboard container">
          <div className="analytics-header">
            <h2><FaChartBar /> Productivity Dashboard</h2>
          </div>

          <div className="analytics-stats">
            <div className="stat-card">
              <h3>Total Tasks</h3>
              <div className="stat-value">{analytics.total}</div>
            </div>
            <div className="stat-card">
              <h3>Completed</h3>
              <div className="stat-value success">{analytics.completed}</div>
            </div>
            <div className="stat-card">
              <h3>Pending</h3>
              <div className="stat-value warning">{analytics.pending}</div>
            </div>
            <div className="stat-card">
              <h3>Delayed</h3>
              <div className="stat-value error">{analytics.delayed}</div>
            </div>
          </div>

          <div className="analytics-charts">
            <div className="chart-container doughnut-container">
              <h3>Priority Queues</h3>
              {analytics.queue_distribution.some(v => v > 0) ? (
                <Doughnut
                  data={{
                    labels: ['Queue 0 (Highest)', 'Queue 1 (Medium)', 'Queue 2 (Lowest)'],
                    datasets: [{
                      data: analytics.queue_distribution,
                      backgroundColor: ['#ff4444', '#ffaa44', '#44ff44'],
                      borderWidth: 0,
                    }]
                  }}
                  options={{
                    plugins: { legend: { position: 'bottom', labels: { color: '#fff' } } },
                    cutout: '70%',
                    maintainAspectRatio: false
                  }}
                />
              ) : (
                <p className="no-data">No pending tasks</p>
              )}
            </div>

            <div className="chart-container bar-container">
              <h3>Completions (Last 7 Days)</h3>
              <Bar
                data={{
                  labels: analytics.days,
                  datasets: [{
                    label: 'Tasks Completed',
                    data: analytics.completions_by_day,
                    backgroundColor: 'rgba(68, 255, 68, 0.6)',
                    borderColor: '#44ff44',
                    borderWidth: 1,
                  }]
                }}
                options={{
                  plugins: { legend: { display: false } },
                  scales: {
                    y: { beginAtZero: true, ticks: { color: '#aaa', stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.1)' } },
                    x: { ticks: { color: '#aaa' }, grid: { display: false } }
                  },
                  maintainAspectRatio: false
                }}
              />
            </div>
          </div>
        </div>
      )}

      <div className="container">
        {nextTask && (
          <div className="next-task-card">
            <h2>Recommended Next Task</h2>
            <div className="next-task-content">
              <span className="task-name">{nextTask.name}</span>
              <span className="task-priority">Priority: {nextTask.final_priority}</span>
              <span className="task-deadline">
                <FaCalendarAlt /> Due: {new Date(nextTask.deadline).toLocaleString()}
              </span>
            </div>
          </div>
        )}

        {explanations.length > 0 && (
          <div className="explanation-card">
            <h3>Why this order?</h3>
            {explanations.map((exp, idx) => (
              <div key={idx} className="explanation-item">
                <strong>{exp.name}</strong>: {exp.reason}
              </div>
            ))}
          </div>
        )}

        <button className="add-btn" onClick={() => setShowAddForm(!showAddForm)}>
          <FaPlus /> Add New Task
        </button>

        {showAddForm && (
          <div className="add-form">
            <input
              type="text"
              placeholder="Task name"
              value={newTask.name}
              onChange={(e) => setNewTask({ ...newTask, name: e.target.value })}
            />
            <input
              type="datetime-local"
              value={newTask.deadline}
              onChange={(e) => setNewTask({ ...newTask, deadline: e.target.value })}
            />
            <select
              value={newTask.priority}
              onChange={(e) => setNewTask({ ...newTask, priority: parseInt(e.target.value) })}
            >
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(p => (
                <option key={p} value={p}>Priority {p} {p === 1 ? '(Highest)' : p === 10 ? '(Lowest)' : ''}</option>
              ))}
            </select>
            <select
              value={newTask.difficulty || 3}
              onChange={(e) => setNewTask({ ...newTask, difficulty: parseInt(e.target.value) })}
              style={{ padding: '0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.2)', color: 'white', border: '1px solid rgba(255,255,255,0.1)' }}
            >
              <option value="1">Difficulty 1 (Easy)</option>
              <option value="2">Difficulty 2</option>
              <option value="3">Difficulty 3 (Medium)</option>
              <option value="4">Difficulty 4 (Hard)</option>
              <option value="5">Difficulty 5 (Very Hard - Auto Decompose)</option>
            </select>
            <button onClick={addTask}>Create Task</button>
          </div>
        )}

        {/* Simple To-Do List */}
        <div className="todo-list-container">
          <h2>To-Do List</h2>
          {tasks.filter(t => t.status !== 'done').length === 0 ? (
            <p className="no-tasks">All caught up! 🎉</p>
          ) : (
            <ul className="simple-todo-list">
              {tasks.filter(t => t.status !== 'done' && !t.parent_id)
                .sort((a, b) => a.final_priority - b.final_priority)
                .map(task => (
                  <React.Fragment key={task.id}>
                    <li className={`todo-item q-border-${task.current_queue}`}
                      style={{ cursor: task.is_parent ? 'pointer' : 'default' }}
                      onClick={() => task.is_parent && toggleExpand(task.id)}>
                      <div className="todo-info">
                        <span className="todo-name">
                          {task.is_parent && (expandedTaskIds.includes(task.id) ? '🔽 ' : '▶️ ')}
                          {task.name}
                        </span>
                        <span className="todo-meta">
                          <FaCalendarAlt className="meta-icon" /> Due: {new Date(task.deadline).toLocaleDateString()} at {new Date(task.deadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <div className="todo-actions" onClick={e => e.stopPropagation()}>
                        <button className="btn-sm complete" onClick={() => completeTask(task.id)} title="Complete Task">
                          <FaCheck />
                        </button>
                        <button className="btn-sm delete" onClick={() => deleteTask(task.id)} title="Delete Task">
                          <FaTrash />
                        </button>
                      </div>
                    </li>
                    {task.is_parent && expandedTaskIds.includes(task.id) && decomposedTasks[task.id] && (
                      <div className="subtasks-container" style={{ marginLeft: '1.5rem', borderLeft: '2px solid rgba(255,255,255,0.1)', paddingLeft: '0.5rem', marginTop: '-0.5rem', marginBottom: '0.5rem' }}>
                        {decomposedTasks[task.id].filter(t => t.status !== 'done').map(subtask => {
                          const displayName = subtask.name.includes(' - ') ? subtask.name.split(' - ').slice(1).join(' - ') : subtask.name;
                          return (
                            <li key={subtask.id} className={`todo-item q-border-${subtask.current_queue} subtask`} style={{ background: 'rgba(0,0,0,0.15)', marginTop: '0.25rem', padding: '0.5rem 1rem' }}>
                              <div className="todo-info">
                                <span className="todo-name" style={{ fontSize: '0.9em', color: 'var(--text-secondary)' }}>↳ {displayName}</span>
                                <span className="todo-meta">
                                  <FaCalendarAlt className="meta-icon" /> Due: {new Date(subtask.deadline).toLocaleDateString()} at {new Date(subtask.deadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                              <div className="todo-actions" onClick={e => e.stopPropagation()}>
                                <button className="btn-sm complete" onClick={() => completeTask(subtask.id)} title="Complete Task">
                                  <FaCheck />
                                </button>
                                <button className="btn-sm delete" onClick={() => deleteTask(subtask.id)} title="Delete Task">
                                  <FaTrash />
                                </button>
                              </div>
                            </li>
                          );
                        })}
                      </div>
                    )}
                  </React.Fragment>
                ))}
            </ul>
          )}
        </div>

        <div className="tasks-container">
          <h2>All Tasks</h2>
          <div className="queue-labels">
            <span className="q0-label"> Queue 0 (Highest - 10min)</span>
            <span className="q1-label"> Queue 1 (Medium - 20min)</span>
            <span className="q2-label"> Queue 2 (Lowest - 40min)</span>
          </div>

          {tasks.length === 0 ? (
            <p className="no-tasks">No tasks yet. Add one above!</p>
          ) : (
            <table className="tasks-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Task</th>
                  <th>Deadline</th>
                  <th>Queue</th>
                  <th>Priority</th>
                  <th>Delays</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tasks.filter(t => t.status !== 'done' && !t.parent_id).map(task => (
                  <React.Fragment key={task.id}>
                    <tr
                      style={{ borderLeft: `4px solid ${getQueueColor(task.current_queue)}`, cursor: task.is_parent ? 'pointer' : 'default', background: task.is_parent ? 'rgba(255,255,255,0.02)' : '' }}
                      onClick={() => task.is_parent && toggleExpand(task.id)}
                    >
                      <td>{getStatusIcon(task.status)}</td>
                      <td className="task-name-cell">
                        {task.is_parent && (expandedTaskIds.includes(task.id) ? '🔽 ' : '▶️ ')}
                        {task.name}
                      </td>
                      <td onClick={e => e.stopPropagation()}>
                        {editingDeadlineId === task.id ? (
                          <div className="inline-edit">
                            <input
                              type="datetime-local"
                              value={editDeadlineValue}
                              onChange={(e) => setEditDeadlineValue(e.target.value)}
                            />
                            <button className="btn-sm complete" onClick={() => updateTaskDeadline(task.id)} title="Save"><FaSave /></button>
                            <button className="btn-sm delete" onClick={() => setEditingDeadlineId(null)} title="Cancel">X</button>
                          </div>
                        ) : (
                          <div className="deadline-display">
                            {new Date(task.deadline).toLocaleString()}
                            <button className="icon-btn edit-icon" onClick={() => {
                              setEditingDeadlineId(task.id);
                              const d = new Date(task.deadline);
                              const pad = (n) => n.toString().padStart(2, '0');
                              setEditDeadlineValue(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`);
                            }}>
                              <FaEdit />
                            </button>
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`queue-badge q${task.current_queue}`}>
                          Q{task.current_queue}
                        </span>
                      </td>
                      <td>{task.final_priority}</td>
                      <td>{task.delay_count}</td>
                      <td className="actions" onClick={e => e.stopPropagation()}>
                        <button className="action-btn execute" onClick={() => executeTask(task.id)} title="Work">
                          <FaClock />
                        </button>
                        <button className="action-btn delay" onClick={() => delayTask(task.id)} title="Delay">
                          <FaPause />
                        </button>
                        <button className="action-btn complete" onClick={() => completeTask(task.id)} title="Complete">
                          <FaCheck />
                        </button>
                        <button className="action-btn delete" onClick={() => deleteTask(task.id)} title="Delete">
                          <FaTrash />
                        </button>
                      </td>
                    </tr>
                    {task.is_parent && expandedTaskIds.includes(task.id) && decomposedTasks[task.id] && (
                      decomposedTasks[task.id].filter(t => t.status !== 'done').map(subtask => {
                        const displayName = subtask.name.includes(' - ') ? subtask.name.split(' - ').slice(1).join(' - ') : subtask.name;
                        return (
                          <tr key={subtask.id} style={{ borderLeft: `4px solid ${getQueueColor(subtask.current_queue)}`, backgroundColor: 'rgba(0,0,0,0.15)' }}>
                            <td>{getStatusIcon(subtask.status)}</td>
                            <td className="task-name-cell" style={{ paddingLeft: '2rem', fontSize: '0.9em', color: 'var(--text-secondary)' }}>↳ {displayName}</td>
                            <td onClick={e => e.stopPropagation()}>
                              {editingDeadlineId === subtask.id ? (
                                <div className="inline-edit">
                                  <input
                                    type="datetime-local"
                                    value={editDeadlineValue}
                                    onChange={(e) => setEditDeadlineValue(e.target.value)}
                                  />
                                  <button className="btn-sm complete" onClick={() => updateTaskDeadline(subtask.id)} title="Save"><FaSave /></button>
                                  <button className="btn-sm delete" onClick={() => setEditingDeadlineId(null)} title="Cancel">X</button>
                                </div>
                              ) : (
                                <div className="deadline-display">
                                  {new Date(subtask.deadline).toLocaleString()}
                                  <button className="icon-btn edit-icon" onClick={() => {
                                    setEditingDeadlineId(subtask.id);
                                    const d = new Date(subtask.deadline);
                                    const pad = (n) => n.toString().padStart(2, '0');
                                    setEditDeadlineValue(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`);
                                  }}>
                                    <FaEdit />
                                  </button>
                                </div>
                              )}
                            </td>
                            <td>
                              <span className={`queue-badge q${subtask.current_queue}`}>
                                Q{subtask.current_queue}
                              </span>
                            </td>
                            <td>{subtask.final_priority}</td>
                            <td>{subtask.delay_count}</td>
                            <td className="actions" onClick={e => e.stopPropagation()}>
                              <button className="action-btn execute" onClick={() => executeTask(subtask.id)} title="Work">
                                <FaClock />
                              </button>
                              <button className="action-btn delay" onClick={() => delayTask(subtask.id)} title="Delay">
                                <FaPause />
                              </button>
                              <button className="action-btn complete" onClick={() => completeTask(subtask.id)} title="Complete">
                                <FaCheck />
                              </button>
                              <button className="action-btn delete" onClick={() => deleteTask(subtask.id)} title="Delete">
                                <FaTrash />
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {tasks.filter(t => t.status === 'done').length > 0 && (
          <div className="completed-section">
            <div className="completed-header">
              <h3>Completed Tasks</h3>
              <button className="clear-btn" onClick={clearCompletedTasks}>Clear All</button>
            </div>
            {tasks.filter(t => t.status === 'done').map(task => (
              <div key={task.id} className="completed-task">
                <span>{task.name}</span>
                <span className="completed-date">Completed</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {showEmailModal && (
        <div className="modal-overlay" onClick={() => setShowEmailModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2><FaEnvelope /> Send Productivity Report</h2>
            <p style={{ margin: '1rem 0', color: '#aaa' }}>Enter the recipient's email address to send a detailed analytics report for this week.</p>
            <input
              type="email"
              placeholder="recipient@example.com"
              value={emailAddress}
              onChange={e => setEmailAddress(e.target.value)}
              className="email-input"
              style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', border: 'none', background: 'rgba(255,255,255,0.1)', color: '#fff', marginBottom: '1.5rem' }}
            />
            <div className="modal-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
              <button className="cancel-btn" onClick={() => setShowEmailModal(false)} style={{ padding: '0.5rem 1rem', background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '8px', cursor: 'pointer' }}>Cancel</button>
              <button className="send-btn" onClick={sendEmailReport} disabled={sendingEmail} style={{ padding: '0.5rem 1rem', background: 'var(--primary)', border: 'none', color: '#fff', borderRadius: '8px', cursor: 'pointer' }}>
                {sendingEmail ? 'Sending...' : 'Send Report'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;