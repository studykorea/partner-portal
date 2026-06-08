# KUA fast Next.js migration v347

This version corrects the visual mismatch reported after v346.

Updated:
- Home featured university carousel height increased so full cards and buttons are visible.
- University cards expanded so statistics, programs, and View Programs button are not cut off.
- Universities hero section restored with campus image slide/collage on the right side.
- Added seal-style SVG university logo image files for KSU, JBNU, KWU, SJU, and YSU.
- Footer restored closer to the Streamlit reference by adding badge image cards and a world-map background layer.
- Next.js production build verified successfully.

Render frontend settings:
- Root Directory: empty
- Build Command: npm install && npm run build
- Start Command: npm run start

After upload, use Manual Deploy > Clear build cache & deploy.
