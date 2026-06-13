"use client";

import { useState } from "react";
import { universities, slugifyUniversity } from "../lib/universities";

type University = (typeof universities)[number];

const nationalityRows = [
  { flag: "/assets/flags/nepal.svg", country: "Nepal", value: "1,200", pct: 100 },
  { flag: "/assets/flags/bangladesh.svg", country: "Bangladesh", value: "1,100", pct: 92 },
  { flag: "/assets/flags/vietnam.svg", country: "Vietnam", value: "200", pct: 18 },
  { flag: "/assets/flags/indonesia.svg", country: "Indonesia", value: "100", pct: 11 },
  { flag: "/assets/flags/pakistan.svg", country: "Pakistan", value: "50", pct: 7 },
];

function safeUrl(url: string) {
  if (!url) return "#";
  return url.startsWith("http") ? url : `https://${url}`;
}

function searchUrl(platform: "facebook" | "instagram" | "youtube", name: string) {
  const q = encodeURIComponent(name);
  if (platform === "facebook") return `https://www.facebook.com/search/top?q=${q}`;
  if (platform === "instagram") return `https://www.instagram.com/explore/search/keyword/?q=${q}`;
  return `https://www.youtube.com/results?search_query=${q}%20campus%20tour`;
}

function getYouTubeId(url?: string) {
  if (!url) return "";
  try {
    const u = new URL(safeUrl(url));
    if (u.hostname.includes("youtu.be")) return u.pathname.replace("/", "").split("?")[0];
    if (u.searchParams.get("v")) return u.searchParams.get("v") || "";
    const parts = u.pathname.split("/").filter(Boolean);
    const marker = parts.findIndex((p) => ["embed", "shorts", "live"].includes(p));
    if (marker >= 0 && parts[marker + 1]) return parts[marker + 1];
  } catch {
    return "";
  }
  return "";
}

function PlayableCampusVideo({ university }: { university: University }) {
  const [playing, setPlaying] = useState(false);
  const videoId = getYouTubeId(university.youtubeUrl);
  const thumbnail = videoId
    ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`
    : (university.heroImage || university.image);
  const embedUrl = videoId
    ? `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1&playsinline=1`
    : "";

  if (playing && embedUrl) {
    return (
      <div className="detail-video-v350 video-inline-v360">
        <iframe
          title={`${university.name} campus tour video`}
          src={embedUrl}
          loading="lazy"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
        />
      </div>
    );
  }

  return (
    <button
      type="button"
      className="detail-video-v350 video-thumb-v360"
      onClick={() => videoId && setPlaying(true)}
      aria-label={`Play ${university.name} campus video`}
    >
      <img src={thumbnail} alt={`${university.name} video thumbnail`} />
      <span className="video-play-v360">▶</span>
      <div className="video-caption-v360">
        <b>Discover {university.name}</b>
        <small>Watch Campus Tour</small>
      </div>
    </button>
  );
}

export default function UniversityProfile({ university = universities[0] }: { university?: University }) {
  const isKyungsung = university.name === "Kyungsung University";
  const logo = university.logo || "/assets/ksu_logo.svg";
  const heroImage = university.heroImage || university.image;
  const slug = slugifyUniversity(university.name);
  const homepageUrl = safeUrl(university.homepage);
  const applyUrl = `/apply?university=${encodeURIComponent(university.name)}`;
  const youtubeSearch = searchUrl("youtube", university.name);
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
    graduate: university.graduatePrograms?.length
      ? university.graduatePrograms
      : isKyungsung
        ? ["Department of Global Business", "Department of Global Hospitality", "Department of Korean Culture and Education", "Department of International Studies", "Department of Global IT Engineering", "Department of Digital Marketing"]
        : university.topMajors.slice(0, 5).map((m) => `Department of ${m}`),
    klp: university.klpPrograms?.length ? university.klpPrograms : ["D4-1 (4 semester)", "Korean Language Program", "KLP / EAP"],
  };

  return (
    <section className="kua-detail-v350">
      <div className="detail-hero-v350" style={{ backgroundImage: `linear-gradient(90deg, rgba(6,26,64,.78), rgba(6,26,64,.48), rgba(6,26,64,.10)), url('${heroImage}')` }}>
        <a href="/universities" className="detail-back-v350">← Back to Universities</a>
        <div className="detail-hero-icons-v350"><a href={homepageUrl} target="_blank" rel="noreferrer" aria-label="Official website">↗</a><a href={`/saved-universities?add=${slug}`} aria-label="Save university">♡</a></div>
        <div className="detail-hero-content-v350">
          <div className="detail-logo-v350"><img src={logo} alt={`${university.name} logo`} /></div>
          <div className="detail-title-v350">
            <span>{university.type || (isKyungsung ? "Private University" : university.region)}</span>
            <h1>{university.name}</h1>
            <p>📍 {university.location}</p>
          </div>
        </div>
        <div className="detail-hero-stats-v350">
          <div><small>Established</small><b>{university.established || "Not updated"}</b></div>
          <div><small>Type</small><b>{university.type || (isKyungsung ? "Private" : "Partner")}</b></div>
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
              <div className="detail-actions-v350"><a href={applyUrl}>Apply Now</a><a href={homepageUrl} target="_blank" rel="noreferrer">Visit Official Website ↗</a></div>
            </div>
            <PlayableCampusVideo university={university} />
          </section>

          <section className="detail-stat-ribbon-v350">
            {stats.map(([icon, value, label]) => <div key={label}><span>{icon}</span><b>{value}</b><small>{label}</small></div>)}
          </section>
        </main>
        <aside id="admissions" className="deadline-panel-v350">
          <h2>Application Deadlines</h2>
          {(university.admissions?.length ? university.admissions : []).map((d) => <div className="deadline-row-v350" key={d.program}><span>🗓️</span><div><b>{d.program}</b><em className={d.tone}>{d.status}</em><small>Open: {d.open || "Not fixed"}</small><small>Close: {d.close || "Not fixed"}</small></div></div>)}
          <a href={applyUrl}>View Details & Apply →</a>
        </aside>
      </div>

      <section className="detail-three-grid-v350">
        <div className="detail-card-v350"><h3>Top Programs</h3>{university.topMajors.slice(0,6).map((m) => <p key={m}>{m}</p>)}<a href="#programs">View All Programs →</a></div>
        <div className="detail-card-v350"><h3>Why Choose {university.name}?</h3><p>✓ Industry-oriented curriculum and practical learning</p><p>✓ Global exchange programs and international support</p><p>✓ Modern campus facilities</p><p>✓ Career support and internship opportunities</p><p>✓ Scholarships for international students</p></div>
        <div className="detail-card-v350 quick-v350"><h3>Quick Facts</h3><dl><dt>Location</dt><dd>{university.location}</dd><dt>Website</dt><dd>{university.homepage}</dd><dt>Total Students</dt><dd>{university.students} students</dd><dt>International Students</dt><dd>{university.internationalStudents} international students</dd><dt>Type</dt><dd>{university.type || (isKyungsung ? "Private University" : "Partner University")}</dd><dt>Accreditation</dt><dd>{university.accreditation || "Not updated"}</dd><dt>Language</dt><dd>Korean, English</dd><dt>Tuition Range</dt><dd>{university.tuition}</dd></dl></div>
      </section>

      <section className="useful-links-v350" id="contact">
        <h2>Useful Links</h2><div className="blue-line-v350"></div>
        <div className="link-grid-v350 social-links-v352">
          <a href={homepageUrl} target="_blank" rel="noreferrer"><span className="social-home-v352">⌂</span><b>Homepage</b><em>↗</em></a>
          <a href={university.brochureUrl ? safeUrl(university.brochureUrl) : `${homepageUrl}/eng`} target="_blank" rel="noreferrer"><span className="social-brochure-v352">▤</span><b>Brochure</b><em>↗</em></a>
          <a href={university.facebookUrl ? safeUrl(university.facebookUrl) : searchUrl("facebook", university.name)} target="_blank" rel="noreferrer"><span className="social-facebook-v352">f</span><b>Facebook</b><em>↗</em></a>
          <a href={university.instagramUrl ? safeUrl(university.instagramUrl) : searchUrl("instagram", university.name)} target="_blank" rel="noreferrer"><span className="social-instagram-v352">◎</span><b>Instagram</b><em>↗</em></a>
          <a href={university.youtubeUrl ? safeUrl(university.youtubeUrl) : youtubeSearch} target="_blank" rel="noreferrer"><span className="social-youtube-v352">▶</span><b>YouTube</b><em>↗</em></a>
        </div>
      </section>

      <section className="enrollment-v350">
        <div className="enroll-head-v350"><div><h2>Student Enrollment Information</h2><p>Enrollment data uploaded by the university admin. <span>2026</span></p></div><b>Total shown: 2,180</b></div>
        <div className="enroll-grid-v350">
          <div className="enroll-card-v350"><h3>🎓 Students by Program Level</h3><div className="bar-row-v350"><b>1,200</b><i style={{width:"55%"}}></i></div><div className="bar-row-v350"><b>800</b><i style={{width:"38%"}}></i></div><div className="bar-row-v350"><b>180</b><i style={{width:"9%"}}></i></div></div>
          <div className="enroll-card-v350"><h3>🌎 Top Nationalities</h3>{nationalityRows.map((row) => <div className="nationality-row-v350" key={row.country}><span><img src={row.flag} alt={`${row.country} flag`} /></span><b>{row.value}</b><i style={{width:`${row.pct}%`}}></i></div>)}</div>
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
