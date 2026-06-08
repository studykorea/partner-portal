# KUA Fast Next.js + FastAPI v345

This version corrects the previous visual mismatch. It restores the KUA / Korea University Admissions branding and rebuilds the Universities page closer to the original Streamlit reference screenshots.

Updated:
- Kept KUA / Korea University Admissions branding.
- Removed wrong UniQuest API name from the FastAPI metadata.
- Rebuilt `/universities` with original-style university cards.
- Added circular university seal/logo placeholders for each card.
- Added Kyungsung University detailed profile section: About card, campus video preview, application deadlines, statistic ribbon, top programs, why choose, quick facts.
- Fixed the blue statistic ribbon so numbers/icons do not overlap.
- Rebuilt `/application-status` closer to the mobile status/timeline reference design.
- Verified `npm run build` succeeds.

Note:
- Actual university logo image files were not included in the uploaded project, so this version uses clean circular seal-style logo placeholders. Replace them with real logo images later by adding logo paths in `lib/universities.ts`.
