# SES Platform Deployment - Option B

Option B means:

- public read access
- login required to add, edit, delete or process shared data
- Supabase PostgreSQL stores the shared database
- the frontend can run on Vercel
- the Python API runs on Render

## 1. Supabase

1. Create a Supabase project.
2. Open SQL Editor.
3. Run `supabase/schema.sql`.
4. In Authentication settings, enable email magic links.
5. Add redirect URLs:
   - `http://localhost:8000`
   - the final Vercel production URL
6. Copy these values into deployment environment variables only:
   - Project URL
   - anon public key
   - service role key

Never commit the service role key.

## 2. Render API

Create a Render Web Service from this repo.

Settings:

- Environment: Python
- Build command: `pip install -r requirements.txt`
- Start command: `python app.py --host 0.0.0.0 --port $PORT`

Environment variables:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `EDIT_AUTH_MODE=authenticated`
- `ALLOWED_ORIGINS=https://your-vercel-app.vercel.app,http://localhost:8000`

## 3. Vercel Frontend

Create a Vercel project from this repo.

Settings:

- Build command: `npm run build`
- Output directory: `dist`

Environment variables:

- `VITE_API_BASE_URL=https://your-render-api.onrender.com`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_AUTH_MODE=authenticated`

## 4. Local Migration

After Supabase tables exist, migrate existing SQLite data with:

```powershell
$env:SUPABASE_URL="https://your-project.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="paste-service-role-key-only-in-this-shell"
python scripts/migrate_sqlite_to_supabase.py
Remove-Item Env:\SUPABASE_SERVICE_ROLE_KEY
```

## 5. Validation

1. Open Vercel URL in one browser.
2. Open it in another browser or private window.
3. Confirm public data is visible without login.
4. Try add/edit/delete without login and confirm it is rejected.
5. Log in with email magic link.
6. Add a carbon fiber.
7. Confirm it appears in both browsers after refresh.
8. Edit and delete the test item.
9. Process one probe and confirm it appears in Database.
10. Save a monocoque calculation and confirm it persists after refresh.
