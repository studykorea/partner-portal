import TopNav from "../../../components/TopNav";
import Footer from "../../../components/Footer";
import UniversityProfile from "../../../components/UniversityProfile";
import { universities, slugifyUniversity } from "../../../lib/universities";

export function generateStaticParams() {
  return universities.map((university) => ({ slug: slugifyUniversity(university.name) }));
}

export default async function UniversityDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const university = universities.find((item) => slugifyUniversity(item.name) === slug) ?? universities[0];
  return (
    <main className="min-h-screen bg-white">
      <TopNav />
      <UniversityProfile university={university} />
      <Footer />
    </main>
  );
}
