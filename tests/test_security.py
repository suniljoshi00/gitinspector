import hashlib
import hmac

from gitinspector.security import verify_github_signature


def test_accepts_valid_signature() -> None:
    body = b'{"action":"opened"}'
    secret = "test-secret"
    signature = "sha256=" + hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    assert verify_github_signature(body, signature, secret)


def test_rejects_invalid_signature() -> None:
    assert not verify_github_signature(b"payload", "sha256=wrong", "secret")
    assert not verify_github_signature(b"payload", None, "secret")
    assert not verify_github_signature(b"payload", "sha256=anything", "")

