from db import create_tables_from_seed

# WARNING:
# refresh=True overwrites Supabase tables with local data/ CSV/JSON files.
# Use only for initial setup or intentional reset.

create_tables_from_seed(refresh=True)
print("Local seed data has been uploaded to Supabase.")
