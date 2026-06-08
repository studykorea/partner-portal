import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import { universities } from "../../lib/universities";

export default function TuitionPage() {
  return (
    <main className="min-h-screen bg-[#F6F9FE]"><TopNav />
      <section className="mx-auto max-w-[1320px] px-5 py-14 lg:px-8">
        <div className="rounded-[32px] bg-[#061A40] p-8 text-white"><p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Tuition & Scholarship</p><h1 className="mt-3 text-5xl font900">Tuition Calculator</h1><p className="mt-4 max-w-3xl text-blue-100">Estimate application fee, admission fee, tuition fee, scholarship discount, and final payment amount.</p></div>
        <div className="mt-8 grid gap-8 lg:grid-cols-[.9fr_1.1fr]">
          <form className="rounded-[28px] border border-[#DCE6F4] bg-white p-7 shadow-sm">
            <div className="grid gap-5 md:grid-cols-2">
              <label className="text-sm font900 text-slate-700">University<select className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3">{universities.map((u)=><option key={u.name}>{u.name}</option>)}</select></label>
              <label className="text-sm font900 text-slate-700">Program<select className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3"><option>Undergraduate</option><option>Graduate</option><option>KLP / EAP</option></select></label>
              <label className="text-sm font900 text-slate-700">Major<input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" /></label>
              <label className="text-sm font900 text-slate-700">Language Score<input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" /></label>
            </div>
            <button type="button" className="mt-7 w-full rounded-2xl bg-[#2457D6] px-5 py-4 text-sm font900 text-white">Calculate Tuition</button>
          </form>
          <div className="rounded-[28px] border border-[#DCE6F4] bg-white p-7 shadow-sm"><h2 className="text-2xl font900 text-[#061A40]">Estimated Summary</h2><div className="mt-5 grid gap-3 text-sm"><div className="flex justify-between rounded-2xl bg-slate-50 p-4"><b>Application Fee</b><span>KRW 80,000</span></div><div className="flex justify-between rounded-2xl bg-slate-50 p-4"><b>Tuition Fee</b><span>Based on program</span></div><div className="flex justify-between rounded-2xl bg-blue-50 p-4 text-blue-800"><b>Scholarship</b><span>30–50% depending on score</span></div><div className="flex justify-between rounded-2xl bg-green-50 p-4 text-green-800"><b>Final Tuition</b><span>Calculated by backend</span></div></div></div>
        </div>
      </section><Footer /></main>
  );
}
