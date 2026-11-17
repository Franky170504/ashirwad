import { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string };

export const inputClass =
  "w-full rounded-sm bg-neutral-300 px-3 py-2 text-base font-semibold text-neutral-900 outline-none " +
  "ring-offset-0 transition focus:bg-neutral-200 focus:ring-2 focus:ring-brand-button aria-[invalid=true]:ring-2 aria-[invalid=true]:ring-red-600";

export default function TextField({ label, error, id, name, ...rest }: Props) {
  const fid = id ?? name;
  return (
    <div>
      <label htmlFor={fid} className="mb-1 block text-sm italic text-neutral-700">{label}</label>
      <input id={fid} name={name} className={inputClass} aria-invalid={!!error} aria-describedby={error ? `${fid}-err` : undefined} {...rest} />
      {error && <p id={`${fid}-err`} className="mt-1 text-sm text-red-700">{error}</p>}
    </div>
  );
}
