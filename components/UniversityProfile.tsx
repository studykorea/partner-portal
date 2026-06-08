import UniversitySeal from "./UniversitySeal";
import { universities } from "../lib/universities";

const kyungsung = universities[0];
const stats = [
  ["👥", "10,000+", "Total Students"],
  ["🌐", "1,966+", "International Students"],
  ["⌂", "7", "Colleges"],
  ["🌎", "65+", "Countries Represented"],
  ["⚭", "300+", "Industry Partners"],
  ["✦", "90%+", "Employment Rate"],
];
const deadlines = [
  ["Undergraduate", "Application Open", "19 May 2026", "30 May 2026"],
  ["Graduate (Masters/Ph.D.)", "Application Open", "15 May 2026", "05 June 2026"],
  ["KLP/EAP", "Application Open", "18 May 2026", "29 May 2026"],
];

export default function UniversityProfile() {
  return (
    <section id={encodeURIComponent(kyungsung.name)} className="kua-profile-section">
      <div className="kua-profile-shell">
        <div className="kua-profile-main">
          <div className="kua-profile-about-card">
            <div className="kua-profile-about-text">
              <h2>About Kyungsung University</h2>
              <p>Kyungsung University, located in the vibrant city of Busan, is a private university committed to fostering global talent and innovation. With a strong focus on practical education and industry collaboration, KSU empowers students to shape the future.</p>
              <div className="kua-profile-actions"><a href="#apply">Apply Now</a><a href="https://ks.ac.kr" target="_blank" rel="noreferrer">Visit Official Website ↗</a></div>
            </div>
            <div className="kua-profile-video-card">
              <img src={kyungsung.image} alt="Kyungsung University campus" />
              <button aria-label="Play campus tour">▶</button>
              <div><b>Discover Kyungsung University</b><span>Watch Campus Tour</span></div>
            </div>
          </div>
          <div className="kua-profile-stat-ribbon">
            {stats.map(([icon, value, label]) => (
              <div key={label} className="kua-profile-stat-item"><span>{icon}</span><b>{value}</b><small>{label}</small></div>
            ))}
          </div>
          <div className="kua-profile-info-grid">
            <div className="kua-info-card"><h3>Top Programs</h3>{kyungsung.topMajors.map((major) => <p key={major}>{major}</p>)}<a href="#programs">View All Programs →</a></div>
            <div className="kua-info-card"><h3>Why Choose Kyungsung University?</h3><p>✓ Industry-oriented curriculum and practical learning</p><p>✓ Global exchange programs and international support</p><p>✓ Modern campus facilities</p><p>✓ Career support and internship opportunities</p><p>✓ Scholarships for international students</p></div>
            <div className="kua-info-card quick-facts"><h3>Quick Facts</h3><dl><dt>Location</dt><dd>Busan, Republic of Korea</dd><dt>Website</dt><dd>ksgc.kr</dd><dt>Total Students</dt><dd>10,000–15,000 students</dd><dt>International Students</dt><dd>1,966 international students</dd><dt>Campus Size</dt><dd>10,000–15,000 students</dd><dt>Type</dt><dd>Private University</dd><dt>Language</dt><dd>Korean, English</dd></dl></div>
          </div>
        </div>
        <aside className="kua-profile-side">
          <div className="kua-deadline-card"><h3>Application Deadlines</h3>{deadlines.map(([program, status, open, close]) => <div className="deadline-item" key={program}><div className="calendar-icon">▣</div><div><b>{program}</b><strong>{status}</strong><span>Open: {open}</span><span>Close: {close}</span></div></div>)}<a href="#deadlines">View All Deadlines →</a></div>
        </aside>
      </div>
    </section>
  );
}
