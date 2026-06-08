type Props = {
  name: string;
  shortName?: string;
  size?: "sm" | "md" | "lg";
};

const shortMap: Record<string, string> = {
  "Kyungsung University": "KSU",
  "Jeonbuk National University": "JBNU",
  "Kyungwoon University": "KWU",
  "Sejong University": "SJU",
  "Youngsan University": "YSU",
};

export default function UniversitySeal({ name, shortName, size = "md" }: Props) {
  const code = shortName || shortMap[name] || name.split(" ").map((w) => w[0]).slice(0, 3).join("").toUpperCase();
  return (
    <div className={`university-seal university-seal-${size}`} aria-label={`${name} logo`}>
      <div className="seal-ring-text">{name.replace(" University", "")}</div>
      <div className="seal-inner-shield">★<span>{code}</span></div>
    </div>
  );
}
