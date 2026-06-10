import { universities } from "../lib/universities";

type University = (typeof universities)[number];

const fallbackStats = [
  ["👥", "Total Students"],
  ["🌐", "International Students"],
  ["🏛️", "Colleges"],
  ["🌎", "Countries Represented"],
  ["🤝", "Industry Partners"],
  ["✨", "Employment Rate"],
];

const defaultDeadlines = [
  { program: "Undergraduate", status: "Closed", tone: "closed", open: "19 May 2026", close: "30 May 2026" },
  { program: "Graduate (Masters/Ph.D.)", status: "Closed", tone: "closed", open: "15 May 2026", close: "05 Jun 2026" },
  { program: "KLP / EAP", status: "Closed", tone: "closed", open: "18 May 2026", close: "29 May 2026" },
];

const nationalityRows = [
  ["🇳🇵", "Nepal", "1,200", 100],
  ["🇧🇩", "Bangladesh", "1,100", 92],
  ["🇻🇳", "Vietnam", "200", 18],
  ["🇮🇩", "Indonesia", "100", 11],
  ["🇵🇰", "Pakistan", "50", 7],
];

export default function UniversityProfile({ university = universities[0] }: { university?: University }) {
  const isKyungsung = university.name === "Kyungsung University";
  const logo = university.logo || "/assets/ksu_logo.svg";
  const stats = [
    ["👥", isKyungsung ? "10,000–15,000" : university.students, "Total Students"],
    ["🌐", `${university.internationalStudents}+`, "International Students"],
    ["🏛️", isKyungsung ? "7" : "—", "Colleges"],
    ["🌎", isKyungsung ? "65+" : "—", "Countries Represented"],
    ["🤝", isKyungsung ? "300+" : "—", "Industry Partners"],
    ["✨", isKyungsung ? "90%+" : "—", "Employment Rate"],
  ];

  const programs = {
    undergraduate: university.topMajors.slice(0, 6),
    graduate: isKyungsung
      ? ["Department of Global Business", "Department of Global Hospitality", "Department of Korean Culture and Education", "Department of International Studies", "Department of Global IT Engineering", "Department of Digital Marketing"]
      : university.topMajors.slice(0, 5).map((m) => `Department of ${m}`),
    klp: ["D4-1 (4 semester)", "Korean Language Program", "KLP / EAP"],
  };

  return (
    <section className="kua-detail-v350">
      <div className="detail-hero-v350" style={{ backgroundImage: `linear-gradient(90deg, rgba(6,26,64,.78), rgba(6,26,64,.48), rgba(6,26,64,.10)), url('${university.image}')` }}>
        <a href="/universities" className="detail-back-v350">← Back to Universities</a>
        <div className="detail-hero-icons-v350"><a href={`https://${university.homepage}`} target="_blank" rel="noreferrer">↗</a><button>♡</button></div>
        <div className="detail-hero-content-v350">
          <div className="detail-logo-v350"><img src={logo} alt={`${university.name} logo`} /></div>
          <div className="detail-title-v350">
            <span>{isKyungsung ? "Private University" : university.region}</span>
            <h1>{university.name}</h1>
            <p>📍 {university.location}</p>
          </div>
        </div>
        <div className="detail-hero-stats-v350">
          <div><small>Established</small><b>{isKyungsung ? "Not updated" : "Not updated"}</b></div>
          <div><small>Type</small><b>{isKyungsung ? "Private" : "Partner"}</b></div>
          <div><small>Students</small><b>{university.students} students</b></div>
          <div><small>International Students</small><b>{university.internationalStudents} international students</b></div>
        </div>
      </div>

      <nav className="detail-tabs-v350">
        <a href="#overview">Overview</a><a href="#programs">Programs</a><a href="#admissions">Admissions</a><a href="#scholarships">Scholarships</a><a href="#campus">Campus Life</a><a href="#facilities">Facilities</a><a href="#rankings">Rankings</a><a href="#gallery">Gallery</a><a href="#contact">Contact</a>
      </nav>

      <div className="detail-main-grid-v350" id="overview">
        <main>
          <section className="detail-about-card-v350">
            <div className="detail-about-text-v350">
              <h2>About {university.name}</h2>
              <p>{isKyungsung ? "A private university in Busan offering global, practical, and industry-oriented programs." : university.overview}</p>
              <div className="detail-actions-v350"><a href="#apply">Apply Now</a><a href={`https://${university.homepage}`} target="_blank" rel="noreferrer">Visit Official Website ↗</a></div>
            </div>
            <div className="detail-video-v350">
              <img src={(university as any).videoImage || university.image} alt={`${university.name} campus tour`} />
              <button>▶</button>
              <div><b>Discover {university.name}</b><span>Watch Campus Tour</span></div>
            </div>
          </section>

          <section className="detail-stat-ribbon-v350">
            {stats.map(([icon, value, label]) => <div key={label}><span>{icon}</span><b>{value}</b><small>{label}</small></div>)}
          </section>
        </main>
        <aside id="admissions" className="deadline-panel-v350">
          <h2>Application Deadlines</h2>
          {defaultDeadlines.map((d) => <div className="deadline-row-v350" key={d.program}><span>🗓️</span><div><b>{d.program}</b><em className={d.tone}>{d.status}</em><small>Open: {d.open}</small><small>Close: {d.close}</small></div></div>)}
          <a href="#apply">View Details & Apply →</a>
        </aside>
      </div>

      <section className="detail-three-grid-v350">
        <div className="detail-card-v350"><h3>Top Programs</h3>{university.topMajors.slice(0,6).map((m) => <p key={m}>{m}</p>)}<a href="#programs">View All Programs →</a></div>
        <div className="detail-card-v350"><h3>Why Choose {university.name}?</h3><p>✓ Industry-oriented curriculum and practical learning</p><p>✓ Global exchange programs and international support</p><p>✓ Modern campus facilities</p><p>✓ Career support and internship opportunities</p><p>✓ Scholarships for international students</p></div>
        <div className="detail-card-v350 quick-v350"><h3>Quick Facts</h3><dl><dt>Location</dt><dd>{university.location}</dd><dt>Website</dt><dd>{university.homepage}</dd><dt>Total Students</dt><dd>{university.students} students</dd><dt>International Students</dt><dd>{university.internationalStudents} international students</dd><dt>Type</dt><dd>{isKyungsung ? "Private University" : "Partner University"}</dd><dt>Language</dt><dd>Korean, English</dd><dt>Tuition Range</dt><dd>{university.tuition}</dd></dl></div>
      </section>

      <section className="useful-links-v350" id="contact">
        <h2>Useful Links</h2><div className="blue-line-v350"></div>
        <div className="link-grid-v350"><a href={`https://${university.homepage}`} target="_blank" rel="noreferrer"><span>⌂</span><b>Homepage</b><em>↗</em></a><a><span>▤</span><b>Brochure</b><em>↗</em></a><a><span>f</span><b>Facebook</b><em>↗</em></a><a><span>◎</span><b>Instagram</b><em>↗</em></a><a><span>▶</span><b>YouTube</b><em>↗</em></a></div>
      </section>

      <section className="enrollment-v350">
        <div className="enroll-head-v350"><div><h2>Student Enrollment Information</h2><p>Enrollment data uploaded by the university admin. <span>2026</span></p></div><b>Total shown: 2,180</b></div>
        <div className="enroll-grid-v350">
          <div className="enroll-card-v350"><h3>🎓 Students by Program Level</h3><div className="bar-row-v350"><b>1,200</b><i style={{width:"55%"}}></i></div><div className="bar-row-v350"><b>800</b><i style={{width:"38%"}}></i></div><div className="bar-row-v350"><b>180</b><i style={{width:"9%"}}></i></div></div>
          <div className="enroll-card-v350"><h3>🌎 Top Nationalities</h3>{nationalityRows.map(([flag, country, value, pct]) => <div className="nationality-row-v350" key={country}><span>{flag}</span><b>{value}</b><i style={{width:`${pct}%`}}></i></div>)}</div>
        </div>
      </section>

      <section className="map-v350">
        <h2>University Location <a href={`https://www.google.com/maps/search/${encodeURIComponent(university.address)}`} target="_blank" rel="noreferrer">Open in Google Maps →</a></h2>
        <p>{university.address}</p>
        <div className="map-frame-v350"><iframe title={`${university.name} map`} src={`https://www.google.com/maps?q=${encodeURIComponent(university.address)}&output=embed`} loading="lazy"></iframe></div>
      </section>

      <section className="programs-v350" id="programs">
        <h2>Available Programs & Majors</h2>
        <div className="program-grid-v350">
          <div><h3>Undergraduate</h3><ul>{programs.undergraduate.map((p) => <li key={p}>{p}</li>)}</ul></div>
          <div><h3>Graduate</h3><ul>{programs.graduate.map((p) => <li key={p}>{p}</li>)}</ul></div>
          <div><h3>KLP / EAP</h3><ul>{programs.klp.map((p) => <li key={p}>{p}</li>)}</ul></div>
        </div>
      </section>
    </section>
  );
}
