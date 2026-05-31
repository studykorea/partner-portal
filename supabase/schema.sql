-- Supabase production schema for Korea University Admissions Partner Portal
-- Run in Supabase SQL Editor after creating a new project.

create extension if not exists "uuid-ossp";

create type public.user_role as enum ('student', 'partner', 'admin', 'super_admin');
create type public.application_status as enum ('draft', 'submitted', 'reviewing', 'approved', 'rejected');
create type public.admission_status as enum ('open', 'closed', 'not_fixed');

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique,
  full_name text,
  role public.user_role not null default 'student',
  agency_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.universities (
  id uuid primary key default uuid_generate_v4(),
  slug text unique not null,
  name text not null,
  city text,
  region text,
  address text,
  university_type text,
  established text,
  total_students text,
  international_students text,
  description text,
  homepage_url text,
  admission_url text,
  facebook_url text,
  instagram_url text,
  youtube_url text,
  google_maps_url text,
  brochure_url text,
  hero_image_url text,
  logo_url text,
  video_url text,
  is_featured boolean not null default true,
  is_visible boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.university_programs (
  id uuid primary key default uuid_generate_v4(),
  university_id uuid not null references public.universities(id) on delete cascade,
  level text not null check (level in ('undergraduate', 'graduate', 'klp_eap')),
  program_name text not null,
  description text,
  tuition_range text,
  is_visible boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.admission_dates (
  id uuid primary key default uuid_generate_v4(),
  university_id uuid not null references public.universities(id) on delete cascade,
  program_level text not null check (program_level in ('undergraduate', 'graduate', 'klp_eap')),
  round_name text,
  open_date date,
  close_date date,
  status public.admission_status not null default 'not_fixed',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.applications (
  id uuid primary key default uuid_generate_v4(),
  applicant_id uuid references auth.users(id) on delete set null,
  partner_id uuid references auth.users(id) on delete set null,
  university_id uuid references public.universities(id) on delete set null,
  program_level text,
  program_name text,
  applicant_name text,
  applicant_email text,
  status public.application_status not null default 'draft',
  submitted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.application_documents (
  id uuid primary key default uuid_generate_v4(),
  application_id uuid not null references public.applications(id) on delete cascade,
  uploaded_by uuid references auth.users(id) on delete set null,
  file_name text not null,
  file_path text not null,
  file_type text,
  bucket_name text not null default 'student-documents',
  created_at timestamptz not null default now()
);

create table if not exists public.favorites (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  university_id uuid not null references public.universities(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique(user_id, university_id)
);

create table if not exists public.audit_logs (
  id uuid primary key default uuid_generate_v4(),
  actor_id uuid references auth.users(id) on delete set null,
  action text not null,
  entity_type text,
  entity_id uuid,
  metadata jsonb,
  created_at timestamptz not null default now()
);

-- Enable RLS
alter table public.profiles enable row level security;
alter table public.universities enable row level security;
alter table public.university_programs enable row level security;
alter table public.admission_dates enable row level security;
alter table public.applications enable row level security;
alter table public.application_documents enable row level security;
alter table public.favorites enable row level security;
alter table public.audit_logs enable row level security;
