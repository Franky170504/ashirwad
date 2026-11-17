"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import { post } from "@/lib/api";

type Me = {
  name: string;
  username: string;
  email: string;
  mobile: string;
  date_joined: string;
  last_login: string | null;
  role: string;
};

const fmt = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—";

export default function DashboardPage() {
  const router = useRouter();
  const { username } = useParams<{ username: string }>();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    fetch("/api/me/", { credentials: "include" })
      .then(res => {
        if (!res.ok) { router.replace("/login"); return null; } // not logged in
        return res.json();
      })
      .then((data: Me | null) => {
        if (!data) return;
        // The URL must belong to the logged-in user; otherwise send them to their own dashboard
        if (decodeURIComponent(username) !== data.username) {
          router.replace(`/${encodeURIComponent(data.username)}/dashboard`);
          return;
        }
        setMe(data);
      })
      .catch(() => router.replace("/login"));
  }, [router, username]);

  async function logout() {
    try { await post("/logout/", {}); } finally { router.replace("/login"); }
  }

  if (!me) {
    return <main className="flex min-h-screen items-center justify-center bg-brand-dark text-white">Loading…</main>;
  }

  const rows: [string, string][] = [
    ["Username", me.username],
    ["Email", me.email || "—"],
    ["Mobile", me.mobile || "—"],
    ["Role", me.role],
    ["Member since", fmt(me.date_joined)],
    ["Last login", fmt(me.last_login)],
  ];

  return (
    <main className="min-h-screen bg-brand-dark">
      <header className="flex items-center justify-between bg-brand-light px-6 py-3">
        <Image src="/logo.png" alt="Ashirwad Industries" width={150} height={47} className="h-auto w-auto" priority />
        <button
          onClick={logout}
          className="rounded-sm bg-brand-button px-4 py-1.5 font-script text-lg text-white hover:bg-brand-buttonHover focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-button focus-visible:ring-offset-2"
        >
          Logout
        </button>
      </header>

      <section className="flex justify-center px-4 py-12">
        <div className="w-full max-w-xl rounded-sm bg-white px-8 py-10 shadow-xl">
          <p className="text-center text-lg italic text-neutral-600">Welcome</p>
          <h1 className="mb-8 mt-1 text-center font-script text-5xl">{me.name}</h1>

          <dl className="divide-y divide-neutral-200">
            {rows.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4 py-3">
                <dt className="italic text-neutral-600">{label}</dt>
                <dd className="break-all text-right font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>
    </main>
  );
}
