import Link from "next/link";
import TopNav from "../components/TopNav";
import Footer from "../components/Footer";
import UniversityCard from "../components/UniversityCard";
import { universities } from "../lib/universities";

const services = [
  ["Eligibility Checking", "Check GPA, IELTS/TOEFL/TOPIK, and program requirements before submitting applications."],
  ["Tuition & Scholarship", "Estimate application fee, admission fee, tuition, scholarship percentage, and final tuition."],
  ["Student Applications", "Prepare student information, documents, application status, and visa result tracking."],
  ["University Information", "Access admission majors, intakes, location, contact details, and partner-only program information."],
];

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      <TopNav />
      <section className="relative min-h-[560px] overflow-hidden bg-[#061A40]">
        <img src="/assets/home_hero.webp" alt="Korean university campus" className="absolute inset-0 h-full w-full object-cover opacity-55" fetchPriority="high" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#061A40] via-[#061A40]/90 to-[#061A40]/25" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_40%_10%,rgba(255,255,255,.18)_0,transparent_28%)]" />
        <div className="relative mx-auto max-w-[1720px] px-5 py-20 lg:px-8 lg:py-24">
          <div className="max-w-3xl">
            <div className="mb-10 inline-flex items-center rounded-full border border-white/25 bg-white/10 px-4 py-2 text-sm font900 text-white backdrop-blur"><span className="mr-2 rounded-full bg-white/20 px-3 py-1">Step 1</span>Home Page</div>
            <h1 className="text-5xl font900 leading-tight tracking-tight text-white md:text-7xl">Partner Portal for<br />University Recruitment</h1>
            <p className="mt-9 max-w-3xl text-xl leading-9 text-white/95">Approved partner agencies can access university details, application requirements, eligibility checking, and tuition/scholarship calculation.</p>
            <div className="mt-9 flex flex-wrap gap-4">
              <Link href="/apply" className="rounded-none bg-[#4968D9] px-7 py-4 text-base font900 text-white shadow-xl shadow-blue-900/25 hover:bg-[#2457D6]">👤&nbsp;&nbsp;Apply for Partner Access</Link>
              <Link href="/universities" className="rounded-none border border-white/60 bg-white/10 px-7 py-4 text-base font900 text-white backdrop-blur hover:bg-white/20">🏛️&nbsp;&nbsp;Explore Universities</Link>
            </div>
            <p className="mt-7 text-base font900 text-white">🔒 Detailed information is available only for approved partners.</p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1720px] px-5 py-20 lg:px-8">
        <div className="mb-10 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-5xl font900 tracking-tight text-[#061A40]">Featured Universities</h2>
            <p className="mt-6 text-lg text-slate-500">Explore top partner universities in Korea.</p>
          </div>
          <Link href="/universities" className="hidden rounded-2xl border border-slate-200 px-7 py-4 text-base font900 text-[#061A40] shadow-sm hover:border-blue-600 hover:text-blue-700 md:inline-flex">View All&nbsp;›</Link>
        </div>
        <div className="grid grid-cols-1 gap-7 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
          {universities.map((university) => <UniversityCard key={university.name} university={university} />)}
        </div>
      </section>

      <section className="bg-[#F6F9FE] px-5 py-20 lg:px-8">
        <div className="mx-auto max-w-[1720px]">
          <div className="text-center">
            <p className="text-sm font900 uppercase tracking-[0.18em] text-[#2457D6]">Partner-only services</p>
            <h2 className="mt-3 text-4xl font900 tracking-tight text-[#061A40]">Everything partners need in one fast portal</h2>
          </div>
          <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {services.map(([title, body]) => (
              <div key={title} className="rounded-[24px] border border-[#DCE6F4] bg-white p-7 shadow-sm">
                <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-xl">✓</div>
                <h3 className="text-xl font900 text-[#061A40]">{title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-5 py-20 lg:px-8">
        <div className="mx-auto grid max-w-[1720px] gap-8 rounded-[32px] bg-[#061A40] p-8 text-white lg:grid-cols-[1fr_.8fr] lg:p-12">
          <div>
            <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Fast migration restored</p>
            <h2 className="mt-3 text-4xl font900 tracking-tight">Same portal content, faster Next.js structure.</h2>
            <p className="mt-5 max-w-3xl text-base leading-8 text-blue-100">This version restores the original homepage, university cards, partner access, dashboard sections, admin modules, eligibility tools, tuition tools, and contact/status pages as fast frontend screens. The legacy Streamlit file is still kept only as backup.</p>
          </div>
          <div className="grid gap-3 text-sm font900">
            <div className="rounded-2xl bg-white/10 p-4">Next.js frontend on Render</div>
            <div className="rounded-2xl bg-white/10 p-4">FastAPI backend ready</div>
            <div className="rounded-2xl bg-white/10 p-4">Supabase database/storage ready</div>
          </div>
        </div>
      </section>
      <Footer />
    </main>
  );
}
