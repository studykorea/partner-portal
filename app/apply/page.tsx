import Link from "next/link";
import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";

export default function ApplyPage() {
  return (
    <main className="min-h-screen bg-[#F6F9FE]"><TopNav />
      <section className="mx-auto grid max-w-[1320px] gap-8 px-5 py-14 lg:grid-cols-[.8fr_1.2fr] lg:px-8">
        <div className="rounded-[30px] bg-[#061A40] p-8 text-white">
          <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Partner Sign Up</p>
          <h1 className="mt-4 text-4xl font900 leading-tight">Create New Partner Account</h1>
          <p className="mt-5 text-blue-100 leading-8">Submit your agency information for approval. Detailed university data is available after admin approval.</p>
          <div className="mt-8 grid gap-3 text-sm font900"><div className="rounded-2xl bg-white/10 p-4">Official agency / representative</div><div className="rounded-2xl bg-white/10 p-4">Country and contact details</div><div className="rounded-2xl bg-white/10 p-4">Approval status tracking</div></div>
        </div>
        <form className="rounded-[30px] border border-[#DCE6F4] bg-white p-8 shadow-sm">
          <div className="grid gap-5 md:grid-cols-2">
            {['Full Name','Agency / Organization','Country','Phone Number','Email','Username'].map((label) => <label key={label} className="text-sm font900 text-slate-700">{label}<input className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-600" placeholder={label} /></label>)}
            <label className="text-sm font900 text-slate-700">Password<input type="password" className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-600" placeholder="••••••••" /></label>
            <label className="text-sm font900 text-slate-700">Account Category<select className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-600"><option>Partner Agency</option><option>Official Representative</option><option>Staff</option></select></label>
          </div>
          <button type="button" className="mt-7 w-full rounded-2xl bg-[#2457D6] px-5 py-4 text-sm font900 text-white">Submit Partner Access Request</button>
          <p className="mt-4 text-center text-sm text-slate-500">Already approved? <Link className="font900 text-blue-700" href="/login">Go to Login</Link></p>
        </form>
      </section><Footer /></main>
  );
}
