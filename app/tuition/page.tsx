"use client";

import { useMemo, useState } from "react";
import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import { universities, type University } from "../../lib/universities";

type Program = "undergraduate" | "graduate" | "eap" | "klp";

const programLabels: Record<Program, string> = {
  undergraduate: "Undergraduate / Bachelor",
  graduate: "Graduate / Master / Ph.D.",
  eap: "EAP - English Academic Purpose",
  klp: "KLP - Korean Language Program",
};

const eapIeltsRequirement: Record<string, number> = {
  "Kyungsung University": 5.0,
  "Jeonbuk National University": 5.0,
  "Kyungwoon University": 4.0,
  "Sejong University": 5.0,
  "Youngsan University": 4.0,
};

function numberOnly(value: string) {
  const n = Number(String(value).replace(/[^0-9.]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function parseTuition(tuition: string, program: Program) {
  if (program === "klp") return 1200000;
  if (program === "eap") return 1500000;

  const numbers = tuition.match(/[0-9,]+/g)?.map((v) => Number(v.replace(/,/g, ""))).filter((v) => v > 100000) || [];
  if (numbers.length >= 2) return Math.round((numbers[0] + numbers[1]) / 2);
  if (numbers.length === 1) return numbers[0];
  return program === "graduate" ? 4500000 : 3800000;
}

function formatKRW(value: number) {
  return `KRW ${Math.max(0, Math.round(value)).toLocaleString()}`;
}

function getMajors(university: University, program: Program) {
  if (program === "undergraduate") return university.topMajors?.length ? university.topMajors : ["Undergraduate program"];
  if (program === "graduate") return university.graduatePrograms?.length ? university.graduatePrograms : ["Graduate program"];
  if (program === "eap") return ["EAP - English Academic Purpose"];
  return university.klpPrograms?.length ? university.klpPrograms : ["KLP - Korean Language Program"];
}

function scholarshipRate(program: Program, gpaRaw: string, langRaw: string, universityName: string) {
  const score = numberOnly(gpaRaw);
  const language = numberOnly(langRaw);
  const normalizedGpa = score > 4.5 ? (score / 100) * 4.5 : score;

  if (program === "klp") {
    if (language >= 5) return 0.3;
    if (language >= 4) return 0.2;
    if (language >= 3) return 0.1;
    return 0;
  }

  if (program === "eap") {
    const min = eapIeltsRequirement[universityName] ?? 4.5;
    if (language >= min + 1.5) return 0.3;
    if (language >= min + 1) return 0.2;
    if (language >= min) return 0.1;
    return 0;
  }

  if (normalizedGpa >= 3.7 && language >= 6.5) return 0.5;
  if (normalizedGpa >= 3.3 && language >= 6.0) return 0.4;
  if (normalizedGpa >= 2.8 && language >= 5.5) return 0.3;
  return 0;
}

export default function TuitionPage() {
  const [selectedUniversity, setSelectedUniversity] = useState(universities[0]?.name || "");
  const [program, setProgram] = useState<Program>("undergraduate");
  const [major, setMajor] = useState("");
  const [gpa, setGpa] = useState("");
  const [languageScore, setLanguageScore] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const university = useMemo(
    () => universities.find((item) => item.name === selectedUniversity) || universities[0],
    [selectedUniversity]
  );

  const majorOptions = useMemo(() => getMajors(university, program), [university, program]);

  const baseTuition = parseTuition(university?.tuition || "", program);
  const applicationFee = program === "klp" ? 50000 : 80000;
  const admissionFee = program === "klp" ? 0 : 200000;
  const rate = scholarshipRate(program, gpa, languageScore, university?.name || "");
  const discount = baseTuition * rate;
  const total = baseTuition + applicationFee + admissionFee - discount;
  const eapRequired = eapIeltsRequirement[university?.name || ""] ?? 4.5;

  function resetAfterChange(fn: () => void) {
    fn();
    setSubmitted(false);
    setError("");
  }

  function handleUniversityChange(name: string) {
    resetAfterChange(() => {
      setSelectedUniversity(name);
      setMajor("");
    });
  }

  function handleProgramChange(value: Program) {
    resetAfterChange(() => {
      setProgram(value);
      setMajor("");
      setGpa("");
      setLanguageScore("");
    });
  }

  function calculate() {
    const missing: string[] = [];
    if (!selectedUniversity) missing.push("university");
    if (!program) missing.push("program");
    if (!major) missing.push("major/program option");
    if (program !== "klp" && numberOnly(gpa) <= 0) missing.push("GPA or percentage");
    if (program !== "klp" && numberOnly(languageScore) <= 0) missing.push("IELTS score");

    if (missing.length) {
      setSubmitted(false);
      setError(`Please input/select ${missing.join(", ")} first.`);
      return;
    }
    setError("");
    setSubmitted(true);
  }

  return (
    <main className="min-h-screen bg-[#F6F9FE]">
      <TopNav />
      <section className="mx-auto max-w-[1320px] px-5 py-14 lg:px-8">
        <div className="rounded-[32px] bg-[#061A40] p-8 text-white">
          <p className="text-sm font900 uppercase tracking-[0.18em] text-blue-300">Tuition & Scholarship</p>
          <h1 className="mt-3 text-5xl font900">Tuition Calculator</h1>
          <p className="mt-4 max-w-3xl text-blue-100">Select university, program, major, GPA/percentage, and language score to estimate tuition and scholarship.</p>
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-[.95fr_1.05fr]">
          <form className="rounded-[28px] border border-[#DCE6F4] bg-white p-7 shadow-sm" onSubmit={(e) => e.preventDefault()}>
            <div className="grid gap-5 md:grid-cols-2">
              <label className="text-sm font900 text-slate-700">University
                <select value={selectedUniversity} onChange={(e) => handleUniversityChange(e.target.value)} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3">
                  {universities.map((u) => <option key={u.name} value={u.name}>{u.name}</option>)}
                </select>
              </label>

              <label className="text-sm font900 text-slate-700">Program
                <select value={program} onChange={(e) => handleProgramChange(e.target.value as Program)} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3">
                  <option value="undergraduate">Undergraduate / Bachelor</option>
                  <option value="graduate">Graduate / Master / Ph.D.</option>
                  <option value="eap">EAP - English Academic Purpose</option>
                  <option value="klp">KLP - Korean Language Program</option>
                </select>
              </label>

              <label className="text-sm font900 text-slate-700 md:col-span-2">Major / Program Option
                <select value={major} onChange={(e) => resetAfterChange(() => setMajor(e.target.value))} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3">
                  <option value="">Select available option</option>
                  {majorOptions.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
                <span className="mt-2 block text-xs font700 text-slate-500">
                  {program === "undergraduate" && "Only undergraduate majors from the selected university are shown."}
                  {program === "graduate" && "Only graduate programs from the selected university are shown."}
                  {program === "eap" && "EAP has no separate major, so EAP appears here."}
                  {program === "klp" && "KLP has no separate major, so Korean language program options appear here."}
                </span>
              </label>

              {program !== "klp" && (
                <label className="text-sm font900 text-slate-700">GPA / Percentage
                  <input value={gpa} onChange={(e) => resetAfterChange(() => setGpa(e.target.value))} placeholder="Example: 3.2 or 72" className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
                </label>
              )}

              {program !== "klp" ? (
                <label className="text-sm font900 text-slate-700">IELTS Score
                  <input value={languageScore} onChange={(e) => resetAfterChange(() => setLanguageScore(e.target.value))} placeholder={program === "eap" ? `Required approx. ${eapRequired}+` : "Example: 5.5"} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
                  <span className="mt-2 block text-xs font700 text-slate-500">
                    {program === "eap" ? `${university.name} EAP IELTS guide: around ${eapRequired}+.` : "IELTS is required for degree-program scholarship estimate."}
                  </span>
                </label>
              ) : (
                <label className="text-sm font900 text-slate-700">TOPIK Score <span className="text-xs text-slate-400">Optional</span>
                  <input value={languageScore} onChange={(e) => resetAfterChange(() => setLanguageScore(e.target.value))} placeholder="Optional: 3, 4, 5..." className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
                  <span className="mt-2 block text-xs font700 text-slate-500">TOPIK is optional for KLP. It can be used only for estimated discount logic.</span>
                </label>
              )}
            </div>

            {error && <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font900 text-red-700">{error}</div>}

            <button type="button" onClick={calculate} className="mt-7 w-full rounded-2xl bg-[#2457D6] px-5 py-4 text-sm font900 text-white shadow-lg shadow-blue-100">
              Calculate Tuition
            </button>
          </form>

          <div className="rounded-[28px] border border-[#DCE6F4] bg-white p-7 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font900 uppercase tracking-[0.14em] text-[#2457D6]">Estimated Summary</p>
                <h2 className="mt-1 text-2xl font900 text-[#061A40]">{submitted ? university.name : "Waiting for calculation"}</h2>
              </div>
              <span className="rounded-full bg-blue-50 px-4 py-2 text-sm font900 text-blue-700">{programLabels[program]}</span>
            </div>

            {!submitted ? (
              <div className="mt-6 rounded-3xl bg-slate-50 p-6 text-slate-600">
                Select all required information and click <b>Calculate Tuition</b>. KLP shows optional TOPIK. EAP uses IELTS requirement depending on the university.
              </div>
            ) : (
              <div className="mt-5 grid gap-3 text-sm">
                <div className="rounded-2xl bg-slate-50 p-4"><b className="block text-slate-500">Selected Major / Program</b><span className="font900 text-[#061A40]">{major}</span></div>
                <div className="flex justify-between rounded-2xl bg-slate-50 p-4"><b>Application Fee</b><span>{formatKRW(applicationFee)}</span></div>
                <div className="flex justify-between rounded-2xl bg-slate-50 p-4"><b>Admission Fee</b><span>{formatKRW(admissionFee)}</span></div>
                <div className="flex justify-between rounded-2xl bg-slate-50 p-4"><b>Tuition Fee</b><span>{formatKRW(baseTuition)}</span></div>
                <div className="flex justify-between rounded-2xl bg-blue-50 p-4 text-blue-800"><b>Estimated Scholarship</b><span>{Math.round(rate * 100)}% / -{formatKRW(discount)}</span></div>
                <div className="flex justify-between rounded-2xl bg-green-50 p-4 text-green-800"><b>Estimated Final Payment</b><span className="font900">{formatKRW(total)}</span></div>
                <p className="pt-3 text-xs font700 text-slate-500">This is an estimate only. Final tuition, admission fee, and scholarship may differ by university, semester, nationality, and official admission result.</p>
              </div>
            )}
          </div>
        </div>
      </section>
      <Footer />
    </main>
  );
}
