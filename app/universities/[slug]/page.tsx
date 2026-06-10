import TopNav from "../../../components/TopNav";
import Footer from "../../../components/Footer";
import UniversityProfile from "../../../components/UniversityProfile";
import { universities } from "../../../lib/universities";

function slugify(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export function generateStaticParams() {
  return universities.map((university) => ({ slug: slugify(university.name) }));
}

export default async function UniversityDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const university = universities.find((item) => slugify(item.name) === slug) ?? universities[0];
  return (
    <main className="min-h-screen bg-white">
      <TopNav />
      <UniversityProfile university={university} />
      <Footer />
    </main>
  );
}
