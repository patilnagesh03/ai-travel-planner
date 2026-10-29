import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { BadgeCheck, KeyRound, Loader2, Save, UserRound } from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import { changePassword, updateProfile } from "@/api/auth"
import { useAuth } from "@/auth/auth-context"
import { PageHeader } from "@/components/shared/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getErrorMessage } from "@/lib/api-error"
import { formatDate, initials } from "@/lib/format"

const profileSchema = z.object({
  first_name: z.string().trim().min(1, "First name is required."),
  last_name: z.string().trim().min(1, "Last name is required."),
  phone_number: z.string().optional(),
  country: z.string().optional(),
  city: z.string().optional(),
  date_of_birth: z.string().optional(),
})

type ProfileFormValues = z.infer<typeof profileSchema>

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password."),
    new_password: z
      .string()
      .min(8, "Use at least 8 characters.")
      .max(128, "Use 128 characters or fewer."),
    confirm_password: z.string().min(1, "Confirm the new password."),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match.",
  })

type PasswordFormValues = z.infer<typeof passwordSchema>

export function ProfilePage() {
  const { user, updateUser } = useAuth()
  const [profileError, setProfileError] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: user?.first_name ?? "",
      last_name: user?.last_name ?? "",
      phone_number: user?.phone_number ?? "",
      country: user?.country ?? "",
      city: user?.city ?? "",
      date_of_birth: user?.date_of_birth ?? "",
    },
  })

  useEffect(() => {
    if (user) {
      reset({
        first_name: user.first_name,
        last_name: user.last_name,
        phone_number: user.phone_number ?? "",
        country: user.country ?? "",
        city: user.city ?? "",
        date_of_birth: user.date_of_birth ?? "",
      })
    }
  }, [user, reset])

  const profileMutation = useMutation({
    mutationFn: (values: ProfileFormValues) =>
      updateProfile({
        first_name: values.first_name.trim(),
        last_name: values.last_name.trim(),
        phone_number: values.phone_number?.trim() || null,
        country: values.country?.trim() || null,
        city: values.city?.trim() || null,
        date_of_birth: values.date_of_birth || null,
      }),
    onSuccess: (savedUser) => {
      updateUser(savedUser)
      setProfileError(null)
      toast.success("Profile updated.")
    },
    onError: (error) => {
      setProfileError(getErrorMessage(error))
    },
  })

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
  })

  const passwordMutation = useMutation({
    mutationFn: (values: PasswordFormValues) =>
      changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
        confirm_password: values.confirm_password,
      }),
    onSuccess: () => {
      passwordForm.reset()
      setPasswordError(null)
      toast.success("Password changed.")
    },
    onError: (error) => {
      setPasswordError(getErrorMessage(error))
    },
  })

  if (!user) {
    return null
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Profile"
        description="Your account details and sign-in credentials."
      />

      <Card>
        <CardContent className="flex flex-col gap-5 py-6 sm:flex-row sm:items-center">
          <span className="grid size-16 shrink-0 place-items-center rounded-full bg-primary text-xl font-semibold text-primary-foreground">
            {initials(user.first_name, user.last_name)}
          </span>

          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-medium">{user.full_name}</h2>
              {user.is_verified ? (
                <Badge
                  variant="secondary"
                  className="gap-1 bg-emerald-500/10 text-emerald-700"
                >
                  <BadgeCheck className="size-3.5" />
                  Verified
                </Badge>
              ) : (
                <Badge variant="outline">Unverified</Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">{user.email}</p>
            <p className="text-xs text-muted-foreground">
              Member since {formatDate(user.created_at)}
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <UserRound className="size-4" />
              Personal details
            </CardTitle>
            <CardDescription>
              Your email address is fixed. Everything else can be changed.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form
              className="space-y-4"
              onSubmit={handleSubmit((values) =>
                profileMutation.mutate(values),
              )}
              noValidate
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="profile-first-name">First name</Label>
                  <Input
                    id="profile-first-name"
                    aria-invalid={!!errors.first_name}
                    {...register("first_name")}
                  />
                  {errors.first_name ? (
                    <p className="text-sm text-destructive">
                      {errors.first_name.message}
                    </p>
                  ) : null}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="profile-last-name">Last name</Label>
                  <Input
                    id="profile-last-name"
                    aria-invalid={!!errors.last_name}
                    {...register("last_name")}
                  />
                  {errors.last_name ? (
                    <p className="text-sm text-destructive">
                      {errors.last_name.message}
                    </p>
                  ) : null}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="profile-phone">Phone number</Label>
                  <Input
                    id="profile-phone"
                    autoComplete="tel"
                    placeholder="+91…"
                    {...register("phone_number")}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="profile-dob">Date of birth</Label>
                  <Input
                    id="profile-dob"
                    type="date"
                    autoComplete="bday"
                    {...register("date_of_birth")}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="profile-city">City</Label>
                  <Input
                    id="profile-city"
                    autoComplete="address-level2"
                    {...register("city")}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="profile-country">Country</Label>
                  <Input
                    id="profile-country"
                    autoComplete="country-name"
                    {...register("country")}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="profile-email">Email</Label>
                <Input id="profile-email" value={user.email} disabled readOnly />
              </div>

              {profileError ? (
                <p className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                  {profileError}
                </p>
              ) : null}

              <Button
                type="submit"
                disabled={profileMutation.isPending || !isDirty}
              >
                {profileMutation.isPending ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Saving…
                  </>
                ) : (
                  <>
                    <Save className="size-4" />
                    Save details
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <KeyRound className="size-4" />
              Change password
            </CardTitle>
            <CardDescription>
              Use a password that is not reused anywhere else.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form
              className="space-y-4"
              onSubmit={passwordForm.handleSubmit((values) =>
                passwordMutation.mutate(values),
              )}
              noValidate
            >
              <div className="space-y-2">
                <Label htmlFor="current-password">Current password</Label>
                <Input
                  id="current-password"
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={!!passwordForm.formState.errors.current_password}
                  {...passwordForm.register("current_password")}
                />
                {passwordForm.formState.errors.current_password ? (
                  <p className="text-sm text-destructive">
                    {passwordForm.formState.errors.current_password.message}
                  </p>
                ) : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="new-password">New password</Label>
                <Input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  aria-invalid={!!passwordForm.formState.errors.new_password}
                  {...passwordForm.register("new_password")}
                />
                {passwordForm.formState.errors.new_password ? (
                  <p className="text-sm text-destructive">
                    {passwordForm.formState.errors.new_password.message}
                  </p>
                ) : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-password">Confirm new password</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  aria-invalid={
                    !!passwordForm.formState.errors.confirm_password
                  }
                  {...passwordForm.register("confirm_password")}
                />
                {passwordForm.formState.errors.confirm_password ? (
                  <p className="text-sm text-destructive">
                    {passwordForm.formState.errors.confirm_password.message}
                  </p>
                ) : null}
              </div>

              {passwordError ? (
                <p className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                  {passwordError}
                </p>
              ) : null}

              <Button
                type="submit"
                variant="outline"
                className="w-full"
                disabled={passwordMutation.isPending}
              >
                {passwordMutation.isPending ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Changing…
                  </>
                ) : (
                  "Change password"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
