import TopNav from "../../components/TopNav";

const modules = ["University management", "Partner agency approvals", "Student applications", "Document verification", "Tuition and scholarship rules", "System settings"];

export default function AdminPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <TopNav />
      <section className="mx-auto max-w-7xl px-5 py-12 lg:px-8">
        <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Admin console</p>
        <h1 className="mt-3 text-5xl font900 tracking-tight">Admin Dashboard</h1>
        <p className="mt-4 max-w-2xl text-slate-300">Production admin functions should be protected by Supabase role-based access control and backend authorization checks.</p>
        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {modules.map((module) => <div key={module} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6"><h2 className="text-xl font900">{module}</h2><p className="mt-3 text-sm leading-6 text-slate-400">Ready to connect to backend APIs and Supabase tables.</p></div>)}
        </div>
      </section>
    </main>
  );
}
