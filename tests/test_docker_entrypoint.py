from sqlalchemy.engine import make_url

from scripts.docker_entrypoint import configure_database_url


def test_container_database_url_encodes_password_safely():
    environment = {
        "DATABASE_HOST": "postgres",
        "POSTGRES_DB": "jira_ai",
        "POSTGRES_USER": "jira_ai",
        "POSTGRES_PASSWORD": "password with / and @",
    }

    configure_database_url(environment)

    database_url = make_url(environment["DATABASE_URL"])
    assert database_url.drivername == "postgresql+psycopg"
    assert database_url.username == "jira_ai"
    assert database_url.password == "password with / and @"
    assert database_url.host == "postgres"
    assert database_url.database == "jira_ai"


def test_container_database_url_preserves_local_configuration_without_host():
    environment = {"DATABASE_URL": "sqlite:///./data/jira_ai.db"}

    configure_database_url(environment)

    assert environment["DATABASE_URL"] == "sqlite:///./data/jira_ai.db"
