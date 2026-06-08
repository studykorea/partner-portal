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
  homepage: string;
  region: string;
  address: string;
  phone: string;
};

export default function UniversityCard({ university }: { university: University }) {
  return (
    <article className="group relative overflow-hidden rounded-[20px] border border-[#DCE6F4] bg-white shadow-[0_12px_28px_rgba(16,24,40,.08)] transition hover:-translate-y-1 hover:shadow-[0_20px_40px_rgba(16,24,40,.14)]">
      <div className="relative h-36 overflow-hidden bg-slate-200">
        <img src={university.image} alt={`${university.name} campus`} className="h-full w-full object-cover transition duration-500 group-hover:scale-105" loading="lazy" />
        <span className="absolute left-4 top-4 rounded-full bg-[#061A40] px-3 py-1.5 text-xs font900 text-white shadow-lg">★ Featured</span>
        <span className="absolute right-4 top-4 rounded-full bg-white/90 px-3 py-1.5 text-xs font900 text-[#061A40]">{university.region}</span>
      </div>
      <div className="absolute left-5 top-[106px] flex h-16 w-16 items-center justify-center rounded-full border-[5px] border-white bg-white shadow-lg">
        <span className="text-lg font900 text-[#2457D6]">{university.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}</span>
      </div>
      <div className="p-6 pt-11">
        <h3 className="text-xl font900 tracking-tight text-[#061A40]">{university.name}</h3>
        <p className="mt-2 flex items-center gap-2 text-sm font700 text-slate-500"><span>📍</span>{university.location}</p>
        <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-2xl bg-[#F6F9FE] p-3"><small className="block font800 text-slate-500">Total Students</small><b className="text-[#061A40]">{university.students}</b></div>
          <div className="rounded-2xl bg-[#F6F9FE] p-3"><small className="block font800 text-slate-500">International</small><b className="text-[#061A40]">{university.internationalStudents}</b></div>
        </div>
        <p className="mt-4 line-clamp-2 text-sm leading-6 text-slate-600">{university.overview}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {university.topMajors.slice(0, 3).map((major) => <span key={major} className="rounded-full bg-blue-50 px-3 py-1 text-xs font800 text-blue-800">{major}</span>)}
        </div>
        <div className="mt-5 rounded-2xl border border-slate-100 bg-slate-50 p-3 text-xs leading-5 text-slate-600">
          <b className="text-[#061A40]">Tuition:</b> {university.tuition}<br />
          <b className="text-[#061A40]">Intake:</b> {university.intake}
        </div>
        <Link href={`/universities#${encodeURIComponent(university.name)}`} className="mt-5 inline-flex w-full items-center justify-between rounded-2xl bg-[#061A40] px-5 py-3 text-sm font900 text-white hover:bg-[#2457D6]"><span>View Programs</span><b>→</b></Link>
      </div>
    </article>
  );
}
