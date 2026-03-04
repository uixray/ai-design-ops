"""
API Key management via Redis.
Structure:
  key:{token}:quota   → int
  key:{token}:used    → int
  key:{token}:label   → str
  key:{token}:created → str (ISO)
  trial:{ip}          → int (TTL 30 days)
"""
import os
import redis
import secrets
from datetime import datetime

r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, db=0, decode_responses=True)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
FREE_TRIAL_LIMIT = 10
FREE_TRIAL_TTL = 86400 * 30  # 30 days


def generate_key(quota: int, label: str = "") -> dict:
    """Create a new API key with given quota."""
    token = "cdocs_" + secrets.token_urlsafe(24)
    r.set(f"key:{token}:quota",   quota)
    r.set(f"key:{token}:used",    0)
    r.set(f"key:{token}:label",   label)
    r.set(f"key:{token}:created", datetime.utcnow().isoformat())
    return {"token": token, "quota": quota, "label": label}


def validate_key(token: str) -> dict | None:
    """Return {quota, used, remaining} or None if key not found."""
    quota = r.get(f"key:{token}:quota")
    if quota is None:
        return None
    used = int(r.get(f"key:{token}:used") or 0)
    return {
        "quota":     int(quota),
        "used":      used,
        "remaining": int(quota) - used,
    }


def consume_key(token: str) -> bool:
    """Decrement quota. Return True on success, False if exhausted/not found."""
    info = validate_key(token)
    if not info or info["remaining"] <= 0:
        return False
    r.incr(f"key:{token}:used")
    return True


def get_trial_remaining(ip: str) -> int:
    """Return remaining free trial requests for given IP."""
    used = int(r.get(f"trial:{ip}") or 0)
    return max(0, FREE_TRIAL_LIMIT - used)


def consume_trial(ip: str) -> bool:
    """Decrement trial counter. Return True on success, False if exhausted."""
    used = int(r.get(f"trial:{ip}") or 0)
    if used >= FREE_TRIAL_LIMIT:
        return False
    r.incr(f"trial:{ip}")
    r.expire(f"trial:{ip}", FREE_TRIAL_TTL)
    return True


def list_keys() -> list[dict]:
    """Return all keys with stats (token preview only)."""
    tokens = {k.split(":")[1] for k in r.scan_iter("key:*:quota")}
    result = []
    for t in tokens:
        info = validate_key(t)
        if info:
            info["token_preview"] = t[:16] + "..."
            info["label"]   = r.get(f"key:{t}:label")   or ""
            info["created"] = r.get(f"key:{t}:created") or ""
            result.append(info)
    return sorted(result, key=lambda x: x.get("created", ""), reverse=True)


def delete_key(token: str) -> bool:
    """Delete a key. Returns True if key existed."""
    if r.get(f"key:{token}:quota") is None:
        return False
    r.delete(f"key:{token}:quota", f"key:{token}:used",
             f"key:{token}:label", f"key:{token}:created")
    return True
