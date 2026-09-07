const API_BASE_URL = "http://127.0.0.1:8000";

/*
 * Upload a contract to the real FastAPI backend.
 *
 * Backend endpoint:
 * POST /api/contracts/analyze
 *
 * The backend performs:
 * - PDF/DOCX text extraction
 * - OCR when required
 * - contract validation
 * - Legal-BERT clause classification
 * - entity extraction
 * - risk scoring
 * - risk findings
 */
export const uploadContract = async (file) => {
  if (!file) {
    throw new Error("No contract file selected.");
  }

  const formData = new FormData();
  formData.append("file", file);

  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/contracts/analyze`,
      {
        method: "POST",
        body: formData,
      }
    );
  } catch (error) {
    throw new Error(
      "Unable to connect to the Contract Intelligence backend. Make sure FastAPI is running on port 8000."
    );
  }

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    let message = `Contract analysis failed (${response.status}).`;

    if (data?.detail?.message) {
      message = data.detail.message;
    } else if (typeof data?.detail === "string") {
      message = data.detail;
    }

    throw new Error(message);
  }

  return data;
};


/*
 * Backend health check.
 */
export const checkBackendHealth = async () => {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}/health`);
  } catch {
    throw new Error("Contract Intelligence backend is unavailable.");
  }

  if (!response.ok) {
    throw new Error("Contract Intelligence backend is unavailable.");
  }

  return await response.json();
};
