import Link from "next/link";
import TopNav from "../../components/TopNav";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-slate-50">
      <TopNav />
      <section className="mx-auto grid max-w-7xl gap-10 px-5 py-16 lg:grid-cols-2 lg:px-8">
        <div className="rounded-[2rem] bg-slate-950 p-10 text-white">
          <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Partner access</p>
          <h1 className="mt-4 text-5xl font900 tracking-tight">Login or apply for access</h1>
          <p className="mt-5 text-slate-300">This frontend is ready for Supabase Auth. The login form is currently a fast UI screen and should be connected to authentication in the backend/API phase.</p>
        </div>
        <form className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200">
          <label className="block text-sm font800 text-slate-700">Email</label>
          <input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-600" placeholder="partner@example.com" />
          <label className="mt-5 block text-sm font800 text-slate-700">Password</label>
          <input type="password" className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-600" placeholder="••••••••" />
          <Link href="/partner-dashboard" className="mt-6 flex w-full justify-center rounded-2xl bg-blue-700 px-5 py-4 text-sm font900 text-white hover:bg-blue-800">Continue to Dashboard</Link>
          <p className="mt-4 text-center text-sm text-slate-500">Production login should use Supabase Auth + protected API routes.</p>
        </form>
      </section>
    </main>
  );
}
