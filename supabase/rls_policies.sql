-- Supabase Row Level Security policies
-- Review and adjust before production launch.

create or replace function public.current_user_role()
returns text
language sql
security definer
set search_path = public
as $$
  select role::text from public.profiles where id = auth.uid();
$$;

create or replace function public.is_admin_or_super_admin()
returns boolean
language sql
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role in ('admin', 'super_admin')
  );
$$;

-- Profiles
create policy "Users can read own profile" on public.profiles
for select using (id = auth.uid() or public.is_admin_or_super_admin());

create policy "Users can update own profile" on public.profiles
for update using (id = auth.uid()) with check (id = auth.uid());

create policy "Admins can manage profiles" on public.profiles
for all using (public.is_admin_or_super_admin()) with check (public.is_admin_or_super_admin());

-- Public university data
create policy "Visible universities are public" on public.universities
for select using (is_visible = true or public.is_admin_or_super_admin());

create policy "Admins manage universities" on public.universities
for all using (public.is_admin_or_super_admin()) with check (public.is_admin_or_super_admin());

create policy "Visible programs are public" on public.university_programs
for select using (is_visible = true or public.is_admin_or_super_admin());

create policy "Admins manage programs" on public.university_programs
for all using (public.is_admin_or_super_admin()) with check (public.is_admin_or_super_admin());

create policy "Admission dates are public" on public.admission_dates
for select using (true);

create policy "Admins manage admission dates" on public.admission_dates
for all using (public.is_admin_or_super_admin()) with check (public.is_admin_or_super_admin());

-- Applications
create policy "Applicants and partners can read own applications" on public.applications
for select using (
  applicant_id = auth.uid()
  or partner_id = auth.uid()
  or public.is_admin_or_super_admin()
);

create policy "Authenticated users can create applications" on public.applications
for insert with check (auth.uid() is not null);

create policy "Owners can update draft applications" on public.applications
for update using (
  (applicant_id = auth.uid() or partner_id = auth.uid())
  or public.is_admin_or_super_admin()
);

-- Documents
create policy "Users can read documents for own applications" on public.application_documents
for select using (
  exists (
    select 1 from public.applications a
    where a.id = application_id
    and (a.applicant_id = auth.uid() or a.partner_id = auth.uid())
  )
  or public.is_admin_or_super_admin()
);

create policy "Authenticated users can add documents" on public.application_documents
for insert with check (auth.uid() is not null);

-- Favorites
create policy "Users can read own favorites" on public.favorites
for select using (user_id = auth.uid());

create policy "Users can add own favorites" on public.favorites
for insert with check (user_id = auth.uid());

create policy "Users can remove own favorites" on public.favorites
for delete using (user_id = auth.uid());

-- Audit logs
create policy "Admins read audit logs" on public.audit_logs
for select using (public.is_admin_or_super_admin());

create policy "Admins create audit logs" on public.audit_logs
for insert with check (public.is_admin_or_super_admin());
