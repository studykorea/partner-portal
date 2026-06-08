import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import { universities } from "../../lib/universities";

export default function EligibilityPage() {
  return (
    <main className="min-h-screen bg-[#F6F9FE]"><TopNav />
      <section className="mx-auto max-w-[1320px] px-5 py-14 lg:px-8">
        <div className="rounded-[32px] bg-[#061A40] p-8 text-white"><p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Eligibility Check</p><h1 className="mt-3 text-5xl font900">Student Eligibility Checker</h1><p className="mt-4 max-w-3xl text-blue-100">Check whether a student meets GPA, IELTS/TOEFL/TOPIK, and major requirements before applying.</p></div>
        <div className="mt-8 grid gap-8 lg:grid-cols-[.9fr_1.1fr]">
          <form className="rounded-[28px] border border-[#DCE6F4] bg-white p-7 shadow-sm">
            <div className="grid gap-5 md:grid-cols-2">
              <label className="text-sm font900 text-slate-700">Student Name<input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" /></label>
              <label className="text-sm font900 text-slate-700">University<select className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3">{universities.map((u)=><option key={u.name}>{u.name}</option>)}</select></label>
              <label className="text-sm font900 text-slate-700">Program<select className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3"><option>Undergraduate</option><option>Graduate</option><option>Korean Language Program</option></select></label>
              <label className="text-sm font900 text-slate-700">Major<input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" /></label>
              <label className="text-sm font900 text-slate-700">GPA / Percentage<input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" /></label>
              <label className="text-sm font900 text-slate-700">IELTS / TOEFL / TOPIK<input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" /></label>
            </div>
            <button type="button" className="mt-7 w-full rounded-2xl bg-[#2457D6] px-5 py-4 text-sm font900 text-white">Check Eligibility</button>
          </form>
          <div className="rounded-[28px] border border-[#DCE6F4] bg-white p-7 shadow-sm"><h2 className="text-2xl font900 text-[#061A40]">Result Preview</h2><div className="mt-5 rounded-2xl bg-green-50 p-5 text-green-800"><b>Eligible / Conditional / Not Eligible</b><p className="mt-2 text-sm leading-7">The final result will be calculated from FastAPI + Supabase admission criteria after backend connection.</p></div><div className="mt-5 grid gap-3 text-sm text-slate-600"><p>Minimum IELTS example: 5.5 or higher</p><p>Minimum GPA example: 2.7 or 60% above</p><p>TOPIK condition depends on program and language track.</p></div></div>
        </div>
      </section><Footer /></main>
  );
}
