import TopNav from "../../components/TopNav";
import UniversityCard from "../../components/UniversityCard";
import { universities } from "../../lib/universities";

export default function UniversitiesPage() {
  return (
    <main className="min-h-screen bg-slate-50">
      <TopNav />
      <section className="mx-auto max-w-7xl px-5 py-16 lg:px-8">
        <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-700">University database</p>
        <h1 className="mt-3 text-5xl font900 tracking-tight text-slate-950">Universities</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">Fast, searchable university cards can later be connected to the FastAPI endpoint and Supabase database. Current data is loaded statically for maximum speed.</p>
        <div className="mt-10 grid grid-cols-1 gap-7 md:grid-cols-2 xl:grid-cols-3">
          {universities.map((university) => <UniversityCard key={university.name} university={university} />)}
        </div>
      </section>
    </main>
  );
}
