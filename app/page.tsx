import Link from "next/link";
import TopNav from "../components/TopNav";
import Footer from "../components/Footer";
import UniversityCard from "../components/UniversityCard";
import { universities } from "../lib/universities";

export default function Home() {
  const carouselItems = [...universities, ...universities];
  return (
    <main className="min-h-screen bg-white">
      <TopNav />
      <section className="hero-reference">
        <div className="hero-dots" />
        <div className="hero-inner">
          <div className="hero-step"><span>Step 1</span><b>Home Page</b></div>
          <h1>Partner Portal for<br />University Recruitment</h1>
          <p className="hero-lead">Approved partner agencies can access university details, application requirements, eligibility checking, and tuition/scholarship calculation.</p>
          <div className="hero-buttons">
            <Link href="/apply" className="hero-btn-primary">👤&nbsp;&nbsp;Apply for Partner Access</Link>
            <Link href="/universities" className="hero-btn-outline">🏛️&nbsp;&nbsp;Explore Universities</Link>
          </div>
          <p className="hero-lock">🔒 Detailed information is available only for approved partners.</p>
        </div>
      </section>

      <section className="home-featured-section">
        <div className="home-featured-head">
          <div>
            <h2>Featured Universities</h2>
            <p>Explore top partner universities in Korea.</p>
          </div>
          <Link href="/universities" className="home-featured-viewall">View All <span>›</span></Link>
        </div>
        <div className="featured-carousel">
          <div className="carousel-track">
            {carouselItems.map((university, index) => <UniversityCard key={`${university.name}-${index}`} university={university} />)}
          </div>
        </div>
        <div className="home-featured-note"><span>◇</span> All universities are official partners and recognized by the Korean Ministry of Education.</div>
      </section>
      <Footer />
    </main>
  );
}
