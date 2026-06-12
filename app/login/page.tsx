"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = email.trim().toLowerCase();
    if (!value || !password) {
      setError("Please enter your email and password.");
      return;
    }

    // Temporary role routing until Supabase Auth is connected.
    // Super admin accounts go to /admin, other approved users go to /partner-dashboard.
    if (value.includes("admin") || value.includes("super")) {
      router.push("/admin");
      return;
    }
    router.push("/partner-dashboard");
  }

  return (
    <main className="min-h-screen bg-[#F6F9FE]">
      <TopNav />
      <section className="mx-auto grid max-w-[1320px] gap-10 px-5 py-16 lg:grid-cols-[.9fr_1.1fr] lg:px-8">
        <div className="rounded-[32px] bg-[#061A40] p-10 text-white shadow-2xl shadow-slate-300">
          <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">KUA Partner Access</p>
          <h1 className="mt-4 text-5xl font900 tracking-tight">Login</h1>
          <p className="mt-5 text-lg leading-8 text-blue-100">
            Login with your approved partner, staff, or super admin account.
          </p>
          <div className="mt-8 rounded-2xl bg-white/10 p-5 text-sm leading-7 text-blue-100">
            Super admins can manage universities, applications, partner approvals, logos, images, deadlines, tuition fees, documents, and platform settings.
          </div>
        </div>

        <form onSubmit={handleLogin} className="rounded-[32px] border border-[#DCE6F4] bg-white p-8 shadow-xl shadow-slate-200">
          <h2 className="text-3xl font900 text-[#061A40]">Account Login</h2>
          <p className="mt-2 text-sm text-slate-500">Enter your approved account information.</p>

          <label className="mt-7 block text-sm font900 text-slate-700">Username or Email</label>
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-600"
            placeholder="admin@kua.com or partner@example.com"
          />

          <label className="mt-5 block text-sm font900 text-slate-700">Password</label>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-600"
            placeholder="••••••••"
          />

          {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm font800 text-red-700">{error}</p>}

          <button type="submit" className="mt-6 w-full rounded-2xl bg-[#061A40] px-5 py-4 text-sm font900 text-white shadow-lg shadow-slate-300 hover:bg-[#2457D6]">
            Login
          </button>

          <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-sm text-slate-500">
            <span>Need access?</span>
            <Link href="/apply" className="font900 text-blue-700">Partner Sign Up</Link>
          </div>
        </form>
      </section>
      <Footer />
    </main>
  );
}
