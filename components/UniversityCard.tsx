import Link from "next/link";

type University = {
  name: string;
  location: string;
  students: string;
  internationalStudents: string;
  topMajors: readonly string[];
  intake: string;
  tuition: string;
  overview: string;
  image: string;
  region: string;
};

export default function UniversityCard({ university }: { university: University }) {
  return (
    <article className="group overflow-hidden rounded-[1.75rem] border border-slate-200 bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-2xl hover:shadow-slate-200">
      <div className="relative h-48 overflow-hidden bg-slate-200">
        <img src={university.image} alt={`${university.name} campus`} className="h-full w-full object-cover transition duration-500 group-hover:scale-105" loading="lazy" />
        <div className="absolute left-4 top-4 rounded-full bg-white/90 px-3 py-1 text-xs font800 text-slate-900 backdrop-blur">{university.region}</div>
      </div>
      <div className="p-6">
        <h3 className="text-xl font900 tracking-tight text-slate-950">{university.name}</h3>
        <p className="mt-1 text-sm font600 text-slate-500">{university.location}</p>
        <p className="mt-4 line-clamp-2 text-sm leading-6 text-slate-600">{university.overview}</p>
        <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-2xl bg-slate-50 p-3"><span className="block font800 text-slate-950">Students</span><span className="text-slate-500">{university.students}</span></div>
          <div className="rounded-2xl bg-slate-50 p-3"><span className="block font800 text-slate-950">Intake</span><span className="text-slate-500">{university.intake}</span></div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {university.topMajors.slice(0, 3).map((major) => <span key={major} className="rounded-full bg-blue-50 px-3 py-1 text-xs font700 text-blue-800">{major}</span>)}
        </div>
        <Link href="/login" className="mt-6 inline-flex w-full justify-center rounded-2xl bg-slate-950 px-5 py-3 text-sm font800 text-white hover:bg-blue-700">View Details</Link>
      </div>
    </article>
  );
}
