"use client";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthShell from "@/components/AuthShell";
import TextField from "@/components/TextField";
import SubmitButton from "@/components/SubmitButton";
import FormMessage from "@/components/FormMessage";
import { ApiError, post } from "@/lib/api";

export default function VerifyCodePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  // Must arrive here from "Forgot Password"
  useEffect(() => { if (!sessionStorage.getItem("reset_email")) router.replace("/forgot-password"); }, [router]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const code = String(new FormData(e.currentTarget).get("code")).trim();
    setErrors({}); setMessage(""); setLoading(true);
    try {
      const res = await post<{ reset_token?: string }>("/verify-code/", {
        email: sessionStorage.getItem("reset_email"), code,
      });
      // Django returns a short-lived token that authorises the password change
      sessionStorage.setItem("reset_token", res.reset_token ?? code);
      router.push("/set-password");
    } catch (err) {
      if (err instanceof ApiError) { setErrors(err.fieldErrors); setMessage(err.message); }
      else setMessage("Could not reach the server.");
    } finally { setLoading(false); }
  }

  return (
    <AuthShell title="Verify Code" backHref="/login">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <TextField label="Code" name="code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} required error={errors.code} />
        <FormMessage text={message} />
        <div className="pt-4"><SubmitButton loading={loading}>Verify</SubmitButton></div>
      </form>
    </AuthShell>
  );
}
