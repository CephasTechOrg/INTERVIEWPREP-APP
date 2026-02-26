# Profile Picture (Avatar) Feature

## Overview

Users can upload a profile photo from the Profile modal. The image is stored in
Supabase Storage and displayed everywhere the user's avatar appears — the top bar,
the sidebar user card, and the dropdown panel.

---

## 1. Environment Variables

Add these to `backend/.env` (template in `backend/.env.example`):

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_BUCKET_PROFILE_PHOTOS=intervIQ
```

`SUPABASE_BUCKET_PROFILE_PHOTOS` defaults to `intervIQ` if omitted. The bucket
must exist in your Supabase project with a **public** read policy so the returned
URL is accessible without authentication.

---

## 2. Dependency

The `supabase` Python package must be installed:

```bash
pip install supabase>=2.0.0
```

It is listed in `backend/requirements.txt`.

---

## 3. Backend

### Storage Service — `backend/app/services/storage_service.py`

```python
def upload_avatar(file_bytes: bytes, content_type: str, user_id: int) -> str | None
```

Uploads the image to Supabase Storage and returns the public URL.

**Key design decision — fixed path, no file extension:**

```python
path = f"avatars/{user_id}"
```

The path never includes a file extension. This means:
- Uploading a PNG after a JPEG does not create a second object.
- The `upsert: true` flag overwrites the same object every time.
- The public URL never changes between uploads.

Returns `None` if Supabase is not configured or if the upload fails (e.g., bucket
not found, network error). The endpoint propagates this as a 500 error.

### API Endpoint — `backend/app/api/v1/users.py`

```
POST /api/v1/users/me/avatar
Content-Type: multipart/form-data
Authorization: Bearer <token>

Form field: file  (image/jpeg | image/png | image/webp)
```

**Validation:**
- Content-type must start with `image/` → 400 if not an image
- File size limit: 5 MB → 400 if exceeded

**Response:** `UserProfileOut` — the full updated user object including the new
`profile.avatar_url`.

**On success:**
1. Calls `upload_avatar()` to upload to Supabase
2. Merges `{ avatar_url: <public_url> }` into `user.profile` (existing profile
   fields are preserved)
3. Saves updated profile via `update_user_profile()`
4. Returns the updated user

### Config — `backend/app/core/config.py`

Three new settings added to `Settings`:

```python
SUPABASE_URL: str | None = None
SUPABASE_SERVICE_ROLE_KEY: str | None = None
SUPABASE_BUCKET_PROFILE_PHOTOS: str = "intervIQ"
```

---

## 4. Frontend

### API Client — `frontend-next/src/lib/api.ts`

```typescript
async postMultipart<T>(url: string, formData: FormData): Promise<T>
```

Sends a `POST` request with `Content-Type: multipart/form-data`. Used only for
the avatar upload. Axios automatically sets the correct multipart boundary when
the request body is a `FormData` object.

### Auth Service — `frontend-next/src/lib/services/authService.ts`

```typescript
async uploadAvatar(file: File): Promise<User>
```

Creates a `FormData` with `file` appended, calls `postMultipart`, and returns the
updated `User` object. The caller (ProfileModal) is responsible for updating the
Zustand store.

### Profile Modal — `frontend-next/src/components/modals/ProfileModal.tsx`

**State added:**
- `uploading: boolean` — shows a spinner over the avatar while uploading
- `avatarPreview: string | null` — local `ObjectURL` for instant preview before
  the server responds
- `fileInputRef` — hidden `<input type="file">` triggered by clicking the avatar

**Flow:**
1. User clicks the avatar circle → hidden file input opens
2. `handleAvatarChange` is called with the selected file
3. A local `ObjectURL` preview is set immediately (no server round-trip yet)
4. `authService.uploadAvatar(file)` is called
5. On success: `useAuthStore().setUser(updatedUser)` persists the new `avatar_url`
6. On error: an error message is shown; preview reverts

**Accepted file types:** `image/jpeg`, `image/png`, `image/webp`

### Top Bar — `frontend-next/src/components/layout/TopBar.tsx`

Both avatar circles (the button trigger and the dropdown panel user info section)
conditionally render either:
- An `<img>` when `user.profile.avatar_url` is set
- The initials `<div>` as a fallback

A "Profile" button was added to the dropdown that opens the `ProfileModal`.
The `ProfileModal` is rendered at the end of the component (after `</header>`).

### Sidebar — `frontend-next/src/components/layout/Sidebar.tsx`

A user mini-card is rendered at the footer of the sidebar with the same
avatar-or-initials conditional display.

---

## 5. Data Flow

```
User selects file in ProfileModal
        │
        ▼
Local ObjectURL preview rendered immediately
        │
        ▼
POST /api/v1/users/me/avatar (multipart)
        │
        ▼
Backend: validate → upload_avatar() → Supabase Storage (upsert)
        │
        ▼
Supabase returns public URL  e.g.
  https://xyz.supabase.co/storage/v1/object/public/intervIQ/avatars/42
        │
        ▼
Backend: merge avatar_url into user.profile → return updated User
        │
        ▼
Frontend: useAuthStore().setUser(updatedUser)
  → Zustand persist middleware writes to localStorage
        │
        ▼
All components re-render with new avatar_url:
  TopBar button  |  TopBar dropdown  |  Sidebar footer
```

---

## 6. Persistence

`avatar_url` is stored in the `user.profile` JSON column. The Zustand
`useAuthStore` uses `persist` middleware so the user object (including
`profile.avatar_url`) survives page reloads without a fresh API call.

---

## 7. Files Changed

| File | Change |
|---|---|
| `backend/requirements.txt` | Added `supabase>=2.0.0` |
| `backend/app/core/config.py` | Added `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_BUCKET_PROFILE_PHOTOS` |
| `backend/app/services/storage_service.py` | **New file** — `upload_avatar()` |
| `backend/app/api/v1/users.py` | Added `POST /users/me/avatar` endpoint |
| `frontend-next/src/lib/api.ts` | Added `postMultipart<T>()` method |
| `frontend-next/src/lib/services/authService.ts` | Added `uploadAvatar(file)` |
| `frontend-next/src/components/modals/ProfileModal.tsx` | Avatar upload UI, preview, spinner |
| `frontend-next/src/components/layout/TopBar.tsx` | Avatar display, Profile button, ProfileModal mount |
| `frontend-next/src/components/layout/Sidebar.tsx` | User mini-card with avatar at footer |

---

## 8. Supabase Setup Checklist

- [ ] Create a bucket named `intervIQ` (or whatever `SUPABASE_BUCKET_PROFILE_PHOTOS` is set to)
- [ ] Set the bucket to **public** (so generated URLs are accessible without a JWT)
- [ ] Add a storage policy allowing `INSERT` / `UPDATE` for authenticated users (or use the service role key which bypasses RLS)
- [ ] Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `backend/.env`
- [ ] Run `pip install -r requirements.txt` to install the `supabase` package
