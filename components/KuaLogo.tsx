export default function KuaLogo({ className = "" }: { className?: string }) {
  return (
    <div className={`kua-logo-mark ${className}`} aria-label="KUA logo">
      <span>KUA</span>
    </div>
  );
}
