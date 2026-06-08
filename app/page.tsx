import Link from "next/link";
import TopNav from "../components/TopNav";
import UniversityCard from "../components/UniversityCard";
import { universities } from "../lib/universities";

const stats = [
  ["5", "Featured universities"],
  ["Fast", "Next.js frontend"],
  ["API", "FastAPI backend"],
  ["Secure", "Supabase-ready storage"],
];

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      <TopNav />
      <section className="relative overflow-hidden bg-slate-950">
        <img src="/assets/home_hero.webp" alt="Korean university campus" className="absolute inset-0 h-full w-full object-cover opacity-45" fetchPriority="high" />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950 via-slate-950/90 to-slate-950/30" />
        <div className="relative mx-auto max-w-7xl px-5 py-24 lg:px-8 lg:py-32">
          <div className="max-w-3xl">
            <span className="rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font800 text-white backdrop-blur">Official partner recruitment system</span>
            <h1 className="mt-8 text-5xl font900 tracking-tight text-white md:text-7xl">Partner Portal for University Recruitment</h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-200">Approved partner agencies can access university details, application requirements, eligibility checking, tuition calculation, and student document management through a faster production-ready portal.</p>
            <div className="mt-10 flex flex-wrap gap-4">
              <Link href="/login" className="rounded-2xl bg-blue-600 px-6 py-4 text-sm font900 text-white shadow-xl shadow-blue-600/30 hover:bg-blue-500">Apply for Partner Access</Link>
              <Link href="/universities" className="rounded-2xl border border-white/30 bg-white/10 px-6 py-4 text-sm font900 text-white backdrop-blur hover:bg-white/20">Explore Universities</Link>
            </div>
          </div>
        </div>
      </section>
      <section className="border-b border-slate-100 bg-white">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-4 px-5 py-8 lg:grid-cols-4 lg:px-8">
          {stats.map(([value, label]) => <div key={label} className="rounded-3xl bg-slate-50 p-6"><p className="text-3xl font900 text-slate-950">{value}</p><p className="mt-1 text-sm font700 text-slate-500">{label}</p></div>)}
        </div>
      </section>
      <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
        <div className="mb-10 flex items-end justify-between gap-4">
          <div><p className="text-sm font900 uppercase tracking-[0.18em] text-blue-700">Featured universities</p><h2 className="mt-3 text-4xl font900 tracking-tight text-slate-950">Explore top partner universities in Korea.</h2></div>
          <Link href="/universities" className="hidden rounded-2xl border border-slate-200 px-5 py-3 text-sm font900 text-slate-950 hover:border-blue-600 hover:text-blue-700 md:inline-flex">View All ›</Link>
        </div>
        <div className="grid grid-cols-1 gap-7 md:grid-cols-2 xl:grid-cols-3">
          {universities.slice(0, 3).map((university) => <UniversityCard key={university.name} university={university} />)}
        </div>
      </section>
      <section className="bg-slate-950 px-5 py-20 text-white lg:px-8">
        <div className="mx-auto max-w-7xl rounded-[2rem] border border-white/10 bg-white/5 p-8 lg:p-12">
          <div className="grid gap-8 lg:grid-cols-[1.2fr_.8fr] lg:items-center">
            <div><h2 className="text-4xl font900 tracking-tight">Built for speed and production deployment.</h2><p className="mt-5 max-w-2xl text-slate-300">This version separates the fast Next.js frontend from the FastAPI backend. Student documents should go to Supabase Storage, not the project folder, so the app remains fast as usage grows.</p></div>
            <div className="grid gap-3 text-sm"><div className="rounded-2xl bg-white/10 p-4 font800">Next.js frontend on Render</div><div className="rounded-2xl bg-white/10 p-4 font800">FastAPI backend on Render</div><div className="rounded-2xl bg-white/10 p-4 font800">Supabase database and storage</div></div>
          </div>
        </div>
      </section>
    </main>
  );
}
