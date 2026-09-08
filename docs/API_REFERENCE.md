# API Reference — ContractIQ

## Authentication

### POST `/api/auth/register`
Creates a user account.

### POST `/api/auth/login`
Authenticates a user and returns a JWT.

### GET `/api/auth/me`
Returns the currently authenticated user.

### PUT `/api/auth/profile`
Updates user profile data.

### POST `/api/auth/change-password`
Changes the authenticated user's password.

### POST `/api/auth/forgot-password`
Starts password recovery and creates an OTP.

### POST `/api/auth/verify-otp`
Verifies the recovery OTP.

### POST `/api/auth/reset-password`
Sets a new password after OTP verification.

## Dashboard / contracts

### GET `/api/dashboard`
Returns dashboard summary data.

### GET `/api/contracts`
Lists the authenticated user's saved contracts.

### POST `/api/contracts`
Uploads/analyzes a contract and stores the result.

### GET `/api/contracts/{id}`
Returns a stored contract and its analysis.

### PATCH `/api/contracts/{id}`
Updates contract metadata/status/favorite fields.

### DELETE `/api/contracts/{id}`
Deletes a stored contract.

## Integration expectations

All protected requests use:

```http
Authorization: Bearer <JWT>
```

Frontend base URL for local development:

```text
http://127.0.0.1:8000
```
