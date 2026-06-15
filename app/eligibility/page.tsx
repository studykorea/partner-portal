import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import EligibilityChecker from "../../components/EligibilityChecker";
import { fetchUniversities } from "../../lib/universities";

export const dynamic = "force-dynamic";

export default async function EligibilityPage() {
  const universities = await fetchUniversities();

  return (
    <main className="min-h-screen bg-[#F6F9FE]">
      <TopNav />
      <section className="mx-auto max-w-[1320px] px-5 py-14 lg:px-8">
        <div className="rounded-[32px] bg-[#061A40] p-8 text-white shadow-lg">
          <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Eligibility Check</p>
          <h1 className="mt-3 text-5xl font900">Student Eligibility Checker</h1>
          <p className="mt-4 max-w-3xl text-blue-100">
            Enter student academic information and see which partner universities are eligible or conditional.
          </p>
        </div>
        <EligibilityChecker universities={universities} />
      </section>
      <Footer />
    </main>
  );
}
