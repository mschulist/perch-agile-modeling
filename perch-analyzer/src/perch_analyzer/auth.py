"""Password hashing for GUI logins.

Deliberately modest: a salted scrypt hash from the standard library, enough to
keep plaintext passwords out of `analyzer.db` on a shared lab machine. There
are no roles; every account can do everything.
"""

import hashlib
import hmac
import os

_SCHEME = "scrypt"
_SALT_BYTES = 16
# Standard interactive-login parameters; about 50 ms per hash.
_N, _R, _P = 2**14, 8, 1

MAX_USERNAME_LENGTH = 64


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)


def hash_password(password: str) -> str:
    """Hash `password` with a fresh random salt, as `scrypt$<salt>$<hash>`."""
    salt = os.urandom(_SALT_BYTES)
    return f"{_SCHEME}${salt.hex()}${_derive(password, salt).hex()}"


def check_password(password: str, stored: str) -> bool:
    """Whether `password` matches a hash produced by `hash_password`."""
    try:
        scheme, salt_hex, hash_hex = stored.split("$")
        if scheme != _SCHEME:
            return False
        expected = bytes.fromhex(hash_hex)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    return hmac.compare_digest(_derive(password, salt), expected)


def normalize_username(username: str) -> str:
    """Strip and validate a username, raising `ValueError` if unusable."""
    name = username.strip()
    if not name:
        raise ValueError("username must not be empty")
    if len(name) > MAX_USERNAME_LENGTH:
        raise ValueError(
            f"username must be at most {MAX_USERNAME_LENGTH} characters long"
        )
    return name


def validate_password(password: str) -> str:
    if not password:
        raise ValueError("password must not be empty")
    return password
