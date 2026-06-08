import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";

const steps = ["Application Submitted", "Document Review", "University Screening", "Admission Result", "VIN / Visa Process", "Final Visa Result"];
export default function StatusPage() {
  return (
    <main className="min-h-screen bg-[#F6F9FE]"><TopNav />
      <section className="mx-auto max-w-[1100px] px-5 py-14 lg:px-8">
        <div className="rounded-[32px] bg-[#061A40] p-8 text-white"><p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Application Status</p><h1 className="mt-3 text-5xl font900">Visa & Application Timeline</h1><p className="mt-4 text-blue-100">Track student application progress from submission to final visa result.</p></div>
        <div className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-8 shadow-sm">
          {steps.map((s, idx) => <div key={s} className="grid grid-cols-[60px_1fr] gap-4"><div className="flex flex-col items-center"><div className={`flex h-12 w-12 items-center justify-center rounded-full text-lg font900 ${idx < 3 ? 'bg-green-600 text-white' : idx === 3 ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-400'}`}>{idx < 3 ? '✓' : idx+1}</div>{idx < steps.length-1 && <div className="h-14 w-1 bg-slate-200" />}</div><div className="pb-8"><h3 className="text-xl font900 text-[#061A40]">{s}</h3><p className="mt-1 text-sm text-slate-500">Status details and dates will be loaded from FastAPI after backend connection.</p></div></div>)}
        </div>
      </section><Footer /></main>
  );
}
