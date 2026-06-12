"use client";

import { useState } from "react";
import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";

const stats = [
  ["Official Representatives", "2", "Approved master partners"],
  ["Partner Agencies", "3", "Approved sub-agencies"],
  ["Pending Approvals", "5", "Waiting for admin review"],
  ["Universities", "7", "University profiles"],
  ["Applications", "37", "Student records"],
  ["Eligibility Checks", "218", "Saved check logs"],
];

const tabs = [
  "Overview",
  "Universities",
  "Applications",
  "Partner Approvals",
  "Images & Logos",
  "Admissions",
  "Tuition & Scholarships",
  "Users & Settings",
];

const applications = [
  ["Aaray Sharma", "Kyungsung University", "Global Hospitality Management", "In Progress", "Interview Date Announced"],
  ["Ravi Gurung", "Sejong University", "Department of Media and Communication", "Submitted", "Documents Pending"],
  ["Minh Anh", "Youngsan University", "Department of Tourism", "Under Review", "University Received"],
];

const universities = [
  ["Kyungsung University", "Busan", "10,000–15,000", "1,966", "Application Closed"],
  ["Jeonbuk National University", "Jeonju", "20,000–25,000", "1,112", "Application Closed"],
  ["Kyungwoon University", "Gumi", "5,000–10,000", "909", "Not fixed yet"],
  ["Sejong University", "Seoul", "15,000–20,000", "2,844", "Not fixed yet"],
  ["Youngsan University", "Yangsan / Haeundae", "2,000–5,000", "842", "Not fixed yet"],
];

export default function AdminPage() {
  const [tab, setTab] = useState("Overview");

  return (
    <main className="min-h-screen bg-[#F6F9FE] text-[#061A40]">
      <TopNav />
      <section className="mx-auto max-w-[1720px] px-5 py-10 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <p className="inline-flex rounded-2xl bg-[#2457D6] px-5 py-3 text-sm font900 uppercase tracking-[.16em] text-white shadow-xl shadow-blue-200">Super Admin</p>
            <h1 className="mt-5 text-5xl font900 tracking-tight">KUA Admin Dashboard</h1>
            <p className="mt-3 max-w-4xl text-slate-600">Manage the full KUA platform: universities, applications, partner approvals, images, logos, deadlines, fees, scholarships, users, and site settings.</p>
          </div>
          <div className="rounded-2xl border border-blue-100 bg-white px-5 py-4 text-sm font900 shadow-sm">Signed in as Super Admin</div>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          {stats.map(([label, value, note]) => (
            <div key={label} className="rounded-[24px] border border-[#DCE6F4] bg-white p-5 shadow-sm">
              <p className="text-sm font900 text-slate-500">{label}</p>
              <p className="mt-5 text-4xl font900">{value}</p>
              <p className="mt-3 text-xs font800 text-slate-500">{note}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3 rounded-[28px] border border-[#DCE6F4] bg-white p-3 shadow-sm">
          {tabs.map((item) => (
            <button
              key={item}
              onClick={() => setTab(item)}
              className={`rounded-2xl px-5 py-3 text-sm font900 ${tab === item ? "bg-[#061A40] text-white" : "bg-[#F4F7FC] text-slate-700 hover:bg-blue-50"}`}
            >
              {item}
            </button>
          ))}
        </div>

        {tab === "Overview" && <OverviewPanel />}
        {tab === "Universities" && <UniversitiesPanel />}
        {tab === "Applications" && <ApplicationsPanel />}
        {tab === "Partner Approvals" && <PartnerPanel />}
        {tab === "Images & Logos" && <ImagesPanel />}
        {tab === "Admissions" && <AdmissionsPanel />}
        {tab === "Tuition & Scholarships" && <TuitionPanel />}
        {tab === "Users & Settings" && <SettingsPanel />}
      </section>
      <Footer />
    </main>
  );
}

function OverviewPanel() {
  return (
    <div className="mt-8 grid gap-5 lg:grid-cols-3">
      {[
        ["Open Official Representatives", "Review master partner organizations and their status."],
        ["Open Partner Agencies", "Approve, reject, or edit agency details."],
        ["Open Pending Approvals", "Check new sign-up requests."],
        ["Open Universities", "Update university cards, details, programs, and links."],
        ["Open Applications", "Track applicants, stages, and documents."],
        ["Open Eligibility Usage", "Review eligibility check history."],
      ].map(([title, body]) => (
        <button key={title} className="rounded-[24px] border border-[#DCE6F4] bg-white p-6 text-left shadow-sm hover:border-blue-400">
          <h2 className="text-xl font900">{title}</h2>
          <p className="mt-3 text-sm leading-7 text-slate-600">{body}</p>
        </button>
      ))}
    </div>
  );
}

function UniversitiesPanel() {
  return (
    <div className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm">
      <div className="flex flex-wrap justify-between gap-3">
        <h2 className="text-3xl font900">University Management</h2>
        <button className="rounded-2xl bg-[#061A40] px-5 py-3 text-sm font900 text-white">+ Add University</button>
      </div>
      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="bg-[#F4F7FC] text-slate-600"><tr>{["University", "City", "Students", "International", "Admission", "Actions"].map(h => <th key={h} className="px-4 py-3 font900">{h}</th>)}</tr></thead>
          <tbody>{universities.map((row) => <tr key={row[0]} className="border-b border-slate-100">{row.map((cell) => <td key={cell} className="px-4 py-4 font800">{cell}</td>)}<td className="px-4 py-4"><button className="rounded-xl bg-blue-50 px-4 py-2 font900 text-blue-700">Edit</button></td></tr>)}</tbody>
        </table>
      </div>
      <EditorGrid />
    </div>
  );
}

function EditorGrid() {
  return (
    <div className="mt-8 grid gap-5 lg:grid-cols-3">
      <AdminField title="Basic Information" fields={["University Name", "Location / City", "Type", "Website", "Language", "Short Description"]} />
      <AdminField title="Programs & Majors" fields={["Undergraduate Programs", "Graduate Programs", "KLP/EAP Programs", "Top Programs"]} />
      <AdminField title="Quick Facts" fields={["Total Students", "International Students", "Colleges", "Countries Represented", "Industry Partners", "Employment Rate"]} />
    </div>
  );
}

function ApplicationsPanel() {
  return (
    <div className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm">
      <div className="flex flex-wrap justify-between gap-3"><h2 className="text-3xl font900">Student Applications</h2><button className="rounded-2xl bg-[#061A40] px-5 py-3 text-sm font900 text-white">Export CSV</button></div>
      <div className="mt-6 overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-[#F4F7FC] text-slate-600"><tr>{["Applicant", "University", "Program", "Status", "Current Step", "Actions"].map(h => <th key={h} className="px-4 py-3 font900">{h}</th>)}</tr></thead><tbody>{applications.map((row) => <tr key={row[0]} className="border-b border-slate-100">{row.map((cell) => <td key={cell} className="px-4 py-4 font800">{cell}</td>)}<td className="px-4 py-4"><button className="rounded-xl bg-blue-50 px-4 py-2 font900 text-blue-700">Open</button></td></tr>)}</tbody></table></div>
    </div>
  );
}

function PartnerPanel() {
  return <GenericPanel title="Partner Agency Approvals" description="Approve official representatives, partner agencies, sub-agencies, and staff access requests." items={["Pending requests", "Approved partners", "Rejected requests", "Agency documents", "MoU contact records", "Role assignment"]} />;
}

function ImagesPanel() {
  return (
    <div className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm">
      <h2 className="text-3xl font900">Images & Logos</h2>
      <p className="mt-3 text-slate-600">Upload KUA logo, university logo/seal, campus images, hero slider images, gallery images, badge images, and brochure files.</p>
      <div className="mt-6 grid gap-5 lg:grid-cols-3">
        {[
          "KUA Main Logo", "University Logo / Seal", "Campus Card Image", "Detail Hero Image", "Hero Slider Images", "Gallery Images", "Brochure PDF", "Badge / Certification Images", "Footer / Map Background"
        ].map((label) => (
          <label key={label} className="rounded-[24px] border border-dashed border-blue-200 bg-[#F8FBFF] p-5">
            <span className="text-sm font900 text-slate-700">{label}</span>
            <input type="file" className="mt-4 block w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm" />
            <button type="button" className="mt-3 rounded-xl bg-[#061A40] px-4 py-2 text-xs font900 text-white">Upload</button>
          </label>
        ))}
      </div>
    </div>
  );
}

function AdmissionsPanel() {
  return <GenericPanel title="Admission Deadlines" description="Edit opening dates, closing dates, admission status, intake round, program level, and application links." items={["Undergraduate", "Graduate", "KLP/EAP", "Fall intake", "Spring intake", "Status badge colors"]} />;
}

function TuitionPanel() {
  return <GenericPanel title="Tuition & Scholarship Rules" description="Update tuition ranges, scholarship percentages, GPA requirements, language requirements, and automatic scholarship calculator rules." items={["Tuition range", "Scholarship rules", "Language score", "GPA requirement", "Bank balance", "Calculator logs"]} />;
}

function SettingsPanel() {
  return <GenericPanel title="Users & Settings" description="Manage roles, passwords, permissions, site notices, backups, security, and system logs." items={["Super admin", "Staff", "Partner", "Read-only", "System logs", "Security settings"]} />;
}

function GenericPanel({ title, description, items }: { title: string; description: string; items: string[] }) {
  return (
    <div className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm">
      <h2 className="text-3xl font900">{title}</h2>
      <p className="mt-3 text-slate-600">{description}</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => <div key={item} className="rounded-2xl border border-slate-100 bg-[#F8FBFF] p-5"><p className="font900">{item}</p><button className="mt-4 rounded-xl bg-white px-4 py-2 text-sm font900 text-blue-700 shadow-sm">Edit</button></div>)}
      </div>
    </div>
  );
}

function AdminField({ title, fields }: { title: string; fields: string[] }) {
  return (
    <div className="rounded-[24px] border border-slate-100 bg-[#F8FBFF] p-5">
      <h3 className="text-xl font900">{title}</h3>
      <div className="mt-4 space-y-3">{fields.map((field) => <input key={field} placeholder={field} className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-500" />)}</div>
      <button className="mt-4 rounded-xl bg-[#061A40] px-4 py-3 text-sm font900 text-white">Save Changes</button>
    </div>
  );
}
