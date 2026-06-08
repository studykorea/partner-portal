import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import UniversityCard from "../../components/UniversityCard";
import { universities } from "../../lib/universities";

export default function UniversitiesPage() {
  return (
    <main className="min-h-screen bg-white">
      <TopNav />
      <section className="uni-list-heading">
        <div>
          <p className="eyebrow">KUA partner university network</p>
          <h1>Universities Information</h1>
          <p>Search and review official partner universities, locations, student size, international student numbers, tuition ranges, and available programs.</p>
        </div>
        <div className="uni-heading-card">Detailed university information is available only for approved partners after login.</div>
      </section>
      <section className="uni-filter-row">
        <input placeholder="Search universities or locations..." aria-label="Search universities" />
        <div className="chip-row"><span>All</span><span>Seoul</span><span>Busan</span><span>Gyeongsang</span><span>Jeolla</span><span>More</span></div>
      </section>
      <section className="university-grid-v289">
        {universities.map((university) => <UniversityCard key={university.name} university={university} />)}
      </section>
      <section className="university-details-list">
        {universities.map((university) => (
          <article key={university.name} id={encodeURIComponent(university.name)} className="uni-detail-card">
            <img src={university.image} alt={`${university.name} campus`} />
            <div>
              <h2>{university.name}</h2>
              <p>{university.overview}</p>
              <div className="detail-grid"><span>Location</span><b>{university.location}</b><span>Intake</span><b>{university.intake}</b><span>Tuition</span><b>{university.tuition}</b><span>Homepage</span><b>{university.homepage}</b></div>
            </div>
          </article>
        ))}
      </section>
      <Footer />
    </main>
  );
}
