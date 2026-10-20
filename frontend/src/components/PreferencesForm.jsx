import { useEffect, useRef, useState } from "react";

const CATEGORIES = [
  ["meeting", "Meetings"],
  ["class", "Classes"],
  ["appointment", "Appointments"],
  ["assignment", "Assignments"],
  ["personal", "Personal tasks"],
];

export default function PreferencesForm({
  initial,       
  firstLaunch,   
  errorField,     
  busy,
  onSave,
  onClose,
}) {
  const [prefs, setPrefs] = useState(initial);
  const firstFieldRef = useRef(null);

  useEffect(() => firstFieldRef.current?.focus(), []);

  const setTime = (category, value) =>
    setPrefs((old) => ({
      ...old,
      preferredTime: { ...old.preferredTime, [category]: value || null },
    }));

  const fieldClass = (name) => (errorField === name ? "has-error" : "");

  return (
    <div className="overlay">
      <form
        className="popup prefs-popup"
        onSubmit={(e) => { e.preventDefault(); onSave(prefs); }}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
        aria-label="Preferences"
      >
        <div className="popup-header">
          <h2>{firstLaunch ? "Welcome! Set your preferences" : "Preferences"}</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        {firstLaunch && (
          <p className="panel-note">
            These help the planner suggest good times. You can change them later
            with the ⚙ button.
          </p>
        )}

        <div className="prefs-section">Preferred time of day</div>
        {CATEGORIES.map(([category, label], i) => (
          <label key={category} className="prefs-row">
            <span>{label}</span>
            <select
              ref={i === 0 ? firstFieldRef : undefined}
              value={prefs.preferredTime[category] ?? ""}
              onChange={(e) => setTime(category, e.target.value)}
            >
              <option value="morning">Morning (6:00–12:00)</option>
              <option value="afternoon">Afternoon (12:00–17:00)</option>
              <option value="night">Night (after 17:00)</option>
              <option value="">No preference</option>
            </select>
          </label>
        ))}

        <div className="prefs-section">Cutoff</div>
        <label className="prefs-row">
          <span>No tasks after</span>
          <input
            type="time"
            className={fieldClass("cutoff")}
            value={prefs.cutoff}
            onChange={(e) => setPrefs((old) => ({ ...old, cutoff: e.target.value }))}
          />
        </label>
        <label className="prefs-row">
          <span>Cutoff mode</span>
          <select
            value={prefs.cutoffMode}
            onChange={(e) => setPrefs((old) => ({ ...old, cutoffMode: e.target.value }))}
          >
            <option value="Flexible">Flexible</option>
            <option value="Strict">Strict</option>
          </select>
        </label>
        <p className="panel-note">
          {prefs.cutoffMode === "Strict"
            ? "Strict: nothing is ever suggested after the cutoff."
            : "Flexible: late slots can be suggested, but always rank last."}
        </p>

        <div className="prefs-section">Working hours (where the planner looks)</div>
        <div className="row">
          <label>
            From
            <input
              type="time"
              className={fieldClass("workingHours")}
              value={prefs.workingHours.start}
              onChange={(e) => setPrefs((old) => ({
                ...old, workingHours: { ...old.workingHours, start: e.target.value } }))}
            />
          </label>
          <label>
            To
            <input
              type="time"
              className={fieldClass("workingHours")}
              value={prefs.workingHours.end}
              onChange={(e) => setPrefs((old) => ({
                ...old, workingHours: { ...old.workingHours, end: e.target.value } }))}
            />
          </label>
        </div>

        <div className="popup-actions">
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Saving…" : "Save"}
          </button>
          {firstLaunch && (
            <button type="button" onClick={onClose}>Skip, use defaults</button>
          )}
        </div>
      </form>
    </div>
  );
}