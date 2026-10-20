const BASE = "/api";
async function request(method, path, body) {
  let response;
  try {
    response = await fetch(BASE + path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw {
      status: 0,
      error: {
        code: null, field: null,
        message: "Cannot reach the server",
        detail: "Make sure the backend is running on port 8000, then try again.",
      },
    };
  }

  const data = await response.json().catch(() => ({}));
  if (response.ok) return data;

  if (data.error) throw { status: response.status, error: data.error };

  const error =
    response.status === 422
      ? { message: "Invalid input",
          detail: "Some of the information sent was in the wrong format." }
      : response.status >= 500
      ? { message: "Cannot reach the server",
          detail: "Make sure the backend is running on port 8000, then try again." }
      : { message: "Something went wrong",
          detail: "The action could not be completed. Nothing was changed." };
  throw { status: response.status, error: { code: null, field: null, ...error } };
}

export const getEvents = () => request("GET", "/events");
export const createEvent = (body) => request("POST", "/events", body);
export const updateEvent = (id, body) => request("PUT", `/events/${id}`, body);
export const deleteEvent = (id) => request("DELETE", `/events/${id}`);
export const getAlternatives = (id) => request("GET", `/events/${id}/alternatives`);

export const getTasks = () => request("GET", "/tasks");
export const createTask = (body) => request("POST", "/tasks", body);
export const deleteTask = (id) => request("DELETE", `/tasks/${id}`);
export const getSuggestions = (id) => request("POST", `/tasks/${id}/suggestions`);
export const acceptSlot = (id, body) => request("POST", `/tasks/${id}/accept`, body);

export const getPreferences = () => request("GET", "/preferences");
export const savePreferences = (body) => request("PUT", "/preferences", body);