"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { slugifyUniversity, type University } from "../lib/universities";

type ProgramLevel = "bachelor" | "master" | "phd" | "klp";

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

function evaluate(university: University, program: ProgramLevel, scoreRaw: string, ieltsRaw: string, major: string) {
  const rule = rules[university.name]?.[program] || rules["Kyungsung University"][program];
  const score = normalizeScore(scoreRaw);
  const ielts = parseNumber(ieltsRaw);
  const hasScore = score.original > 0;
  const needsLanguage = program !== "klp";
  const hasEnglish = !needsLanguage || ielts > 0;
  const scorePass = program === "klp" || (hasScore && (score.gpa >= rule.gpa || score.percent >= rule.percent));
  const englishPass = !needsLanguage || (hasEnglish && ielts >= rule.ielts);
  const majors = [...(university.topMajors || []), ...(university.graduatePrograms || []), ...(university.klpPrograms || [])];
  const majorMatch = !major.trim() || majors.some((m) => m.toLowerCase().includes(major.toLowerCase()) || major.toLowerCase().includes(m.toLowerCase().split(" ")[0]));
  const missing = [];
  if (!hasScore && program !== "klp") missing.push(scoreLabel(program));
  if (!hasEnglish && needsLanguage) missing.push("IELTS / TOEFL / TOPIK");

  let status: "Eligible" | "Conditional" | "Not Eligible" = "Not Eligible";
  if (program === "klp") status = "Eligible";
  else if (scorePass && englishPass && majorMatch) status = "Eligible";
  else if ((scorePass || englishPass) && majorMatch) status = "Conditional";

  return { rule, status, scorePass, englishPass, majorMatch, missing };
}

export default function EligibilityChecker({ universities }: { universities: University[] }) {
  const [name, setName] = useState("");
  const [program, setProgram] = useState<ProgramLevel>("bachelor");
  const [score, setScore] = useState("");
  const [ielts, setIelts] = useState("");
  const [major, setMajor] = useState("");

  const results = useMemo(() => {
    return universities.map((university) => ({
      university,
      result: evaluate(university, program, score, ielts, major),
    })).sort((a, b) => {
      const rank = { Eligible: 0, Conditional: 1, "Not Eligible": 2 };
      return rank[a.result.status] - rank[b.result.status];
    });
  }, [universities, program, score, ielts, major]);

  const visibleResults = results.filter((item) => item.result.status !== "Not Eligible");
  const hasInput = program === "klp" || parseNumber(score) > 0 || parseNumber(ielts) > 0 || major.trim().length > 0;

  return (
    <div className="eligibility-tool-v368">
      <div className="eligibility-form-card-v368">
        <div className="eligibility-grid-v368">
          <label>Student Name
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Student name" />
          </label>

          <label>Program Level
            <select value={program} onChange={(e) => setProgram(e.target.value as ProgramLevel)}>
              <option value="bachelor">Bachelor / Undergraduate</option>
              <option value="master">Master</option>
              <option value="phd">Ph.D.</option>
              <option value="klp">Korean Language / KLP / EAP</option>
            </select>
          </label>

          {program === "bachelor" && (
            <label>High School GPA or %
              <input value={score} onChange={(e) => setScore(e.target.value)} placeholder="Example: 3.2 or 72" />
            </label>
          )}

          {program === "master" && (
            <label>Bachelor GPA or %
              <input value={score} onChange={(e) => setScore(e.target.value)} placeholder="Example: 3.0 or 70" />
            </label>
          )}

          {program === "phd" && (
            <label>Master GPA or %
              <input value={score} onChange={(e) => setScore(e.target.value)} placeholder="Example: 3.3 or 78" />
            </label>
          )}

          {program !== "klp" && (
            <label>IELTS / TOEFL / TOPIK
              <input value={ielts} onChange={(e) => setIelts(e.target.value)} placeholder="IELTS example: 5.5" />
            </label>
          )}

          <label>Preferred Major
            <input value={major} onChange={(e) => setMajor(e.target.value)} placeholder="Example: Business, Hospitality, IT" />
          </label>
        </div>

        <div className="eligibility-summary-v368">
          <b>{name ? `${name}'s result` : "Live eligibility result"}</b>
          <span>Results update automatically while you type.</span>
        </div>
      </div>

      <div className="eligibility-results-card-v368">
        <div className="eligibility-results-head-v368">
          <div>
            <p>Recommended Universities</p>
            <h2>{hasInput ? `${visibleResults.length} possible match${visibleResults.length === 1 ? "" : "es"}` : "Enter student information"}</h2>
          </div>
          <span>{program === "bachelor" ? "Bachelor" : program === "master" ? "Master" : program === "phd" ? "Ph.D." : "KLP / EAP"}</span>
        </div>

        {!hasInput ? (
          <div className="eligibility-empty-v368">
            Enter GPA/percentage and language score. Eligible or conditional universities will appear here automatically.
          </div>
        ) : (
          <div className="eligibility-result-list-v368">
            {results.map(({ university, result }) => (
              <div className={`eligibility-result-item-v368 ${result.status.toLowerCase().replace(" ", "-")}`} key={university.name}>
                <img src={university.logo || university.image} alt={`${university.name} logo`} />
                <div>
                  <h3>{university.name}</h3>
                  <p>{university.location}</p>
                  <small>
                    Requirement: {program === "klp" ? "No IELTS required for KLP/EAP" : `GPA ${result.rule.gpa}+ or ${result.rule.percent}%+, IELTS ${result.rule.ielts}+`}
                  </small>
                </div>
                <div className="eligibility-status-wrap-v368">
                  <b>{result.status}</b>
                  <Link href={`/universities/${slugifyUniversity(university.name)}`}>View Details →</Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
