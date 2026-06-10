import Link from "next/link";
import { slugifyUniversity, type University } from "../lib/universities";

export default function UniversityCard({ university }: { university: University; index?: number }) {
  return (
    <article className="streamlit-university-card">
      <div className="streamlit-card-cover">
        <img src={university.image} alt={`${university.name} campus`} loading="lazy" />
        <button className="streamlit-heart" aria-label="Save university">♡</button>
      </div>
      <div className="streamlit-logo-bubble">Logo</div>
      <div className="streamlit-card-body">
        <div className="streamlit-title-row">
          <h3>{university.name}</h3>
          <p className="streamlit-location"><span>⌖</span>{university.location}</p>
        </div>
        <div className="streamlit-stat-grid">
          <div className="streamlit-stat-box"><span className="streamlit-stat-icon">♙</span><section><small>Total Students</small><b>{university.students}</b></section></div>
          <div className="streamlit-stat-box"><span className="streamlit-stat-icon">◎</span><section><small>International Students</small><b>{university.internationalStudents}</b></section></div>
        </div>
        <h4 className="streamlit-snapshot-title">Admissions Snapshot</h4>
        <div className="streamlit-admission-list">
          {university.admissions.map((item) => (
            <div className="streamlit-admission-row" key={item.program}>
              <span>{item.program}</span>
              <b className={`streamlit-status ${item.tone}`}>{item.status}</b>
            </div>
          ))}
        </div>
        <Link className="streamlit-scholarship-link" href={`/universities/${slugifyUniversity(university.name)}`}>Scholarship details →</Link>
        <Link className="streamlit-detail-button" href={`/universities/${slugifyUniversity(university.name)}`}><span>View Details</span><b>→</b></Link>
      </div>
    </article>
  );
}
