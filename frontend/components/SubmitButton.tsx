export default function SubmitButton({ loading, children }: { loading?: boolean; children: React.ReactNode }) {
  return (
    <button
      type="submit" disabled={loading}
      className="w-full rounded-sm bg-brand-button py-2 font-script text-xl text-white transition hover:bg-brand-buttonHover focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-button focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {loading ? "Please wait…" : children}
    </button>
  );
}
