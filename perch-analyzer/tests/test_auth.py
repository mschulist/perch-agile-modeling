import pytest

from perch_analyzer import auth
from perch_analyzer.app_context import AppContext

from .conftest import TEST_PASSWORD, TEST_USERNAME


def test_hash_round_trips():
    stored = auth.hash_password("hunter2")
    assert auth.check_password("hunter2", stored)
    assert not auth.check_password("hunter3", stored)


def test_hashes_are_salted():
    assert auth.hash_password("same") != auth.hash_password("same")


@pytest.mark.parametrize("stored", ["", "plaintext", "md5$00$00", "scrypt$zz$zz"])
def test_malformed_hashes_never_match(stored: str):
    assert not auth.check_password("anything", stored)


def test_usernames_are_stripped_and_validated():
    assert auth.normalize_username("  ana ") == "ana"
    with pytest.raises(ValueError):
        auth.normalize_username("   ")
    with pytest.raises(ValueError):
        auth.normalize_username("x" * (auth.MAX_USERNAME_LENGTH + 1))


def test_create_and_verify_user(ctx: AppContext):
    analyzer_db = ctx.analyzer_db
    analyzer_db.create_user(" ana ", "pw")
    assert analyzer_db.verify_user("ana", "pw")
    assert not analyzer_db.verify_user("ana", "wrong")
    assert not analyzer_db.verify_user("nobody", "pw")
    assert [u.username for u in analyzer_db.list_users()] == ["ana", TEST_USERNAME]
    assert analyzer_db.count_users() == 2


def test_duplicate_username_is_refused(ctx: AppContext):
    with pytest.raises(ValueError, match="already exists"):
        ctx.analyzer_db.create_user(TEST_USERNAME, "other")


def test_empty_password_is_refused(ctx: AppContext):
    with pytest.raises(ValueError):
        ctx.analyzer_db.create_user("ana", "")


def test_set_password_and_delete(ctx: AppContext):
    analyzer_db = ctx.analyzer_db
    analyzer_db.set_password(TEST_USERNAME, "new")
    assert analyzer_db.verify_user(TEST_USERNAME, "new")
    assert not analyzer_db.verify_user(TEST_USERNAME, TEST_PASSWORD)

    analyzer_db.delete_user(TEST_USERNAME)
    assert not analyzer_db.user_exists(TEST_USERNAME)
    with pytest.raises(KeyError):
        analyzer_db.delete_user(TEST_USERNAME)
    with pytest.raises(KeyError):
        analyzer_db.set_password(TEST_USERNAME, "x")


def test_existing_database_gains_users_table(ctx: AppContext):
    """A database made before logins existed opens, and gets a users table."""
    import sqlite3

    from perch_analyzer.db.db import AnalyzerDB

    db_path = ctx.data_dir / ctx.config.db_path
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE users")
    with sqlite3.connect(db_path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    assert "users" not in tables

    reopened = AnalyzerDB(ctx.config)
    assert reopened.count_users() == 0
    assert len(reopened.get_all_classifiers()) == 1
