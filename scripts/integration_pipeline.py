#!/usr/bin/env python
import sys
import anyio
import dagger
from datetime import datetime

async def test():
  async with dagger.Connection(dagger.Config(log_output=sys.stderr)) as client:
    database = (
      client.container()
      .from_("postgres:15.2")
      .with_env_variable("POSTGRES_USER", "postgres")
      .with_env_variable("POSTGRES_PASSWORD", "password")
      .with_env_variable("POSTGRES_DB", "postgres")
      .with_exec(["postgres"])
      .with_exposed_port(5432)
    )

    src = client.host().directory(".")

    test_base = (
      client.container(platform=dagger.Platform("linux/amd64"))
      .from_("python:3.11-slim-buster")
      .with_service_binding("db", database)
      .with_mounted_directory("/usr/app", src)
      .with_workdir("/usr/app")
      .with_exec(["apt-get", "update"])
      .with_exec(["apt-get", "install", "-y", "postgresql", "libpq-dev", "git"])
      .with_exec(["python", "-m", "pip", "install", "tox"])
      .with_env_variable("NO_DAGGER_CACHE", str(datetime.now()))
    )

    setup_db = (
      test_base
      .with_env_variable("PGHOST", "db")
      .with_env_variable("PGUSER", "postgres")
      .with_env_variable("PGDATABASE", "postgres")
      .with_env_variable("PGPASSWORD", "password")
      .with_exec(["./test/setup_db.sh"])
    )

    integration = (
      setup_db
      .with_env_variable("POSTGRES_TEST_HOST", "db")
      .with_env_variable("TOXENV", "integration")
      .with_env_variable("PYTEST_ADDOPTS", "-v --color=yes -n4 --csv integration_results.csv")
      .with_env_variable("DBT_INVOCATION_ENV", "github-actions")
      .with_env_variable("DBT_TEST_USER_1", "dbt_test_user_1")
      .with_env_variable("DBT_TEST_USER_2", "dbt_test_user_2")
      .with_env_variable("DBT_TEST_USER_3", "dbt_test_user_3")
      .with_exec(["tox"])
    )

    # execute
    await integration.exit_code()


if __name__ == "__main__":
    anyio.run(test)