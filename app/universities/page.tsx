export const dynamic = "force-dynamic";

import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import UniversityCard from "../../components/UniversityCard";
import { fetchUniversities, slugifyUniversity } from "../../lib/universities";
import Link from "next/link";

export default async function UniversitiesPage() {
  const universities = await fetchUniversities();
  const heroSlides = [universities[4], universities[0], universities[1], universities[3]].filter(Boolean);
  return (
    <main className="min-h-screen bg-white universities-v349-page">
      <TopNav />
      <section className="streamlit-hero-slider" aria-label="Universities Information hero slider">
        {heroSlides.map((university, index) => (
          <div className={`streamlit-hero-slide slide-${index + 1}`} key={university.name}>
            <img src={university.image} alt={`${university.name} campus`} />
          </div>
        ))}
        <div className="streamlit-hero-overlay" />
        <button className="streamlit-hero-arrow left" aria-label="Previous slide">‹</button>
        <button className="streamlit-hero-arrow right" aria-label="Next slide">›</button>
        <div className="streamlit-hero-content">
          <span className="streamlit-hero-eyebrow">Explore Korean Universities</span>
          <h1>Universities<br />Information</h1>
          <p>Filter universities by location/city, program type, admission status, intake, and more.</p>
          <div className="streamlit-hero-actions"><button>ⓘ How It Works</button><Link href="#university-list">Explore Universities <span>→</span></Link></div>
        </div>
        <Link className="streamlit-hero-caption" href={`/universities/${slugifyUniversity(heroSlides[0].name)}`}>
          <div className="streamlit-caption-logo">Logo</div>
          <div><strong>{heroSlides[0].name}</strong><span>{heroSlides[0].location}</span><em>View Details →</em></div>
        </Link>
        <div className="streamlit-hero-dots"><i/><i/></div>
      </section>

      <section className="streamlit-filter-panel" aria-label="University filters">
        <label><span>Search</span><input placeholder="Search university, city, program, keyword..." /></label>
        <label><span>Location / City</span><select defaultValue="All"><option>All</option><option>Busan</option><option>Seoul</option><option>Gyeongsang</option><option>Jeolla</option></select></label>
        <label><span>Program Type</span><select defaultValue="All"><option>All</option><option>Undergraduate</option><option>Graduate</option><option>KLP / EAP</option></select></label>
        <label><span>Admission Status</span><select defaultValue="All"><option>All</option><option>Open</option><option>Opening Soon</option><option>Closed</option></select></label>
        <label><span>Intake / Round</span><select defaultValue="All"><option>All</option><option>March Intake</option><option>September Intake</option></select></label>
        <label><span>Sort By</span><select defaultValue="Default"><option>Default</option><option>Name</option><option>Highest International Students</option></select></label>
        <button className="streamlit-filter-button">Apply Filters</button>
      </section>

      <section id="university-list" className="streamlit-university-list-section">
        <div className="streamlit-info-bar"><span>i</span><b>Showing {universities.length} of {universities.length} universities</b><em>· Admission status updates automatically based on official program dates. Dates may differ by Undergraduate, Graduate, KLP/EAP, and admission round.</em></div>
        <div className="streamlit-card-grid">
          {universities.map((university, index) => <UniversityCard key={university.name} university={university} index={index} />)}
        </div>
      </section>
      <Footer />
    </main>
  );
}
