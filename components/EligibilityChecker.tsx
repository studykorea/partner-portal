"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { slugifyUniversity, type University } from "../lib/universities";

type ProgramLevel = "bachelor" | "master" | "phd" | "klp";
type MajorCategory = "business" | "it" | "engineering" | "hospitality" | "korean" | "media" | "tourism" | "other";

const majorOptions: { value: MajorCategory; label: string; keywords: string[] }[] = [
  { value: "business", label: "Business / Management", keywords: ["business", "commerce", "management", "administration", "marketing"] },
  { value: "it", label: "IT / Software / Computer", keywords: ["it", "software", "computer", "digital", "data", "information"] },
  { value: "engineering", label: "Engineering / Mechanical", keywords: ["engineering", "mechanical", "design"] },
  { value: "hospitality", label: "Hospitality / Hotel", keywords: ["hospitality", "hotel", "food", "culinary"] },
  { value: "korean", label: "Korean Studies / Korean Language", keywords: ["korean", "language", "culture", "klp", "eap"] },
  { value: "media", label: "Media / Communication / Entertainment", keywords: ["media", "communication", "entertainment", "k-entertainment"] },
  { value: "tourism", label: "Tourism / Airline / Convention", keywords: ["tourism", "airline", "convention"] },
  { value: "other", label: "Other / Not decided", keywords: [] },
];

const rules: Record<string, Record<ProgramLevel, { gpa: number; percent: number; ielts: number; label: string }>> = {
  "Kyungsung University": {
    bachelor: { gpa: 2.5, percent: 60, ielts: 5.5, label: "Bachelor / Undergraduate" },
    master: { gpa: 2.7, percent: 65, ielts: 5.5, label: "Master" },
    phd: { gpa: 3.0, percent: 70, ielts: 6.0, label: "Ph.D." },
    klp: { gpa: 0, percent: 0, ielts: 0, label: "KLP / EAP" },
  },
  "Jeonbuk National University": {
    bachelor: { gpa: 2.8, percent: 65, ielts: 5.5, label: "Bachelor / Undergraduate" },
    master: { gpa: 3.0, percent: 70, ielts: 6.0, label: "Master" },
    phd: { gpa: 3.2, percent: 75, ielts: 6.0, label: "Ph.D." },
    klp: { gpa: 0, percent: 0, ielts: 0, label: "KLP / EAP" },
  },
  "Kyungwoon University": {
    bachelor: { gpa: 2.3, percent: 55, ielts: 5.0, label: "Bachelor / Undergraduate" },
    master: { gpa: 2.5, percent: 60, ielts: 5.5, label: "Master" },
    phd: { gpa: 2.8, percent: 65, ielts: 5.5, label: "Ph.D." },
    klp: { gpa: 0, percent: 0, ielts: 0, label: "KLP / EAP" },
  },
  "Sejong University": {
    bachelor: { gpa: 3.0, percent: 70, ielts: 6.0, label: "Bachelor / Undergraduate" },
    master: { gpa: 3.2, percent: 75, ielts: 6.0, label: "Master" },
    phd: { gpa: 3.3, percent: 78, ielts: 6.5, label: "Ph.D." },
    klp: { gpa: 0, percent: 0, ielts: 0, label: "KLP / EAP" },
  },
  "Youngsan University": {
    bachelor: { gpa: 2.2, percent: 55, ielts: 5.0, label: "Bachelor / Undergraduate" },
    master: { gpa: 2.5, percent: 60, ielts: 5.0, label: "Master" },
    phd: { gpa: 2.8, percent: 65, ielts: 5.5, label: "Ph.D." },
    klp: { gpa: 0, percent: 0, ielts: 0, label: "KLP / EAP" },
  },
};

function parseNumber(value: string) {
  const n = Number(String(value).replace(/[^0-9.]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function scoreLabel(program: ProgramLevel) {
  if (program === "bachelor") return "High school GPA or %";
  if (program === "master") return "Bachelor GPA or %";
  if (program === "phd") return "Master GPA or %";
  return "Latest education GPA or %";
}

function normalizeScore(raw: string) {
  const value = parseNumber(raw);
  if (value > 4.5) return { percent: value, gpa: (value / 100) * 4.5, original: value };
  return { gpa: value, percent: (value / 4.5) * 100, original: value };
}

function universityHasMajor(university: University, major: MajorCategory) {
  if (major === "other") return true;
  const selected = majorOptions.find((m) => m.value === major);
  if (!selected) return true;

  const searchableText = [
    university.name,
    university.location,
    ...(university.topMajors || []),
    ...(university.graduatePrograms || []),
    ...(university.klpPrograms || []),
  ].join(" ").toLowerCase();

  return selected.keywords.some((keyword) => searchableText.includes(keyword));
}

function evaluate(university: University, program: ProgramLevel, scoreRaw: string, ieltsRaw: string, major: MajorCategory) {
  const rule = rules[university.name]?.[program] || rules["Kyungsung University"][program];
  const score = normalizeScore(scoreRaw);
  const ielts = parseNumber(ieltsRaw);

  if (program === "klp") {
    return { rule, eligible: universityHasMajor(university, major) };
  }

  const scorePass = score.original > 0 && (score.gpa >= rule.gpa || score.percent >= rule.percent);
  const englishPass = ielts > 0 && ielts >= rule.ielts;
  const majorPass = universityHasMajor(university, major);

  return { rule, eligible: scorePass && englishPass && majorPass };
}

export default function EligibilityChecker({ universities }: { universities: University[] }) {
  const [name, setName] = useState("");
  const [program, setProgram] = useState<ProgramLevel>("bachelor");
  const [score, setScore] = useState("");
  const [ielts, setIelts] = useState("");
  const [major, setMajor] = useState<MajorCategory | "">("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const eligibleResults = useMemo(() => {
    if (!submitted) return [];
    return universities
      .map((university) => ({
        university,
        result: evaluate(university, program, score, ielts, major as MajorCategory),
      }))
      .filter((item) => item.result.eligible);
  }, [universities, program, score, ielts, major, submitted]);

  const selectedProgramLabel =
    program === "bachelor" ? "Bachelor / Undergraduate" :
    program === "master" ? "Master" :
    program === "phd" ? "Ph.D." : "KLP / EAP";

  const selectedMajorLabel = majorOptions.find((m) => m.value === major)?.label || "";

  function handleCheck() {
    const missing: string[] = [];
    if (!name.trim()) missing.push("student name");
    if (!program) missing.push("program level");
    if (!major) missing.push("major category");
    if (program !== "klp" && parseNumber(score) <= 0) missing.push(scoreLabel(program));
    if (program !== "klp" && parseNumber(ielts) <= 0) missing.push("IELTS / TOEFL / TOPIK score");

    if (missing.length > 0) {
      setSubmitted(false);
      setError(`Please input ${missing.join(", ")} first.`);
      return;
    }

    setError("");
    setSubmitted(true);
  }

  function handleChange(fn: () => void) {
    fn();
    setSubmitted(false);
    setError("");
  }

  return (
    <div className="eligibility-tool-v368">
      <div className="eligibility-form-card-v368">
        <div className="eligibility-grid-v368">
          <label>Student Name
            <input value={name} onChange={(e) => handleChange(() => setName(e.target.value))} placeholder="Student name" />
          </label>

          <label>Program Level
            <select value={program} onChange={(e) => handleChange(() => setProgram(e.target.value as ProgramLevel))}>
              <option value="bachelor">Bachelor / Undergraduate</option>
              <option value="master">Master</option>
              <option value="phd">Ph.D.</option>
              <option value="klp">Korean Language / KLP / EAP</option>
            </select>
          </label>

          {program === "bachelor" && (
            <label>High School GPA or %
              <input value={score} onChange={(e) => handleChange(() => setScore(e.target.value))} placeholder="Example: 3.2 or 72" />
            </label>
          )}

          {program === "master" && (
            <label>Bachelor GPA or %
              <input value={score} onChange={(e) => handleChange(() => setScore(e.target.value))} placeholder="Example: 3.0 or 70" />
            </label>
          )}

          {program === "phd" && (
            <label>Master GPA or %
              <input value={score} onChange={(e) => handleChange(() => setScore(e.target.value))} placeholder="Example: 3.3 or 78" />
            </label>
          )}

          {program !== "klp" && (
            <label>IELTS / TOEFL / TOPIK
              <input value={ielts} onChange={(e) => handleChange(() => setIelts(e.target.value))} placeholder="IELTS example: 5.5" />
            </label>
          )}

          <label className={program === "klp" ? "eligibility-wide-v369" : ""}>Major Category
            <select value={major} onChange={(e) => handleChange(() => setMajor(e.target.value as MajorCategory))}>
              <option value="">Select major category</option>
              {majorOptions.map((option) => (
                <option value={option.value} key={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>

        {error && <div className="eligibility-error-v369">{error}</div>}

        <button type="button" onClick={handleCheck} className="eligibility-check-button-v369">
          Check Eligibility
        </button>

        <div className="eligibility-summary-v368">
          <b>{name.trim() ? `${name.trim()}'s result` : "Eligibility result"}</b>
          <span>Input all information and click Check Eligibility. Only eligible universities will appear.</span>
        </div>
      </div>

      <div className="eligibility-results-card-v368">
        <div className="eligibility-results-head-v368">
          <div>
            <p>Eligible Universities</p>
            <h2>
              {!submitted
                ? "Waiting for check"
                : eligibleResults.length > 0
                  ? `${name.trim()}, you are eligible for ${eligibleResults.length} ${eligibleResults.length === 1 ? "university" : "universities"}`
                  : `${name.trim()}, no eligible university found`}
            </h2>
          </div>
          <span>{selectedProgramLabel}</span>
        </div>

        {!submitted ? (
          <div className="eligibility-empty-v368">
            Please enter all student information, choose a major category, then click <b>Check Eligibility</b>.
          </div>
        ) : eligibleResults.length === 0 ? (
          <div className="eligibility-empty-v368">
            No fully eligible university matched this information. Try a different major category or check the GPA/language score.
          </div>
        ) : (
          <>
            <div className="eligibility-success-v369">
              Major category: <b>{selectedMajorLabel}</b>. Only fully eligible universities are shown below.
            </div>
            <div className="eligibility-result-list-v368">
              {eligibleResults.map(({ university, result }) => (
                <div className="eligibility-result-item-v368 eligible" key={university.name}>
                  <img src={university.logo || university.image} alt={`${university.name} logo`} />
                  <div>
                    <h3>{university.name}</h3>
                    <p>{university.location}</p>
                    <small>
                      Requirement passed: {program === "klp" ? "KLP / EAP" : `GPA ${result.rule.gpa}+ or ${result.rule.percent}%+, IELTS ${result.rule.ielts}+`}
                    </small>
                  </div>
                  <div className="eligibility-status-wrap-v368">
                    <b>Eligible</b>
                    <Link href={`/universities/${slugifyUniversity(university.name)}`}>View Details →</Link>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
