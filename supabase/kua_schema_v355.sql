-- KUA Partner Portal v355 Supabase schema
-- Run this in Supabase SQL Editor before using the real Super Admin save/upload system.

create table if not exists public.universities (
  slug text primary key,
  name text not null,
  location text default '',
  region text default '',
  students text default '',
  international_students text default '',
  type text default 'Partner University',
  established text default 'Not updated',
  accreditation text default 'Not updated',
  accreditation_badge_url text default '',
  homepage text default '',
  email text default '',
  phone text default '',
  address text default '',
  overview text default '',
  tuition text default '',
  intake text default '',
  top_majors text default '',
  graduate_programs text default '',
  klp_programs text default '',
  card_image_url text default '',
  logo_url text default '',
  hero_image_url text default '',
  video_url text default '',
  brochure_url text default '',
  facebook_url text default '',
  instagram_url text default '',
  youtube_url text default '',
  sort_order integer default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.admission_timelines (
  id bigint generated always as identity primary key,
  university_slug text not null references public.universities(slug) on delete cascade,
  program text not null,
  open_date text default '',
  close_date text default '',
  status text default 'Not fixed yet',
  tone text default 'notfixed' check (tone in ('open','soon','closed','notfixed')),
  sort_order integer default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.applications (
  id bigint generated always as identity primary key,
  applicant_name text not null,
  university_slug text references public.universities(slug),
  program text default '',
  status text default 'Submitted',
  current_step text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.partners (
  id bigint generated always as identity primary key,
  agency_name text not null,
  contact_name text default '',
  email text default '',
  role text default 'partner',
  approval_status text default 'pending',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists admission_timelines_university_slug_idx on public.admission_timelines(university_slug);

alter table public.universities enable row level security;
alter table public.admission_timelines enable row level security;
alter table public.applications enable row level security;
alter table public.partners enable row level security;

-- Public pages can read university information.
drop policy if exists "Public read universities" on public.universities;
create policy "Public read universities" on public.universities for select using (true);

drop policy if exists "Public read admission timelines" on public.admission_timelines;
create policy "Public read admission timelines" on public.admission_timelines for select using (true);

-- Writes are done by FastAPI using the service-role key, which bypasses RLS.
-- Do not expose SUPABASE_SERVICE_ROLE_KEY in the frontend.

-- Storage bucket. If this fails in SQL editor, create it manually in Storage UI.
insert into storage.buckets (id, name, public)
values ('kua-university-assets', 'kua-university-assets', true)
on conflict (id) do update set public = true;

drop policy if exists "Public read KUA university assets" on storage.objects;
create policy "Public read KUA university assets" on storage.objects for select using (bucket_id = 'kua-university-assets');
