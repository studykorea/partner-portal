-- v373: Add structured tuition and scholarship fields for KUA admin
-- Run this once in Supabase SQL Editor before using the new admin Tuition & Scholarships editor.

alter table public.universities
  add column if not exists undergraduate_tuition jsonb default '[]'::jsonb,
  add column if not exists graduate_tuition jsonb default '[]'::jsonb,
  add column if not exists language_tuition jsonb default '[]'::jsonb,
  add column if not exists scholarship_rules jsonb default '[]'::jsonb,
  add column if not exists other_scholarships text default '';

-- Optional: refresh PostgREST schema cache
notify pgrst, 'reload schema';
