# UniQuest Partner Portal v11 Polished Clickable

This version fixes:
- No left sidebar on public pages
- Top menu is fully clickable using real Streamlit buttons
- University cards have clickable View Details buttons
- Layout is cleaner and closer to the reference concept
- Partner dashboard, universities, eligibility, tuition, contact, and admin pages are included
- White background uses black/navy text
- Navy background uses white text

Run:
```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Local test admin:
- Username: admin
- Password: admin123!

v12: fixed login/signup blank spacing, added clickable CTA/footer buttons, improved top spacing and logo size.


v13 updates:
- Removed Step 1 badge.
- Removed fake HTML hero buttons.
- Only real clickable Streamlit buttons are shown.
- Enlarged logo.
- Updated contact number and email.


v14:
- Footer contact information fully replaced.
- Hero fake buttons removed.
- Real clickable hero buttons visually placed on the navy hero area.
- Updated contact info: +82 51 711 2773 / uniqueststudy@gmail.com / Busan, Republic of Korea.


v15:
- Fixed admin login error caused by Streamlit interpreting inline conditional expression.
- Reduced blank space above admin dashboard.
- Reconfirmed footer contact information.


v16:
- Removed excessive blank space above admin dashboard.
- Simplified footer by removing Quick Links, Partnership Inquiries, and Follow Us.
- Footer now shows only UniQuest brand and Contact Us section.
- Added Contact Us inquiries to Admin Dashboard.


v17:
- Added uploaded UniQuest logo to the top header.
- Added UniQuest logo to the footer.
- Footer simplified and neatly aligned with brand + contact info only.
- Removed excessive admin top blank space.
- Admin dashboard shows Recent Contact Inquiries.


v18:
- Fixed footer HTML showing as text.
- Removed Registration Number / ID from partner sign-up.
- Reduced top blank space in admin and logged-in pages.
- Reconfirmed footer contact information.
- Admin dashboard includes Recent Contact Inquiries.


v19:
- Changed phone format to +82 51 711 2773.
- Redesigned approved partner dashboard with hero section, statistics, quick actions, and featured universities.


v20:
- Added user-provided university images.
- Home and Universities pages now show cropped uniform photos.
- University list limited to Kyungsung, Jeonbuk National, Kyungwoon, Sejong, and Youngsan.
- Other university information removed from sample data.


v21:
- Fixed footer contact showing as raw HTML code.
- Removed bottom duplicated navigation tabs.
- Aligned top navigation buttons vertically with the UniQuest logo.
- Contact number set to +82 51 711 2773.


v22:
- Added basic university information from University Alert screenshots.
- Added homepage, address, phone, fax, region, school size, and international student count.
- University information page now shows only basic information + foreign student count.


v23:
- Changed Korean school size values to English.
- Fixed footer Contact Us showing as raw HTML code.
- Footer text forced to white on navy background.


v24:
- Converted university basic information values to English.
- Region, address, school size, and foreign student count are now English-formatted.
- Footer Contact Us fixed to render as normal visible text, not raw HTML/code.


v25:
- Integrated uploaded Excel file: Universitieds information.xlsx.
- Updated English-track departments/majors, IELTS criteria, GPA/% criteria, application fee, admission fee, and tuition fee per semester.
- Eligibility now uses uploaded GPA and IELTS criteria.
- Tuition page now uses uploaded fee data and does not guess scholarship rules.
- Scholarship column was not present in the uploaded Excel file; therefore scholarship is shown as not provided.


v26:
- Removed UniQuest logo from header and footer.
- Site branding changed to plain text: Partner Portal for University Recruitment.
- Home hero now uses the newly uploaded Kyungsung University photo.
- CTA buttons moved upward into the hero area as white/navy tab-style buttons.
- Footer simplified to site name + contact details only.
- Kyungsung University information photo updated.


v27:
- Fixed hero duplicate/ghost text.
- Used the second uploaded Kyungsung photo for home hero and Kyungsung info.
- Moved hero action buttons upward into the blue/photo hero area.
- Changed site name to two lines in the header and moved Home nav closer left.
- Removed logo branding from header/footer.


v28:
- Added three-level role structure: UniQuest Admin, Agency Representative, Agency Staff.
- Partner sign-up now includes Account Type and Agency Name.
- Agency Representative dashboard can view agency-wide eligibility logs and staff activity.
- Agency Staff dashboard can view only their own records.
- UniQuest Admin can still view all accounts and all logs.
- Eligibility and tuition logs now save agency_id and checked_by_name.


v29:
- Removed Agency Code from partner sign-up.
- Accounts are connected by Agency Name only.
- Agency Representative can view records from users under the same Agency Name / agency_id.


v30:
- Agency Name is now a dropdown for KIEC and Realize Education.
- Other / New Agency can still manually enter an agency name.
- Agency Code remains removed.
- Agency Representative and Agency Staff are linked by the normalized Agency Name / agency_id.


v31:
- Home hero uses the newly provided first image (Korean flag/campus scene).
- Removed Kyungsung photo from home hero.
- Site title color and header spacing improved.
- Hero action buttons moved upward inside the hero area.
- Universities page now shows clean equal-size basic information cards only.
- Removed English Track Programs / Criteria / Fees table from university information page.
- Program/criteria/fee details are moved toward Eligibility Check result output.
- University photos are full-width cover images without side white gaps.


v32:
- Corrected Kyungsung University image to the newly uploaded campus panorama.
- Home hero uses Korean flag/campus scene while Kyungsung university cards/info use Kyungsung campus photo.
- Removed English Track Programs / Criteria / Fees table from University Information page.
- University information photos are full-width cover images with no side white gaps.
- Basic information cards are equal height and aligned.
- Site title color/readability fixed.
- Eligibility Check results display program/criteria/fee information.


v33:
- Forced the main hero title to white using inline style and final CSS override.
- Replaced Kyungsung University image with the newly provided panorama image.
- Saved Kyungsung image in higher quality for university cards and university information page.
- Increased university information image height and ensured full-width cover layout.


v34:
- Aligned Create Password and Confirm Password side by side in partner sign-up.
- Fixed Admin Dashboard Partner Approval Requests to show pending Agency Representative and Agency Staff accounts.
- Added Approve and Reject buttons directly in Admin Dashboard.
- Partner Management now hides password_hash and displays cleaner user columns.


v35:
- Fixed Admin login crash caused by incorrect admin_shell function name.
- Admin Dashboard now uses the existing dash_shell layout.
- Partner Management still hides password_hash.


v36:
- Eligibility Check now supports IELTS, TOEFL iBT, and New TOEFL.
- Korean Language Program does not require an English score.
- Eligibility results are shown as polished cards with University, Department/Major, PASS status, criteria, and fee information.
- Raw Excel-style result table removed from Eligibility Check.
- Tuition page redesigned to show clean fee summary cards instead of raw data-like display.


v37:
- Tuition page major dropdown now updates dynamically when University or Program changes.
- User does not need to click View Fee Information before the major list changes.
- Fee result remains card-style, not Excel-style.
- Featured University cards now use fixed equal height.
- University card image height is fixed for all schools, including Youngsan University.
- Improved Jeonbuk and Youngsan image export quality when source images are available.
- Note: page refresh still logs out in this Streamlit MVP because login is stored in session_state. Production should use DB-backed authentication and cookies/sessions.


v38:
- Replaced Jeonbuk National University photo with the newly uploaded JBN U campus image.
- Optimized the image for website cards and university information pages.


v39:
- Replaced Jeonbuk National University image with the newly uploaded night campus photo.
- Optimized cropping and quality for both the Featured Universities card and the university information page.


v40:
- Removed Student Name from Tuition Fees page.
- Removed form behavior from Tuition Fees page so University/Program changes immediately update Major dropdown.
- Fee Summary card updates automatically without needing to click View Fee Information first.
- Added optional Save Fee Check Record button for logging.


v41:
- Integrated uploaded scholarship rules Excel as data/scholarship_rules.csv.
- Eligibility Check now requires Student Full Name before search.
- Language Score Type updates score input immediately outside of a form.
- Added TOPIK option and kept Korean Language Program score-free.
- Eligibility results now calculate scholarship percent and final tuition based on available rules.
- University information pages now include available Undergraduate, Graduate, and Korean Language Program majors.


v42:
- Removed Excel/internal database explanatory text from Eligibility and Tuition pages.
- Removed the major-list explanatory note from Tuition page.
- Removed Save Fee Check Record button from Tuition page.
- Forced the university name in the fee result header to white for readability.


v43:
- Hides blank / not-provided fields instead of displaying 'Not provided'.
- Removes Korean Language Program box when information is not provided.
- Hides Scholarship card/field when scholarship information is not available.
- Cleans duplicate commas in Scholarship Criteria and language criteria text.


v44:
- Fully removed Scholarship card from Tuition & Scholarship result when scholarship data is not provided.
- Replaced leftover 'Not provided in uploaded Excel file' display text with blank/hidden output.
- Cleaned duplicate commas in language and scholarship criteria text.


v45:
- Connected Tuition & Scholarship page to scholarship_rules.csv.
- Tuition page no longer relies on blank Scholarship_Info from admission criteria.
- Updated Jeonbuk National University scholarship rules exactly as provided.
- Scholarship Criteria now appears when rules exist, and stays hidden when no rule exists.


v47:
- Converted decimal scholarship text such as 0.4 and 0.5 into percentage format.
- Normalized scholarship wording into percent-based display.
- Improved top header navigation alignment so menu buttons align vertically with the site name.


v48:
- Added Admin-editable management pages.
- Admin can edit Universities, Eligibility Criteria, Tuition Rules, and Scholarship Rules directly from the website.
- Admin can upload/change university photos from the Universities Management page.
- CSV files are saved automatically when Save Changes is clicked, so future edits do not require a new code package for every small data update.


v49:
- Added Admin Add New University function.
- Admin can now add a university with basic information and photo upload.
- Admin can edit or delete existing universities.
- Admin can add/edit/delete majors, eligibility criteria, fees, and tuition rules.
- Admin can add/edit/delete scholarship rules.
- Uploaded university images are saved to assets/universities and automatically used on the site.


v50:
- Empty values no longer display as nan.
- If an Admin deletes the content of a field, that field/card is hidden on the public university information page.
- CSV columns are kept internally for stability, but blank fields are not shown to users.
- Admin edit forms load blank values instead of nan.


v51:
- Fixed Home Featured Universities layout.
- University cards now render in clean rows of 5.
- When an Admin adds a new university, it appears on the next row instead of stacking unevenly under the first card.
- Card row spacing and equal height are maintained.


v52:
- Fixed PermissionError caused by blank/invalid image paths.
- Image loader now reads only real image files, never folders.
- If an added university has no image, a clean placeholder is shown instead of crashing.


v53:
- Fixed Home Featured Universities row layout using separate rows of five cards.
- Kyungsung and all first-row universities now align at the same top position.
- 6th university appears on a new row beneath the first row.
- Student count now uses multiple fallback columns so Admin-added student numbers display correctly.


v54:
- Restored the original v53 UI/design.
- Added SQLite database storage by changing only the data layer helpers.
- Existing v53 screens, cards, layout, and CSS are preserved.
- CSV/JSON files remain as initial seed files, but runtime reads/writes go to partner_portal.db.


v55:
- Fixed Admin > Universities data_editor save issue.
- New universities added in the editable table now save to SQLite DB, not only CSV.
- New universities remain visible after leaving and returning to the page.
- Photo upload dropdown now sees newly added universities after saving.


v56:
- Admin > Universities now opens the proper Add/Edit University form with photo upload.
- Added universities are saved to SQLite and also synced to data/universities.csv.
- New universities appear on Home after saving.
- Eligibility requires separate major/criteria rows under Eligibility Rules.


v57:
- Changed 'Final Tuition After Scholarship' to 'Estimated Tuition Fee After Scholarship'.
- Changed displayed 'PASS' wording to 'Eligible'.


v58:
- Admin > Partner Management now supports editing user information.
- Admin can approve/reject users, change role/agency/email/phone/country.
- Admin can delete selected users except the main admin account.
- Admin can manually add a new partner user.


v59 Supabase Ready:
- Keeps v58 design and functions.
- Removes SQLite dependency.
- Uses Supabase/PostgreSQL through DATABASE_URL.
- Do not upload .streamlit/secrets.toml or partner_portal.db to GitHub.
- For local testing, create .streamlit/secrets.toml using secrets.example.toml.
- In Streamlit Cloud, add DATABASE_URL in App settings > Secrets.


v60:
- Added Supabase read caching to improve click speed.
- Added image base64 caching to reduce repeated image loading.
- Changed universities/criteria/scholarship helpers to read from Supabase through cached DB helpers.
- Added refresh-safe login using a signed auth token in the URL query parameter.
- Logout clears the auth token.
- Added Streamlit Cloud button color CSS fix inside the existing style block.


v61:
- Added university filters on Universities page.
- Filter by location/city.
- Filter by application/intake status: opened, March, September, Spring, Fall.
- Sort universities by scholarship high-to-low or low-to-high.
- Scholarship sorting uses the highest percentage found in Scholarship Rules.
