import Link from "next/link";
import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-[#F6F9FE]"><TopNav />
      <section className="mx-auto grid max-w-[1320px] gap-10 px-5 py-16 lg:grid-cols-[.9fr_1.1fr] lg:px-8">
        <div className="rounded-[32px] bg-[#061A40] p-10 text-white">
          <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Partner access</p>
          <h1 className="mt-4 text-5xl font900 tracking-tight">Login</h1>
          <p className="mt-5 text-lg leading-8 text-blue-100">Approved partners, staff, and admin users can access dashboards after login.</p>
          <div className="mt-8 rounded-2xl bg-white/10 p-5 text-sm leading-7 text-blue-100">Access includes university details, application forms, eligibility checks, tuition/scholarship calculators, and application status management.</div>
        </div>
        <form className="rounded-[32px] border border-[#DCE6F4] bg-white p-8 shadow-xl shadow-slate-200">
          <label className="block text-sm font900 text-slate-700">Username or Email</label>
          <input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-600" placeholder="partner@example.com" />
          <label className="mt-5 block text-sm font900 text-slate-700">Password</label>
          <input type="password" className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-600" placeholder="••••••••" />
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <Link href="/partner-dashboard" className="flex justify-center rounded-2xl bg-[#2457D6] px-5 py-4 text-sm font900 text-white hover:bg-blue-800">Partner Dashboard</Link>
            <Link href="/admin" className="flex justify-center rounded-2xl bg-[#061A40] px-5 py-4 text-sm font900 text-white hover:bg-slate-800">Admin Dashboard</Link>
          </div>
          <p className="mt-5 text-center text-sm text-slate-500">Need access? <Link href="/apply" className="font900 text-blue-700">Create New Partner Account</Link></p>
        </form>
      </section><Footer /></main>
  );
}
