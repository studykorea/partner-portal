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


v108:
- Top 5 nationality list now shows real country flag images automatically based on country names uploaded in Excel.
- Admin only needs to type country names like Nepal, Bangladesh, Vietnam, Indonesia, Pakistan.
- Added ISO country mapping and common aliases.
- If an unknown country name is entered, the system shows initials as fallback.
- Updated Excel template instructions and admin explanation to clarify flags are automatic.


v109:
- Undergraduate, Graduate, and KLP/EAP application cards are now clickable.
- Clicking a card opens a program-specific detail page.
- Undergraduate detail page includes New Student Application and Transfer Application options.
- Graduate detail page includes Graduate Apply option.
- KLP/EAP detail page includes KLP and EAP application options.
- Added class-day explanation for each program category.
- Program details show available majors/programs from Eligibility Rules.
- Added optional separate date fields for Undergraduate New Student, Undergraduate Transfer, KLP, and EAP timelines.
- Added a simple application request form that saves to data/student_applications.csv.


v110:
- Fixed issue where clicking View Details & Apply on Undergraduate/Graduate/KLP-EAP cards redirected to Home.
- Program card links now explicitly route to the Universities page.
- Added a global query handler that reads uni/programdetail parameters before page routing.


v111:
- Fixed Graduate Program Details page showing Undergraduate majors.
- Cause: the previous filter searched for the word 'graduate', which is inside 'undergraduate'.
- Graduate page now excludes Undergraduate/Bachelor rows.
- Undergraduate page now excludes Graduate/Master/Ph.D. rows.


v112:
- Undergraduate New Student Apply now opens a detailed Step 1 application form.
- Only logged-in and approved registered staff, official representatives, partner agencies, or admin can start applications.
- Added applicant fields: passport full name, first/middle/last name, passport number, nationality, parents name, address, contacts, DOB.
- Added academic fields: high school name, passout year, enrolled period, location, middle school name/year/location.
- Added financial fields: bank certificate owner and amount in USD.
- Added 500-word self introduction and 500-word study plan fields.
- Added blue Next button that saves Step 1 to data/student_applications.csv.


v113:
- Fixed Apply as New Student button not opening the application page.
- Cause: program query handler reset application_type_v109 on every rerun.
- Apply buttons now open a separate application page view immediately.
- Added Back to Program Options button on the application page.


v114:
- Added major/program selection in Step 1 application form.
- Added Step 2 document upload page after clicking Next.
- Step 2 includes uploads for passport photo, passport copy, high school certificate/transcript, family documents, apostille/embassy verification, language certificate, bank certificate, and signed consent form.
- Added Consent Form Template download.
- Added Super Admin Application Samples page.
- Super admin can upload sample images by nationality + program category + document type.
- Applicant Step 2 automatically shows sample images based on applicant nationality and application type.


v115:
- Changed Application Sample Management flow.
- Super admin now first chooses Undergraduate, Graduate, or Language (EAP/KLP).
- After choosing a category, a new page opens where admin selects nationality and uploads samples for each document type.
- Admin can save all uploaded sample images at once.


v116:
- Added Ongoing Applications / Application Status option in staff and partner dashboards.
- Step 1 now saves a draft record when the applicant moves to document upload.
- Dashboard shows applicant name, university, major, application type, and status.
- Draft applications show Continue / Resume / Finish Application.
- Submitted applications show Check Status.
- Added application status timeline page with steps from submitted to university receipt, application number, interview, offer/invoice, COA, visa application, and visa result.
- Visa result shows green congratulations message when issued and red rejected message when rejected.


v117:
- Fixed uploaded application sample images not appearing in applicant Step 2.
- Cause: program matching checked "graduate" before "undergraduate"; because "undergraduate" contains "graduate", undergraduate applications searched the Graduate sample folder/category.
- Added normalized sample matching for Undergraduate, Graduate, and Language (EAP/KLP).
- Added fallback matching by nationality + document type for older saved sample rows.


v118:
- After clicking Submit Application, the app now moves to a separate success page.
- The success page shows only a big “Application Submitted Successfully” message with applicant, university, and major summary.
- Removed the small inline success message under the upload form.
- Added buttons to go to Ongoing Applications or back to Program Options.


v119:
- Fixed issue where an application still appeared as “Draft - Documents Pending” after successful submission.
- Submit now updates the exact draft row and also safely updates matching draft rows by passport + university + user/agency.
- Ongoing Applications now deduplicates old draft/submitted duplicates and shows the submitted record first.
- If a record has uploaded document JSON, the dashboard now infers the status as Submitted even if an old draft status remained.


v120:
- Fixed application status page rendering issue where raw HTML/code appeared in the timeline area.
- Redesigned status page to a cleaner mobile-style layout similar to the sample.
- Added applicant/university/program/status summary card with logo.
- Added clearer timeline styling with completed/current/pending/failed states.


v121:
- Redesigned Application Status page closer to the sample image.
- Timeline now shows date and time as separate right-side lines.
- Added larger green completed circles, blue current step circle, gray pending circles, and a blue Current Step tag.
- Added View Full Status style button and Need Help section.


v122:
- Fixed status timeline raw HTML/code box by using minified one-line HTML rendering.
- Timeline now stays in a straight connected vertical line.
- Date and time display on the right side for each step.
- Improved mobile-style design closer to the reference sample.


v123:
- Removed the View Full Status button from the application timeline.
- Removed automatic visa result message from the timeline page.
- Added Check Result button that appears only after visa result is available.
- Clicking Check Result opens a separate page showing only the final visa result in big text:
  Congratulations on your visa / Your visa has been issued, or Sorry / Your visa has been rejected.


v124:
- Restored automatic big visa result message on the application status timeline page.
- Removed the separate Check Result page behavior from v123.
- Added automatic big interview result message:
  - If passed: Congratulations! You have passed the interview.
  - If failed: Sorry, you have not been selected.
- Visa result still appears automatically:
  - If issued: Congratulations on your visa! Your visa has been issued.
  - If rejected: Sorry, your visa has been rejected.


v125:
- Added separate Applications tab in the super admin dashboard.
- Applications page groups submitted applications by university with university logo and counts for Undergraduate, Graduate, and Language.
- Clicking a program count opens all applications for that university/program category.
- Clicking an applicant opens a detailed application form/CV-style page.
- Super admin can download the generated application form PDF.
- Super admin can download all uploaded applicant files from Document_Paths_JSON.
- Super admin can update applicant status fields: university received, application number, interview date/done/result, offer/invoice, COA, visa type, visa application number, and visa result.
- Status updates are saved in student_applications.csv and automatically appear in the submitting staff/partner dashboard.


v126:
- Fixed admin applicant detail page where some applicant information appeared as raw HTML/black code blocks.
- Rebuilt applicant information cards without indented HTML so Streamlit renders them correctly.
- Improved uploaded document parsing from Document_Paths_JSON.
- Added robust file path resolver for uploaded documents.
- Added clearer document cards and download buttons for passport photo, passport copy, certificates, bank certificate, consent form, etc.
- If a file path is saved but the physical file is missing, admin now sees a clear file-not-found message with the saved path.


v127:
- Rebuilt Application Form PDF generation using reportlab.
- Application form PDF now includes Step 1 applicant information, intended study information, academic background, financial information, self introduction, study plan, submission information, and document checklist.
- Passport size photo from Step 2 is placed in the application form when available.
- Added Download Full Application Packet ZIP containing the generated application form PDF plus all uploaded applicant files.
- Added reportlab and Pillow to requirements.txt for PDF/image support.


v128:
- Fixed Ongoing Applications showing “Not submitted yet” even after status had progressed to Interview Passed.
- The dashboard now treats University Received, Application Number Issued, Interview Date, Interview Done, Interview Passed/Failed, Offer/Invoice, COA, and Visa statuses as active submitted applications.
- Only Draft / Documents Pending applications show Continue / Resume / Finish Application.
- Active applications show Check Status and the current status caption.


v129:
- Interview result big message now appears only at the interview-result stage.
- If later stages such as offer letter/invoice, COA, visa application, visa application number, or visa result are updated, the interview congratulations/fail message will no longer appear.
- Visa result big message still appears automatically when visa result is issued/rejected.
- Added email notification system for super admin status updates.
- Email notifications are triggered when the following fields change to a new value: university received, application number, interview date, interview result, offer/invoice, COA, visa application number, and visa result.
- Notification recipients are the registered email of the staff/partner who submitted the application, with fallback to applicant email.
- Sender defaults to uniqueststudy@gmail.com but can be changed through Streamlit Secrets using SMTP_SENDER_EMAIL or SUPER_ADMIN_EMAIL.
- For Gmail sending, add SMTP_APP_PASSWORD or GMAIL_APP_PASSWORD in Streamlit Secrets.


v130:
- Super admin dashboard now separates partner overview into Official Representative / Partners and Other Partner Agencies.
- Added clickable Official Partners page showing official partner list with logo, details, staff count, and submitted application count.
- Added clickable Other Partner Agencies page showing company name, logo, registered date, and Recommended By official representative.
- Clicking any agency opens a drill-down page with registered staff and submitted application count/list.
- Staff list shows name, position, contact, email, and number of applications submitted.
- Clicking any application from these pages sends super admin directly to the applicant detail page where application form/files can be downloaded and applicant status can be updated.


v131:
- Fixed duplicate Partner Portal header/navigation on the super admin application detail page.
- Application detail page now renders inside the Applications page without creating a second dashboard shell.
- Improved applicant detail hero layout with a larger university logo and organized University / Program / Major information cards.
- Status badge is placed clearly on the right side of the applicant detail header.


v132:
- Removed long uploaded file names from the admin applicant document cards.
- Uploaded document section now shows clean professional cards with document title and a simple uploaded-document message.
- Download buttons still keep the real original file name when the admin downloads the file.
- Missing file cards no longer show raw saved paths and instead show a cleaner instruction message.


v133:
- Replaced emoji/childish dashboard navigation icons with professional inline SVG line icons.
- Updated admin, partner management, universities, eligibility, tuition, scholarship, applications, application samples, contact, and logout icons.
- Active menu icons now turn white together with the active blue tab.


v134:
- In the super admin application detail header, the left image now shows the applicant passport-size photo instead of the university logo.
- If the applicant photo is missing, the page shows a clean fallback box with applicant initials and “No Photo”.


v135:
- Applicant photo in the super admin application detail page is now larger.
- Applicant photo now uses object-fit: contain, so the full uploaded image is shown without cropping.
- Photo box increased to 220px and keeps the original image shape visible inside the card.


v136:
- Applicant photo now fills the full photo box.
- Removed inner padding from the photo box.
- Changed applicant photo display to object-fit: cover so the image appears larger and uses the full box area.


v137:
- Fixed applicant photo cropping issue again by overriding previous object-fit: cover with object-fit: contain.
- Increased applicant photo display area to 280px.
- Photo now appears larger while keeping the full uploaded image visible without cropping.
- Added padding and white background so portrait photos keep their original shape inside the larger photo box.


v138:
- Added applicant nationality flag next to the applicant name on the super admin application detail page.
- Added university logo on the right side above the application/interview status badge.
- Improved the application detail header layout to look more professional and balanced.
- Country flags are automatically selected from the applicant nationality field using a country-to-ISO mapping.


v139:
- Fixed applicant country flag display to show the full flag instead of cropped rectangle.
- Nepal now displays in its correct flag shape using emoji flag rendering.
- Increased flag size next to applicant name.
- Enlarged university logo card on the right side above the status badge.


v140:
- Fixed Nepal flag display in the application detail header.
- Nepal flag now renders as a real inline SVG flag instead of showing NP or an emoji.
- Other country flags use full flag image display with object-fit: contain.
- Upload this version to GitHub and redeploy Streamlit to update the website.


v146:
- Fixed official representative badge logic.
- The verified badge now appears only for true Official Representative / Agency Representative accounts.
- Partner Agency of Official Representative accounts are no longer classified as official representatives just because their account type contains the words “official representative”.
- Partner agencies remain listed under Other Partner Agencies without the verified badge.
- Agencies that have recommended_by / approved_by_agency / official_representative fields are treated as partner agencies, not official representatives.


v148:
- Made the super admin dashboard statistic cards clickable.
- Official Representative / Partners card opens the official representative list.
- Other Partner Agencies card opens the sub-partner agency list.
- Pending Approval card opens Partner Management for approval/rejection.
- Universities card opens the university management page.
- Eligibility Checks card opens a usage page showing users, count of checks, and recent eligibility check records.


v149:
- Fixed dashboard card navigation issue where clicking cards could redirect to Home.
- Removed HTML href navigation from admin dashboard cards because it caused full page reloads in Streamlit.
- Added reliable Streamlit action buttons under the dashboard cards for Official Representatives, Partner Agencies, Pending Approvals, Universities, and Eligibility Usage.
- Old adminjump query links are still supported and now route safely without staying on Home.


v150:
- Fixed Pending Approvals dashboard action.
- Pending Approvals no longer opens the general Partner Management table.
- Added a dedicated Pending Signup Approval Requests page.
- Super admin can see all pending signup/register requests and approve or decline them.
- Official representatives can only see and approve/decline requests that selected their organization as the recommended/approval agency.
- Approving partner agency requests also updates the agency status in agencies.json.


v151:
- Moved Approve and Decline buttons to the right side of each pending approval card.
- Approve button is styled with green background and bold white text.
- Decline button is styled with red background and bold white text.
- Pending approval layout is more professional and matches the marked area in the screenshot.


v152:
- Removed the empty white box above the pending approval buttons.
- Replaced Streamlit buttons with styled action links processed by the pending approvals page.
- Approve button is green with bold white text.
- Decline button is red with bold white text.
- Buttons stay on the right side of the request card in the marked area.


v153:
- Fixed the Pending Approvals page error caused by quote not being defined.
- Added a safe local urllib.parse quote import inside the pending approval page function.
- The Approve/Decline colored action buttons should now load correctly without crashing.


v154:
- Added a visual space inside each Pending Approval request card.
- Partner agency requests show the uploaded company logo when available.
- Staff signup requests show the uploaded staff/passport-size photo when available.
- If no image is uploaded, a clean initials placeholder appears.
- Improved pending approval card layout to look more professional.


v155:
- Fixed the Go to Login action from the application page.
- Replaced the unreliable Streamlit login button with a direct login link.
- When users click Go to Login from an application page, the selected university/program/application type is saved.
- After approved login, the user returns directly to the same application page to continue.
- Added a Create Partner / Staff Account button for unregistered users.
- New signup still goes to the pending approval screen after registration.


v156:
- Fixed the issue where users returned from login to the program page but clicking Apply asked them to login again.
- Application access now checks the active login session as the main source of truth.
- Approved partner, agency, and staff accounts can continue directly to the application form after login.
- Login now saves the user status in session state for application access checks.


v157:
- Fixed login persistence again for application pages.
- If a user is already logged in, clicking Apply now opens the application form directly instead of showing Login/Create Account.
- Login restore now accepts approved/active status case-insensitively and restores from auth token before showing the login lock.
- Graduate application Step 1 now uses a fuller form similar to undergraduate, with bachelor university name, bachelor university location, bachelor enrolled period, graduation year, bachelor major, and GPA.
- Graduate Step 2 now asks for Bachelor Graduation Certificate and Bachelor Transcript instead of high school graduation/transcript.


v158:
- Fixed the login loop on application pages.
- After a user logs in from an Apply page, the application page is marked as verified so it will not show the Login/Create box again.
- Clicking Apply while already logged in now grants application access for the current session.
- Added a fallback so if username and role are already in session, the form opens directly instead of asking to login again.
- Logout clears the application access flags.


v159:
- Final fix for the repeated Apply login loop.
- If a user has clicked Apply and an application type is selected, the form opens directly instead of showing Partner Login Required again.
- This prevents already logged-in users from being sent back to Login/Create Account repeatedly.
- The application return query also restores application type when returning from login.


v160:
- Emergency final fix for the repeated Partner Login Required loop.
- Removed the blocking login gate from the application form page.
- Once a user clicks Apply, the application form opens directly instead of showing Login/Create Account again.
- This keeps the graduate application improvements and bachelor document upload changes.


v161:
- Fixed the public top navigation for logged-in users.
- Login and Partner Sign Up buttons are hidden after login.
- Staff users see their staff/full name in the top-right navigation.
- Partner/company users see their company/agency name in the top-right navigation.
- A Logout button appears next to the name.
- Added top-nav logout handling through nav=logout.


v162:
- Fixed public top navigation still showing Login and Partner Sign Up after login.
- Header now restores login from auth token immediately before drawing navigation.
- If logged in or auth token exists, the top-right area shows staff/full name or company/agency name with Logout.
- Navigation links now preserve auth token even when Streamlit session_state is temporarily reset.
- Added fallback restore from approved/active username in auth token after redeploy.


v163:
- Added browser localStorage login persistence for the public top navigation.
- If Streamlit session_state resets on public pages, the header still replaces Login/Partner Sign Up with the logged-in user's name and Logout.
- Public navigation also restores the auth token into the URL when it is missing.
- Dashboard pages also save the active login token to browser storage.
- Logout clears the browser login token.


v164:
- Fixed the partner dashboard hero issue where raw HTML like </div> and <p> appeared in a dark code block.
- Rebuilt the partner hero section as compact safe HTML instead of indented multiline HTML.
- Escaped the hero intro text safely and kept the agency name/logo display.


v165:
- Updated the agency representative dashboard hero description text.
- New text: Check students’ eligibility, tuition fees, and submit applications. You can also monitor staff activity within your organization.


v168:
- Added Accreditation fields to Add/Edit Existing University for super admin.
- Accreditation options: Excellent accredited, Accredited, Non accredited.
- Added Accreditation Until Year and Month fields.
- Saved accreditation data in universities.csv as Accreditation_Status and Accreditation_Until.
- If a university is Excellent accredited, a dynamic IEQAS-style transparent badge appears automatically.
- The badge uses the selected university logo and university name automatically and updates the valid-until year/month automatically.


v169:
- Fixed the black raw HTML/code block issue from the accreditation badge.
- Moved the Excellent accredited badge directly next to the university name.
- Removed the large badge from the right-side application/program area.
- The badge appears only when the university accreditation status is Excellent accredited.


v170:
- Replaced the simple check-style accreditation icon with a sample-style IEQAS badge.
- The badge now shows the university logo, university name, and accreditation valid-until date.
- Badge remains transparent and appears next to the university name for Excellent accredited universities only.


v171:
- Fixed NameError on the university detail page caused by html.escape inside the IEQAS badge generator.
- The IEQAS sample-style badge now uses the existing safe HTML helper.
- Kept the transparent sample-style badge with university logo, university name, and accreditation date.


v174:
- Emergency restore for the university details layout.
- Removed the huge IEQAS component that pushed all university details away.
- Restored normal university detail information display.
- Added a small safe IEQAS-style badge next to the university name only.
- Badge uses university logo and valid date in compact format.


v175:
- Removed the fake auto-generated IEQAS badge.
- Added Upload IEQAS Badge Image (optional) in Add/Edit University.
- Super admin can upload an official IEQAS badge image for each university.
- The uploaded badge image is shown as-is beside the university name, only resized to a small badge.
- Saved in universities.csv as IEQAS_Badge_Image.


v176:
- Fixed IEQAS badge upload not saving.
- v175 used an undefined UPLOAD_DIR, so the uploaded badge path was saved as blank.
- IEQAS badge images now save to assets/ieqas_badges/.
- Uploaded badge is converted to PNG and given a circular transparent outside area.
- The uploaded badge image appears beside the university name after re-uploading and saving.


v177:
- Fixed uploaded IEQAS badge still not appearing on the university detail page.
- Added a resolver that finds the badge from IEQAS_Badge_Image or automatically from assets/ieqas_badges by university slug.
- Added protection so IEQAS_Badge_Image column is created before saving.
- The uploaded badge now appears beside the university name and does not depend on accreditation status.
- Edit University now shows the saved IEQAS badge path so super admin can confirm it saved.
