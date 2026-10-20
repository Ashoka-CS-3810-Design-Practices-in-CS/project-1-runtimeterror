import { useState } from "react";

export default function Notification({ error, onClose }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="notification" role="alert">
      <strong>{error.message}</strong>
      {expanded && <p>{error.detail}</p>}
      <div className="notification-actions">
        {!expanded && error.detail && (
          <button type="button" onClick={() => setExpanded(true)}>Explain</button>
        )}
        <button type="button" className="primary" onClick={onClose}>Okay</button>
      </div>
    </div>
  );
}