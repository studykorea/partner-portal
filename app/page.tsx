export default function Home() {
  const universities = [
    {
      name: "Kyungsung University",
      location: "Busan, South Korea",
      programs: "Global Hospitality, Business, Korean Language",
      status: "Featured",
    },
    {
      name: "Realize Education",
      location: "South Korea",
      programs: "Study Korea Consultation",
      status: "Partner",
    },
    {
      name: "UniQuest",
      location: "South Korea",
      programs: "Admissions and Student Support",
      status: "Active",
    },
  ];

  return (
    <main className="min-h-screen bg-black text-white">
      <section className="px-8 py-8 border-b border-zinc-800">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl font-bold">UniQuest Partner Portal</h1>
          <div className="flex gap-3">
            <button className="px-4 py-2 rounded-lg bg-white text-black font-medium">
              Login
            </button>
            <button className="px-4 py-2 rounded-lg border border-zinc-600">
              Apply Now
            </button>
          </div>
        </div>
      </section>

      <section className="px-8 py-20">
        <div className="max-w-6xl mx-auto">
          <p className="text-sm uppercase tracking-widest text-zinc-400 mb-4">
            Study Korea Admission Platform
          </p>
          <h2 className="text-5xl font-bold max-w-3xl leading-tight">
            Connect students, agencies, and Korean universities in one portal.
          </h2>
          <p className="mt-6 text-lg text-zinc-300 max-w-2xl">
            Manage university information, partner agencies, student applications,
            and documents through a modern Study Korea partner system.
          </p>
        </div>
      </section>

      <section className="px-8 py-12 bg-zinc-950">
        <div className="max-w-6xl mx-auto">
          <h3 className="text-3xl font-bold mb-8">Featured Universities</h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {universities.map((uni) => (
              <div
                key={uni.name}
                className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6"
              >
                <span className="text-xs bg-zinc-800 px-3 py-1 rounded-full">
                  {uni.status}
                </span>
                <h4 className="text-xl font-semibold mt-5">{uni.name}</h4>
                <p className="text-zinc-400 mt-2">{uni.location}</p>
                <p className="text-zinc-300 mt-4">{uni.programs}</p>
                <button className="mt-6 w-full px-4 py-2 rounded-lg bg-white text-black font-medium">
                  View Programs
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-8 py-16">
        <div className="max-w-6xl mx-auto rounded-2xl border border-zinc-800 bg-zinc-950 p-8">
          <h3 className="text-3xl font-bold">Partner Agencies</h3>
          <p className="text-zinc-300 mt-4 max-w-2xl">
            Approved partner agencies can manage student inquiries, upload
            documents, and track application progress.
          </p>
          <button className="mt-6 px-5 py-3 rounded-lg bg-white text-black font-medium">
            Agency Dashboard
          </button>
        </div>
      </section>
    </main>
  );
}
