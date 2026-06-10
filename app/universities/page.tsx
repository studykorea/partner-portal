import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import UniversityCard from "../../components/UniversityCard";
import { universities } from "../../lib/universities";

export default function UniversitiesPage() {
  return (
    <main className="min-h-screen bg-white">
      <TopNav />
      <section className="kua-universities-hero v348-full-slider">
        <div className="kua-universities-hero-copy">
          <p className="eyebrow">KUA official partner network</p>
          <h1>Universities</h1>
          <p>Review partner universities in Korea, available programs, application periods, tuition information, and student support details.</p>
        </div>
        <div className="kua-hero-full-image-slider" aria-label="Partner university campus image slider">
          {universities.slice(0, 5).map((university, index) => (
            <div className={`kua-full-slide slide-${index + 1}`} key={university.name}>
              <img src={university.image} alt={`${university.name} campus`} />
              <div className="kua-full-slide-caption">
                <span>{university.name}</span>
                <small>{university.location}</small>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="kua-university-card-section v348-list-only">
        <div className="home-featured-head compact">
          <div><h2>Featured Universities</h2><p>Explore official university information and program options.</p></div>
        </div>
        <div className="kua-university-grid v348-university-grid">
          {universities.map((university, index) => <UniversityCard key={university.name} university={university} index={index} />)}
        </div>
      </section>
      <Footer />
    </main>
  );
}
