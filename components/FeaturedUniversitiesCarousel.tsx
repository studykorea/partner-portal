"use client";

import { useEffect, useMemo, useRef } from "react";
import UniversityCard from "./UniversityCard";
import type { University } from "../lib/universities";

export default function FeaturedUniversitiesCarousel({ universities }: { universities: University[] }) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const loopItems = useMemo(() => [...universities, ...universities], [universities]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || universities.length === 0) return;

    let frame = 0;
    let lastTime = 0;
    const pixelsPerSecond = 84; // visible movement, smooth continuous sliding

    const animate = (time: number) => {
      if (!lastTime) lastTime = time;
      const delta = time - lastTime;
      lastTime = time;

      el.scrollLeft += (pixelsPerSecond * delta) / 1000;

      const halfway = el.scrollWidth / 2;
      if (el.scrollLeft >= halfway) {
        el.scrollLeft = 0;
      }

      frame = window.requestAnimationFrame(animate);
    };

    el.scrollLeft = 0;
    frame = window.requestAnimationFrame(animate);

    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [universities.length]);

  return (
    <div className="home-featured-carousel-shell">
      <div className="home-featured-carousel-scroll" ref={scrollRef}>
        <div className="home-featured-carousel-track-js">
          {loopItems.map((university, index) => (
            <div className="home-featured-carousel-item" key={`${university.name}-${index}`}>
              <UniversityCard university={university} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
