"""Supabase Storage helpers — profile photo uploads."""

from app.core.config import settings


def upload_avatar(file_bytes: bytes, content_type: str, user_id: int) -> str | None:
    """
    Upload a profile photo to Supabase Storage.

    Stores the file at `avatars/{user_id}.{ext}` in the profile-photos bucket,
    overwriting any previous upload for the same user.

    Returns the public URL on success, or None if storage is not configured / fails.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return None

    try:
        from supabase import create_client  # lazy import — only needed at runtime

        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        bucket = settings.SUPABASE_BUCKET_PROFILE_PHOTOS

        # Fixed path per user — no extension — so any new upload always overwrites
        # the same object regardless of image format.
        path = f"avatars/{user_id}"

        # upsert overwrites the previous photo
        client.storage.from_(bucket).upload(
            path,
            file_bytes,
            {"content-type": content_type, "upsert": "true"},
        )

        public_url: str = client.storage.from_(bucket).get_public_url(path)
        return public_url
    except Exception:
        return None
