import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import UniversityCard from "../../components/UniversityCard";
import { universities } from "../../lib/universities";

export default function UniversitiesPage() {
  const regions = ["All", ...Array.from(new Set(universities.map((u) => u.region)))];
  return (
    <main className="min-h-screen bg-[#F6F9FE]">
      <TopNav />
      <section className="bg-[#061A40] px-5 py-16 text-white lg:px-8">
        <div className="mx-auto max-w-[1720px]">
          <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Universities Information</p>
          <h1 className="mt-4 text-5xl font900 tracking-tight">Explore Partner Universities</h1>
          <p className="mt-5 max-w-3xl text-lg leading-8 text-blue-100">Approved partners can review admission programs, tuition ranges, intake periods, contact details, eligibility criteria, and application links.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            {regions.map((r) => <span key={r} className="rounded-full bg-white/10 px-4 py-2 text-sm font900 text-white">{r}</span>)}
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-[1720px] px-5 py-12 lg:px-8">
        <div className="mb-8 grid gap-4 rounded-[24px] border border-[#DCE6F4] bg-white p-5 shadow-sm md:grid-cols-4">
          <div className="rounded-2xl bg-slate-50 p-4"><b className="text-[#061A40]">{universities.length}</b><p className="text-sm text-slate-500">Partner universities</p></div>
          <div className="rounded-2xl bg-slate-50 p-4"><b className="text-[#061A40]">March / September</b><p className="text-sm text-slate-500">Main intake</p></div>
          <div className="rounded-2xl bg-slate-50 p-4"><b className="text-[#061A40]">Undergraduate / Graduate</b><p className="text-sm text-slate-500">Program levels</p></div>
          <div className="rounded-2xl bg-slate-50 p-4"><b className="text-[#061A40]">Partner-only</b><p className="text-sm text-slate-500">Detailed access</p></div>
        </div>
        <div className="grid grid-cols-1 gap-7 md:grid-cols-2 xl:grid-cols-3">
          {universities.map((university) => <div key={university.name} id={encodeURIComponent(university.name)}><UniversityCard university={university} /></div>)}
        </div>
      </section>
      <Footer />
    </main>
  );
}
