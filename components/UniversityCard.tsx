import Link from "next/link";
import { slugifyUniversity, type University } from "../lib/universities";

function primaryAdmission(university: University) {
  return university.admissions?.find((item) => item.program.toLowerCase().includes("undergraduate")) || university.admissions?.[0];
}

function cleanNumber(value?: string) {
  return (value || "Not updated")
    .replace(/\s*international\s*students?/gi, "")
    .replace(/\s*students?/gi, "")
    .trim();
}

export default function UniversityCard({ university }: { university: University; index?: number }) {
  const detailHref = `/universities/${slugifyUniversity(university.name)}`;
  const admission = primaryAdmission(university);
  const majors = university.topMajors?.slice(0, 3) || [];

  return (
    <article className="streamlit-university-card v361-premium-card v377-sample-card">
      <Link className="streamlit-card-cover v361-card-cover" href={detailHref} aria-label={`View ${university.name} details`}>
        <img src={university.image} alt={`${university.name} campus`} loading="lazy" />
        <span className="v361-cover-shine" />
        <span className="v361-featured-badge">★ Featured</span>
        {admission ? <span className={`v361-mini-status ${admission.tone}`}>{admission.status}</span> : null}
        <button className="streamlit-heart v361-heart" aria-label="Save university" type="button">♡</button>
      </Link>

      <Link className="streamlit-logo-bubble v361-logo-bubble" href={detailHref} aria-label={`${university.name} logo`}>
        {university.logo ? <img src={university.logo} alt={`${university.name} logo`} /> : <span>Logo</span>}
      </Link>

      <div className="streamlit-card-body v361-card-body">
        <div className="v361-card-topline">
          <span>{university.type || "Partner University"}</span>
          <span>{university.region || university.location}</span>
        </div>

        <div className="streamlit-title-row v361-title-row v377-title-row">
          <h3>{university.name}</h3>
          <p className="streamlit-location v361-location"><span>⌖</span>{university.location}</p>
        </div>

        <div className="streamlit-stat-grid v361-stat-grid">
          <div className="streamlit-stat-box v361-stat-box"><span className="streamlit-stat-icon">👥</span><section><small>Total Students</small><b>{cleanNumber(university.students)}</b></section></div>
          <div className="streamlit-stat-box v361-stat-box"><span className="streamlit-stat-icon">🌐</span><section><small>International</small><b>{cleanNumber(university.internationalStudents)}</b></section></div>
        </div>

        {majors.length ? (
          <div className="v361-major-chips" aria-label="Top programs">
            {majors.map((major) => <span key={major}>{major}</span>)}
          </div>
        ) : null}

        <h4 className="streamlit-snapshot-title v361-snapshot-title">Admissions Snapshot</h4>
        <div className="streamlit-admission-list v361-admission-list">
          {university.admissions.map((item) => (
            <div className="streamlit-admission-row v361-admission-row" key={item.program}>
              <span>{item.program}</span>
              <b className={`streamlit-status ${item.tone}`}>{item.status}</b>
            </div>
          ))}
        </div>

        <div className="v361-card-links">
          <Link className="streamlit-scholarship-link v361-scholarship-link" href={`${detailHref}#scholarships`}>Scholarship details →</Link>
        </div>
        <Link className="streamlit-detail-button v361-detail-button" href={detailHref}><span>View Details & Programs</span><b>→</b></Link>
      </div>
    </article>
  );
}
