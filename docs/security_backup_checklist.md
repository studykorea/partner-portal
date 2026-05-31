# Security and backup checklist

## Security
- Enable RLS on every table.
- Keep service-role key only in backend environment variables.
- Never expose `SUPABASE_SERVICE_ROLE_KEY` in frontend code.
- Use private bucket for student documents.
- Use signed URLs for private documents.
- Limit accepted upload types to PDF, JPG, JPEG, PNG.
- Limit file size.
- Add virus scanning before final production if handling official documents.
- Add audit logs for admin/super-admin actions.

## Backups
- Enable database backups in Supabase.
- Schedule regular exports of important tables.
- Back up storage buckets or sync to S3-compatible storage.
- Test restore process before launch.

## Performance
- Store images in storage, not GitHub.
- Resize/compress images before upload.
- Use lazy loading for university images.
- Use thumbnails for listings and larger images only on detail pages.
- Use pagination or infinite loading for large university lists.
