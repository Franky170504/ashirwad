"use client";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthShell from "@/components/AuthShell";
import PasswordField from "@/components/PasswordField";
import SubmitButton from "@/components/SubmitButton";
import FormMessage from "@/components/FormMessage";
import { ApiError, post } from "@/lib/api";

export default function SetPasswordPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  useEffect(() => { if (!sessionStorage.getItem("reset_token")) router.replace("/forgot-password"); }, [router]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const password = String(fd.get("new_password"));
    setMessage("");
    if (password !== fd.get("confirm_new_password")) {
      setErrors({ confirm_new_password: "Passwords do not match." });
      return;
    }
    setErrors({}); setLoading(true);
    try {
      await post("/set-password/", {
        email: sessionStorage.getItem("reset_email"),
        reset_token: sessionStorage.getItem("reset_token"),
        new_password: password,
      });
      sessionStorage.removeItem("reset_email");
      sessionStorage.removeItem("reset_token");
      router.push("/login?reset=1");
    } catch (err) {
      if (err instanceof ApiError) { setErrors(err.fieldErrors); setMessage(err.message); }
      else setMessage("Could not reach the server.");
    } finally { setLoading(false); }
  }

  return (
    <AuthShell title="Set Password" backHref="/verify-code">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <PasswordField label="New Password" name="new_password" autoComplete="new-password" required minLength={8} error={errors.new_password} />
        <PasswordField label="Confirm New Password" name="confirm_new_password" autoComplete="new-password" required error={errors.confirm_new_password} />
        <FormMessage text={message} />
        <div className="pt-4"><SubmitButton loading={loading}>Set Password</SubmitButton></div>
      </form>
    </AuthShell>
  );
}
