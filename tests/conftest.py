"""
Shared fixtures for AuthBridge test suite.
"""
import os
import pytest
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Use a temp DB for all tests
@pytest.fixture(scope="session", autouse=True)
def test_db(tmp_path_factory):
    db_path = str(tmp_path_factory.mktemp("db") / "test_authbridge.db")
    os.environ["SQLITE_DB_PATH"] = db_path
    os.environ["CHROMA_PERSIST_DIR"] = str(tmp_path_factory.mktemp("chroma"))
    from database.db import init_database, seed_demo_data
    init_database()
    seed_demo_data()
    yield db_path


@pytest.fixture
def sample_employee_id():
    return "EMP001"


@pytest.fixture
def sample_tenant_id():
    return "authbridge"
