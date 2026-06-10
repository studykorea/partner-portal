import { universities } from "../lib/universities";

type University = (typeof universities)[number];

const stats = [
  ["👥", "10,000+", "Total Students"],
  ["🌐", "1,966+", "International Students"],
  ["⌂", "7", "Colleges"],
  ["🌎", "65+", "Countries Represented"],
  ["⚭", "300+", "Industry Partners"],
  ["✦", "90%+", "Employment Rate"],
];
const deadlines = [
  ["Undergraduate", "Application Open", "19 May 2026", "30 May 2026", "open"],
  ["Graduate (Masters/Ph.D.)", "Opening Soon", "15 May 2026", "05 June 2026", "soon"],
  ["KLP/EAP", "Closed", "18 May 2026", "29 May 2026", "closed"],
];

export default function UniversityProfile({ university = universities[0] }: { university?: University }) {
  const isKyungsung = university.name === "Kyungsung University";
  return (
    <section id={encodeURIComponent(university.name)} className="kua-profile-section v348-detail-page">
      <div className="kua-detail-title-row">
        <p className="eyebrow">University Details</p>
        <h1>{university.name}</h1>
        <p>{university.overview}</p>
      </div>
      <div className="kua-profile-shell">
        <div className="kua-profile-main">
          <div className="kua-profile-about-card">
            <div className="kua-profile-about-text">
              <h2>About {university.name}</h2>
              <p>{university.name}, located in {university.location}, is a partner university offering programs and student support for international applicants. Approved partners can review application requirements, deadline information, tuition guidance, and available programs.</p>
              <div className="kua-profile-actions"><a href="#apply">Apply Now</a><a href={`https://${university.homepage}`} target="_blank" rel="noreferrer">Visit Official Website ↗</a></div>
            </div>
            <div className="kua-profile-video-card">
              <img src={university.image} alt={`${university.name} campus`} />
              <button aria-label="Play campus tour">▶</button>
              <div><b>Discover {university.name}</b><span>Watch Campus Tour</span></div>
            </div>
          </div>
          <div className="kua-profile-stat-ribbon">
            {stats.map(([icon, value, label]) => (
              <div key={label} className="kua-profile-stat-item"><span>{icon}</span><b>{isKyungsung ? value : label === "Total Students" ? university.students : label === "International Students" ? university.internationalStudents.replace(" international students", "+") : value}</b><small>{label}</small></div>
            ))}
          </div>
          <div className="kua-profile-info-grid">
            <div className="kua-info-card"><h3>Top Programs</h3>{university.topMajors.map((major) => <p key={major}>{major}</p>)}<a href="#programs">View All Programs →</a></div>
            <div className="kua-info-card"><h3>Why Choose {university.name}?</h3><p>✓ Partner university information in one place</p><p>✓ Admission period and program guidance</p><p>✓ Support for international applicants</p><p>✓ Tuition and scholarship information</p><p>✓ Partner-only application support</p></div>
            <div className="kua-info-card quick-facts"><h3>Quick Facts</h3><dl><dt>Location</dt><dd>{university.location}</dd><dt>Website</dt><dd>{university.homepage}</dd><dt>Total Students</dt><dd>{isKyungsung ? "10,000–15,000 students" : university.students}</dd><dt>International Students</dt><dd>{university.internationalStudents}</dd><dt>Region</dt><dd>{university.region}</dd><dt>Language</dt><dd>Korean, English</dd></dl></div>
          </div>
        </div>
        <aside className="kua-profile-side">
          <div className="kua-deadline-card"><h3>Application Deadlines</h3>{deadlines.map(([program, status, open, close, tone]) => <div className={`deadline-item ${tone}`} key={program}><div className="calendar-icon">▣</div><div><b>{program}</b><strong>{status}</strong><span>Open: {open}</span><span>Close: {close}</span></div></div>)}<a href="#deadlines">View All Deadlines →</a></div>
        </aside>
      </div>
    </section>
  );
}
