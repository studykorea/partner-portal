"use client";

import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import { universities as baseUniversities, slugifyUniversity, API_URL } from "../../lib/universities";

type AdmissionTone = "open" | "soon" | "closed" | "notfixed";
type AdmissionEdit = { program: string; open: string; close: string; status: string; tone: AdmissionTone };
type EditableUniversity = {
  name: string;
  location: string;
  region: string;
  students: string;
  internationalStudents: string;
  type: string;
  established: string;
  accreditation: string;
  accreditationBadge: string;
  homepage: string;
  email: string;
  phone: string;
  address: string;
  overview: string;
  tuition: string;
  intake: string;
  topMajors: string[];
  graduatePrograms: string[];
  klpPrograms: string[];
  image: string;
  logo: string;
  heroImage: string;
  detailCoverImage: string;
  galleryImages: string[];
  videoUrl: string;
  brochureUrl: string;
  facebookUrl: string;
  instagramUrl: string;
  youtubeUrl: string;
  admissions: AdmissionEdit[];
};

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

const stats = [
  ["Official Representatives", "2", "Approved master partners"],
  ["Partner Agencies", "3", "Approved sub-agencies"],
  ["Pending Approvals", "5", "Waiting for admin review"],
  ["Universities", "7", "University profiles"],
  ["Applications", "37", "Student records"],
  ["Eligibility Checks", "218", "Saved check logs"],
];

const applications = [
  ["Aaray Sharma", "Kyungsung University", "Global Hospitality Management", "In Progress", "Interview Date Announced"],
  ["Ravi Gurung", "Sejong University", "Department of Media and Communication", "Submitted", "Documents Pending"],
  ["Minh Anh", "Youngsan University", "Department of Tourism", "Under Review", "University Received"],
];

function defaultAdmissions(name: string): AdmissionEdit[] {
  const isFixed = name === "Kyungsung University" || name === "Jeonbuk National University";
  return [
    { program: "Undergraduate", open: "19 May 2026", close: "30 May 2026", status: isFixed ? "Admission Closed" : "Not fixed yet", tone: isFixed ? "closed" : "notfixed" },
    { program: "Graduate (Masters/Ph.D.)", open: "15 May 2026", close: "05 Jun 2026", status: isFixed ? "Admission Closed" : "Not fixed yet", tone: isFixed ? "closed" : "notfixed" },
    { program: "KLP / EAP", open: "18 May 2026", close: "29 May 2026", status: isFixed ? "Admission Closed" : "Not fixed yet", tone: isFixed ? "closed" : "notfixed" },
  ];
}

function toEditable(source = baseUniversities): EditableUniversity[] {
  return source.map((u: any) => ({
    name: u.name,
    location: u.location,
    region: u.region,
    students: u.students,
    internationalStudents: u.internationalStudents,
    type: u.type || (u.name === "Kyungsung University" ? "Private University" : "Partner University"),
    established: u.established || "Not updated",
    accreditation: u.accreditation || (u.name === "Kyungsung University" ? "IEQAS Excellent Accredited" : "Accredited"),
    accreditationBadge: u.accreditationBadge || (u.name === "Kyungsung University" ? "/assets/ieqas_badge.png" : "/assets/certified_information_badge_custom.png"),
    homepage: u.homepage,
    email: u.email || "koreastudypartner@gmail.com",
    phone: u.phone || "",
    address: u.address || "",
    overview: u.overview,
    tuition: u.tuition,
    intake: u.intake,
    topMajors: [...u.topMajors],
    graduatePrograms: u.graduatePrograms?.length ? u.graduatePrograms : (u.name === "Kyungsung University"
      ? ["Department of Global Business", "Department of Global Hospitality", "Department of Korean Culture and Education", "Department of International Studies", "Department of Global IT Engineering", "Department of Digital Marketing"]
      : (u.topMajors || []).map((m: string) => `Department of ${m}`)),
    klpPrograms: u.klpPrograms?.length ? u.klpPrograms : ["D4-1 (4 semester)", "Korean Language Program", "KLP / EAP"],
    image: u.image,
    logo: u.logo || "",
    heroImage: u.heroImage || u.image,
    detailCoverImage: u.heroImage || u.image,
    galleryImages: [u.image].filter(Boolean),
    videoUrl: u.videoUrl || u.youtubeUrl || `https://www.youtube.com/results?search_query=${encodeURIComponent(`${u.name} campus tour`)}`,
    brochureUrl: u.brochureUrl || (u.homepage ? `https://${u.homepage.replace(/^https?:\/\//, "")}` : ""),
    facebookUrl: u.facebookUrl || `https://www.facebook.com/search/top?q=${encodeURIComponent(u.name)}`,
    instagramUrl: u.instagramUrl || `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(u.name)}`,
    youtubeUrl: u.youtubeUrl || u.videoUrl || `https://www.youtube.com/results?search_query=${encodeURIComponent(`${u.name} campus tour`)}`,
    admissions: u.admissions?.length ? u.admissions.map((a: any) => ({ program: a.program, open: a.open || "", close: a.close || "", status: a.status || "Not fixed yet", tone: (a.tone || "notfixed") as AdmissionTone })) : defaultAdmissions(u.name),
  }));
}

function deriveStatus(openDate: string, closeDate: string): { status: string; tone: AdmissionTone } {
  const now = new Date();
  const open = new Date(openDate);
  const close = new Date(closeDate);
  if (Number.isNaN(open.getTime()) || Number.isNaN(close.getTime())) return { status: "Not fixed yet", tone: "notfixed" };
  const threeWeeks = 1000 * 60 * 60 * 24 * 21;
  if (now >= open && now <= close) return { status: "Application Open", tone: "open" };
  if (now < open && open.getTime() - now.getTime() <= threeWeeks) return { status: "Opening Soon", tone: "soon" };
  if (now > close) return { status: "Admission Closed", tone: "closed" };
  return { status: "Not fixed yet", tone: "notfixed" };
}

export default function AdminPage() {
  const [tab, setTab] = useState("Universities");
  const [items, setItems] = useState<EditableUniversity[]>(toEditable());
  const [selected, setSelected] = useState(0);
  const [saveMessage, setSaveMessage] = useState<{type: "ok" | "err"; text: string} | null>(null);
  const editorRef = useRef<HTMLDivElement | null>(null);
  const selectedUniversity = items[selected] || items[0];

  function selectUniversity(index: number) {
    setSelected(index);
    setTimeout(() => editorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
  }

  useEffect(() => {
    if (!API_URL) return;
    fetch(`${API_URL}/api/universities`, { cache: "no-store" })
      .then((res) => res.ok ? res.json() : null)
      .then((data) => { if (data?.items?.length) setItems(toEditable(data.items)); })
      .catch(() => undefined);
  }, []);

  function updateSelected(next: EditableUniversity) {
    setItems((old) => old.map((u, i) => (i === selected ? next : u)));
  }

  async function saveSelectedUniversity() {
    if (!API_URL) {
      setSaveMessage({ type: "err", text: "Backend is not connected. Add NEXT_PUBLIC_API_URL to the frontend Render environment." });
      return;
    }
    const slug = slugifyUniversity(selectedUniversity.name);
    try {
      const res = await fetch(`${API_URL}/api/admin/universities/${slug}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(selectedUniversity),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSaveMessage({ type: "ok", text: `Saved permanently to Supabase. Public pages will load the updated data. Slug: ${data.slug || slug}` });
    } catch (err: any) {
      setSaveMessage({ type: "err", text: `Save failed: ${err?.message || "Check backend Supabase environment variables and schema."}` });
    }
  }

  return (
    <main className="min-h-screen bg-[#F6F9FE] text-[#061A40]">
      <TopNav />
      <section className="mx-auto max-w-[1720px] px-5 py-10 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <p className="inline-flex rounded-2xl bg-[#2457D6] px-5 py-3 text-sm font900 uppercase tracking-[.16em] text-white shadow-xl shadow-blue-200">Super Admin</p>
            <h1 className="mt-5 text-5xl font900 tracking-tight">KUA Admin Dashboard</h1>
            <p className="mt-3 max-w-5xl text-slate-600">Manage the full KUA platform: universities, applications, partner approvals, images, logos, admissions, fees, scholarships, users, and site settings.</p>
          </div>
          <div className="rounded-2xl border border-blue-100 bg-white px-5 py-4 text-sm font900 shadow-sm">Signed in as Super Admin</div>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          {stats.map(([label, value, note]) => (
            <div key={label} className="rounded-[24px] border border-[#DCE6F4] bg-white p-5 shadow-sm">
              <p className="text-sm font900 text-slate-500">{label}</p><p className="mt-5 text-4xl font900">{value}</p><p className="mt-3 text-xs font800 text-slate-500">{note}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3 rounded-[28px] border border-[#DCE6F4] bg-white p-3 shadow-sm">
          {tabs.map((item) => <button key={item} onClick={() => setTab(item)} className={`rounded-2xl px-5 py-3 text-sm font900 ${tab === item ? "bg-[#061A40] text-white" : "bg-[#F4F7FC] text-slate-700 hover:bg-blue-50"}`}>{item}</button>)}
        </div>

        {tab === "Overview" && <OverviewPanel />}
        {tab === "Universities" && <UniversitiesPanel items={items} selected={selected} setSelected={selectUniversity} editorRef={editorRef} selectedUniversity={selectedUniversity} updateSelected={updateSelected} saveSelectedUniversity={saveSelectedUniversity} saveMessage={saveMessage} />}
        {tab === "Applications" && <ApplicationsPanel />}
        {tab === "Partner Approvals" && <GenericPanel title="Partner Agency Approvals" description="Approve official representatives, partner agencies, sub-agencies, and staff access requests." items={["Pending requests", "Approved partners", "Rejected requests", "Agency documents", "MoU contact records", "Role assignment"]} />}
        {tab === "Images & Logos" && <ImagesPanel items={items} selected={selected} setSelected={selectUniversity} selectedUniversity={selectedUniversity} updateSelected={updateSelected} />}
        {tab === "Admissions" && <AdmissionsPanel selectedUniversity={selectedUniversity} updateSelected={updateSelected} />}
        {tab === "Tuition & Scholarships" && <TuitionPanel items={items} selected={selected} setSelected={selectUniversity} selectedUniversity={selectedUniversity} updateSelected={updateSelected} />}
        {tab === "Users & Settings" && <GenericPanel title="Users & Settings" description="Manage roles, passwords, permissions, site notices, backups, security, and system logs." items={["Super admin", "Staff", "Partner", "Read-only", "System logs", "Security settings"]} />}
      </section>
      <Footer />
    </main>
  );
}

function OverviewPanel() {
  return <div className="mt-8 grid gap-5 lg:grid-cols-3">{["Official Representatives", "Partner Agencies", "Pending Approvals", "Universities", "Applications", "Eligibility Usage"].map((title) => <button key={title} className="rounded-[24px] border border-[#DCE6F4] bg-white p-6 text-left shadow-sm hover:border-blue-400"><h2 className="text-xl font900">Open {title}</h2><p className="mt-3 text-sm leading-7 text-slate-600">Review and manage {title.toLowerCase()} records.</p></button>)}</div>;
}

function UniversitiesPanel({ items, selected, setSelected, editorRef, selectedUniversity, updateSelected, saveSelectedUniversity, saveMessage }: { items: EditableUniversity[]; selected: number; setSelected: (n: number) => void; editorRef: RefObject<HTMLDivElement | null>; selectedUniversity: EditableUniversity; updateSelected: (u: EditableUniversity) => void; saveSelectedUniversity: () => void; saveMessage: {type: "ok" | "err"; text: string} | null }) {
  return (
    <div className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm">
      <div className="flex flex-wrap justify-between gap-3"><h2 className="text-3xl font900">University Management</h2><button className="rounded-2xl bg-[#061A40] px-5 py-3 text-sm font900 text-white">+ Add University</button></div>
      <p className="mt-3 text-sm text-slate-600">Click Edit to select a university, then update its name, majors, deadlines, logo, hero image, accreditation, and links below.</p>
      <div className="mt-6 overflow-x-auto"><table className="w-full min-w-[1050px] text-left text-sm"><thead className="bg-[#F4F7FC] text-slate-600"><tr>{["University", "City", "Students", "International", "Accreditation", "Admission", "Actions"].map(h => <th key={h} className="px-4 py-3 font900">{h}</th>)}</tr></thead><tbody>{items.map((row, index) => <tr key={`${row.name}-${index}`} onClick={() => setSelected(index)} className={`cursor-pointer border-b border-slate-100 hover:bg-blue-50/60 ${selected === index ? "bg-blue-50/70 ring-1 ring-blue-100" : ""}`}><td className="px-4 py-4 font900">{row.name}</td><td className="px-4 py-4 font800">{row.location}</td><td className="px-4 py-4 font800">{row.students}</td><td className="px-4 py-4 font800">{row.internationalStudents}</td><td className="px-4 py-4 font800">{row.accreditation}</td><td className="px-4 py-4 font800"><span className={`admin-status ${row.admissions[0]?.tone || "notfixed"}`}>{row.admissions[0]?.status || "Not fixed yet"}</span></td><td className="px-4 py-4"><button type="button" onClick={(e) => { e.stopPropagation(); setSelected(index); }} className="rounded-xl bg-blue-50 px-4 py-2 font900 text-blue-700 hover:bg-blue-100">Edit</button></td></tr>)}</tbody></table></div>
      <div ref={editorRef}><UniversityEditor university={selectedUniversity} updateSelected={updateSelected} saveSelectedUniversity={saveSelectedUniversity} saveMessage={saveMessage} /></div>
    </div>
  );
}

function UniversityEditor({ university, updateSelected, saveSelectedUniversity, saveMessage }: { university: EditableUniversity; updateSelected: (u: EditableUniversity) => void; saveSelectedUniversity: () => void; saveMessage: {type: "ok" | "err"; text: string} | null }) {
  function updateField<K extends keyof EditableUniversity>(key: K, value: EditableUniversity[K]) { updateSelected({ ...university, [key]: value }); }
  function textAreaList(value: string[], setter: (v: string[]) => void, placeholder: string) { return <textarea value={value.join("\n")} placeholder={placeholder} onChange={(e) => setter(e.target.value.split("\n").filter(Boolean))} className="admin-textarea" />; }

  return (
    <div className="mt-8 rounded-[26px] border border-blue-100 bg-[#F8FBFF] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="text-2xl font900">Editing: {university.name}</h3><p className="text-sm text-slate-600">Changes below save permanently through FastAPI + Supabase. Upload images first, then click Save University Changes after editing text fields.</p></div><a href={`/universities/${slugifyUniversity(university.name)}`} target="_blank" className="rounded-xl bg-white px-4 py-3 text-sm font900 text-blue-700 shadow-sm">Open public detail page ↗</a></div>
      <div className="mt-6 grid gap-5 xl:grid-cols-3">
        <AdminBox title="Basic Information">
          <AdminInput label="University Name" value={university.name} onChange={(v) => updateField("name", v)} />
          <AdminInput label="Location / City" value={university.location} onChange={(v) => updateField("location", v)} />
          <AdminInput label="Region" value={university.region} onChange={(v) => updateField("region", v)} />
          <AdminInput label="University Type" value={university.type} onChange={(v) => updateField("type", v)} />
          <AdminInput label="Established" value={university.established} onChange={(v) => updateField("established", v)} />
          <label className="admin-label">Overview<textarea value={university.overview} onChange={(e) => updateField("overview", e.target.value)} className="admin-textarea" /></label>
        </AdminBox>
        <AdminBox title="Programs & Majors">
          <label className="admin-label">Undergraduate Programs{ textAreaList(university.topMajors, (v) => updateField("topMajors", v), "One major per line") }</label>
          <label className="admin-label">Graduate Programs{ textAreaList(university.graduatePrograms, (v) => updateField("graduatePrograms", v), "One graduate program per line") }</label>
          <label className="admin-label">KLP / EAP Programs{ textAreaList(university.klpPrograms, (v) => updateField("klpPrograms", v), "One language program per line") }</label>
        </AdminBox>
        <AdminBox title="Quick Facts & Accreditation">
          <AdminInput label="Total Students" value={university.students} onChange={(v) => updateField("students", v)} />
          <AdminInput label="International Students" value={university.internationalStudents} onChange={(v) => updateField("internationalStudents", v)} />
          <AdminInput label="Tuition Range" value={university.tuition} onChange={(v) => updateField("tuition", v)} />
          <AdminInput label="Intake" value={university.intake} onChange={(v) => updateField("intake", v)} />
          <label className="admin-label">Accreditation<select value={university.accreditation} onChange={(e) => updateField("accreditation", e.target.value)} className="admin-input"><option>IEQAS Excellent Accredited</option><option>IEQAS Accredited</option><option>Accredited</option><option>Not accredited yet</option><option>Not updated</option></select></label>
          <AdminInput label="Accreditation Badge URL" value={university.accreditationBadge} onChange={(v) => updateField("accreditationBadge", v)} />
        </AdminBox>
      </div>
      <AdmissionsEditor university={university} updateSelected={updateSelected} />
      <MediaEditor university={university} updateSelected={updateSelected} />
      <button onClick={saveSelectedUniversity} className="mt-6 rounded-2xl bg-[#061A40] px-6 py-4 text-sm font900 text-white">Save University Changes</button>{saveMessage && <div className={`save-message ${saveMessage.type}`}>{saveMessage.text}</div>}
    </div>
  );
}

function AdmissionsEditor({ university, updateSelected }: { university: EditableUniversity; updateSelected: (u: EditableUniversity) => void }) {
  function updateAdmission(index: number, field: keyof AdmissionEdit, value: string) {
    const admissions = university.admissions.map((a, i) => i === index ? { ...a, [field]: value } : a);
    updateSelected({ ...university, admissions });
  }
  function autoStatus(index: number) {
    const item = university.admissions[index];
    const derived = deriveStatus(item.open, item.close);
    const admissions = university.admissions.map((a, i) => i === index ? { ...a, ...derived } : a);
    updateSelected({ ...university, admissions });
  }
  return (
    <div className="mt-6 rounded-[24px] border border-slate-100 bg-white p-5">
      <h3 className="text-xl font900">Application Timeline by Program</h3>
      <p className="mt-2 text-sm text-slate-600">Set opening/closing dates for Undergraduate, Graduate, and KLP/EAP. Use Auto Status to create green/yellow/red/gray public badges.</p>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {university.admissions.map((a, index) => <div key={a.program} className="rounded-2xl border border-slate-100 bg-[#F8FBFF] p-4">
          <AdminInput label="Program" value={a.program} onChange={(v) => updateAdmission(index, "program", v)} />
          <AdminInput label="Open Date" value={a.open} onChange={(v) => updateAdmission(index, "open", v)} />
          <AdminInput label="Close Date" value={a.close} onChange={(v) => updateAdmission(index, "close", v)} />
          <label className="admin-label">Status<select value={a.tone} onChange={(e) => { const tone = e.target.value as AdmissionTone; const status = tone === "open" ? "Application Open" : tone === "soon" ? "Opening Soon" : tone === "closed" ? "Admission Closed" : "Not fixed yet"; const admissions = university.admissions.map((old, i) => i === index ? { ...old, tone, status } : old); updateSelected({ ...university, admissions }); }} className="admin-input"><option value="open">Green - Application Open</option><option value="soon">Yellow - Opening Soon</option><option value="closed">Red - Admission Closed</option><option value="notfixed">Gray - Not fixed yet</option></select></label>
          <div className="mt-3 flex items-center justify-between"><span className={`admin-status ${a.tone}`}>{a.status}</span><button onClick={() => autoStatus(index)} className="rounded-xl bg-white px-3 py-2 text-xs font900 text-blue-700 shadow-sm">Auto Status</button></div>
        </div>)}
      </div>
    </div>
  );
}

function MediaEditor({ university, updateSelected }: { university: EditableUniversity; updateSelected: (u: EditableUniversity) => void }) {
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  async function uploadAsset(field: "logo" | "image" | "heroImage" | "accreditationBadge" | "brochureUrl", assetType: string, file?: File) {
    if (!file) return;
    const previewUrl = URL.createObjectURL(file);
    updateSelected({ ...university, [field]: previewUrl } as EditableUniversity);
    if (!API_URL) { setUploadMessage("Preview only: NEXT_PUBLIC_API_URL is missing."); return; }
    const form = new FormData();
    form.append("asset_type", assetType);
    form.append("file", file);
    try {
      const res = await fetch(`${API_URL}/api/admin/universities/${slugifyUniversity(university.name)}/upload`, { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      updateSelected({ ...university, [field]: data.url } as EditableUniversity);
      setUploadMessage(`Uploaded ${assetType.replace("_", " ")} permanently to Supabase Storage. Public pages will use it after refresh; click Save University Changes after editing text fields.`);
    } catch (err: any) {
      setUploadMessage(`Upload failed: ${err?.message || "check Supabase Storage bucket"}`);
    }
  }
  return (
    <div className="mt-6 rounded-[24px] border border-slate-100 bg-white p-5">
      <h3 className="text-xl font900">University Images, Logo & Links</h3>
      {uploadMessage && <div className="mt-3 rounded-2xl bg-blue-50 px-4 py-3 text-sm font900 text-blue-800">{uploadMessage}</div>}
      <div className="mt-4 grid gap-5 xl:grid-cols-3">
        <UploadBox label="University Logo / Seal" current={university.logo} onChange={(f) => uploadAsset("logo", "logo", f)} />
        <UploadBox label="Card Campus Image" current={university.image} onChange={(f) => uploadAsset("image", "card_image", f)} />
        <UploadBox label="Detail Hero Cover Image" current={university.heroImage} onChange={(f) => uploadAsset("heroImage", "hero_image", f)} />
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <AdminInput label="Official Homepage URL" value={university.homepage} onChange={(v) => updateSelected({ ...university, homepage: v })} />
        <AdminInput label="Brochure URL / PDF" value={university.brochureUrl} onChange={(v) => updateSelected({ ...university, brochureUrl: v })} />
        <AdminInput label="YouTube Video URL" value={university.youtubeUrl} onChange={(v) => updateSelected({ ...university, youtubeUrl: v })} />
        <AdminInput label="Facebook URL" value={university.facebookUrl} onChange={(v) => updateSelected({ ...university, facebookUrl: v })} />
        <AdminInput label="Instagram URL" value={university.instagramUrl} onChange={(v) => updateSelected({ ...university, instagramUrl: v })} />
        <AdminInput label="Contact Email" value={university.email} onChange={(v) => updateSelected({ ...university, email: v })} />
      </div>
    </div>
  );
}

function ImagesPanel(props: { items: EditableUniversity[]; selected: number; setSelected: (n: number) => void; selectedUniversity: EditableUniversity; updateSelected: (u: EditableUniversity) => void }) {
  return <div className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm"><h2 className="text-3xl font900">Images & Logos</h2><p className="mt-3 text-slate-600">Select a university and upload its logo, card image, detail hero image, gallery, accreditation badge, and social media links.</p><select value={props.selected} onChange={(e) => props.setSelected(Number(e.target.value))} className="admin-input mt-5 max-w-md">{props.items.map((u, i) => <option key={u.name} value={i}>{u.name}</option>)}</select><MediaEditor university={props.selectedUniversity} updateSelected={props.updateSelected} /></div>;
}

function AdmissionsPanel({ selectedUniversity, updateSelected }: { selectedUniversity: EditableUniversity; updateSelected: (u: EditableUniversity) => void }) {
  return <div className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm"><h2 className="text-3xl font900">Admission Deadlines</h2><p className="mt-3 text-slate-600">Edit opening dates, closing dates, admission status, intake round, and application links.</p><AdmissionsEditor university={selectedUniversity} updateSelected={updateSelected} /></div>;
}

function TuitionPanel({ items, selected, setSelected, selectedUniversity, updateSelected }: { items: EditableUniversity[]; selected: number; setSelected: (n: number) => void; selectedUniversity: EditableUniversity; updateSelected: (u: EditableUniversity) => void }) {
  const undergraduateText = selectedUniversity.topMajors?.join("\n") || "";
  const graduateText = selectedUniversity.graduatePrograms?.join("\n") || "";
  const languageText = selectedUniversity.klpPrograms?.join("\n") || "KLP\nEAP";

  function updateList(field: "topMajors" | "graduatePrograms" | "klpPrograms", value: string) {
    updateSelected({
      ...selectedUniversity,
      [field]: value.split("\n").map((item) => item.trim()).filter(Boolean),
    });
  }

  return (
    <div className="mt-8 space-y-6">
      <div className="rounded-[30px] border border-[#DCE6F4] bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font900 uppercase tracking-[.16em] text-[#2457D6]">Tuition & Scholarship Setup</p>
            <h2 className="mt-2 text-3xl font900">Select a university first</h2>
            <p className="mt-2 max-w-4xl text-sm leading-7 text-slate-600">
              Manage tuition by university, program, and major. Scholarship rules should be based on tuition only. Add separate notes for university/government scholarships when needed.
            </p>
          </div>
          <span className="rounded-2xl bg-blue-50 px-4 py-3 text-sm font900 text-blue-700">
            Editing: {selectedUniversity.name}
          </span>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {items.map((u, index) => (
            <button
              type="button"
              key={u.name}
              onClick={() => setSelected(index)}
              className={`group rounded-[24px] border p-4 text-left transition hover:-translate-y-1 hover:shadow-xl ${selected === index ? "border-[#2457D6] bg-blue-50 shadow-lg shadow-blue-100" : "border-[#DCE6F4] bg-white"}`}
            >
              <div className="flex items-center gap-3">
                <div className="h-16 w-16 shrink-0 overflow-hidden rounded-full border border-blue-100 bg-white shadow-sm">
                  {u.logo ? <img src={u.logo} alt={`${u.name} logo`} className="h-full w-full object-contain p-1" /> : <div className="grid h-full place-items-center text-xs font900 text-slate-400">Logo</div>}
                </div>
                <div>
                  <h3 className="line-clamp-2 text-base font900 leading-tight">{u.name}</h3>
                  <p className="mt-1 text-xs font800 text-slate-500">{u.location}</p>
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between rounded-2xl bg-white px-3 py-2 text-xs font900 text-slate-600">
                <span>{u.tuition || "Tuition not updated"}</span>
                <span className="text-blue-700">Edit →</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_.95fr]">
        <div className="rounded-[30px] border border-[#DCE6F4] bg-white p-6 shadow-sm">
          <div className="flex items-center gap-4 border-b border-slate-100 pb-5">
            <div className="h-20 w-20 overflow-hidden rounded-full border border-blue-100 bg-white shadow-sm">
              {selectedUniversity.logo ? <img src={selectedUniversity.logo} alt={`${selectedUniversity.name} logo`} className="h-full w-full object-contain p-1" /> : <div className="grid h-full place-items-center text-xs font900 text-slate-400">Logo</div>}
            </div>
            <div>
              <p className="text-xs font900 uppercase tracking-[.16em] text-[#2457D6]">Selected University</p>
              <h2 className="text-3xl font900">{selectedUniversity.name}</h2>
              <p className="mt-1 text-sm font800 text-slate-500">{selectedUniversity.location}</p>
            </div>
          </div>

          <div className="mt-6 grid gap-5 md:grid-cols-2">
            <AdminInput label="General Tuition Range" value={selectedUniversity.tuition} onChange={(v) => updateSelected({ ...selectedUniversity, tuition: v })} />
            <AdminInput label="Intake / Semester" value={selectedUniversity.intake} onChange={(v) => updateSelected({ ...selectedUniversity, intake: v })} />
          </div>

          <div className="mt-6 grid gap-5 lg:grid-cols-3">
            <label className="admin-label">
              Undergraduate majors and tuition notes
              <textarea
                value={undergraduateText}
                onChange={(e) => updateList("topMajors", e.target.value)}
                className="admin-textarea-v372"
                placeholder={"Global Business Administration - KRW ...\nGlobal Hospitality Management - KRW ..."}
              />
              <small className="admin-help-v372">Write one major per line. Add tuition amount beside each major if different.</small>
            </label>

            <label className="admin-label">
              Graduate majors and tuition notes
              <textarea
                value={graduateText}
                onChange={(e) => updateList("graduatePrograms", e.target.value)}
                className="admin-textarea-v372"
                placeholder={"Department of Global Business - KRW ...\nDepartment of Global Hospitality - KRW ..."}
              />
              <small className="admin-help-v372">Use this for Masters/Ph.D. program tuition by department.</small>
            </label>

            <label className="admin-label">
              Language programs
              <textarea
                value={languageText}
                onChange={(e) => updateList("klpPrograms", e.target.value)}
                className="admin-textarea-v372"
                placeholder={"KLP - Korean Language Program\nEAP - English Academic Purpose"}
              />
              <small className="admin-help-v372">KLP and EAP should be managed separately.</small>
            </label>
          </div>
        </div>

        <div className="rounded-[30px] border border-[#DCE6F4] bg-white p-6 shadow-sm">
          <p className="text-sm font900 uppercase tracking-[.16em] text-[#2457D6]">Scholarship Rules</p>
          <h2 className="mt-2 text-3xl font900">Tuition-based scholarship</h2>
          <p className="mt-2 text-sm leading-7 text-slate-600">
            Use this area as the rule guide for the calculator. The actual discount must apply only to tuition fee, not application fee or admission fee.
          </p>

          <div className="mt-6 space-y-4">
            <div className="rounded-[24px] border border-blue-100 bg-[#F8FBFF] p-5">
              <h3 className="font900">Undergraduate / Bachelor</h3>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <AdminInput label="GPA / %" value="Example: 2.5+ or 60%+" onChange={() => {}} />
                <AdminInput label="IELTS / TOPIK" value="Example: IELTS 5.5+" onChange={() => {}} />
                <AdminInput label="Scholarship %" value="Example: 30 / 50 / 70" onChange={() => {}} />
              </div>
            </div>

            <div className="rounded-[24px] border border-blue-100 bg-[#F8FBFF] p-5">
              <h3 className="font900">Graduate / Masters / Ph.D.</h3>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <AdminInput label="GPA / %" value="Example: 3.0+ or 70%+" onChange={() => {}} />
                <AdminInput label="IELTS / TOPIK" value="Example: IELTS 6.0+" onChange={() => {}} />
                <AdminInput label="Scholarship %" value="Example: 30 / 50 / 70" onChange={() => {}} />
              </div>
            </div>

            <div className="rounded-[24px] border border-blue-100 bg-[#F8FBFF] p-5">
              <h3 className="font900">KLP / EAP</h3>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <AdminInput label="KLP condition" value="TOPIK optional / Korean language track" onChange={() => {}} />
                <AdminInput label="EAP condition" value="IELTS 4.0 or 5.0 depending on university" onChange={() => {}} />
              </div>
            </div>

            <label className="admin-label">
              Other scholarship notes
              <textarea
                className="admin-textarea-v372 min-h-[120px]"
                placeholder="Example: Government scholarship, university special scholarship, nationality-based scholarship, early registration discount..."
                defaultValue=""
              />
              <small className="admin-help-v372">Use this for any extra university or government scholarships. These notes are separate from the tuition calculator.</small>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

function ApplicationsPanel() {
  return <div className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm"><div className="flex flex-wrap justify-between gap-3"><h2 className="text-3xl font900">Student Applications</h2><button className="rounded-2xl bg-[#061A40] px-5 py-3 text-sm font900 text-white">Export CSV</button></div><div className="mt-6 overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-[#F4F7FC] text-slate-600"><tr>{["Applicant", "University", "Program", "Status", "Current Step", "Actions"].map(h => <th key={h} className="px-4 py-3 font900">{h}</th>)}</tr></thead><tbody>{applications.map((row) => <tr key={row[0]} className="border-b border-slate-100">{row.map((cell) => <td key={cell} className="px-4 py-4 font800">{cell}</td>)}<td className="px-4 py-4"><button className="rounded-xl bg-blue-50 px-4 py-2 font900 text-blue-700">Open</button></td></tr>)}</tbody></table></div></div>;
}

function GenericPanel({ title, description, items }: { title: string; description: string; items: string[] }) { return <div className="mt-8 rounded-[28px] border border-[#DCE6F4] bg-white p-6 shadow-sm"><h2 className="text-3xl font900">{title}</h2><p className="mt-3 text-slate-600">{description}</p><div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{items.map((item) => <div key={item} className="rounded-2xl border border-slate-100 bg-[#F8FBFF] p-5"><p className="font900">{item}</p><button className="mt-4 rounded-xl bg-white px-4 py-2 text-sm font900 text-blue-700 shadow-sm">Edit</button></div>)}</div></div>; }
function AdminBox({ title, children }: { title: string; children: React.ReactNode }) { return <div className="rounded-[24px] border border-slate-100 bg-white p-5"><h3 className="text-xl font900">{title}</h3><div className="mt-4 space-y-3">{children}</div></div>; }
function AdminInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label className="admin-label">{label}<input value={value} onChange={(e) => onChange(e.target.value)} className="admin-input" /></label>; }
function UploadBox({ label, current, onChange }: { label: string; current: string; onChange: (file?: File) => void }) { return <label className="rounded-[24px] border border-dashed border-blue-200 bg-[#F8FBFF] p-5"><span className="text-sm font900 text-slate-700">{label}</span><div className="mt-3 h-28 overflow-hidden rounded-2xl bg-white flex items-center justify-center border border-slate-100">{current ? <img src={current} alt={label} className="h-full w-full object-cover" /> : <span>No image</span>}</div><input type="file" accept="image/*,.pdf" onChange={(e) => onChange(e.target.files?.[0])} className="mt-4 block w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm" /><button type="button" className="mt-3 rounded-xl bg-[#061A40] px-4 py-2 text-xs font900 text-white">Upload / Preview</button></label>; }
