import hashlib
import hmac


def verify_github_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if not secret or not signature:
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

