const API_BASE_URL = "http://localhost:8000";

/*
 * Upload a contract to the FastAPI backend.
 *
 * The backend will eventually:
 * 1. Receive the PDF/DOCX
 * 2. Extract the text
 * 3. Run NLP/ML analysis
 * 4. Return entities, clauses and risk information
 */

export const uploadContract = async (file) => {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(
    `${API_BASE_URL}/api/contracts/analyze`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error(
      `Contract analysis failed: ${response.status}`
    );
  }

  return await response.json();
};


/*
 * Health check.
 *
 * This allows the frontend to check whether
 * the FastAPI backend is running.
 */

export const checkBackendHealth = async () => {
  const response = await fetch(
    `${API_BASE_URL}/health`
  );

  if (!response.ok) {
    throw new Error("Backend is not available");
  }

  return await response.json();
};