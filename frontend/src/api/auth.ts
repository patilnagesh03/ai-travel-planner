import { api } from "@/api/client"
import type {
  ApiEnvelope,
  ChangePasswordPayload,
  ProfilePayload,
  SignInResponse,
  SignUpPayload,
  SignUpResponse,
  User,
} from "@/api/types"
import { unwrap } from "@/lib/envelope"

interface SignInPayload {
  email: string
  password: string
}

export async function signIn(payload: SignInPayload): Promise<SignInResponse> {
  const response = await api.post<ApiEnvelope<SignInResponse>>(
    "/api/auth/signin/",
    payload,
  )

  return unwrap(response.data)
}

export async function signUp(payload: SignUpPayload): Promise<SignUpResponse> {
  const response = await api.post<ApiEnvelope<SignUpResponse>>(
    "/api/auth/signup/",
    payload,
  )

  return unwrap(response.data)
}

export async function getProfile(): Promise<User> {
  const response = await api.get<ApiEnvelope<User>>("/api/auth/profile/")

  return unwrap(response.data)
}

export async function updateProfile(payload: ProfilePayload): Promise<User> {
  const response = await api.patch<ApiEnvelope<User>>(
    "/api/auth/profile/",
    payload,
  )

  return unwrap(response.data)
}

export async function changePassword(
  payload: ChangePasswordPayload,
): Promise<void> {
  await api.post("/api/auth/change-password/", payload)
}

export async function logout(refresh: string): Promise<void> {
  await api.post("/api/auth/logout/", { refresh })
}
