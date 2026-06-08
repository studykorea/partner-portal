import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import UniversityCard from "../../components/UniversityCard";
import { universities } from "../../lib/universities";

export default function SavedUniversitiesPage() {
  return (
    <main className="min-h-screen bg-[#F6F9FE]"><TopNav />
      <section className="mx-auto max-w-[1720px] px-5 py-14 lg:px-8">
        <div className="rounded-[32px] bg-white p-8 shadow-sm border border-[#DCE6F4]"><h1 className="text-4xl font900 text-[#061A40]">Saved Universities</h1><p className="mt-3 text-slate-600">Your shortlisted universities will appear here after login.</p></div>
        <div className="mt-8 grid grid-cols-1 gap-7 md:grid-cols-2 xl:grid-cols-3">{universities.slice(0,3).map((u)=><UniversityCard key={u.name} university={u}/>)}</div>
      </section><Footer /></main>
  );
}
