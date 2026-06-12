export const dynamic = "force-dynamic";

import TopNav from "../../../components/TopNav";
import Footer from "../../../components/Footer";
import UniversityProfile from "../../../components/UniversityProfile";
import { universities, slugifyUniversity, fetchUniversity } from "../../../lib/universities";

export function generateStaticParams() {
  return universities.map((university) => ({ slug: slugifyUniversity(university.name) }));
}

export default async function UniversityDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const university = await fetchUniversity(slug);
  return (
    <main className="min-h-screen bg-white">
      <TopNav />
      <UniversityProfile university={university} />
      <Footer />
    </main>
  );
}
