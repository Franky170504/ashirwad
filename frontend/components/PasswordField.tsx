"use client";
import { InputHTMLAttributes, useState } from "react";
import { inputClass } from "./TextField";

type Props = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string };

/** Password input with a show / hide toggle. */
export default function PasswordField({ label, error, id, name, ...rest }: Props) {
  const [visible, setVisible] = useState(false);
  const fid = id ?? name;

  return (
    <div>
      <label htmlFor={fid} className="mb-1 block text-sm italic text-neutral-700">{label}</label>
      <div className="relative">
        <input
          id={fid} name={name} type={visible ? "text" : "password"}
          className={`${inputClass} pr-10`} aria-invalid={!!error}
          aria-describedby={error ? `${fid}-err` : undefined} {...rest}
        />
        <button
          type="button" onClick={() => setVisible(v => !v)}
          aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible}
          className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-neutral-600 hover:text-brand-button focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-button"
        >
          {visible ? (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M3 3l18 18" /><path d="M10.6 6.1A9.8 9.8 0 0112 6c5 0 8.5 4 9.5 6a13 13 0 01-2.6 3.3M6.6 6.7C4.4 8.1 2.9 10.2 2.5 12c1 2 4.5 6 9.5 6 1.6 0 3-.4 4.2-1" /><path d="M9.9 9.9a3 3 0 004.2 4.2" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M2.5 12C3.5 10 7 6 12 6s8.5 4 9.5 6c-1 2-4.5 6-9.5 6S3.5 14 2.5 12z" /><circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>
      {error && <p id={`${fid}-err`} className="mt-1 text-sm text-red-700">{error}</p>}
    </div>
  );
}
