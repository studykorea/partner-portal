import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import UniversityCard from "../../components/UniversityCard";
import UniversityProfile from "../../components/UniversityProfile";
import { universities } from "../../lib/universities";

export default function UniversitiesPage() {
  return (
    <main className="min-h-screen bg-white">
      <TopNav />
      <section className="kua-universities-hero">
        <div className="kua-universities-hero-copy">
          <p className="eyebrow">KUA official partner network</p>
          <h1>Universities</h1>
          <p>Review partner universities in Korea, available programs, application periods, tuition information, and student support details.</p>
        </div>
        <div className="kua-universities-hero-slider" aria-label="Partner university campus images">
          <div className="hero-slide-card hero-slide-main"><img src="/assets/kyungsung.webp" alt="Kyungsung University campus" /><span>Kyungsung University</span></div>
          <div className="hero-slide-card hero-slide-small one"><img src="/assets/jeonbuk.webp" alt="Jeonbuk National University" /></div>
          <div className="hero-slide-card hero-slide-small two"><img src="/assets/sejong.webp" alt="Sejong University" /></div>
        </div>
      </section>
      <section className="kua-university-card-section">
        <div className="home-featured-head compact">
          <div><h2>Featured Universities</h2><p>Explore official university information and program options.</p></div>
        </div>
        <div className="kua-university-grid">
          {universities.map((university) => <UniversityCard key={university.name} university={university} />)}
        </div>
      </section>
      <UniversityProfile />
      <Footer />
    </main>
  );
}
