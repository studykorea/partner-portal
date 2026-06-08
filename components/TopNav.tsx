import Link from "next/link";
import KuaLogo from "./KuaLogo";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/universities", label: "Universities" },
  { href: "/eligibility", label: "Eligibility Check" },
  { href: "/tuition", label: "Tuition Fees" },
  { href: "/contact", label: "Contact Us" },
  { href: "/contact", label: "MoU Contact" },
];

export default function TopNav() {
  return (
    <header className="nav-shell">
      <div className="nav-inner">
        <Link href="/" className="brand-link" aria-label="Korea University Admissions home">
          <KuaLogo />
          <span>
            <strong>Korea University</strong>
            <small>Admissions</small>
          </span>
        </Link>
        <nav className="nav-menu">
          {navItems.map((item) => (
            <Link key={`${item.href}-${item.label}`} href={item.href} className="nav-item">{item.label}</Link>
          ))}
        </nav>
        <div className="nav-actions">
          <Link href="/login" className="nav-login-btn"><span>👤</span>Login</Link>
          <Link href="/apply" className="nav-signup-btn"><span>👥</span>Partner Sign Up</Link>
        </div>
      </div>
    </header>
  );
}
