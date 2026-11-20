"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import AuthShell from "@/components/AuthShell";
import TextField from "@/components/TextField";
import PasswordField from "@/components/PasswordField";
import SubmitButton from "@/components/SubmitButton";
import FormMessage from "@/components/FormMessage";
import { ApiError, post } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>;
    setMessage("");
    if (f.password !== f.confirm_password) {
      setErrors({ confirm_password: "Passwords do not match." });
      return;
    }
    setErrors({}); setLoading(true);
    try {
      const res = await post<{ username: string }>("/register/", f);
      router.push(`/login?registered=1&u=${encodeURIComponent(res.username)}`);
    } catch (err) {
      if (err instanceof ApiError) { setErrors(err.fieldErrors); setMessage(err.message); }
      else setMessage("Could not reach the server.");
    } finally { setLoading(false); }
  }

  return (
    <AuthShell title="New User">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <div className="grid grid-cols-2 gap-4">
          <TextField label="First Name" name="firstname" autoComplete="given-name" required error={errors.firstname} />
          <TextField label="Last Name" name="lastname" autoComplete="family-name" required error={errors.lastname} />
          <TextField label="Email" name="email" type="email" autoComplete="email" required error={errors.email} />
          <TextField label="Mobile" name="mobile_no" type="tel" inputMode="tel" autoComplete="tel" required error={errors.mobile_no} />
        </div>
        <PasswordField label="Password" name="password" autoComplete="new-password" required minLength={8} error={errors.password} />
        <PasswordField label="Confirm Password" name="confirm_password" autoComplete="new-password" required error={errors.confirm_password} />
        <FormMessage text={message} />
        <div className="pt-4"><SubmitButton loading={loading}>Create</SubmitButton></div>
      </form>
    </AuthShell>
  );
}