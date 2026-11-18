import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { z } from "zod"

import { signUp } from "@/api/auth"
import { AuthLayout } from "@/components/layout/auth-layout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getErrorMessage } from "@/lib/api-error"

const signUpSchema = z
  .object({
    first_name: z.string().trim().min(1, "First name is required."),
    last_name: z.string().trim().min(1, "Last name is required."),
    email: z
      .string()
      .min(1, "Email is required.")
      .email("Enter a valid email address."),
    password: z
      .string()
      .min(8, "Use at least 8 characters.")
      .max(128, "Use 128 characters or fewer."),
    confirm_password: z.string().min(1, "Confirm your password."),
    phone_number: z.string().trim().optional(),
    country: z.string().trim().optional(),
    city: z.string().trim().optional(),
    date_of_birth: z.string().optional(),
  })
  .refine((values) => values.password === values.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match.",
  })

type SignUpValues = z.infer<typeof signUpSchema>

export function SignUpPage() {
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignUpValues>({
    resolver: zodResolver(signUpSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      password: "",
      confirm_password: "",
      phone_number: "",
      country: "",
      city: "",
      date_of_birth: "",
    },
  })

  const onSubmit = async (values: SignUpValues) => {
    setFormError(null)

    try {
      await signUp({
        email: values.email.trim(),
        first_name: values.first_name.trim(),
        last_name: values.last_name.trim(),
        password: values.password,
        confirm_password: values.confirm_password,
        ...(values.phone_number
          ? { phone_number: values.phone_number.trim() }
          : {}),
        ...(values.country ? { country: values.country.trim() } : {}),
        ...(values.city ? { city: values.city.trim() } : {}),
        ...(values.date_of_birth
          ? { date_of_birth: values.date_of_birth }
          : {}),
      })

      toast.success("Account created. Please sign in.")
      navigate("/signin", {
        replace: true,
        state: { email: values.email.trim(), registered: true },
      })
    } catch (error) {
      setFormError(getErrorMessage(error))
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      description="Start planning trips grounded in real places."
      footer={
        <span>
          Already have an account?{" "}
          <Link
            to="/signin"
            className="font-medium text-foreground underline underline-offset-4"
          >
            Sign in
          </Link>
        </span>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="first_name">First name</Label>
            <Input
              id="first_name"
              autoComplete="given-name"
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
            <Label htmlFor="last_name">Last name</Label>
            <Input
              id="last_name"
              autoComplete="family-name"
              aria-invalid={!!errors.last_name}
              {...register("last_name")}
            />
            {errors.last_name ? (
              <p className="text-sm text-destructive">
                {errors.last_name.message}
              </p>
            ) : null}
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            aria-invalid={!!errors.email}
            {...register("email")}
          />
          {errors.email ? (
            <p className="text-sm text-destructive">{errors.email.message}</p>
          ) : null}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              aria-invalid={!!errors.password}
              {...register("password")}
            />
            {errors.password ? (
              <p className="text-sm text-destructive">
                {errors.password.message}
              </p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm_password">Confirm password</Label>
            <Input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              aria-invalid={!!errors.confirm_password}
              {...register("confirm_password")}
            />
            {errors.confirm_password ? (
              <p className="text-sm text-destructive">
                {errors.confirm_password.message}
              </p>
            ) : null}
          </div>
        </div>

        <fieldset className="space-y-4 rounded-xl border p-4">
          <legend className="px-1 text-sm font-medium">
            Optional details
          </legend>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="phone_number">Phone number</Label>
              <Input
                id="phone_number"
                autoComplete="tel"
                placeholder="+91…"
                {...register("phone_number")}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="date_of_birth">Date of birth</Label>
              <Input
                id="date_of_birth"
                type="date"
                autoComplete="bday"
                {...register("date_of_birth")}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="city">City</Label>
              <Input id="city" autoComplete="address-level2" {...register("city")} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="country">Country</Label>
              <Input
                id="country"
                autoComplete="country-name"
                {...register("country")}
              />
            </div>
          </div>
        </fieldset>

        {formError ? (
          <p className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {formError}
          </p>
        ) : null}

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Creating account…
            </>
          ) : (
            "Create account"
          )}
        </Button>
      </form>
    </AuthLayout>
  )
}
