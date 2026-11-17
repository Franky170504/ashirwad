"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import AuthShell from "@/components/AuthShell";
import TextField from "@/components/TextField";
import SubmitButton from "@/components/SubmitButton";
import FormMessage from "@/components/FormMessage";
import { ApiError, post } from "@/lib/api";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const email = String(new FormData(e.currentTarget).get("email"));
    setErrors({}); setMessage(""); setLoading(true);
    try {
      await post("/forgot-password/", { email });
      sessionStorage.setItem("reset_email", email);
      router.push("/verify-code");
    } catch (err) {
      if (err instanceof ApiError) { setErrors(err.fieldErrors); setMessage(err.message); }
      else setMessage("Could not reach the server.");
    } finally { setLoading(false); }
  }

  return (
    <AuthShell title="Forgot Password" backHref="/login">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <TextField label="Email" name="email" type="email" autoComplete="email" required error={errors.email} />
        <FormMessage text={message} />
        <div className="pt-4"><SubmitButton loading={loading}>Submit</SubmitButton></div>
      </form>
    </AuthShell>
  );
}
