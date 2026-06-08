import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";

const modules = [
  ["University Management", "Add/edit universities, images, majors, tuition, and application links."],
  ["Partner Agency Approvals", "Approve, reject, and manage partner agency access requests."],
  ["Student Applications", "Review submitted application records and attached documents."],
  ["Document Verification", "Check passport, academic documents, language certificates, and bank files."],
  ["Tuition & Scholarship Rules", "Update scholarship conditions and tuition rules by university/program."],
  ["System Settings", "Manage users, agencies, logs, security, and site settings."],
];

export default function AdminPage() {
  return (
    <main className="min-h-screen bg-[#061A40] text-white"><TopNav />
      <section className="mx-auto max-w-[1720px] px-5 py-12 lg:px-8">
        <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Super Admin Console</p>
        <h1 className="mt-3 text-5xl font900 tracking-tight">Admin Dashboard</h1>
        <p className="mt-4 max-w-3xl text-blue-100">Control partner approvals, university database, application records, document review, tuition rules, and system management.</p>
        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {modules.map(([module, body]) => <div key={module} className="rounded-[24px] border border-white/10 bg-white/5 p-6 shadow-sm"><h2 className="text-xl font900">{module}</h2><p className="mt-3 text-sm leading-7 text-blue-100">{body}</p><button className="mt-5 rounded-2xl bg-white px-5 py-3 text-sm font900 text-[#061A40]">Open Module</button></div>)}
        </div>
      </section><Footer /></main>
  );
}
