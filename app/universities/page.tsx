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
        <p className="eyebrow">KUA official partner network</p>
        <h1>Universities</h1>
        <p>Review partner universities in Korea, available programs, application periods, tuition information, and student support details.</p>
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
