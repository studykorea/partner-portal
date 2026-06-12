export type AdmissionTone = "open" | "soon" | "closed" | "notfixed";

export type AdmissionTimeline = {
  program: string;
  open?: string;
  close?: string;
  status: string;
  tone: AdmissionTone | string;
};

export type University = {
  slug?: string;
  name: string;
  location: string;
  students: string;
  internationalStudents: string;
  topMajors: string[];
  graduatePrograms?: string[];
  klpPrograms?: string[];
  intake: string;
  tuition: string;
  overview: string;
  image: string;
  logo?: string;
  heroImage?: string;
  videoImage?: string;
  videoUrl?: string;
  brochureUrl?: string;
  facebookUrl?: string;
  instagramUrl?: string;
  youtubeUrl?: string;
  accreditation?: string;
  accreditationBadge?: string;
  type?: string;
  established?: string;
  email?: string;
  homepage: string;
  region: string;
  address: string;
  phone: string;
  admissions: AdmissionTimeline[];
};

export const universities: University[] = [
  {
    name: "Kyungsung University",
    location: "Busan",
    students: "10,000–15,000",
    internationalStudents: "1,966",
    topMajors: ["Global Business Administration", "Global Hospitality Management", "Global Korean Studies", "Global Mechanical Design Engineering", "Global IT Engineering"],
    graduatePrograms: ["Department of Global Business", "Department of Global Hospitality", "Department of Korean Culture and Education", "Department of International Studies", "Department of Global IT Engineering", "Department of Digital Marketing"],
    klpPrograms: ["D4-1 (4 semester)", "Korean Language Program", "KLP / EAP"],
    intake: "March, September",
    tuition: "KRW 3,396,000–5,856,000 per semester",
    overview: "Kyungsung University, located in the vibrant city of Busan, is a private university committed to fostering global talent and innovation.",
    image: "/assets/kyungsung.webp",
    logo: "/assets/ksu_logo.svg",
    heroImage: "/assets/kyungsung.webp",
    videoImage: "/assets/kyungsung.webp",
    homepage: "ks.ac.kr",
    region: "Busan",
    address: "309 Suyeong-ro, Nam-gu, Busan, Republic of Korea, 48434",
    phone: "051-663-4114",
    type: "Private University",
    established: "Not updated",
    accreditation: "IEQAS Excellent Accredited",
    email: "koreastudypartner@gmail.com",
    admissions: [
      { program: "Undergraduate", open: "19 May 2026", close: "30 May 2026", status: "Admission Closed", tone: "closed" },
      { program: "Graduate (Masters/Ph.D.)", open: "15 May 2026", close: "05 Jun 2026", status: "Admission Closed", tone: "closed" },
      { program: "KLP / EAP", open: "18 May 2026", close: "29 May 2026", status: "Admission Closed", tone: "closed" },
    ],
  },
  {
    name: "Jeonbuk National University",
    location: "Jeonju, Republic of Korea",
    students: "20,000–25,000",
    internationalStudents: "1,112",
    topMajors: ["Glocal Commerce", "K-Entertainment", "Korean Language"],
    intake: "March, September",
    tuition: "KRW 2,016,000–4,048,000 per semester",
    overview: "A leading national university with strong academic reputation and research-oriented programs.",
    image: "/assets/jeonbuk.webp",
    logo: "/assets/jbnu_logo.svg",
    heroImage: "/assets/jeonbuk.webp",
    homepage: "www.jbnu.ac.kr",
    region: "Jeolla",
    address: "567 Baekje-daero, Deokjin-gu, Jeonju-si, Jeollabuk-do, Republic of Korea, 54896",
    phone: "063-270-2114",
    type: "National University",
    established: "Not updated",
    accreditation: "Accredited",
    admissions: [
      { program: "Undergraduate", open: "19 May 2026", close: "30 May 2026", status: "Admission Closed", tone: "closed" },
      { program: "Graduate (Masters/Ph.D.)", open: "15 May 2026", close: "05 Jun 2026", status: "Admission Closed", tone: "closed" },
      { program: "KLP / EAP", open: "18 May 2026", close: "29 May 2026", status: "Admission Closed", tone: "closed" },
    ],
  },
  {
    name: "Kyungwoon University",
    location: "Gumi, Republic of Korea",
    students: "5,000–10,000",
    internationalStudents: "909",
    topMajors: ["Global Business Administration", "Global Korean Studies", "Software / IT"],
    intake: "March, September",
    tuition: "KRW 4,120,000 per semester",
    overview: "A specialized university known for aviation, engineering, and applied professional education.",
    image: "/assets/kyungwoon.webp",
    logo: "/assets/kwu_logo.svg",
    heroImage: "/assets/kyungwoon.webp",
    homepage: "www.ikw.ac.kr",
    region: "Gyeongsang",
    address: "730 Gangdong-ro, Sandong-eup, Gumi-si, Gyeongsangbuk-do, Republic of Korea, 39160",
    phone: "054-479-1114",
    type: "Partner University",
    established: "Not updated",
    accreditation: "Accredited",
    admissions: [
      { program: "Undergraduate", status: "Not fixed yet", tone: "notfixed" },
      { program: "Graduate (Masters/Ph.D.)", status: "Not fixed yet", tone: "notfixed" },
      { program: "KLP / EAP", status: "Not fixed yet", tone: "notfixed" },
    ],
  },
  {
    name: "Sejong University",
    location: "Seoul, Republic of Korea",
    students: "15,000–20,000",
    internationalStudents: "2,844",
    topMajors: ["Division of Global Leadership", "Department of Public Administration", "Department of Media and Communication", "Faculty of Business Administration", "Department of Economics"],
    intake: "March, September",
    tuition: "KRW 4,669,000–8,367,000 per semester",
    overview: "A well-known university in Seoul with strong programs in hospitality, tourism, business, and technology.",
    image: "/assets/sejong.webp",
    logo: "/assets/sju_logo.svg",
    heroImage: "/assets/sejong.webp",
    homepage: "www.sejong.ac.kr",
    region: "Seoul",
    address: "209 Neungdong-ro, Gwangjin-gu, Seoul, Republic of Korea, 05006",
    phone: "02-3408-3114",
    type: "Partner University",
    established: "Not updated",
    accreditation: "Accredited",
    admissions: [
      { program: "Undergraduate", status: "Not fixed yet", tone: "notfixed" },
      { program: "Graduate (Masters/Ph.D.)", status: "Not fixed yet", tone: "notfixed" },
      { program: "KLP / EAP", status: "Not fixed yet", tone: "notfixed" },
    ],
  },
  {
    name: "Youngsan University",
    location: "Yangsan / Haeundae, Republic of Korea",
    students: "2,000–5,000",
    internationalStudents: "842",
    topMajors: ["Department of Hotel and Tourism", "Department of Airline and Tourism", "Department of Tourism and Convention", "Department of Logistics Management", "Global Culinary Major"],
    intake: "March, September",
    tuition: "KRW 3,131,000–3,400,000 per semester",
    overview: "A practice-oriented university with strong hospitality, tourism, and service management programs.",
    image: "/assets/youngsan.webp",
    logo: "/assets/ysu_logo.svg",
    heroImage: "/assets/youngsan.webp",
    homepage: "www.ysu.ac.kr",
    region: "Busan",
    address: "142 Bansongsunhwan-ro, Haeundae-gu, Busan, Republic of Korea, 48015",
    phone: "051-540-7000",
    type: "Partner University",
    established: "Not updated",
    accreditation: "Accredited",
    admissions: [
      { program: "Undergraduate", status: "Not fixed yet", tone: "notfixed" },
      { program: "Graduate (Masters/Ph.D.)", status: "Not fixed yet", tone: "notfixed" },
      { program: "KLP / EAP", status: "Not fixed yet", tone: "notfixed" },
    ],
  },
];


const fallbackBySlug: Record<string, Partial<University>> = {
  "kyungsung-university": { image: "/assets/kyungsung.webp", logo: "/assets/ksu_logo.svg", heroImage: "/assets/kyungsung.webp" },
  "jeonbuk-national-university": { image: "/assets/jeonbuk.webp", logo: "/assets/jbnu_logo.svg", heroImage: "/assets/jeonbuk.webp" },
  "kyungwoon-university": { image: "/assets/kyungwoon.webp", logo: "/assets/kwu_logo.svg", heroImage: "/assets/kyungwoon.webp" },
  "sejong-university": { image: "/assets/sejong.webp", logo: "/assets/sju_logo.svg", heroImage: "/assets/sejong.webp" },
  "youngsan-university": { image: "/assets/youngsan.webp", logo: "/assets/ysu_logo.svg", heroImage: "/assets/youngsan.webp" },
};

function isMissingAsset(value?: string) {
  return !value || value === "Logo" || value === "University image" || value === "Not updated";
}

export function hydrateUniversityAssets(item: University): University {
  const slug = item.slug || slugifyUniversity(item.name || "University");
  const fallback = fallbackBySlug[slug] || {};
  return {
    ...item,
    slug,
    image: isMissingAsset(item.image) ? (fallback.image || "/assets/kyungsung.webp") : item.image,
    logo: isMissingAsset(item.logo) ? fallback.logo : item.logo,
    heroImage: isMissingAsset(item.heroImage) ? (fallback.heroImage || fallback.image || item.image) : item.heroImage,
  };
}

export function slugifyUniversity(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

export async function fetchUniversities(): Promise<University[]> {
  if (!API_URL) return universities;
  try {
    const res = await fetch(`${API_URL}/api/universities`, { cache: "no-store" });
    if (!res.ok) return universities;
    const data = await res.json();
    return Array.isArray(data.items) && data.items.length ? data.items.map(hydrateUniversityAssets) : universities;
  } catch {
    return universities;
  }
}

export async function fetchUniversity(slug: string): Promise<University> {
  if (API_URL) {
    try {
      const res = await fetch(`${API_URL}/api/universities/${slug}`, { cache: "no-store" });
      if (res.ok) return hydrateUniversityAssets(await res.json());
    } catch {}
  }
  return hydrateUniversityAssets(universities.find((item) => slugifyUniversity(item.name) === slug) ?? universities[0]);
}
