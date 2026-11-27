"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthShell from "@/components/AuthShell";
import TextField from "@/components/TextField";
import SubmitButton from "@/components/SubmitButton";
import FormMessage from "@/components/FormMessage";
import { ApiError, post } from "@/lib/api";

const COOLDOWN = 30; // seconds before "Resend code" is enabled (the server enforces the same)

export default function VerifyLoginPage() {
  const router = useRouter();
  const [emailHint, setEmailHint] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [info, setInfo] = useState("");
  const [secondsLeft, setSecondsLeft] = useState(COOLDOWN);

  const tick = useCallback(() => {
    const sentAt = Number(sessionStorage.getItem("login_otp_sent_at") || 0);
    setSecondsLeft(Math.max(0, COOLDOWN - Math.floor((Date.now() - sentAt) / 1000)));
  }, []);

  useEffect(() => {
    const hint = sessionStorage.getItem("login_email_hint");
    if (!hint) { router.replace("/login"); return; } // must come from the login page
    setEmailHint(hint);
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [router, tick]);

  // Server says the pending login is gone (expired / too many attempts): start over
  function backToLogin() {
    sessionStorage.removeItem("login_email_hint");
    sessionStorage.removeItem("login_otp_sent_at");
    router.replace("/login");
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const code = String(new FormData(e.currentTarget).get("code")).trim();
    setErrors({}); setMessage(""); setInfo(""); setLoading(true);
    try {
      const res = await post<{ username: string }>("/verify-login-otp/", { code });
      sessionStorage.removeItem("login_email_hint");
      sessionStorage.removeItem("login_otp_sent_at");
      router.push(`/${encodeURIComponent(res.username)}/dashboard`);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) { backToLogin(); return; }
        setErrors(err.fieldErrors);
        setMessage(err.message);
      } else setMessage("Could not reach the server.");
    } finally { setLoading(false); }
  }

  async function resend() {
    setErrors({}); setMessage(""); setInfo(""); setResending(true);
    try {
      await post("/resend-login-otp/", {});
      sessionStorage.setItem("login_otp_sent_at", String(Date.now()));
      tick();
      setInfo("A new code has been sent to your email.");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) { backToLogin(); return; }
        setMessage(err.message || "Could not resend the code.");
      } else setMessage("Could not reach the server.");
    } finally { setResending(false); }
  }

  const waiting = secondsLeft > 0;

  return (
    <AuthShell title="Verify Login" backHref="/login">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {emailHint && (
          <p className="text-center text-sm italic text-neutral-600">
            We sent a 6-digit login code to <span className="font-semibold">{emailHint}</span>
          </p>
        )}

        <TextField label="Code" name="code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} required error={errors.code} />

        <div className="flex justify-end">
          <button
            type="button" onClick={resend} disabled={waiting || resending}
            className="text-sm italic text-brand-button hover:underline focus:outline-none focus-visible:underline disabled:cursor-not-allowed disabled:text-neutral-400 disabled:no-underline"
          >
            {waiting ? `Resend code in ${secondsLeft}s` : resending ? "Sending…" : "Resend code"}
          </button>
        </div>

        <FormMessage kind="success" text={info} />
        <FormMessage text={message} />
        <div className="pt-2"><SubmitButton loading={loading}>Verify</SubmitButton></div>
      </form>
    </AuthShell>
  );
}