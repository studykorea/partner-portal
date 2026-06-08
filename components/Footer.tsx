export default function Footer() {
  return (
    <footer className="bg-[#061A40] text-white">
      <div className="mx-auto grid max-w-[1720px] gap-10 px-5 py-12 lg:grid-cols-[1.1fr_.9fr_.9fr] lg:px-8">
        <div>
          <div className="flex items-center gap-3">
            <img src="/assets/uniquest_logo_footer.webp" alt="UniQuest" className="h-12 w-12 rounded-xl object-contain" />
            <h3 className="text-2xl font900 leading-tight">Partner Portal for<br />University Recruitment</h3>
          </div>
          <div className="mt-5 h-1 w-16 rounded-full bg-blue-400" />
          <p className="mt-5 max-w-md text-sm leading-7 text-blue-100">Empowering global education partnerships and connecting students with the right opportunities worldwide.</p>
        </div>
        <div>
          <h4 className="font900">Quick Access</h4>
          <div className="mt-4 grid gap-3 text-sm text-blue-100">
            <a href="/universities">Universities Information</a>
            <a href="/eligibility">Eligibility Check</a>
            <a href="/tuition">Tuition & Scholarship</a>
            <a href="/login">Partner Dashboard</a>
          </div>
        </div>
        <div>
          <h4 className="font900">Partner Support</h4>
          <p className="mt-4 text-sm leading-7 text-blue-100">Detailed admission information, eligibility checking, tuition calculation, and application management are available only for approved partners.</p>
          <div className="mt-5 flex gap-2 text-xs font900"><span className="rounded-full bg-white/10 px-3 py-2">Privacy Policy</span><span className="rounded-full bg-white/10 px-3 py-2">Terms of Use</span><span className="rounded-full bg-white/10 px-3 py-2">Help Center</span></div>
        </div>
      </div>
      <div className="border-t border-white/10 px-5 py-5 text-center text-xs text-blue-100">© 2026 Partner Portal for University Recruitment. All rights reserved.</div>
    </footer>
  );
}
