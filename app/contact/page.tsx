import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-[#F6F9FE]"><TopNav />
      <section className="mx-auto max-w-[1100px] px-5 py-14 lg:px-8">
        <div className="rounded-[32px] bg-[#061A40] p-8 text-white"><p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Contact Us</p><h1 className="mt-3 text-5xl font900">Partner Support Center</h1><p className="mt-4 max-w-3xl text-blue-100">Send questions about university recruitment, partner access, applications, documents, or visa status.</p></div>
        <form className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-8 shadow-sm">
          <div className="grid gap-5 md:grid-cols-2"><label className="text-sm font900 text-slate-700">Name<input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" /></label><label className="text-sm font900 text-slate-700">Email<input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" /></label></div>
          <label className="mt-5 block text-sm font900 text-slate-700">Message<textarea className="mt-2 h-40 w-full rounded-2xl border border-slate-200 px-4 py-3" /></label>
          <button type="button" className="mt-6 rounded-2xl bg-[#2457D6] px-8 py-4 text-sm font900 text-white">Submit Inquiry</button>
        </form>
      </section><Footer /></main>
  );
}
