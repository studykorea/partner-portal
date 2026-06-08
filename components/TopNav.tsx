import Link from "next/link";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/universities", label: "Universities" },
  { href: "/eligibility", label: "Eligibility Check" },
  { href: "/tuition", label: "Tuition & Scholarship" },
  { href: "/contact", label: "Contact Us" },
];

export default function TopNav() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/95 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1720px] items-center justify-between px-5 py-3 lg:px-8">
        <Link href="/" className="flex items-center gap-3">
          <img src="/assets/uniquest_logo.webp" alt="UniQuest" className="h-10 w-10 rounded-xl object-contain" />
          <span>
            <span className="block text-base font900 tracking-tight text-[#061A40]">Partner Portal</span>
            <span className="block text-xs font700 text-slate-500">University Recruitment</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-2 text-sm font800 text-slate-700 lg:flex">
          {navItems.map((item, idx) => (
            <Link key={item.href} href={item.href} className="rounded-full px-4 py-2 hover:bg-blue-50 hover:text-blue-700">
              {idx === 0 ? "Step 1  " : ""}{item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link href="/apply" className="hidden rounded-full border border-blue-200 px-4 py-2 text-sm font900 text-blue-700 hover:bg-blue-50 md:inline-flex">Apply for Partner Access</Link>
          <Link href="/login" className="rounded-full bg-[#2457D6] px-5 py-2.5 text-sm font900 text-white shadow-lg shadow-blue-700/20 hover:bg-blue-700">Login</Link>
        </div>
      </div>
    </header>
  );
}
