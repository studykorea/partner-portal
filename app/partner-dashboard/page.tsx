import TopNav from "../../components/TopNav";

const cards = [
  ["Applications", "24", "Track student application status"],
  ["Documents", "18", "Review pending document uploads"],
  ["Eligibility checks", "42", "Check GPA, language, and program fit"],
  ["Inquiries", "9", "Follow up with interested students"],
];

export default function PartnerDashboardPage() {
  return (
    <main className="min-h-screen bg-slate-50">
      <TopNav />
      <section className="mx-auto max-w-7xl px-5 py-12 lg:px-8">
        <h1 className="text-5xl font900 tracking-tight text-slate-950">Partner Dashboard</h1>
        <p className="mt-4 max-w-2xl text-slate-600">Fast dashboard shell. Connect this page to FastAPI endpoints after Supabase tables and authentication are finalized.</p>
        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {cards.map(([title, value, desc]) => <div key={title} className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm"><p className="text-sm font800 text-slate-500">{title}</p><p className="mt-3 text-4xl font900 text-slate-950">{value}</p><p className="mt-2 text-sm text-slate-500">{desc}</p></div>)}
        </div>
        <div className="mt-8 rounded-[2rem] border border-slate-200 bg-white p-6">
          <h2 className="text-2xl font900 text-slate-950">Recent activity</h2>
          <div className="mt-5 overflow-hidden rounded-2xl border border-slate-100">
            {["New D4-1 inquiry created", "Eligibility check completed", "Student passport uploaded", "University shortlist updated"].map((item, idx) => <div key={item} className="flex items-center justify-between border-b border-slate-100 px-5 py-4 last:border-b-0"><span className="font700 text-slate-700">{item}</span><span className="text-sm text-slate-400">Step {idx + 1}</span></div>)}
          </div>
        </div>
      </section>
    </main>
  );
}
