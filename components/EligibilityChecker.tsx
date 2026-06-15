"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { slugifyUniversity, type University } from "../lib/universities";

type ProgramLevel = "bachelor" | "master" | "phd" | "eap" | "klp";
type MajorCategory = "business" | "it" | "engineering" | "hospitality" | "korean" | "media" | "tourism" | "other";

const majorOptions: { value: MajorCategory; label: string; keywords: string[] }[] = [
  { value: "business", label: "Business / Management", keywords: ["business", "commerce", "management", "administration", "marketing"] },
  { value: "it", label: "IT / Software / Computer", keywords: ["it", "software", "computer", "digital", "data", "information"] },
  { value: "engineering", label: "Engineering / Mechanical", keywords: ["engineering", "mechanical", "design"] },
  { value: "hospitality", label: "Hospitality / Hotel", keywords: ["hospitality", "hotel", "food", "culinary"] },
  { value: "korean", label: "Korean Studies / Korean Language", keywords: ["korean", "language", "culture"] },
  { value: "media", label: "Media / Communication / Entertainment", keywords: ["media", "communication", "entertainment", "k-entertainment"] },
  { value: "tourism", label: "Tourism / Airline / Convention", keywords: ["tourism", "airline", "convention"] },
  { value: "other", label: "Other / Not decided", keywords: [] },
];

type Rule = { gpa: number; percent: number; ielts: number; label: string };

const rules: Record<string, Record<ProgramLevel, Rule>> = {
  "Kyungsung University": {
    bachelor: { gpa: 2.5, percent: 60, ielts: 5.5, label: "Bachelor / Undergraduate" },
    master: { gpa: 2.7, percent: 65, ielts: 5.5, label: "Master" },
    phd: { gpa: 3.0, percent: 70, ielts: 6.0, label: "Ph.D." },
    eap: { gpa: 2.0, percent: 50, ielts: 4.0, label: "EAP" },
    klp: { gpa: 2.0, percent: 50, ielts: 0, label: "KLP" },
  },
  "Jeonbuk National University": {
    bachelor: { gpa: 2.8, percent: 65, ielts: 5.5, label: "Bachelor / Undergraduate" },
    master: { gpa: 3.0, percent: 70, ielts: 6.0, label: "Master" },
    phd: { gpa: 3.2, percent: 75, ielts: 6.0, label: "Ph.D." },
    eap: { gpa: 2.5, percent: 60, ielts: 5.0, label: "EAP" },
    klp: { gpa: 2.0, percent: 50, ielts: 0, label: "KLP" },
  },
  "Kyungwoon University": {
    bachelor: { gpa: 2.3, percent: 55, ielts: 5.0, label: "Bachelor / Undergraduate" },
    master: { gpa: 2.5, percent: 60, ielts: 5.5, label: "Master" },
    phd: { gpa: 2.8, percent: 65, ielts: 5.5, label: "Ph.D." },
    eap: { gpa: 2.0, percent: 50, ielts: 4.0, label: "EAP" },
    klp: { gpa: 2.0, percent: 50, ielts: 0, label: "KLP" },
  },
  "Sejong University": {
    bachelor: { gpa: 3.0, percent: 70, ielts: 6.0, label: "Bachelor / Undergraduate" },
    master: { gpa: 3.2, percent: 75, ielts: 6.0, label: "Master" },
    phd: { gpa: 3.3, percent: 78, ielts: 6.5, label: "Ph.D." },
    eap: { gpa: 2.7, percent: 65, ielts: 5.0, label: "EAP" },
    klp: { gpa: 2.0, percent: 50, ielts: 0, label: "KLP" },
  },
  "Youngsan University": {
    bachelor: { gpa: 2.2, percent: 55, ielts: 5.0, label: "Bachelor / Undergraduate" },
    master: { gpa: 2.5, percent: 60, ielts: 5.0, label: "Master" },
    phd: { gpa: 2.8, percent: 65, ielts: 5.5, label: "Ph.D." },
    eap: { gpa: 2.0, percent: 50, ielts: 4.0, label: "EAP" },
    klp: { gpa: 2.0, percent: 50, ielts: 0, label: "KLP" },
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
  if (program === "eap") return "GPA or %";
  return "GPA or %";
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
  ].join(" ").toLowerCase();

  return selected.keywords.some((keyword) => searchableText.includes(keyword));
}

function getRule(universityName: string, program: ProgramLevel) {
  return rules[universityName]?.[program] || rules["Kyungsung University"][program];
}

function evaluate(university: University, program: ProgramLevel, scoreRaw: string, ieltsRaw: string, major: MajorCategory | "") {
  const rule = getRule(university.name, program);
  const score = normalizeScore(scoreRaw);
  const ielts = parseNumber(ieltsRaw);

  const scorePass = score.original > 0 && (score.gpa >= rule.gpa || score.percent >= rule.percent);

  if (program === "klp") {
    return { rule, eligible: scorePass, detail: `GPA ${rule.gpa}+ or ${rule.percent}%+. TOPIK is optional.` };
  }

  if (program === "eap") {
    const englishPass = ielts > 0 && ielts >= rule.ielts;
    return { rule, eligible: scorePass && englishPass, detail: `GPA ${rule.gpa}+ or ${rule.percent}%+, IELTS ${rule.ielts}+` };
  }

  const englishPass = ielts > 0 && ielts >= rule.ielts;
  const majorPass = major ? universityHasMajor(university, major) : false;

  return { rule, eligible: scorePass && englishPass && majorPass, detail: `GPA ${rule.gpa}+ or ${rule.percent}%+, IELTS ${rule.ielts}+` };
}

export default function EligibilityChecker({ universities }: { universities: University[] }) {
  const [name, setName] = useState("");
  const [program, setProgram] = useState<ProgramLevel>("bachelor");
  const [score, setScore] = useState("");
  const [ielts, setIelts] = useState("");
  const [topik, setTopik] = useState("");
  const [major, setMajor] = useState<MajorCategory | "">("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const needsMajor = program === "bachelor" || program === "master" || program === "phd";
  const needsIelts = program !== "klp";
  const isLanguageProgram = program === "eap" || program === "klp";

  const eligibleResults = useMemo(() => {
    if (!submitted) return [];
    return universities
      .map((university) => ({
        university,
        result: evaluate(university, program, score, ielts, major),
      }))
      .filter((item) => item.result.eligible);
  }, [universities, program, score, ielts, major, submitted]);

  const selectedProgramLabel =
    program === "bachelor" ? "Bachelor / Undergraduate" :
    program === "master" ? "Master" :
    program === "phd" ? "Ph.D." :
    program === "eap" ? "EAP" : "KLP";

  const selectedMajorLabel = needsMajor ? (majorOptions.find((m) => m.value === major)?.label || "") : selectedProgramLabel;

  function resetAfterChange(fn: () => void) {
    fn();
    setSubmitted(false);
    setError("");
  }

  function handleProgramChange(nextProgram: ProgramLevel) {
    resetAfterChange(() => {
      setProgram(nextProgram);
      setMajor("");
      setIelts("");
      setTopik("");
    });
  }

  function handleCheck() {
    const missing: string[] = [];
    if (!name.trim()) missing.push("student name");
    if (!program) missing.push("program level");
    if (needsMajor && !major) missing.push("major category");
    if (parseNumber(score) <= 0) missing.push(scoreLabel(program));
    if (needsIelts && parseNumber(ielts) <= 0) missing.push(program === "eap" ? "IELTS score for EAP" : "IELTS / TOEFL / TOPIK score");

    if (missing.length > 0) {
      setSubmitted(false);
      setError(`Please input ${missing.join(", ")} first.`);
      return;
    }

    setError("");
    setSubmitted(true);
  }

  return (
    <div className="eligibility-tool-v368">
      <div className="eligibility-form-card-v368">
        <div className="eligibility-grid-v368">
          <label>Student Name
            <input value={name} onChange={(e) => resetAfterChange(() => setName(e.target.value))} placeholder="Student name" />
          </label>

          <label>Program Level
            <select value={program} onChange={(e) => handleProgramChange(e.target.value as ProgramLevel)}>
              <option value="bachelor">Bachelor / Undergraduate</option>
              <option value="master">Master</option>
              <option value="phd">Ph.D.</option>
              <option value="eap">EAP - English Academic Purpose</option>
              <option value="klp">KLP - Korean Language Program</option>
            </select>
          </label>

          {program === "bachelor" && (
            <label>High School GPA or %
              <input value={score} onChange={(e) => resetAfterChange(() => setScore(e.target.value))} placeholder="Example: 3.2 or 72" />
            </label>
          )}

          {program === "master" && (
            <label>Bachelor GPA or %
              <input value={score} onChange={(e) => resetAfterChange(() => setScore(e.target.value))} placeholder="Example: 3.0 or 70" />
            </label>
          )}

          {program === "phd" && (
            <label>Master GPA or %
              <input value={score} onChange={(e) => resetAfterChange(() => setScore(e.target.value))} placeholder="Example: 3.3 or 78" />
            </label>
          )}

          {isLanguageProgram && (
            <label>GPA or %
              <input value={score} onChange={(e) => resetAfterChange(() => setScore(e.target.value))} placeholder="Example: 2.8 or 65" />
            </label>
          )}

          {needsIelts && (
            <label>{program === "eap" ? "IELTS Score" : "IELTS / TOEFL / TOPIK"}
              <input value={ielts} onChange={(e) => resetAfterChange(() => setIelts(e.target.value))} placeholder={program === "eap" ? "Example: 4.0 or 5.0" : "IELTS example: 5.5"} />
              {program === "eap" && <small className="eligibility-help-v371">EAP IELTS requirement differs by university: some accept 4.0 and some require 5.0.</small>}
            </label>
          )}

          {program === "klp" && (
            <label>TOPIK Score / Level <span className="eligibility-optional-v371">(optional)</span>
              <input value={topik} onChange={(e) => resetAfterChange(() => setTopik(e.target.value))} placeholder="Optional, example: TOPIK 2" />
            </label>
          )}

          {needsMajor && (
            <label className="eligibility-wide-v369">Major Category
              <select value={major} onChange={(e) => resetAfterChange(() => setMajor(e.target.value as MajorCategory))}>
                <option value="">Select major category</option>
                {majorOptions.map((option) => (
                  <option value={option.value} key={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
          )}
        </div>

        {error && <div className="eligibility-error-v369">{error}</div>}

        <button type="button" onClick={handleCheck} className="eligibility-check-button-v369">
          Check Eligibility
        </button>

        <div className="eligibility-summary-v368">
          <b>{name.trim() ? `${name.trim()}'s result` : "Eligibility result"}</b>
          <span>Input all required information and click Check Eligibility. Only eligible universities will appear.</span>
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
            Please enter all required student information, then click <b>Check Eligibility</b>.
          </div>
        ) : eligibleResults.length === 0 ? (
          <div className="eligibility-empty-v368">
            No fully eligible university matched this information. Try checking GPA/percentage, language score, or program level.
          </div>
        ) : (
          <>
            <div className="eligibility-success-v369">
              Program: <b>{selectedProgramLabel}</b>{needsMajor ? <> · Major category: <b>{selectedMajorLabel}</b></> : null}. Only fully eligible universities are shown below.
            </div>
            <div className="eligibility-result-list-v368">
              {eligibleResults.map(({ university, result }) => (
                <div className="eligibility-result-item-v368 eligible" key={university.name}>
                  <img src={university.logo || university.image} alt={`${university.name} logo`} />
                  <div>
                    <h3>{university.name}</h3>
                    <p>{university.location}</p>
                    <small>Requirement passed: {result.detail}</small>
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
