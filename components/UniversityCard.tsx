import Link from "next/link";
import UniversitySeal from "./UniversitySeal";

const admissionStatus = [
  { label: "Application Open", tone: "open", note: "Undergraduate · Graduate · KLP/EAP" },
  { label: "Opening Soon", tone: "soon", note: "Fall 2026 intake" },
  { label: "Application Open", tone: "open", note: "Global programs available" },
  { label: "Closed", tone: "closed", note: "Next round will be announced" },
  { label: "Opening Soon", tone: "soon", note: "Tourism programs available" },
] as const;

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
  logo?: string;
};

function slugify(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export default function UniversityCard({ university, index = 0 }: { university: University; index?: number }) {
  const status = admissionStatus[index % admissionStatus.length];
  return (
    <article className="kua-university-card v348-card">
      <div className="kua-card-photo-wrap">
        <img src={university.image} alt={`${university.name} campus`} className="kua-card-photo" loading="lazy" />
        <div className="kua-card-badge">★ Featured</div>
        <div className="kua-card-gradient" />
      </div>
      <div className="kua-card-logo-overlap">
        {university.logo ? <img src={university.logo} alt={`${university.name} logo`} /> : <UniversitySeal name={university.name} size="sm" />}
      </div>
      <div className="kua-card-body">
        <div className={`kua-admission-status ${status.tone}`}>
          <span>{status.label}</span>
          <small>{status.note}</small>
        </div>
        <h3>{university.name}</h3>
        <p className="kua-card-location">⌖ {university.location}</p>
        <div className="kua-card-stat-row">
          <div><small>Total Students</small><b>{university.name === "Kyungsung University" ? "10,000+" : university.students}</b></div>
          <div><small>International</small><b>{university.internationalStudents.replace(" international students", "")}</b></div>
        </div>
        <div className="kua-card-programs">
          {university.topMajors.slice(0, 3).map((major) => <span key={major}>{major}</span>)}
        </div>
        <Link href={`/universities/${slugify(university.name)}`} className="kua-card-btn">View Details & Programs <b>→</b></Link>
      </div>
    </article>
  );
}
