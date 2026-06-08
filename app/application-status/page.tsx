import TopNav from "../../components/TopNav";
import Footer from "../../components/Footer";
import UniversitySeal from "../../components/UniversitySeal";

const steps = [
  ["Application Submitted", "Your application has been submitted successfully.", "10 Apr 2025", "10:30 AM", "done"],
  ["University Received Your Application", "Kyungsung University has received your application.", "11 Apr 2025", "02:15 PM", "done"],
  ["Application Number Issued", "Your application number has been generated.", "12 Apr 2025", "11:05 AM", "done"],
  ["Interview Date Announced", "Your interview date will be announced soon.", "14 Apr 2025", "09:00 AM", "current"],
  ["Interview Completed", "Complete your interview as per the schedule.", "-", "", "next"],
  ["Admission Result Released", "The admission result will be released.", "-", "", "next"],
];
export default function StatusPage() {
  return (
    <main className="min-h-screen bg-[#F6F9FE]"><TopNav />
      <section className="kua-mobile-status-shell">
        <div className="status-phone-card">
          <div className="status-phone-top"><span>‹</span><h1>Application Status</h1><b>🔔</b></div>
          <div className="status-summary-card"><UniversitySeal name="Kyungsung University" size="lg" /><dl><dt>Applicant</dt><dd>Aaray Sharma</dd><dt>University</dt><dd>Kyungsung University</dd><dt>Program</dt><dd>Global Hospitality Management</dd><dt>Status</dt><dd><em>In Progress</em></dd></dl></div>
          <div className="status-timeline">
            {steps.map(([title, desc, date, time, state], idx) => <div key={title} className={`status-step ${state}`}><div className="status-dot">{state === "done" ? "✓" : state === "current" ? "◷" : idx + 1}</div><div className="status-step-body"><div><h3>{idx + 1}. {title}</h3><p>{desc}</p>{state === "current" && <strong>Current Step</strong>}</div><aside><b>{date}</b><span>{time}</span></aside></div></div>)}
          </div>
          <button className="status-full-btn">▣ View Full Status</button>
          <div className="status-help"><span>🛡</span><div><b>Need Help?</b><p>Contact our support team</p></div><i>›</i></div>
        </div>
      </section><Footer /></main>
  );
}
