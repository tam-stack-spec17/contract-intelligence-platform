const API_BASE_URL = "http://127.0.0.1:8000";

const getToken = () => {
  return localStorage.getItem("contractintel_token");
};

const request = async (endpoint, options = {}) => {
  const token = getToken();

  const headers = {
    Accept: "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });
  } catch (error) {
    console.error("API CONNECTION ERROR:", error);

    throw new Error(
      "Unable to connect to the Contract Intelligence backend. Make sure FastAPI is running on http://127.0.0.1:8000."
    );
  }

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;

    if (data?.detail?.message) {
      message = data.detail.message;
    } else if (typeof data?.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data?.detail)) {
      message = data.detail
        .map((item) => item?.msg || "Invalid request")
        .join(", ");
    } else if (data?.message) {
      message = data.message;
    }

    const error = new Error(message);
    error.status = response.status;
    error.responseData = data;

    throw error;
  }

  return data;
};

/* ============================================================
   AUTHENTICATION
============================================================ */

export const registerUser = async ({
  name,
  email,
  password,
  company,
}) => {
  return request("/api/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name,
      email,
      password,
      company,
    }),
  });
};

export const loginUser = async ({
  email,
  password,
}) => {
  return request("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      password,
    }),
  });
};

export const getMyProfile = async () => {
  return request("/api/auth/me");
};

export const updateProfile = async ({
  name,
  company,
}) => {
  return request("/api/auth/profile", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name,
      company,
    }),
  });
};

export const changePassword = async ({
  current_password,
  new_password,
}) => {
  return request("/api/auth/change-password", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      current_password,
      new_password,
    }),
  });
};

/* ============================================================
   FORGOT PASSWORD / OTP
============================================================ */

export const requestForgotPassword = async (email) => {
  if (!email?.trim()) {
    throw new Error("Please enter your registered email address.");
  }

  return request("/api/auth/forgot-password", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: email.trim().toLowerCase(),
    }),
  });
};

export const requestVerifyOTP = async (
  email,
  otp
) => {
  if (!email?.trim()) {
    throw new Error("Email address is required.");
  }

  if (!otp?.trim()) {
    throw new Error("Please enter the verification code.");
  }

  return request("/api/auth/verify-otp", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: email.trim().toLowerCase(),
      otp: otp.trim(),
    }),
  });
};

export const requestResetPassword = async (
  email,
  otp,
  newPassword
) => {
  if (!email?.trim()) {
    throw new Error("Email address is required.");
  }

  if (!otp?.trim()) {
    throw new Error("Verification code is required.");
  }

  if (!newPassword) {
    throw new Error("New password is required.");
  }

  if (newPassword.length < 8) {
    throw new Error(
      "New password must contain at least 8 characters."
    );
  }

  return request("/api/auth/reset-password", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: email.trim().toLowerCase(),
      otp: otp.trim(),
      new_password: newPassword,
    }),
  });
};

/* ============================================================
   CONTRACT ANALYSIS
============================================================ */

export const analyzeContract = async (file) => {
  if (!file) {
    throw new Error("No contract file selected.");
  }

  const formData = new FormData();
  formData.append("file", file);

  return request("/api/contracts/analyze", {
    method: "POST",
    body: formData,
  });
};

export const analyzeAndSaveContract = async (
  file
) => {
  if (!file) {
    throw new Error("No contract file selected.");
  }

  const formData = new FormData();
  formData.append("file", file);

  return request("/api/contracts/analyze-and-save", {
    method: "POST",
    body: formData,
  });
};

export const analyzeManyContracts = async (
  files
) => {
  if (!files?.length) {
    throw new Error("No contract files selected.");
  }

  const formData = new FormData();

  Array.from(files).forEach((file) => {
    formData.append("files", file);
  });

  return request("/api/contracts/analyze-many", {
    method: "POST",
    body: formData,
  });
};

/* ============================================================
   CONTRACT LIBRARY
============================================================ */

export const listContracts = async ({
  search,
  favorite,
  status,
  folder,
} = {}) => {
  const params = new URLSearchParams();

  if (search) {
    params.set("search", search);
  }

  if (favorite !== undefined) {
    params.set("favorite", String(favorite));
  }

  if (status) {
    params.set("status", status);
  }

  if (folder) {
    params.set("folder", folder);
  }

  const queryString = params.toString();

  return request(
    `/api/contracts${
      queryString ? `?${queryString}` : ""
    }`
  );
};

export const getContract = async (
  contractId
) => {
  return request(`/api/contracts/${contractId}`);
};

export const updateContract = async (
  contractId,
  updates
) => {
  return request(`/api/contracts/${contractId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(updates),
  });
};

export const deleteContract = async (
  contractId
) => {
  return request(`/api/contracts/${contractId}`, {
    method: "DELETE",
  });
};

/* ============================================================
   DASHBOARD
============================================================ */

export const getDashboard = async () => {
  return request("/api/dashboard");
};

export const checkBackendHealth = async () => {
  return request("/health");
};