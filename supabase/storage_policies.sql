-- Supabase Storage buckets and policies
-- Student documents should be private.

insert into storage.buckets (id, name, public)
values
  ('student-documents', 'student-documents', false),
  ('university-media', 'university-media', true),
  ('university-brochures', 'university-brochures', true)
on conflict (id) do nothing;

-- Allow public read for university media and brochures.
create policy "Public read university media" on storage.objects
for select using (bucket_id in ('university-media', 'university-brochures'));

-- Admins can upload/update/delete university media and brochures.
create policy "Admins manage university media" on storage.objects
for all using (
  bucket_id in ('university-media', 'university-brochures')
  and exists (select 1 from public.profiles where id = auth.uid() and role in ('admin', 'super_admin'))
) with check (
  bucket_id in ('university-media', 'university-brochures')
  and exists (select 1 from public.profiles where id = auth.uid() and role in ('admin', 'super_admin'))
);

-- Student documents: users can upload into their own folder path.
-- Recommended path format: {auth.uid()}/{application_id}/{filename}
create policy "Users upload own student documents" on storage.objects
for insert with check (
  bucket_id = 'student-documents'
  and auth.uid()::text = (storage.foldername(name))[1]
);

create policy "Users read own student documents" on storage.objects
for select using (
  bucket_id = 'student-documents'
  and auth.uid()::text = (storage.foldername(name))[1]
);

create policy "Admins read student documents" on storage.objects
for select using (
  bucket_id = 'student-documents'
  and exists (select 1 from public.profiles where id = auth.uid() and role in ('admin', 'super_admin'))
);
