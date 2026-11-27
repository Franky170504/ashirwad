"use client";
import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import AuthShell from "@/components/AuthShell";
import TextField from "@/components/TextField";
import PasswordField from "@/components/PasswordField";
import SubmitButton from "@/components/SubmitButton";
import FormMessage from "@/components/FormMessage";
import { ApiError, post } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setErrors({}); setMessage(""); setLoading(true);
    try {
      const res = await post<{ otp_required?: boolean; email?: string; username?: string }>("/login/", {
        identifier: fd.get("identifier"),
        password: fd.get("password"),
        remember_me: fd.get("remember_me") === "on",
      });

      // Password was correct: a code has been emailed, go verify it
      if (res.otp_required) {
        sessionStorage.setItem("login_email_hint", res.email ?? "");
        sessionStorage.setItem("login_otp_sent_at", String(Date.now()));
        router.push("/verify-login"); // use your actual route for the verify page
        return;
      }

      // Fallback if the server ever logs in without 2FA
      if (res.username) router.push(`/${encodeURIComponent(res.username)}/dashboard`);
    } catch (err) {
      if (err instanceof ApiError) { setErrors(err.fieldErrors); setMessage(err.message); }
      else setMessage("Could not reach the server.");
    } finally { setLoading(false); }
  }

  return (
    <AuthShell title="Login">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {params.get("reset") && <FormMessage kind="success" text="Password updated. Please log in." />}
        <TextField label="Email / UserID" name="identifier" autoComplete="username" required error={errors.identifier} />
        <PasswordField label="Password" name="password" autoComplete="current-password" required error={errors.password} />

        <div className="flex items-center justify-between text-sm">
          <label className="flex cursor-pointer items-center gap-2 italic">
            <input type="checkbox" name="remember_me" className="h-4 w-4 accent-brand-button" /> Remember Me
          </label>
          <Link href="/forgot-password" className="italic text-brand-button hover:underline">Reset Password</Link>
        </div>

        <FormMessage text={message} />
        <SubmitButton loading={loading}>Login</SubmitButton>
      </form>
    </AuthShell>
  );
}

export default function LoginPage() {
  return <Suspense><LoginForm /></Suspense>;
}