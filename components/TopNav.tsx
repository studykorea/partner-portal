import Link from "next/link";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/universities", label: "Universities" },
  { href: "/partner-dashboard", label: "Partner Dashboard" },
  { href: "/admin", label: "Admin" },
];

export default function TopNav() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 lg:px-8">
        <Link href="/" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-950 text-sm font-black text-white">UQ</span>
          <span>
            <span className="block text-base font-black tracking-tight text-slate-950">UniQuest</span>
            <span className="block text-xs font-medium text-slate-500">Partner Portal</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-7 text-sm font700 text-slate-700 md:flex">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href} className="hover:text-blue-700">
              {item.label}
            </Link>
          ))}
        </nav>
        <Link href="/login" className="rounded-full bg-blue-700 px-5 py-2.5 text-sm font800 text-white shadow-lg shadow-blue-700/20 hover:bg-blue-800">
          Login
        </Link>
      </div>
    </header>
  );
}
