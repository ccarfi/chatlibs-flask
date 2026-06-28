"""Vercel Blob storage for generated images.

Images are otherwise ephemeral (data URIs shown in-app only), which means the
shareable /story page has no picture. Uploading to Vercel Blob gives a durable
public https URL we can put in share links and Open Graph tags.

Vercel Blob has no native object expiry, so delete_old_images() (run daily by a
Vercel Cron hitting /api/cleanup) prunes anything older than 30 days.

Requires BLOB_READ_WRITE_TOKEN in the environment (auto-added when you create a
Blob store in the Vercel dashboard). When it's absent, blob_enabled() is False
and callers fall back to inline data URIs.
"""

import datetime
import os

# All ChatLibs images live under this prefix so cleanup never touches anything
# else in the store.
PREFIX = "chatlibs/"
MAX_AGE_DAYS = 30


def blob_enabled():
    return bool(os.getenv("BLOB_READ_WRITE_TOKEN"))


def upload_image(data, content_type="image/jpeg"):
    """Upload JPEG bytes to Vercel Blob; return the public https URL."""
    import vercel_blob

    resp = vercel_blob.put(
        PREFIX + "story.jpg",
        data,
        {"addRandomSuffix": "true", "contentType": content_type},
    )
    return resp["url"]


def _parse_uploaded_at(value):
    """Parse Vercel Blob's ISO-8601 uploadedAt (e.g. '2026-06-28T12:00:00.000Z')."""
    if isinstance(value, datetime.datetime):
        return value
    return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def delete_old_images(max_age_days=MAX_AGE_DAYS):
    """Delete ChatLibs blobs older than max_age_days. Returns the count deleted."""
    import vercel_blob

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=max_age_days
    )
    deleted = 0
    cursor = None
    while True:
        opts = {"limit": "1000"}
        if cursor:
            opts["cursor"] = cursor
        result = vercel_blob.list(opts)

        stale = [
            b["url"]
            for b in result.get("blobs", [])
            if b.get("pathname", "").startswith(PREFIX)
            and _parse_uploaded_at(b["uploadedAt"]) < cutoff
        ]
        if stale:
            vercel_blob.delete(stale)
            deleted += len(stale)

        if result.get("hasMore") and result.get("cursor"):
            cursor = result["cursor"]
        else:
            break
    return deleted
