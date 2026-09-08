import { useEffect, useMemo, useRef, useState } from "react";
import {
  analyzeAndSaveContract,
  deleteContract,
  getDashboard,
  getMyProfile,
  listContracts,
  loginUser,
  registerUser,
  updateContract,
  updateProfile,
  changePassword,
  getContract,
  requestForgotPassword,
  requestVerifyOTP,
  requestResetPassword,
} from "./services/api";
import "./App.css";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: "⌂" },
  { id: "contracts", label: "Contract Library", icon: "▤" },
  { id: "risk", label: "Risk Center", icon: "!" },
  { id: "clauses", label: "Clause Intelligence", icon: "◈" },
  { id: "entities", label: "Entities", icon: "◎" },
  { id: "settings", label: "Settings", icon: "⚙" },
];

const riskClass = (level = "") => {
  const value = level.toUpperCase();

  if (value === "HIGH") return "risk-high";
  if (value === "MEDIUM") return "risk-medium";
  return "risk-low";
};

const formatDate = (value) => {
  if (!value) return "—";

  try {
    return new Date(value).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return value;
  }
};

const formatScore = (score) => {
  if (
    score === null ||
    score === undefined ||
    Number.isNaN(Number(score))
  ) {
    return "—";
  }

  return Number(score).toFixed(1);
};

function App() {
  const [session, setSession] = useState(() => {
    const token = localStorage.getItem("contractintel_token");
    const user = localStorage.getItem("contractintel_user");

    let parsedUser = null;

    try {
      parsedUser = user ? JSON.parse(user) : null;
    } catch {
      parsedUser = null;
    }

    return {
      token,
      user: parsedUser,
    };
  });

  const [activePage, setActivePage] = useState("dashboard");
  const [contracts, setContracts] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [profile, setProfile] = useState(session.user);

  const [selectedContract, setSelectedContract] =
    useState(null);
  const [selectedAnalysis, setSelectedAnalysis] =
    useState(null);

  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");

  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [authMode, setAuthMode] = useState("login");

  const [authForm, setAuthForm] = useState({
    name: "",
    email: "",
    password: "",
    company: "",
  });

  const [profileForm, setProfileForm] = useState({
    name: "",
    company: "",
  });

  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
  });

  const [showUserMenu, setShowUserMenu] =
    useState(false);

  const [showUploadPanel, setShowUploadPanel] =
    useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] =
    useState(false);

  const fileInputRef = useRef(null);

  const isAuthenticated = Boolean(session.token);

  const setAuth = (data) => {
    localStorage.setItem(
      "contractintel_token",
      data.access_token
    );

    localStorage.setItem(
      "contractintel_user",
      JSON.stringify(data.user)
    );

    setSession({
      token: data.access_token,
      user: data.user,
    });

    setProfile(data.user);

    setProfileForm({
      name: data.user?.name || "",
      company: data.user?.company || "",
    });
  };

  const logout = () => {
    localStorage.removeItem("contractintel_token");
    localStorage.removeItem("contractintel_user");

    setSession({
      token: null,
      user: null,
    });

    setContracts([]);
    setDashboard(null);
    setSelectedContract(null);
    setSelectedAnalysis(null);
    setActivePage("dashboard");
    setShowUserMenu(false);
  };

  const loadWorkspace = async () => {
    if (!localStorage.getItem("contractintel_token")) {
      return;
    }

    setPageLoading(true);
    setError("");

    try {
      const [
        contractData,
        dashboardData,
        userData,
      ] = await Promise.all([
        listContracts(),
        getDashboard(),
        getMyProfile(),
      ]);

      setContracts(contractData?.contracts || []);
      setDashboard(dashboardData || null);
      setProfile(userData);

      localStorage.setItem(
        "contractintel_user",
        JSON.stringify(userData)
      );

      setSession((previous) => ({
        ...previous,
        user: userData,
      }));

      setProfileForm({
        name: userData?.name || "",
        company: userData?.company || "",
      });
    } catch (err) {
      if (
        err?.message
          ?.toLowerCase()
          .includes("authentication") ||
        err?.message?.toLowerCase().includes("token") ||
        err?.status === 401
      ) {
        logout();
      } else {
        setError(
          err.message ||
            "Unable to load workspace."
        );
      }
    } finally {
      setPageLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadWorkspace();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    const handleNavigation = (event) => {
      if (event.detail) {
        setActivePage(event.detail);
      }
    };

    window.addEventListener(
      "contractiq-nav",
      handleNavigation
    );

    return () => {
      window.removeEventListener(
        "contractiq-nav",
        handleNavigation
      );
    };
  }, []);

  const handleAuthSubmit = async (event) => {
    event.preventDefault();

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      let data;

      if (authMode === "login") {
        data = await loginUser({
          email: authForm.email,
          password: authForm.password,
        });
      } else {
        data = await registerUser({
          name: authForm.name,
          email: authForm.email,
          password: authForm.password,
          company: authForm.company,
        });
      }

      setAuth(data);

      setSuccess(
        authMode === "login"
          ? "Welcome back."
          : "Your workspace has been created."
      );

      setAuthForm({
        name: "",
        email: "",
        password: "",
        company: "",
      });
    } catch (err) {
      setError(
        err.message ||
          "Authentication failed."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (files) => {
    if (!files?.length) return;

    setUploadLoading(true);
    setError("");
    setSuccess("");

    try {
      for (const file of Array.from(files)) {
        await analyzeAndSaveContract(file);
      }

      setSuccess(
        files.length === 1
          ? "Contract analyzed and saved successfully."
          : `${files.length} contracts analyzed and saved successfully.`
      );

      setShowUploadPanel(false);

      await loadWorkspace();

      setActivePage("contracts");
    } catch (err) {
      setError(
        err.message ||
          "Contract analysis failed."
      );
    } finally {
      setUploadLoading(false);
    }
  };

  const openContract = async (contract) => {
    setLoading(true);
    setError("");

    try {
      const data = await getContract(contract.id);

      setSelectedContract(data.contract);
      setSelectedAnalysis(data.analysis);
    } catch (err) {
      setError(
        err.message ||
          "Unable to open contract."
      );
    } finally {
      setLoading(false);
    }
  };

  const toggleFavorite = async (contract) => {
    try {
      const result = await updateContract(
        contract.id,
        {
          favorite: !contract.favorite,
        }
      );

      setContracts((previous) =>
        previous.map((item) =>
          item.id === contract.id
            ? result.contract
            : item
        )
      );

      setSuccess(
        result.contract.favorite
          ? "Added to favorites."
          : "Removed from favorites."
      );
    } catch (err) {
      setError(
        err.message ||
          "Unable to update contract."
      );
    }
  };

  const handleStatusChange = async (
    contract,
    status
  ) => {
    try {
      const result = await updateContract(
        contract.id,
        {
          status,
        }
      );

      setContracts((previous) =>
        previous.map((item) =>
          item.id === contract.id
            ? result.contract
            : item
        )
      );

      setSuccess(
        "Contract status updated."
      );
    } catch (err) {
      setError(
        err.message ||
          "Unable to update contract."
      );
    }
  };

  const handleDelete = async () => {
    if (!selectedContract) return;

    setLoading(true);

    try {
      await deleteContract(
        selectedContract.id
      );

      setContracts((previous) =>
        previous.filter(
          (item) =>
            item.id !== selectedContract.id
        )
      );

      setSelectedContract(null);
      setSelectedAnalysis(null);
      setShowDeleteConfirm(false);

      await loadWorkspace();

      setSuccess(
        "Contract deleted successfully."
      );
    } catch (err) {
      setError(
        err.message ||
          "Unable to delete contract."
      );
    } finally {
      setLoading(false);
    }
  };

  const saveProfile = async (event) => {
    event.preventDefault();

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const result = await updateProfile({
        name: profileForm.name,
        company: profileForm.company,
      });

      setProfile(result.user);

      localStorage.setItem(
        "contractintel_user",
        JSON.stringify(result.user)
      );

      setSession((previous) => ({
        ...previous,
        user: result.user,
      }));

      setSuccess(
        "Profile updated successfully."
      );
    } catch (err) {
      setError(
        err.message ||
          "Unable to update profile."
      );
    } finally {
      setLoading(false);
    }
  };

  const savePassword = async (event) => {
    event.preventDefault();

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      await changePassword(passwordForm);

      setPasswordForm({
        current_password: "",
        new_password: "",
      });

      setSuccess(
        "Password changed successfully."
      );
    } catch (err) {
      setError(
        err.message ||
          "Unable to change password."
      );
    } finally {
      setLoading(false);
    }
  };

  const filteredContracts = useMemo(() => {
    const query = search
      .trim()
      .toLowerCase();

    return contracts.filter((contract) => {
      const matchesSearch =
        !query ||
        contract.filename
          ?.toLowerCase()
          .includes(query) ||
        contract.folder
          ?.toLowerCase()
          .includes(query);

      const matchesRisk =
        riskFilter === "ALL" ||
        contract.risk_level?.toUpperCase() ===
          riskFilter;

      return matchesSearch && matchesRisk;
    });
  }, [
    contracts,
    search,
    riskFilter,
  ]);

  if (!isAuthenticated) {
    return (
      <AuthScreen
        mode={authMode}
        setMode={setAuthMode}
        form={authForm}
        setForm={setAuthForm}
        onSubmit={handleAuthSubmit}
        loading={loading}
        error={error}
        setError={setError}
      />
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            CI
          </div>

          <div>
            <div className="brand-name">
              ContractIQ
            </div>

            <div className="brand-subtitle">
              Intelligence Platform
            </div>
          </div>
        </div>

        <div className="workspace-label">
          WORKSPACE
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${
                activePage === item.id
                  ? "active"
                  : ""
              }`}
              onClick={() => {
                setActivePage(item.id);
                setSelectedContract(null);
                setSelectedAnalysis(null);
              }}
            >
              <span className="nav-icon">
                {item.icon}
              </span>

              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="ai-status">
            <span className="status-dot" />

            <div>
              <strong>
                AI Engine Online
              </strong>

              <span>
                Legal-BERT • 41 classes
              </span>
            </div>
          </div>

          <div className="sidebar-user">
            <div className="avatar">
              {(profile?.name || "U")
                .charAt(0)
                .toUpperCase()}
            </div>

            <div className="sidebar-user-info">
              <strong>
                {profile?.name || "User"}
              </strong>

              <span>
                {profile?.company ||
                  "Workspace"}
              </span>
            </div>

            <button
              className="logout-mini"
              onClick={logout}
              title="Logout"
            >
              ↪
            </button>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="breadcrumb">
              Contract Intelligence
              <span>/</span>
              {
                navItems.find(
                  (item) =>
                    item.id === activePage
                )?.label
              }
            </div>

            <h1>
              {activePage === "dashboard" &&
                "Portfolio Overview"}

              {activePage === "contracts" &&
                "Contract Library"}

              {activePage === "risk" &&
                "Risk Center"}

              {activePage === "clauses" &&
                "Clause Intelligence"}

              {activePage === "entities" &&
                "Entity Intelligence"}

              {activePage === "settings" &&
                "Workspace Settings"}
            </h1>
          </div>

          <div className="topbar-actions">
            <div className="system-pill">
              <span className="status-dot" />
              AI Ready
            </div>

            <button
              className="primary-button"
              onClick={() =>
                setShowUploadPanel(true)
              }
            >
              <span>+</span>
              Analyze Contract
            </button>

            <div className="profile-menu-wrapper">
              <button
                className="profile-trigger"
                onClick={() =>
                  setShowUserMenu(
                    (previous) =>
                      !previous
                  )
                }
              >
                <div className="avatar small">
                  {(profile?.name || "U")
                    .charAt(0)
                    .toUpperCase()}
                </div>

                <span>
                  {profile?.name || "User"}
                </span>

                <span className="chevron">
                  ▾
                </span>
              </button>

              {showUserMenu && (
                <div className="profile-menu">
                  <button
                    onClick={() => {
                      setActivePage(
                        "settings"
                      );
                      setShowUserMenu(false);
                    }}
                  >
                    Profile & Settings
                  </button>

                  <button
                    onClick={logout}
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {error && (
          <div className="alert error-alert">
            <span>!</span>

            <div>{error}</div>

            <button
              onClick={() =>
                setError("")
              }
            >
              ×
            </button>
          </div>
        )}

        {success && (
          <div className="alert success-alert">
            <span>✓</span>

            <div>{success}</div>

            <button
              onClick={() =>
                setSuccess("")
              }
            >
              ×
            </button>
          </div>
        )}

        {pageLoading ? (
          <LoadingWorkspace />
        ) : (
          <>
            {activePage ===
              "dashboard" && (
              <DashboardPage
                dashboard={dashboard}
                contracts={contracts}
                onOpen={openContract}
                onUpload={() =>
                  setShowUploadPanel(
                    true
                  )
                }
              />
            )}

            {activePage ===
              "contracts" && (
              <ContractsPage
                contracts={
                  filteredContracts
                }
                total={contracts.length}
                search={search}
                setSearch={setSearch}
                riskFilter={riskFilter}
                setRiskFilter={
                  setRiskFilter
                }
                onOpen={openContract}
                onUpload={() =>
                  setShowUploadPanel(
                    true
                  )
                }
                onFavorite={
                  toggleFavorite
                }
                onStatusChange={
                  handleStatusChange
                }
              />
            )}

            {activePage === "risk" && (
              <RiskCenterPage
                contracts={contracts}
                onOpen={openContract}
              />
            )}

            {activePage ===
              "clauses" && (
              <ClauseIntelligencePage
                contracts={contracts}
                onOpen={openContract}
              />
            )}

            {activePage ===
              "entities" && (
              <EntitiesPage
                contracts={contracts}
                onOpen={openContract}
              />
            )}

            {activePage ===
              "settings" && (
              <SettingsPage
                profile={profile}
                profileForm={
                  profileForm
                }
                setProfileForm={
                  setProfileForm
                }
                passwordForm={
                  passwordForm
                }
                setPasswordForm={
                  setPasswordForm
                }
                saveProfile={
                  saveProfile
                }
                savePassword={
                  savePassword
                }
                loading={loading}
                logout={logout}
              />
            )}
          </>
        )}
      </main>

      {showUploadPanel && (
        <UploadModal
          inputRef={fileInputRef}
          loading={uploadLoading}
          onClose={() =>
            setShowUploadPanel(false)
          }
          onFiles={handleUpload}
        />
      )}

      {selectedContract && (
        <ContractModal
          contract={selectedContract}
          analysis={selectedAnalysis}
          onClose={() => {
            setSelectedContract(null);
            setSelectedAnalysis(null);
          }}
          onDelete={() =>
            setShowDeleteConfirm(
              true
            )
          }
        />
      )}

      {showDeleteConfirm && (
        <ConfirmModal
          title="Delete contract?"
          message="This will remove the saved contract and its analysis from your workspace."
          onCancel={() =>
            setShowDeleteConfirm(
              false
            )
          }
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
}

function AuthScreen({
  mode,
  setMode,
  form,
  setForm,
  onSubmit,
  loading,
  error,
  setError,
}) {
  const [forgotStep, setForgotStep] =
    useState("email");

  const [forgotEmail, setForgotEmail] =
    useState("");

  const [otp, setOtp] = useState("");

  const [
    newPassword,
    setNewPassword,
  ] = useState("");

  const [
    confirmPassword,
    setConfirmPassword,
  ] = useState("");

  const [
    forgotLoading,
    setForgotLoading,
  ] = useState(false);

  const [
    developmentOtp,
    setDevelopmentOtp,
  ] = useState("");

  const [
    forgotSuccess,
    setForgotSuccess,
  ] = useState("");

  const resetForgotState = () => {
    setForgotStep("email");
    setForgotEmail("");
    setOtp("");
    setNewPassword("");
    setConfirmPassword("");
    setDevelopmentOtp("");
    setForgotSuccess("");
    setError("");
  };

  const switchToLogin = () => {
    resetForgotState();
    setMode("login");
  };

  const handleForgotSubmit = async (
    event
  ) => {
    event.preventDefault();

    setForgotLoading(true);
    setError("");
    setForgotSuccess("");

    try {
      const data =
        await requestForgotPassword(
          forgotEmail
        );

      if (data?.development_otp) {
        setDevelopmentOtp(
          String(
            data.development_otp
          )
        );
      }

      setForgotSuccess(
        data?.message ||
          "A verification code has been generated."
      );

      setForgotStep("otp");
    } catch (err) {
      setError(
        err.message ||
          "Unable to send the verification code."
      );
    } finally {
      setForgotLoading(false);
    }
  };

  const handleVerifyOTP = async (
    event
  ) => {
    event.preventDefault();

    setForgotLoading(true);
    setError("");
    setForgotSuccess("");

    try {
      await requestVerifyOTP(
        forgotEmail,
        otp
      );

      setForgotSuccess(
        "OTP verified successfully. Create your new password."
      );

      setForgotStep("reset");
    } catch (err) {
      setError(
        err.message ||
          "Invalid or expired OTP."
      );
    } finally {
      setForgotLoading(false);
    }
  };

  const handleResetPassword = async (
    event
  ) => {
    event.preventDefault();

    setError("");
    setForgotSuccess("");

    if (newPassword.length < 8) {
      setError(
        "New password must contain at least 8 characters."
      );
      return;
    }

    if (newPassword !== confirmPassword) {
      setError(
        "New passwords do not match."
      );
      return;
    }

    setForgotLoading(true);

    try {
      const data =
        await requestResetPassword(
          forgotEmail,
          otp,
          newPassword
        );

      setForgotSuccess(
        data?.message ||
          "Password reset successfully."
      );

      setForgotStep("complete");

      setOtp("");
      setNewPassword("");
      setConfirmPassword("");
      setDevelopmentOtp("");
    } catch (err) {
      setError(
        err.message ||
          "Unable to reset password."
      );
    } finally {
      setForgotLoading(false);
    }
  };

  if (mode === "forgot") {
    return (
      <div className="auth-screen">
        <div className="auth-background-grid" />

        <div className="auth-left">
          <div className="auth-brand">
            <div className="brand-mark large">
              CI
            </div>

            <div>
              <div className="brand-name">
                ContractIQ
              </div>

              <div className="brand-subtitle">
                Intelligence Platform
              </div>
            </div>
          </div>

          <div className="auth-hero">
            <div className="eyebrow">
              SECURE ACCOUNT RECOVERY
            </div>

            <h1>
              Regain access to your
              <span>
                {" "}
                intelligence workspace.
              </span>
            </h1>

            <p>
              Verify your account with a
              one-time code and securely
              create a new password.
            </p>

            <div className="auth-benefits">
              <div>
                <span>✓</span>
                Secure OTP verification
              </div>

              <div>
                <span>✓</span>
                Password reset
              </div>

              <div>
                <span>✓</span>
                Protected workspace access
              </div>
            </div>
          </div>

          <div className="auth-footer">
            Enterprise-ready contract
            intelligence
          </div>
        </div>

        <div className="auth-right">
          <div className="auth-card">
            <div className="auth-card-heading">
              <span className="auth-kicker">
                ACCOUNT RECOVERY
              </span>

              <h2>
                {forgotStep ===
                  "email" &&
                  "Forgot your password?"}

                {forgotStep ===
                  "otp" &&
                  "Verify your account"}

                {forgotStep ===
                  "reset" &&
                  "Create a new password"}

                {forgotStep ===
                  "complete" &&
                  "Password reset complete"}
              </h2>

              <p>
                {forgotStep ===
                  "email" &&
                  "Enter your registered email address to receive a verification code."}

                {forgotStep ===
                  "otp" &&
                  `Enter the verification code sent for ${forgotEmail}.`}

                {forgotStep ===
                  "reset" &&
                  "Choose a strong new password for your ContractIQ workspace."}

                {forgotStep ===
                  "complete" &&
                  "Your password has been updated successfully. You can now sign in."}
              </p>
            </div>

            {error && (
              <div className="auth-error">
                <span>!</span>

                {error}

                <button
                  onClick={() =>
                    setError("")
                  }
                >
                  ×
                </button>
              </div>
            )}

            {forgotSuccess && (
              <div className="auth-success">
                <span>✓</span>
                {forgotSuccess}
              </div>
            )}

            {forgotStep ===
              "email" && (
              <form
                className="auth-form"
                onSubmit={
                  handleForgotSubmit
                }
              >
                <label>
                  Work email

                  <input
                    type="email"
                    value={
                      forgotEmail
                    }
                    onChange={(
                      event
                    ) =>
                      setForgotEmail(
                        event.target
                          .value
                      )
                    }
                    placeholder="you@company.com"
                    required
                  />
                </label>

                <button
                  type="submit"
                  className="auth-submit"
                  disabled={forgotLoading}
                >
                  {forgotLoading
                    ? "Generating code..."
                    : "Send verification code"}
                </button>
              </form>
            )}

            {forgotStep ===
              "otp" && (
              <>
                {developmentOtp && (
                  <div className="development-otp">
                    <div>
                      <span>
                        DEVELOPMENT MODE
                      </span>

                      <strong>
                        {developmentOtp}
                      </strong>
                    </div>

                    <small>
                      This code is displayed
                      because email delivery
                      is disabled in the local
                      development environment.
                    </small>
                  </div>
                )}

                <form
                  className="auth-form"
                  onSubmit={
                    handleVerifyOTP
                  }
                >
                  <label>
                    Verification code

                    <input
                      type="text"
                      value={otp}
                      onChange={(
                        event
                      ) =>
                        setOtp(
                          event.target
                            .value
                        )
                      }
                      placeholder="Enter 6-digit OTP"
                      inputMode="numeric"
                      maxLength={6}
                      required
                    />
                  </label>

                  <button
                    type="submit"
                    className="auth-submit"
                    disabled={forgotLoading}
                  >
                    {forgotLoading
                      ? "Verifying..."
                      : "Verify code"}
                  </button>
                </form>
              </>
            )}

            {forgotStep ===
              "reset" && (
              <form
                className="auth-form"
                onSubmit={
                  handleResetPassword
                }
              >
                <label>
                  New password

                  <input
                    type="password"
                    value={
                      newPassword
                    }
                    onChange={(
                      event
                    ) =>
                      setNewPassword(
                        event.target
                          .value
                      )
                    }
                    placeholder="Minimum 8 characters"
                    minLength={8}
                    required
                  />
                </label>

                <label>
                  Confirm new password

                  <input
                    type="password"
                    value={
                      confirmPassword
                    }
                    onChange={(
                      event
                    ) =>
                      setConfirmPassword(
                        event.target
                          .value
                      )
                    }
                    placeholder="Re-enter your password"
                    minLength={8}
                    required
                  />
                </label>

                <button
                  type="submit"
                  className="auth-submit"
                  disabled={forgotLoading}
                >
                  {forgotLoading
                    ? "Resetting password..."
                    : "Reset password"}
                </button>
              </form>
            )}

            {forgotStep ===
              "complete" && (
              <div className="reset-complete">
                <div className="reset-complete-icon">
                  ✓
                </div>

                <h3>
                  You're all set
                </h3>

                <p>
                  Your ContractIQ password
                  has been changed. Sign in
                  using your new password.
                </p>

                <button
                  type="button"
                  className="auth-submit"
                  onClick={switchToLogin}
                >
                  Return to sign in
                </button>
              </div>
            )}

            {forgotStep !==
              "complete" && (
              <div className="auth-switch">
                <button
                  type="button"
                  onClick={switchToLogin}
                >
                  ← Back to sign in
                </button>
              </div>
            )}

            <div className="auth-security">
              <span>◉</span>
              Your workspace is protected
              with authenticated access.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-screen">
      <div className="auth-background-grid" />

      <div className="auth-left">
        <div className="auth-brand">
          <div className="brand-mark large">
            CI
          </div>

          <div>
            <div className="brand-name">
              ContractIQ
            </div>

            <div className="brand-subtitle">
              Intelligence Platform
            </div>
          </div>
        </div>

        <div className="auth-hero">
          <div className="eyebrow">
            AI-POWERED CONTRACT INTELLIGENCE
          </div>

          <h1>
            Turn complex contracts into
            <span>
              {" "}
              actionable intelligence.
            </span>
          </h1>

          <p>
            Analyze contractual language,
            identify risk-bearing clauses,
            extract entities, and build a
            centralized contract intelligence
            workspace.
          </p>

          <div className="auth-benefits">
            <div>
              <span>✓</span>
              Legal-BERT clause intelligence
            </div>

            <div>
              <span>✓</span>
              Explainable risk scoring
            </div>

            <div>
              <span>✓</span>
              Persistent contract workspace
            </div>
          </div>
        </div>

        <div className="auth-footer">
          Enterprise-ready contract
          intelligence
        </div>
      </div>

      <div className="auth-right">
        <div className="auth-card">
          <div className="auth-card-heading">
            <span className="auth-kicker">
              SECURE WORKSPACE
            </span>

            <h2>
              {mode === "login"
                ? "Welcome back"
                : "Create your workspace"}
            </h2>

            <p>
              {mode === "login"
                ? "Sign in to access your contract intelligence workspace."
                : "Create an account to securely manage and analyze your contracts."}
            </p>
          </div>

          {error && (
            <div className="auth-error">
              <span>!</span>

              {error}

              <button
                onClick={() =>
                  setError("")
                }
              >
                ×
              </button>
            </div>
          )}

          <form
            className="auth-form"
            onSubmit={onSubmit}
          >
            {mode ===
              "register" && (
              <>
                <label>
                  Full name

                  <input
                    type="text"
                    value={form.name}
                    onChange={(
                      event
                    ) =>
                      setForm({
                        ...form,
                        name: event.target
                          .value,
                      })
                    }
                    placeholder="Your name"
                    required
                  />
                </label>

                <label>
                  Company

                  <input
                    type="text"
                    value={
                      form.company
                    }
                    onChange={(
                      event
                    ) =>
                      setForm({
                        ...form,
                        company:
                          event.target
                            .value,
                      })
                    }
                    placeholder="Company name"
                  />
                </label>
              </>
            )}

            <label>
              Work email

              <input
                type="email"
                value={form.email}
                onChange={(event) =>
                  setForm({
                    ...form,
                    email:
                      event.target
                        .value,
                  })
                }
                placeholder="you@company.com"
                required
              />
            </label>

            <label>
              Password

              <input
                type="password"
                value={
                  form.password
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    password:
                      event.target
                        .value,
                  })
                }
                placeholder="Minimum 8 characters"
                minLength={8}
                required
              />
            </label>

            {mode === "login" && (
              <div
                className="forgot-password-row"
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  marginTop: "-6px",
                  marginBottom: "6px",
                }}
              >
                <button
                  type="button"
                  style={{
                    border: 0,
                    background: "transparent",
                    padding: "6px 0",
                    color: "#2563eb",
                    fontWeight: 700,
                    cursor: "pointer",
                    fontSize: "14px",
                  }}
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    setError("");
                    setMode("forgot");
                  }}
                >
                  Forgot password?
                </button>
              </div>
            )}

            <button
              className="auth-submit"
              disabled={loading}
            >
              {loading
                ? "Authenticating..."
                : mode === "login"
                ? "Sign in to workspace"
                : "Create workspace"}
            </button>
          </form>

          <div className="auth-switch">
            {mode === "login"
              ? "Don't have an account?"
              : "Already have an account?"}

            <button
              onClick={() => {
                setMode(
                  mode === "login"
                    ? "register"
                    : "login"
                );

                setError("");
              }}
            >
              {mode === "login"
                ? "Create account"
                : "Sign in"}
            </button>
          </div>

          <div className="auth-security">
            <span>◉</span>
            Your workspace is protected
            with authenticated access.
          </div>
        </div>
      </div>
    </div>
  );
}

function DashboardPage({
  dashboard,
  contracts,
  onOpen,
  onUpload,
}) {
  const total =
    dashboard?.total_contracts || 0;

  const high =
    dashboard?.high_risk || 0;

  const medium =
    dashboard?.medium_risk || 0;

  const low =
    dashboard?.low_risk || 0;

  const average =
    dashboard?.average_risk || 0;

  const recent =
    dashboard?.recent_contracts?.length
      ? dashboard.recent_contracts
      : contracts.slice(0, 5);

  return (
    <div className="page">
      <section className="welcome-banner">
        <div>
          <div className="eyebrow">
            PORTFOLIO INTELLIGENCE
          </div>

          <h2>
            Your contract portfolio,
            <span> at a glance.</span>
          </h2>

          <p>
            Monitor contractual exposure,
            prioritize high-risk agreements,
            and accelerate review with
            AI-powered intelligence.
          </p>
        </div>

        <button
          className="secondary-light-button"
          onClick={onUpload}
        >
          + Analyze new contract
        </button>
      </section>

      <section className="kpi-grid">
        <KpiCard
          label="Total Contracts"
          value={total}
          detail="Saved in workspace"
          icon="▤"
        />

        <KpiCard
          label="High Risk"
          value={high}
          detail="Requires attention"
          icon="!"
          tone="danger"
        />

        <KpiCard
          label="Medium Risk"
          value={medium}
          detail="Review recommended"
          icon="◐"
          tone="warning"
        />

        <KpiCard
          label="Average Risk"
          value={average}
          detail="Portfolio indicator"
          icon="◉"
          tone="neutral"
        />
      </section>

      <div className="dashboard-grid">
        <section className="panel risk-overview-panel">
          <PanelHeader
            title="Risk exposure"
            subtitle="Portfolio distribution by risk level"
          />

          <div className="risk-visual">
            <div
              className="risk-donut"
              style={{
                "--high": `${
                  total
                    ? (high / total) * 100
                    : 0
                }%`,
                "--medium": `${
                  total
                    ? (medium / total) * 100
                    : 0
                }%`,
              }}
            >
              <div className="risk-donut-center">
                <strong>
                  {average}
                </strong>

                <span>
                  AVG RISK
                </span>
              </div>
            </div>

            <div className="risk-legend">
              <RiskLegend
                label="High risk"
                count={high}
                total={total}
                className="high"
              />

              <RiskLegend
                label="Medium risk"
                count={medium}
                total={total}
                className="medium"
              />

              <RiskLegend
                label="Low risk"
                count={low}
                total={total}
                className="low"
              />
            </div>
          </div>
        </section>

        <section className="panel">
          <PanelHeader
            title="AI capabilities"
            subtitle="Current intelligence stack"
          />

          <div className="capability-list">
            <Capability
              icon="◈"
              title="Clause Classification"
              text="41-class Legal-BERT model"
            />

            <Capability
              icon="!"
              title="Risk Scoring"
              text="Policy-weighted exposure indicators"
            />

            <Capability
              icon="◎"
              title="Entity Extraction"
              text="Parties, dates, money & jurisdiction"
            />

            <Capability
              icon="▣"
              title="Document Intelligence"
              text="PDF, DOCX & OCR processing"
            />
          </div>
        </section>
      </div>

      <section className="panel recent-panel">
        <PanelHeader
          title="Recent contracts"
          subtitle="Latest activity in your workspace"
          action={
            <button
              className="text-button"
              onClick={() => {
                window.dispatchEvent(
                  new CustomEvent(
                    "contractiq-nav",
                    {
                      detail:
                        "contracts",
                    }
                  )
                );
              }}
            >
              View library →
            </button>
          }
        />

        {recent.length ? (
          <ContractTable
            contracts={recent}
            onOpen={onOpen}
          />
        ) : (
          <EmptyState
            title="No contracts yet"
            text="Upload your first contract to begin building your intelligence portfolio."
          />
        )}
      </section>
    </div>
  );
}

function ContractsPage({
  contracts,
  total,
  search,
  setSearch,
  riskFilter,
  setRiskFilter,
  onOpen,
  onUpload,
  onFavorite,
  onStatusChange,
}) {
  return (
    <div className="page">
      <div className="page-intro">
        <div>
          <p>
            Manage, analyze and revisit your
            contract portfolio from one
            centralized workspace.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={onUpload}
        >
          + Upload contracts
        </button>
      </div>

      <section className="library-toolbar">
        <div className="search-box">
          <span>⌕</span>

          <input
            value={search}
            onChange={(event) =>
              setSearch(
                event.target.value
              )
            }
            placeholder="Search contracts..."
          />
        </div>

        <div className="filter-group">
          {[
            "ALL",
            "HIGH",
            "MEDIUM",
            "LOW",
          ].map((filter) => (
            <button
              key={filter}
              className={
                riskFilter === filter
                  ? "filter active"
                  : "filter"
              }
              onClick={() =>
                setRiskFilter(
                  filter
                )
              }
            >
              {filter === "ALL"
                ? "All"
                : `${filter.charAt(
                    0
                  )}${filter
                    .slice(1)
                    .toLowerCase()} risk`}
            </button>
          ))}
        </div>

        <div className="result-count">
          {contracts.length} of {total}
        </div>
      </section>

      <section className="panel library-panel">
        {contracts.length ? (
          <ContractTable
            contracts={contracts}
            onOpen={onOpen}
            onFavorite={onFavorite}
            onStatusChange={
              onStatusChange
            }
            detailed
          />
        ) : (
          <EmptyState
            title="No matching contracts"
            text="Try adjusting your search or risk filters."
          />
        )}
      </section>
    </div>
  );
}

function RiskCenterPage({
  contracts,
  onOpen,
}) {
  const highRisk =
    contracts.filter(
      (contract) =>
        contract.risk_level?.toUpperCase() ===
        "HIGH"
    );

  const mediumRisk =
    contracts.filter(
      (contract) =>
        contract.risk_level?.toUpperCase() ===
        "MEDIUM"
    );

  return (
    <div className="page">
      <div className="page-intro">
        <div>
          <p>
            Prioritize contracts requiring
            legal or business attention based
            on AI-generated risk indicators.
          </p>
        </div>
      </div>

      <div className="risk-summary-grid">
        <div className="risk-summary-card danger">
          <span className="summary-icon">
            !
          </span>

          <div>
            <strong>
              {highRisk.length}
            </strong>

            <span>
              High-risk contracts
            </span>
          </div>
        </div>

        <div className="risk-summary-card warning">
          <span className="summary-icon">
            ◐
          </span>

          <div>
            <strong>
              {mediumRisk.length}
            </strong>

            <span>
              Medium-risk contracts
            </span>
          </div>
        </div>

        <div className="risk-summary-card neutral">
          <span className="summary-icon">
            ◉
          </span>

          <div>
            <strong>
              {contracts.length}
            </strong>

            <span>
              Total analyzed
            </span>
          </div>
        </div>
      </div>

      <section className="panel">
        <PanelHeader
          title="Priority review queue"
          subtitle="Contracts ranked by portfolio risk"
        />

        {contracts.length ? (
          <div className="risk-queue">
            {[...contracts]
              .sort(
                (a, b) =>
                  (b.risk_score ||
                    0) -
                  (a.risk_score ||
                    0)
              )
              .map((contract) => (
                <button
                  className="risk-queue-item"
                  key={contract.id}
                  onClick={() =>
                    onOpen(contract)
                  }
                >
                  <div className="risk-score-badge">
                    {formatScore(
                      contract.risk_score
                    )}
                  </div>

                  <div className="risk-queue-main">
                    <strong>
                      {
                        contract.filename
                      }
                    </strong>

                    <span>
                      {contract.folder ||
                        "General"}
                      {" • "}
                      Updated{" "}
                      {formatDate(
                        contract.updated_at
                      )}
                    </span>
                  </div>

                  <span
                    className={`risk-pill ${riskClass(
                      contract.risk_level
                    )}`}
                  >
                    {contract.risk_level ||
                      "LOW"}
                  </span>

                  <span className="arrow">
                    →
                  </span>
                </button>
              ))}
          </div>
        ) : (
          <EmptyState
            title="Risk center is empty"
            text="Analyze contracts to populate your risk portfolio."
          />
        )}
      </section>
    </div>
  );
}

function ClauseIntelligencePage({
  contracts,
  onOpen,
}) {
  const [query, setQuery] =
    useState("");

  const clauseRows = [];

  contracts.forEach(
    (contract) => {
      const analysis =
        contract.analysis || {};

      (
        analysis.clauses || []
      ).forEach((clause) => {
        clauseRows.push({
          ...clause,
          filename:
            contract.filename,
          contractId:
            contract.id,
        });
      });
    }
  );

  const filtered =
    clauseRows.filter((clause) =>
      clause.name
        ?.toLowerCase()
        .includes(
          query.toLowerCase()
        )
    );

  const clauseCounts = {};

  clauseRows.forEach((clause) => {
    clauseCounts[clause.name] =
      (clauseCounts[clause.name] ||
        0) + 1;
  });

  const topClauses =
    Object.entries(clauseCounts)
      .sort(
        (a, b) => b[1] - a[1]
      )
      .slice(0, 8);

  return (
    <div className="page">
      <div className="page-intro">
        <div>
          <p>
            Explore contractual clauses
            detected across your portfolio
            and identify recurring language
            patterns.
          </p>
        </div>
      </div>

      <div className="analytics-grid">
        <section className="panel">
          <PanelHeader
            title="Most detected clauses"
            subtitle="Across analyzed contracts"
          />

          <div className="clause-ranking">
            {topClauses.length ? (
              topClauses.map(
                (
                  [name, count],
                  index
                ) => (
                  <div
                    className="clause-ranking-row"
                    key={name}
                  >
                    <span className="rank">
                      {String(
                        index + 1
                      ).padStart(
                        2,
                        "0"
                      )}
                    </span>

                    <span className="clause-ranking-name">
                      {name}
                    </span>

                    <span className="clause-count">
                      {count}
                    </span>
                  </div>
                )
              )
            ) : (
              <EmptyState
                title="No clause data"
                text="Analyze a contract to populate clause intelligence."
              />
            )}
          </div>
        </section>

        <section className="panel intelligence-card">
          <div className="intelligence-icon">
            ◈
          </div>

          <span className="eyebrow">
            MODEL INTELLIGENCE
          </span>

          <h3>
            41 legal clause categories
          </h3>

          <p>
            The Legal-BERT classifier
            evaluates contractual language
            against a 41-category legal clause
            taxonomy.
          </p>

          <div className="model-meter">
            <span />
          </div>

          <small>
            Confidence varies by clause and
            document.
          </small>
        </section>
      </div>

      <section className="panel">
        <PanelHeader
          title="Clause register"
          subtitle={`${filtered.length} detected clauses`}
        />

        <div className="search-box inline">
          <span>⌕</span>

          <input
            value={query}
            onChange={(event) =>
              setQuery(
                event.target.value
              )
            }
            placeholder="Search clause types..."
          />
        </div>

        {filtered.length ? (
          <div className="clause-register">
            {filtered.map(
              (
                clause,
                index
              ) => (
                <button
                  className="clause-register-row"
                  key={`${clause.contractId}-${index}`}
                  onClick={() => {
                    const contract =
                      contracts.find(
                        (item) =>
                          item.id ===
                          clause.contractId
                      );

                    if (contract) {
                      onOpen(
                        contract
                      );
                    }
                  }}
                >
                  <div className="clause-type">
                    {clause.name}
                  </div>

                  <div className="clause-contract">
                    {
                      clause.filename
                    }
                  </div>

                  <div className="confidence">
                    {(
                      Number(
                        clause.confidence ||
                          0
                      ) * 100
                    ).toFixed(1)}
                    %
                  </div>

                  <span
                    className={`status-tag ${
                      clause.status ===
                      "High Risk"
                        ? "high"
                        : clause.status ===
                          "Medium Risk"
                        ? "medium"
                        : "low"
                    }`}
                  >
                    {clause.status ||
                      "Detected"}
                  </span>

                  <span>→</span>
                </button>
              )
            )}
          </div>
        ) : (
          <EmptyState
            title="No clauses found"
            text="No detected clauses match your search."
          />
        )}
      </section>
    </div>
  );
}

function EntitiesPage({
  contracts,
  onOpen,
}) {
  const entityMap = {};

  contracts.forEach(
    (contract) => {
      const entities =
        contract.analysis
          ?.entities || [];

      entities.forEach(
        (entity) => {
          const key = `${entity.type}:${entity.text}`;

          if (!entityMap[key]) {
            entityMap[key] = {
              ...entity,
              count: 0,
              contracts: [],
            };
          }

          entityMap[key].count += 1;

          if (
            !entityMap[
              key
            ].contracts.includes(
              contract.filename
            )
          ) {
            entityMap[
              key
            ].contracts.push(
              contract.filename
            );
          }
        }
      );
    }
  );

  const entities =
    Object.values(entityMap)
      .sort(
        (a, b) =>
          b.count - a.count
      )
      .slice(0, 50);

  return (
    <div className="page">
      <div className="page-intro">
        <div>
          <p>
            Review key entities extracted
            from your contract portfolio.
          </p>
        </div>
      </div>

      <div className="entity-type-grid">
        {[
          "PARTY",
          "DATE",
          "MONEY",
          "JURISDICTION",
        ].map((type) => (
          <div
            className="entity-type-card"
            key={type}
          >
            <span className="entity-type-label">
              {type}
            </span>

            <strong>
              {
                entities.filter(
                  (entity) =>
                    entity.type ===
                    type
                ).length
              }
            </strong>

            <span>
              Unique entities
            </span>
          </div>
        ))}
      </div>

      <section className="panel">
        <PanelHeader
          title="Extracted entities"
          subtitle={`${entities.length} unique entities shown`}
        />

        {entities.length ? (
          <div className="entity-grid">
            {entities.map(
              (entity) => (
                <div
                  className="entity-card"
                  key={`${entity.type}-${entity.text}`}
                >
                  <div className="entity-card-top">
                    <span className="entity-badge">
                      {entity.type}
                    </span>

                    <span className="entity-count">
                      ×{entity.count}
                    </span>
                  </div>

                  <strong>
                    {entity.text}
                  </strong>

                  <div className="entity-contract-list">
                    {entity.contracts
                      .slice(0, 2)
                      .map(
                        (
                          filename
                        ) => {
                          const contract =
                            contracts.find(
                              (
                                item
                              ) =>
                                item.filename ===
                                filename
                            );

                          return (
                            <button
                              key={
                                filename
                              }
                              onClick={() => {
                                if (
                                  contract
                                ) {
                                  onOpen(
                                    contract
                                  );
                                }
                              }}
                            >
                              {
                                filename
                              }
                            </button>
                          );
                        }
                      )}
                  </div>
                </div>
              )
            )}
          </div>
        ) : (
          <EmptyState
            title="No entities yet"
            text="Upload and analyze contracts to populate entity intelligence."
          />
        )}
      </section>
    </div>
  );
}

function SettingsPage({
  profile,
  profileForm,
  setProfileForm,
  passwordForm,
  setPasswordForm,
  saveProfile,
  savePassword,
  loading,
  logout,
}) {
  return (
    <div className="page">
      <div className="settings-grid">
        <section className="panel settings-profile">
          <PanelHeader
            title="Profile"
            subtitle="Manage your workspace identity"
          />

          <form
            className="settings-form"
            onSubmit={saveProfile}
          >
            <div className="profile-large">
              {(profile?.name ||
                "U")
                .charAt(0)
                .toUpperCase()}
            </div>

            <label>
              Full name

              <input
                value={
                  profileForm.name
                }
                onChange={(event) =>
                  setProfileForm({
                    ...profileForm,
                    name: event.target
                      .value,
                  })
                }
                required
              />
            </label>

            <label>
              Email

              <input
                value={
                  profile?.email || ""
                }
                disabled
              />
            </label>

            <label>
              Company

              <input
                value={
                  profileForm.company
                }
                onChange={(event) =>
                  setProfileForm({
                    ...profileForm,
                    company:
                      event.target
                        .value,
                  })
                }
              />
            </label>

            <button
              className="primary-button"
              disabled={loading}
            >
              Save profile
            </button>
          </form>
        </section>

        <section className="panel">
          <PanelHeader
            title="Security"
            subtitle="Manage your account credentials"
          />

          <form
            className="settings-form"
            onSubmit={savePassword}
          >
            <label>
              Current password

              <input
                type="password"
                value={
                  passwordForm.current_password
                }
                onChange={(event) =>
                  setPasswordForm({
                    ...passwordForm,
                    current_password:
                      event.target
                        .value,
                  })
                }
                required
              />
            </label>

            <label>
              New password

              <input
                type="password"
                value={
                  passwordForm.new_password
                }
                onChange={(event) =>
                  setPasswordForm({
                    ...passwordForm,
                    new_password:
                      event.target
                        .value,
                  })
                }
                minLength={8}
                required
              />
            </label>

            <button
              className="secondary-button"
              disabled={loading}
            >
              Change password
            </button>
          </form>

          <div className="security-note">
            <span>✓</span>
            Passwords are securely hashed
            before storage.
          </div>

          <button
            className="danger-outline-button"
            onClick={logout}
          >
            Sign out
          </button>
        </section>
      </div>

      <section className="panel platform-info">
        <PanelHeader
          title="Platform information"
          subtitle="Contract Intelligence environment"
        />

        <div className="platform-grid">
          <InfoItem
            label="AI Model"
            value="Legal-BERT"
          />

          <InfoItem
            label="Clause Classes"
            value="41"
          />

          <InfoItem
            label="Document Formats"
            value="PDF / DOCX"
          />

          <InfoItem
            label="OCR"
            value="Available"
          />

          <InfoItem
            label="Storage"
            value="Workspace Database"
          />

          <InfoItem
            label="Risk Engine"
            value="Policy Weighted"
          />
        </div>
      </section>
    </div>
  );
}

function ContractTable({
  contracts,
  onOpen,
  onFavorite,
  onStatusChange,
  detailed = false,
}) {
  return (
    <div className="contract-table">
      <div className="contract-table-head">
        <span>Contract</span>
        <span>Risk</span>
        <span>Status</span>
        <span>Updated</span>
        <span />
      </div>

      {contracts.map(
        (contract) => (
          <div
            className="contract-row"
            key={contract.id}
          >
            <button
              className="contract-main"
              onClick={() =>
                onOpen(contract)
              }
            >
              <div className="file-icon">
                {contract.filename
                  ?.toLowerCase()
                  .endsWith(".docx")
                  ? "DOC"
                  : "PDF"}
              </div>

              <div>
                <strong>
                  {contract.filename}
                </strong>

                <span>
                  {contract.folder ||
                    "General"}
                  {" • "}
                  {formatDate(
                    contract.created_at
                  )}
                </span>
              </div>
            </button>

            <div>
              <span
                className={`risk-pill ${riskClass(
                  contract.risk_level
                )}`}
              >
                {formatScore(
                  contract.risk_score
                )}{" "}
                ·{" "}
                {contract.risk_level ||
                  "LOW"}
              </span>
            </div>

            {detailed &&
            onStatusChange ? (
              <select
                className="status-select"
                value={
                  contract.status ||
                  "Pending Review"
                }
                onChange={(event) =>
                  onStatusChange(
                    contract,
                    event
                      .target
                      .value
                  )
                }
                onClick={(event) =>
                  event.stopPropagation()
                }
              >
                <option>
                  Pending Review
                </option>

                <option>
                  Under Review
                </option>

                <option>
                  Reviewed
                </option>

                <option>
                  Approved
                </option>

                <option>
                  Rejected
                </option>
              </select>
            ) : (
              <span className="status-text">
                {contract.status ||
                  "Pending Review"}
              </span>
            )}

            <span className="date-text">
              {formatDate(
                contract.updated_at
              )}
            </span>

            <div className="row-actions">
              {onFavorite && (
                <button
                  className={`favorite-button ${
                    contract.favorite
                      ? "active"
                      : ""
                  }`}
                  onClick={() =>
                    onFavorite(
                      contract
                    )
                  }
                  title="Favorite"
                >
                  {contract.favorite
                    ? "★"
                    : "☆"}
                </button>
              )}

              <button
                className="open-arrow"
                onClick={() =>
                  onOpen(contract)
                }
              >
                →
              </button>
            </div>
          </div>
        )
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  detail,
  icon,
  tone = "",
}) {
  return (
    <div
      className={`kpi-card ${tone}`}
    >
      <div className="kpi-top">
        <span>{label}</span>

        <span className="kpi-icon">
          {icon}
        </span>
      </div>

      <strong>{value}</strong>

      <small>{detail}</small>
    </div>
  );
}

function RiskLegend({
  label,
  count,
  total,
  className,
}) {
  const percentage = total
    ? Math.round(
        (count / total) * 100
      )
    : 0;

  return (
    <div className="risk-legend-item">
      <span
        className={`legend-dot ${className}`}
      />

      <div>
        <strong>{label}</strong>

        <span>
          {count} contracts
        </span>
      </div>

      <b>{percentage}%</b>
    </div>
  );
}

function Capability({
  icon,
  title,
  text,
}) {
  return (
    <div className="capability">
      <div className="capability-icon">
        {icon}
      </div>

      <div>
        <strong>{title}</strong>

        <span>{text}</span>
      </div>

      <span className="capability-check">
        ✓
      </span>
    </div>
  );
}

function PanelHeader({
  title,
  subtitle,
  action,
}) {
  return (
    <div className="panel-header">
      <div>
        <h3>{title}</h3>

        {subtitle && (
          <p>{subtitle}</p>
        )}
      </div>

      {action}
    </div>
  );
}

function InfoItem({
  label,
  value,
}) {
  return (
    <div className="info-item">
      <span>{label}</span>

      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({
  title,
  text,
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        ◇
      </div>

      <h3>{title}</h3>

      <p>{text}</p>
    </div>
  );
}

function LoadingWorkspace() {
  return (
    <div className="loading-workspace">
      <div className="loading-spinner" />

      <h3>
        Loading workspace
      </h3>

      <p>
        Synchronizing your contract
        intelligence portfolio...
      </p>
    </div>
  );
}

function UploadModal({
  inputRef,
  loading,
  onClose,
  onFiles,
}) {
  const [dragging, setDragging] =
    useState(false);

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);

    const files =
      event.dataTransfer.files;

    if (files?.length) {
      onFiles(files);
    }
  };

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
    >
      <div
        className="modal upload-modal"
        onClick={(event) =>
          event.stopPropagation()
        }
      >
        <button
          className="modal-close"
          onClick={onClose}
        >
          ×
        </button>

        <div className="modal-kicker">
          CONTRACT ANALYSIS
        </div>

        <h2>
          Analyze contracts
        </h2>

        <p>
          Upload one or more PDF or DOCX
          contracts. Each document will be
          processed by the Contract
          Intelligence pipeline and saved
          to your workspace.
        </p>

        <div
          className={`drop-zone ${
            dragging
              ? "dragging"
              : ""
          }`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() =>
            setDragging(false)
          }
          onDrop={handleDrop}
          onClick={() =>
            inputRef.current?.click()
          }
        >
          <div className="upload-icon">
            ↑
          </div>

          <strong>
            {loading
              ? "Analyzing contract..."
              : "Drop contracts here"}
          </strong>

          <span>
            or click to browse files
          </span>

          <small>
            PDF or DOCX • Maximum 50 MB per
            file
          </small>

          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx"
            multiple
            hidden
            onChange={(event) => {
              onFiles(
                event.target.files
              );

              event.target.value =
                "";
            }}
          />
        </div>

        {loading && (
          <div className="upload-progress">
            <div className="loading-spinner small-spinner" />

            <span>
              Extracting text, classifying
              clauses and calculating
              risk...
            </span>
          </div>
        )}

        <div className="upload-capabilities">
          <span>✓ OCR</span>
          <span>
            ✓ Legal-BERT
          </span>
          <span>
            ✓ Risk scoring
          </span>
          <span>
            ✓ Entity extraction
          </span>
        </div>
      </div>
    </div>
  );
}

function ContractModal({
  contract,
  analysis,
  onClose,
  onDelete,
}) {
  const clauses =
    analysis?.clauses || [];

  const findings =
    analysis?.findings || [];

  const entities =
    analysis?.entities || [];

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
    >
      <div
        className="modal contract-modal"
        onClick={(event) =>
          event.stopPropagation()
        }
      >
        <div className="contract-modal-header">
          <div>
            <div className="modal-kicker">
              CONTRACT DETAILS
            </div>

            <h2>
              {contract.filename}
            </h2>

            <span>
              {contract.folder ||
                "General"}
              {" • "}
              {formatDate(
                contract.updated_at
              )}
            </span>
          </div>

          <button
            className="modal-close"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="contract-detail-score">
          <div
            className={`score-circle ${riskClass(
              contract.risk_level
            )}`}
          >
            <strong>
              {formatScore(
                contract.risk_score
              )}
            </strong>

            <span>
              RISK SCORE
            </span>
          </div>

          <div>
            <span className="detail-label">
              Portfolio risk level
            </span>

            <strong
              className={`detail-risk ${riskClass(
                contract.risk_level
              )}`}
            >
              {contract.risk_level ||
                "LOW"}
            </strong>

            <p>
              Application-level policy
              indicator generated from
              model predictions and
              configured risk weights.
            </p>
          </div>
        </div>

        <div className="modal-stats">
          <MiniStat
            label="Clauses"
            value={
              clauses.length
            }
          />

          <MiniStat
            label="Findings"
            value={
              findings.length
            }
          />

          <MiniStat
            label="Entities"
            value={
              entities.length
            }
          />

          <MiniStat
            label="Status"
            value={
              contract.status ||
              "Pending Review"
            }
          />
        </div>

        <div className="modal-section">
          <div className="modal-section-title">
            Priority findings
          </div>

          {findings.length ? (
            <div className="finding-list">
              {findings
                .slice(0, 8)
                .map(
                  (
                    finding,
                    index
                  ) => (
                    <div
                      className="finding-item"
                      key={index}
                    >
                      <span
                        className={`finding-severity ${riskClass(
                          finding.severity
                        )}`}
                      >
                        {
                          finding.severity
                        }
                      </span>

                      <div>
                        <strong>
                          {
                            finding.clause
                          }
                        </strong>

                        <p>
                          {finding.explanation ||
                            finding.evidence}
                        </p>
                      </div>

                      <span className="finding-confidence">
                        {(
                          Number(
                            finding.confidence ||
                              0
                          ) * 100
                        ).toFixed(1)}
                        %
                      </span>
                    </div>
                  )
                )}
            </div>
          ) : (
            <EmptyState
              title="No priority findings"
              text="No configured findings were returned for this analysis."
            />
          )}
        </div>

        <div className="modal-section">
          <div className="modal-section-title">
            Detected clauses
          </div>

          {clauses.length ? (
            <div className="detected-clause-list">
              {clauses
                .slice(0, 15)
                .map(
                  (
                    clause,
                    index
                  ) => (
                    <div
                      className="detected-clause"
                      key={index}
                    >
                      <div>
                        <strong>
                          {
                            clause.name
                          }
                        </strong>

                        <p>
                          {
                            clause.text
                          }
                        </p>
                      </div>

                      <span>
                        {(
                          Number(
                            clause.confidence ||
                              0
                          ) * 100
                        ).toFixed(1)}
                        %
                      </span>
                    </div>
                  )
                )}
            </div>
          ) : (
            <p className="muted">
              No clause records available.
            </p>
          )}
        </div>

        <div className="modal-footer">
          <button
            className="danger-outline-button"
            onClick={onDelete}
          >
            Delete contract
          </button>

          <button
            className="secondary-button"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
}) {
  return (
    <div className="mini-stat">
      <span>{label}</span>

      <strong>{value}</strong>
    </div>
  );
}

function ConfirmModal({
  title,
  message,
  onCancel,
  onConfirm,
}) {
  return (
    <div className="modal-backdrop">
      <div className="modal confirm-modal">
        <div className="confirm-icon">
          !
        </div>

        <h2>{title}</h2>

        <p>{message}</p>

        <div className="confirm-actions">
          <button
            className="secondary-button"
            onClick={onCancel}
          >
            Cancel
          </button>

          <button
            className="danger-button"
            onClick={onConfirm}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;