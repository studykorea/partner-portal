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


v62:
- Fixed raw HTML showing as a black code block on university details.
- Added View Details button for each filtered university result.
- Added Back to List button after opening details.
- Clarified Application Opened filter text.
- Cleaned university details rendering to avoid Markdown code-block behavior.


v63:
- Added Application Status filter options: Application Open, Application Closed, Application Opens Soon.
- Added color badges:
  - Open = green with white text
  - Closed = red with white text
  - Opens Soon = yellow with black text
- Supports optional Admin/DB column named Application_Status. If absent, status is inferred from Intake.


v64:
- Added Application Status and Application Open Date fields in Admin > Universities.
- Application status supports Open, Closed, and Opens Soon.
- If Opens Soon has a future open date, it stays Opens Soon; when date arrives it displays Open.
- Replaced right-side university detail badges with Undergraduate, Graduate (Masters/Ph.D.), and KLP/EAP program badges plus application status/open date.


v65:
- Added Application Close Date in Admin > Universities.
- Application status is now automatically calculated from dates:
  - Today before open date = Application Opens Soon
  - Today between open and close dates = Application Open
  - Today after close date = Application Closed
- The saved Application_Status is updated automatically when Admin saves the university.


v66:
- Application Status is directly linked with Application Open Date and Application Close Date.
- Before open date: Application Opens Soon.
- Between open date and close date: Application Open.
- After close date: Application Closed.
- University cards/details show calculated status and date badges.
- Admin note clarifies that status is auto-calculated from dates.


v67:
- Fixed NameError: _program_badges_html_v64 was not defined.
- Program badges now show Undergraduate, Graduate (Masters/Ph.D.), and KLP/EAP.
- University cards/details load without the red error block.
- Status display uses the date-linked v66 calculation.


v69:
- Rebuilt home hero to match the reference image more closely.
- Text is forced to white using color and -webkit-text-fill-color.
- Buttons are real HTML hero buttons placed inside the hero area.
- Apply for Partner Access is blue with white text.
- Explore Universities is outline/transparent with white text.
- Added query routing so hero buttons still navigate correctly.


v70:
- Replaced the top navigation with a reference-style white navbar.
- Login is now an outline button.
- Partner Sign Up is now a blue button with white text.
- Active page is shown with blue text and underline.
- Navigation uses HTML links with query-parameter routing.


v71:
- Added separate application open/close dates for Undergraduate, Graduate (Masters/Ph.D.), and KLP/EAP.
- Admin Add/Edit University now has program-specific date fields.
- University cards/details show program-specific application status and open/close dates.
- If program-specific dates are empty, the general application period is used as fallback.


v72:
- Fixed StreamlitDuplicateElementKey in Admin Dashboard approval/reject buttons by generating unique keys.
- Admin form submit buttons are now blue with bold white text.
- Upload button text readability improved.


v73:
- Redesigned Admin Dashboard in a premium card-based layout similar to the provided sample.
- Added Step pill, metric cards, approval panel, right-side partner approval status panel, quick admin action panel, and bottom feature strip.
- Fixed approval/reject button loop to avoid duplicate/undefined key issues.
- Blue admin action buttons with bold white text preserved.


v74:
- Eligibility Rules, Tuition Rules, and Scholarship Rules are now edited university-by-university.
- Admin selects one university first, then sees only that university's rows.
- Saving replaces only the selected university's rows and keeps all other universities unchanged.
- New rows are automatically assigned to the selected university.


v75:
- Agency staff accounts linked to an existing approved agency representative can now be approved/rejected by that representative from the partner dashboard.
- Super admin can still approve/reject all pending users.
- Pending users see a personalized approval message when trying to use protected features.
- Signup stores approval_scope so Realize/KIEC representative approvals can work.


v76:
- Fixed pending users seeing generic Partner Access Required after clicking Eligibility/Tuition.
- Pending user state is now preserved with a signed pending token in the URL.
- Top navigation preserves pending token while moving between pages.
- Pending users now see the personalized message on protected services.
- Agency representative approval matching now supports Realize / Realize Education aliases and KIEC aliases.
- Realize Education representatives can see pending staff even if the staff selected Realize or Realize Education.


v77:
- Redesigned signup account categories:
  1. Staff of Official Representative Agency
  2. Partner Agency of Official Representative
  3. Official Representative Agency
- Staff accounts select their organization such as KIEC or Realize Education and can be approved by that organization.
- Partner agency accounts enter company name, CEO/representative, main contact, position, phone, and email, then select the official representative that recommended them.
- Official representatives can approve both staff and sub-partner agency accounts.
- Partner agency accounts are listed under the official representative dashboard after approval.
- Added official representative star badge beside official representative agency names.


v78:
- Fixed signup dynamic fields by moving Account Category selector outside the Streamlit form.
- When Partner Agency of Official Representative is selected, the form now immediately shows organization/company, CEO/representative, position, email, contact number, and official partner selector.
- After signup, the pending screen says thank you, explains the account is under review, and tells users they may contact their selected official partner organization for approval.


v79:
- Updated Partner Agency signup note to remove example agency names.
- Changed user-facing labels from Create Eligibleword / Confirm Eligibleword to Create Password / Confirm Password.
- Changed password mismatch error text to 'Passwords do not match.'


v80:
- Fixed Realize/KIEC official representative approval for Partner Agency requests.
- Approval now matches by sponsor/official representative group, not by the applicant company's own agency ID.
- When a Partner Agency is approved/rejected, the related agency record status is also updated.
- Pending approval list now checks sponsor_agency_id, official_representative, and requested_approver_agency_id.
- Duplicate pending cards are reduced by username/email.


v81:
- Added official representative dashboard details.
- Added Confirmed Co-Partner Agencies count.
- Added Confirmed Staff count.
- Added clickable buttons to view co-partner agencies, staff list, and all activity.
- Co-partner list includes agency/company name, CEO/representative, main contact, position, phone, email, username, status, eligibility checks, tuition estimates, and applications lodged.
- Staff list includes staff name, position, phone, email, username, status, eligibility checks, tuition estimates, and applications lodged.
- Activity log summary combines staff and co-partner agency activity.
- Applications Lodged count is prepared for future application tracking columns; it remains 0 until application lodging data is recorded.


v82:
- Removed example agency names from Staff account note.
- Staff organization list now includes approved official representative agencies and approved sub-partner agencies.
- If Edukorea is approved as a partner agency, Edukorea appears in the staff organization dropdown.
- Staff who select Edukorea will be routed to Edukorea for approval when an approved Edukorea partner account exists.
- Approved partner agency accounts can now access the agency-style dashboard and approve their own staff accounts.


v83:
- Added company logo image upload to Partner Agency signup and Official Representative signup.
- Uploaded logo is saved in assets/partner_logos and stored in the user/agency record.
- When a partner/official representative logs in, their logo appears beside the company name in the dashboard welcome hero.
- Partner agency approval also updates the agency logo record when available.


v84:
- Increased partner/company logo display size on the dashboard.
- Logo now appears larger, clearer, and more premium beside the company name.
- Added extra hero spacing for the larger logo.


v85:
- View Partner Agencies and View Staff List now open separate pages instead of showing details under the dashboard.
- Staff list page shows staff name, position, contact number, email, username, status, and activity summary.
- Each staff row has a blue Activity button to open that staff member's performance/activity log.
- Partner agency list page also has Activity buttons for each partner agency.
- Activity page shows eligibility check logs, tuition estimate logs, and summary counts.


v86:
- Fixed StreamlitDuplicateElementKey on Partner Agency / Staff / Activity detail pages.
- The error was caused by rendering the partner dashboard shell twice.
- Separate detail pages now render their own shell only once.


v87:
- Official representatives and partner agencies can view activity/performance for staff only.
- Removed partner agency Activity button from the co-partner agency list page.
- Removed partner agency activity/performance counts from the official representative partner agency page.
- View All Activity changed to staff-only activity.
- Deprecated partner_activity route now redirects back to partner agency list and shows a warning.
- Partner agency activity remains reserved for the portal super admin.


v88:
- Added university logo upload in Admin > Universities > Add/Edit.
- Added University_Logo column support.
- University cards now use the empty right side for large Undergraduate / Graduate / KLP/EAP application cards.
- University logo now appears as a large clear logo box near the university title/overview.


v89:
- Added Upload Slideshow Images in Admin > Universities > Add New University.
- Added Upload New Slideshow Images in Admin > Universities > Edit Existing Universities.
- Added Image_Gallery column support using pipe-separated image paths.
- University card hero image now auto-changes/slides through uploaded photos.
- If no slideshow images are uploaded, the main university photo is used as fallback.


v90:
- Fixed Admin > Universities > Edit Existing Universities form state issue.
- When selecting a different university, all fields and upload widgets now refresh for that selected university only.
- File uploader keys are now university-specific, so Jeonbuk uploaded files will not remain when editing another university.
- Saving now correctly stores Image_Gallery for the selected university.


v91:
- University name color now automatically follows the uploaded university logo accent color.
- The system extracts a strong non-white/non-gray dominant color from the logo.
- Kyungsung-style yellow/gold logos will produce a gold-toned university name.
- Jeonbuk-style purple logos will produce a purple-toned university name.
- Future uploaded university logos will automatically apply their matching accent color.


v92:
- Strengthened automatic university-logo accent color extraction.
- University name color now passes the university name into the color extractor for better fallback.
- Added stronger inline span styling so global CSS cannot override the extracted color.
- Kyungsung should now appear in a gold/yellow tone and Jeonbuk in a purple tone when their logos are uploaded.


v93:
- Fixed Kyungsung/Jeonbuk name color not changing by using deterministic known-university accent colors.
- Kyungsung University name is forced to gold/yellow.
- Jeonbuk National University name is forced to purple.
- Other universities still use automatic logo accent extraction.
- Added stronger inline style generation to prevent global CSS override.


v94:
- Updated Eligibility Rules, Tuition Rules, and Scholarship Rules admin pages to match the sample format.
- Added selected university card with university logo and university name.
- Added Program & Major Eligibility Rules header and + Add New Rule button.
- Added search box, filter button, clean table layout, and visual actions column.
- The editor still saves only the selected university's records.


v95:
- Fixed StreamlitAPIException on Eligibility Rules/Tuition Rules/Scholarship Rules table.
- The error was caused by applying TextColumn formatting to numeric/mixed columns in Streamlit data_editor.
- Editable rule tables are now safely converted to text view before rendering.
- Rule editor keys are now university-specific to prevent stale table state when switching universities.


v96:
- Replaced dashboard button navigation with styled HTML navigation links.
- Active/current page is now highlighted in blue for admin, official representative, partner agency, and staff users.
- Dashboard, Universities, Eligibility Rules/Check, Tuition Rules/Scholarship, etc. now show active blue state when selected.
- Logout remains available in the same navigation bar.


v97:
- Fixed university slideshow showing a gray/blank area.
- If there is only one image, it now displays as a normal visible image without animation.
- If multiple images are uploaded, they fade/slide automatically.
- If saved image paths are missing from the server, the card shows an upload instruction message instead of an empty gray block.


v98:
- Added automatic logo cleaning for university logos and partner/agency logos.
- When admin uploads a logo, the system removes unnecessary outside white/near-white background.
- The logo is cropped to the actual visible mark and centered on a transparent square canvas.
- This helps uploaded logos look consistent even if the original image has a white box or large empty margins.
- Existing old logos need to be re-uploaded once to apply the cleaning process.


v99:
- Redesigned university View Details page to remove excessive empty space.
- Detail page now has a compact hero: campus image, logo, university name, overview, and application cards.
- Added Google Maps embed based on university name/address/location.
- Added Open in Google Maps button so users can quickly view the university location.


v100:
- Fixed University View Details page showing raw HTML code in a black block.
- The issue was caused by indented multiline HTML being interpreted by Markdown as a code block.
- Detail page HTML is now dedented before rendering.


v101:
- Fixed NameError: textwrap is not defined on University View Details page.
- v100 used textwrap.dedent to fix raw HTML rendering, but textwrap was not imported correctly because the import line was combined.
- University detail page should now load normally.


v102:
- Fixed University View Details still showing raw HTML in a black code block.
- The issue was caused by indented HTML lines inside Markdown.
- The detail page now removes left indentation from every HTML line before rendering.


v103:
- Added optional university detail links: Homepage, Language School Homepage, Promotional Materials, Facebook, Instagram, YouTube, and SNS information.
- Admin can enter these fields in Add/Edit University; all are optional.
- If admin enters a link, it appears in University View Details as a clickable card with icon and external-link marker.
- Blank optional links are not shown on the public details page.


v104:
- Fixed admin/user login persistence across navigation links.
- Dashboard and top navigation links now keep the auth token, so users stay logged in until they click Logout.
- If a logged-in user/admin clicks Home/Login/Sign Up, they are redirected back to their dashboard instead of appearing logged out.
- Fixed Admin > Universities Add New University optional link fields that were referenced but not visible.
- Added a clear note above Add/Edit University tabs so admins can easily find Add New University and Edit Existing Universities.


v105:
- Updated Useful Links section to show official-style icons for Facebook, Instagram, and YouTube.
- Kept Homepage, Language School Homepage, and Promotional Materials links intact.


v106:
- Added optional student enrollment statistics Excel upload for each university.
- Admin can download a sample Excel format, fill Summary and Nationality sheets, and upload it when adding/editing a university.
- University detail page now shows a Students by Program Level graph for Undergraduate, Graduate, and Language Study students.
- University detail page now shows Top 5 Nationality Students with country flags and student numbers.
- Student statistics upload is optional; if no file is uploaded, the section is hidden.
- Added openpyxl dependency for Excel reading/writing in Streamlit.


v107:
- Added a clear Student Statistics Excel explanation box next to the Excel upload area.
- Added a blue Download Excel Format link directly beside the Student Statistics Excel upload field in Add/Edit University forms.
- Clarified that the Excel upload is optional and used only to create student graph/top nationality information in university details.
