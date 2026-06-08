import KuaLogo from "./KuaLogo";

export default function Footer() {
  return (
    <>
      <section className="credentials-section streamlit-match">
        <div className="credentials-grid">
          <div className="credential-card"><img className="credential-img" src="/assets/official_representative_verified.png" alt="Official representative"/><h3>Trusted Partnerships</h3><div className="credential-line"/><p>Work with verified universities and trusted education partners.</p></div>
          <div className="credential-card"><img className="credential-img" src="/assets/certified_information_badge_custom.png" alt="Certified information"/><h3>Certified Information</h3><div className="credential-line"/><p>Access up-to-date admission requirements and fee details you can trust.</p></div>
          <div className="credential-card"><img className="credential-img" src="/assets/eligibility_ieee_logo.png" alt="Awarded badge"/><h3>Awarded by IEEE</h3><div className="credential-line"/><p>Recognized for excellence in technology and education partnerships.</p></div>
          <div className="credential-card"><img className="credential-img" src="/assets/kladi_badge_gold_transparent.png" alt="Scholarship support"/><h3>Scholarship Support</h3><div className="credential-line"/><p>Discover and maximize scholarship opportunities to achieve your dreams.</p></div>
        </div>
      </section>
      <footer className="premium-footer streamlit-footer">
        <div className="footer-map-bg" />
        <div className="premium-footer-grid">
          <div className="footer-brand">
            <div className="footer-brand-row"><KuaLogo /><h3>Korea University<br/>Admissions</h3></div>
            <div className="footer-blue-line" />
            <p>Empowering global education partnerships and connecting students with the right opportunities across Korea.</p>
          </div>
          <div className="footer-contact-card"><div className="footer-contact-icon">☎</div><h4>Phone</h4><div className="footer-blue-line small"/><b>+82 51 711 2773</b><p>Mon – Fri, 9:00 AM – 6:00 PM (KST)</p></div>
          <div className="footer-contact-card"><div className="footer-contact-icon">✉</div><h4>Email</h4><div className="footer-blue-line small"/><b>koreastudypartner@gmail.com</b><p>We’ll get back to you as soon as possible.</p></div>
          <div className="footer-contact-card"><div className="footer-contact-icon">⌖</div><h4>Location</h4><div className="footer-blue-line small"/><b>Busan, Republic of Korea</b><p>Our headquarters in the heart of Busan.</p></div>
        </div>
        <div className="premium-footer-bottom"><p>© 2026 Korea University Admissions KUA. All rights reserved.</p><div><span>Privacy Policy</span><span>Terms of Use</span><span>Help Center</span><span>Follow us</span></div></div>
      </footer>
    </>
  );
}
