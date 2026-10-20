import { useEffect, useRef, useState } from "react";

const CATEGORIES = [
  ["meeting", "Meeting"],
  ["class", "Class"],
  ["appointment", "Appointment"],
  ["assignment", "Assignment"],
  ["personal", "Personal task"],
];

const MOVABLE_BY_DEFAULT = {
  meeting: false,
  class: false,
  appointment: false,
  assignment: true,
  personal: true,
};

export default function EventForm({
  initial,        
  isEdit,        
  position,      
  errorField,   
  busy,         
  onSave,
  onDelete,
  onClose,
}) {
  const [values, setValues] = useState(initial);
  const [movableTouched, setMovableTouched] = useState(isEdit);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const titleRef = useRef(null);

  useEffect(() => titleRef.current?.focus(), []);

  function set(field, value) {
    setValues((old) => {
      const next = { ...old, [field]: value };
      if (field === "category" && !movableTouched) {
        next.movable = MOVABLE_BY_DEFAULT[value];
      }
      return next;
    });
  }

  function handleSubmit(e) {
    e.preventDefault();         
    onSave({ ...values, title: values.title.trim() });
  }

  const style = {
    left: Math.min(position.x + 12, window.innerWidth - 360),
    top: Math.min(Math.max(position.y - 40, 12), window.innerHeight - 470),
  };

  const fieldClass = (name) => (errorField === name ? "has-error" : "");

  return (
    <form
      className="popup"
      style={style}
      onSubmit={handleSubmit}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
      aria-label={isEdit ? "Edit event" : "Schedule an event"}
    >
      <div className="popup-header">
        <h2>{isEdit ? "Edit Event" : "Schedule an Event"}</h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </div>

      <label>
        Title
        <input
          ref={titleRef}
          className={fieldClass("title")}
          value={values.title}
          onChange={(e) => set("title", e.target.value)}
          placeholder="Give your event a name"
        />
      </label>

      <div className="row times">
        <label>
          Start
          <input
            type="datetime-local"
            className={fieldClass("start")}
            value={values.start}
            onChange={(e) => set("start", e.target.value)}
          />
        </label>
        <label>
          End
          <input
            type="datetime-local"
            className={fieldClass("end")}
            value={values.end}
            onChange={(e) => set("end", e.target.value)}
          />
        </label>
      </div>

      <label>
        Location
        <input
          value={values.location}
          onChange={(e) => set("location", e.target.value)}
          placeholder="Where do you have to go?"
        />
      </label>

      <div className="row">
        <label>
          Movable or Fixed
          <select
            value={values.movable ? "movable" : "fixed"}
            onChange={(e) => {
              setMovableTouched(true);
              set("movable", e.target.value === "movable");
            }}
          >
            <option value="movable">Movable</option>
            <option value="fixed">Fixed</option>
          </select>
        </label>
        <label>
          Priority
          <select
            value={values.priority ?? ""}
            onChange={(e) => set("priority", e.target.value || null)}
          >
            <option value="">Not set</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </label>
      </div>

      <label>
        Event type
        <select
          className={fieldClass("category")}
          value={values.category}
          onChange={(e) => set("category", e.target.value)}
        >
          {CATEGORIES.map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </label>

      <div className="popup-actions">
        <button type="submit" className="primary" disabled={busy}>
          {busy ? "Saving…" : "Schedule"}
        </button>

        {isEdit && !confirmingDelete && (
          <button type="button" onClick={() => setConfirmingDelete(true)} disabled={busy}>
            Delete
          </button>
        )}
        {isEdit && confirmingDelete && (
          <>
            <span className="confirm-text">Delete this event?</span>
            <button type="button" className="danger" onClick={onDelete} disabled={busy}>
              Yes, delete
            </button>
            <button type="button" onClick={() => setConfirmingDelete(false)}>
              No
            </button>
          </>
        )}
      </div>
    </form>
  );
}