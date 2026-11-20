import Image from "next/image";
import Link from "next/link";

type Props = { title: string; backHref?: string; children: React.ReactNode };

export default function AuthShell({ title, backHref, children }: Props) {
  return (
    <main className="grid min-h-screen md:grid-cols-[35%_1fr]">
      {/* Left: brand panel (hidden on small screens; logo moves into the card) */}
      <aside className="hidden items-center justify-center bg-brand-light p-8 md:flex">
        <Logo />
      </aside>

      {/* Right: form panel */}
      <section className="flex items-center justify-center bg-brand-dark px-4 py-10">
        <div className="w-full max-w-[400px] rounded-sm bg-white px-8 py-10 shadow-xl md:min-h-[520px]">
          <div className="mb-6 flex justify-center md:hidden"><Logo small /></div>

          {backHref && (
            <Link href={backHref} className="mb-2 inline-flex items-center gap-1 text-sm text-neutral-600 hover:text-brand-button focus:outline-none focus-visible:underline">
              <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M12 4l-6 6 6 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back
            </Link>
          )}

          <h1 className="mb-8 mt-2 text-center font-script text-4xl font-medium">{title}</h1>
          {children}
        </div>
      </section>
    </main>
  );
}

function Logo({ small = false }: { small?: boolean }) {
  // Put your logo file at /public/logo.png
  return (
    <Image src="/logo.png" alt="Ashirwad Industries – Complete Wirecut Solutions"
      width={small ? 180 : 240} height={small ? 56 : 75} priority className="h-auto w-auto" />
  );
}
