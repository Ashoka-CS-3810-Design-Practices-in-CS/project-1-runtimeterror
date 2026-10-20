import { useState } from "react";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"];
const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

const sameDay = (a, b) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate();

export default function MiniCalendar({ onPick }) {
  const today = new Date();
  const [month, setMonth] = useState(new Date(today.getFullYear(), today.getMonth(), 1));

  const sinceMonday = (month.getDay() + 6) % 7;
  const first = new Date(month.getFullYear(), month.getMonth(), 1 - sinceMonday);
  const days = Array.from({ length: 42 }, (_, i) =>
    new Date(first.getFullYear(), first.getMonth(), first.getDate() + i));

  const changeMonth = (step) =>
    setMonth(new Date(month.getFullYear(), month.getMonth() + step, 1));

  return (
    <div className="mini-calendar">
      <div className="mini-header">
        <span>{MONTHS[month.getMonth()]} {month.getFullYear()}</span>
        <span>
          <button type="button" className="icon-button" aria-label="Previous month"
            onClick={() => changeMonth(-1)}>‹</button>
          <button type="button" className="icon-button" aria-label="Next month"
            onClick={() => changeMonth(1)}>›</button>
        </span>
      </div>
      <div className="mini-grid">
        {WEEKDAYS.map((d) => <span key={d} className="mini-weekday">{d}</span>)}
        {days.map((day) => (
          <button
            key={day.toDateString()}
            type="button"
            className={[
              "mini-day",
              day.getMonth() !== month.getMonth() ? "other-month" : "",
              sameDay(day, today) ? "today" : "",
            ].join(" ")}
            onClick={() => onPick(day)}
            aria-label={day.toDateString()}
          >
            {day.getDate()}
          </button>
        ))}
      </div>
    </div>
  );
}