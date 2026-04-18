import hmac
from hashlib import sha256

from inspector.verify import verify_signature


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()


def test_valid_signature_passes() -> None:
    body = b'{"event":"subscription.created","id":123}'
    secret = "top-secret"
    assert verify_signature(body, sign(body, secret), secret) is True


def test_tampered_body_fails() -> None:
    body = b'{"event":"subscription.created"}'
    tampered = b'{"event":"subscription.deleted"}'
    secret = "top-secret"
    assert verify_signature(tampered, sign(body, secret), secret) is False


def test_tampered_signature_fails() -> None:
    body = b'{"event":"member_created"}'
    secret = "top-secret"
    signature = sign(body, secret)
    bad_signature = ("0" if signature[0] != "0" else "1") + signature[1:]
    assert verify_signature(body, bad_signature, secret) is False


def test_wrong_secret_fails() -> None:
    body = b'{"event":"order.purchased"}'
    assert verify_signature(body, sign(body, "right-secret"), "wrong-secret") is False


def test_empty_signature_fails() -> None:
    assert verify_signature(b'{"event":"plan.created"}', "", "top-secret") is False
