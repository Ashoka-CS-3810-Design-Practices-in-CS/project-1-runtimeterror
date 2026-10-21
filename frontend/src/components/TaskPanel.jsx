import { useEffect, useState } from "react";
import * as api from "../api";

const CATEGORIES = [
  ["assignment", "Assignment"],
  ["personal", "Personal task"],
  ["meeting", "Meeting"],
  ["class", "Class"],
  ["appointment", "Appointment"],
];

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function when(text) {
  const d = new Date(text);
  return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}, ${text.slice(11, 16)}`;
}

const EMPTY_FORM = {
  name: "", durationMinutes: 60, toDate: "", priority: "Medium", category: "assignment",
};

export default function TaskPanel({ onEventCreated, onError }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [errorField, setErrorField] = useState(null);
  const [tasks, setTasks] = useState([]);          
  const [activeTask, setActiveTask] = useState(null);
  const [result, setResult] = useState(null);      
  const [loading, setLoading] = useState(false);
  const [chosen, setChosen] = useState(null);      

  useEffect(() => {
    api.getTasks().then((data) => setTasks(data.tasks));
  }, []);

  const set = (field, value) => setForm((old) => ({ ...old, [field]: value }));

  async function suggestFor(task) {
    setActiveTask(task);
    setResult(null);
    setChosen(null);
    setLoading(true);           
    try {
      setResult(await api.getSuggestions(task.id));
    } catch (err) {
      onError(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      const { task } = await api.createTask({
        name: form.name.trim(),
        category: form.category,
        durationMinutes: Number(form.durationMinutes),
        priority: form.priority,
        toDate: form.toDate || null,     
      });
      setErrorField(null);
      setForm(EMPTY_FORM);
      setTasks((old) => [...old, task]);
      await suggestFor(task);
    } catch (err) {
      setErrorField(err?.error?.field ?? null);   
      onError(err);
    }
  }

  async function handleAccept() {
    const slot = result.slots[chosen];
    try {
      const res = await api.acceptSlot(activeTask.id, { start: slot.start, end: slot.end });
      onEventCreated(res.event, res.conflicts);
      setTasks((old) => old.filter((t) => t.id !== res.removedTaskId));
      setActiveTask(null);
      setResult(null);
    } catch (err) {
      onError(err);
      if (err?.status === 409) await suggestFor(activeTask);
    }
  }

  async function handleDeleteTask(task) {
    try {
      await api.deleteTask(task.id);
      setTasks((old) => old.filter((t) => t.id !== task.id));
      if (activeTask?.id === task.id) {
        setActiveTask(null);
        setResult(null);
      }
    } catch (err) {
      onError(err);
    }
  }

  const fieldClass = (name) => (errorField === name ? "has-error" : "");

  return (
    <div className="task-panel">
      <form className="task-form" onSubmit={handleSubmit}>
        <input
          className={fieldClass("name")}
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="Give your task a name"
          aria-label="Task name"
        />
        <div className="row">
          <label>
            Duration (min)
            <input
              type="number" min="5" step="5"
              className={fieldClass("durationMinutes")}
              value={form.durationMinutes}
              onChange={(e) => set("durationMinutes", e.target.value)}
            />
          </label>
          <label>
            Deadline
            <input type="date" value={form.toDate}
              onChange={(e) => set("toDate", e.target.value)} />
          </label>
        </div>
        <div className="row">
          <label>
            Priority
            <select className={fieldClass("priority")} value={form.priority}
              onChange={(e) => set("priority", e.target.value)}>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </label>
          <label>
            Task type
            <select value={form.category} onChange={(e) => set("category", e.target.value)}>
              {CATEGORIES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
            </select>
          </label>
        </div>
        <button type="submit" className="primary">Suggest Slots</button>
      </form>

      {activeTask && (
        <div className="suggestions">
          <div className="panel-note">Suggestions for <strong>{activeTask.name}</strong>:</div>
          {loading && <p className="panel-note">Finding the best times…</p>}

          {result && result.slots.length === 0 && (
            <div className="no-slot">
              <strong>No suitable slot found</strong>
              <p className="panel-note">{result.noSlotReason}</p>
              {result.tryInstead?.length > 0 && (
                <p className="panel-note">Try: {result.tryInstead.join(", ")}.</p>
              )}
            </div>
          )}

          {result?.slots.map((slot, i) => (
            <button
              key={slot.start}
              type="button"
              className={`slot-card ${chosen === i ? "selected" : ""}`}
              onClick={() => setChosen(i)}
              aria-pressed={chosen === i}
            >
              <div className="slot-time">
                {i + 1}. {when(slot.start)} – {slot.end.slice(11, 16)}
              </div>
              {slot.reasons.map((r) => <div key={r} className="slot-reason">{r}</div>)}
            </button>
          ))}

          {result?.slots.length > 0 && (
            <div className="popup-actions">
              <button type="button" className="primary" disabled={chosen === null}
                onClick={handleAccept}>
                Accept
              </button>
              <button type="button" onClick={() => { setActiveTask(null); setResult(null); }}>
                Not now
              </button>
            </div>
          )}
        </div>
      )}

      {tasks.length > 0 && (
        <div className="task-list">
          <div className="panel-note">Unscheduled tasks</div>
          {tasks.map((t) => (
            <div key={t.id} className="task-row">
              <span>
                <strong>{t.name}</strong> · {t.durationMinutes} min · {t.priority}
              </span>
              <span>
                <button type="button" onClick={() => suggestFor(t)}>Suggest</button>
                <button type="button" className="icon-button"
                  aria-label={`Delete ${t.name}`} onClick={() => handleDeleteTask(t)}>✕</button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}