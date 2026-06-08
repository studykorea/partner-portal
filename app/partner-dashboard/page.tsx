import Link from "next/link";
import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";

const cards = [
  ["Ongoing Applications", "24", "Track application and visa status", "/application-status"],
  ["Saved Universities", "8", "Review shortlisted universities", "/saved-universities"],
  ["Eligibility Checks", "42", "Check GPA and language criteria", "/eligibility"],
  ["Tuition Calculations", "31", "Estimate tuition and scholarship", "/tuition"],
];
const quick = ["Start New Student Application", "Upload Student Documents", "Check Application Status", "Download Admission Checklist", "Contact University Staff"];

export default function PartnerDashboardPage() {
  return (
    <main className="min-h-screen bg-[#F6F9FE]"><TopNav />
      <section className="mx-auto max-w-[1720px] px-5 py-12 lg:px-8">
        <div className="rounded-[32px] bg-[#061A40] p-8 text-white">
          <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Partner Dashboard</p>
          <h1 className="mt-3 text-5xl font900 tracking-tight">Welcome back, Partner</h1>
          <p className="mt-4 max-w-3xl text-blue-100">Manage universities, eligibility checks, tuition calculations, student applications, documents, and visa status from one dashboard.</p>
        </div>
        <div className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {cards.map(([title, value, desc, href]) => <Link key={title} href={href} className="rounded-[24px] border border-[#DCE6F4] bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"><p className="text-sm font900 text-slate-500">{title}</p><p className="mt-3 text-4xl font900 text-[#061A40]">{value}</p><p className="mt-2 text-sm text-slate-500">{desc}</p></Link>)}
        </div>
        <div className="mt-8 grid gap-8 lg:grid-cols-[.8fr_1.2fr]">
          <div className="rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm">
            <h2 className="text-2xl font900 text-[#061A40]">Quick Actions</h2>
            <div className="mt-5 grid gap-3">{quick.map((q) => <button key={q} className="rounded-2xl border border-slate-200 px-5 py-4 text-left text-sm font900 text-slate-700 hover:border-blue-500 hover:text-blue-700">{q}</button>)}</div>
          </div>
          <div className="rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm">
            <h2 className="text-2xl font900 text-[#061A40]">Recent Activity</h2>
            <div className="mt-5 overflow-hidden rounded-2xl border border-slate-100">
              {['New D4-1 inquiry created','Eligibility check completed','Student passport uploaded','University shortlist updated','Tuition calculation saved'].map((item, idx) => <div key={item} className="flex items-center justify-between border-b border-slate-100 px-5 py-4 last:border-b-0"><span className="font800 text-slate-700">{item}</span><span className="rounded-full bg-blue-50 px-3 py-1 text-xs font900 text-blue-700">Step {idx + 1}</span></div>)}
            </div>
          </div>
        </div>
      </section><Footer /></main>
  );
}
