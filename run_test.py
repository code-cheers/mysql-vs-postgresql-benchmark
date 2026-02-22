#!/usr/bin/env python3
import argparse
import subprocess as sp
import sys
from os import environ
from pathlib import Path

DOCKER_CONTAINER_NAME = "sql-db-performance-tests"
OPTIONS_TO_TEST_CASES = {
    1: 'INSERT_USERS',
    2: 'SELECT_USERS_BY_ID',
    3: 'SELECT_SORTED_BY_ID_USER_PAGES',
    4: 'UPDATE_USER_EMAILS_BY_ID',
    5: 'UPDATE_USER_UPDATED_ATS_BY_ID',
    6: 'DELETE_ORDERS_BY_ID',
    7: 'DELETE_ORDERS_IN_BATCHES_BY_ID'
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run SQL DB performance test case against MySQL/PostgreSQL in Docker"
    )
    parser.add_argument(
        "--test-case",
        help="Test case option (1..7) or test case name, for example INSERT_USERS",
    )
    parser.add_argument(
        "--db",
        help="DB option (1 or 2) or name (mysql/postgresql)",
    )
    parser.add_argument(
        "--output-dir",
        default=environ.get("RESULTS_DIR", "result"),
        help="Directory where test logs will be saved (default: RESULTS_DIR env or result)",
    )
    return parser.parse_args()


def optional_env(name):
    value = environ.get(name)
    return value if value else None


def normalize_test_case(test_case_input):
    if test_case_input is None:
        return None

    candidate = str(test_case_input).strip()
    if not candidate:
        return None

    if candidate.isdigit():
        option = int(candidate)
        if option in OPTIONS_TO_TEST_CASES:
            return OPTIONS_TO_TEST_CASES[option]
        raise ValueError(f"Unsupported test case option: {candidate}")

    normalized = candidate.upper().replace("-", "_")
    if normalized in OPTIONS_TO_TEST_CASES.values():
        return normalized

    raise ValueError(f"Unsupported test case: {candidate}")


def normalize_db(db_input):
    if db_input is None:
        return None

    candidate = str(db_input).strip().lower()
    if not candidate:
        return None

    if candidate in {"1", "mysql"}:
        return 1
    if candidate in {"2", "postgresql", "postgres", "pg"}:
        return 2
    raise ValueError(f"Unsupported db option: {db_input}. Supported options are 1/2 or mysql/postgresql")


def choose_test_case_interactive():
    options = '\n'.join([f'{k} - {v}' for k, v in OPTIONS_TO_TEST_CASES.items()])
    test_case_input = input(f"""
Choose test case. Available options:
{options}
""").strip()

    if not test_case_input:
        raise ValueError("Test case must be chosen but was not!")

    test_case = normalize_test_case(test_case_input)
    print(f"Chosen test case: {test_case}")
    return test_case


def choose_db_interactive():
    db_type = int(input(f"""
Choose db. Available options:
1 - MySQL
2 - PostgreSQL
""").strip() or 1)
    print()
    return db_type


def db_connection_config(db_type):
    db_host = environ.get("DB_HOST", "localhost")
    if db_type == 1:
        return {
            "db_type_name": "mysql",
            "data_source_url": f"jdbc:mysql://{db_host}:3306/performance",
            "data_source_username": "root",
            "data_source_password": "performance",
            "data_source_connection_pool_size": str(environ.get("DATA_SOURCE_CONNECTION_POOL_SIZE", 8 * 16)),
            "label": "MySQL",
        }
    if db_type == 2:
        return {
            "db_type_name": "postgresql",
            "data_source_url": f"jdbc:postgresql://{db_host}:5432/performance",
            "data_source_username": "postgres",
            "data_source_password": "performance",
            "data_source_connection_pool_size": str(environ.get("DATA_SOURCE_CONNECTION_POOL_SIZE", 8 * 8)),
            "label": "PostgreSQL",
        }
    raise ValueError(f"Unsupported db option: {db_type}. Supported options are 1 and 2.")


def result_file_path(test_case, db_type_name, queries_rate, output_dir):
    name = f"{test_case.lower()}_{db_type_name}"
    if queries_rate:
        name += f"_{queries_rate}_qps"
    name += ".txt"
    target = Path(output_dir).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target / name


def run_test_in_docker(test_case, db_config, queries_to_execute, queries_rate):
    docker_env_keys = [
        "DATA_SOURCE_URL",
        "DATA_SOURCE_USERNAME",
        "DATA_SOURCE_PASSWORD",
        "DATA_SOURCE_CONNECTION_POOL_SIZE",
        "TEST_CASE",
    ]
    if queries_to_execute:
        docker_env_keys.append("QUERIES_TO_EXECUTE")
    if queries_rate:
        docker_env_keys.append("QUERIES_RATE")

    run_env = environ.copy()
    run_env.update({
        "DATA_SOURCE_URL": db_config["data_source_url"],
        "DATA_SOURCE_USERNAME": db_config["data_source_username"],
        "DATA_SOURCE_PASSWORD": db_config["data_source_password"],
        "DATA_SOURCE_CONNECTION_POOL_SIZE": db_config["data_source_connection_pool_size"],
        "TEST_CASE": test_case,
    })
    if queries_to_execute:
        run_env["QUERIES_TO_EXECUTE"] = queries_to_execute
    if queries_rate:
        run_env["QUERIES_RATE"] = queries_rate

    sp.run(["docker", "rm", DOCKER_CONTAINER_NAME], check=False, stdout=sp.DEVNULL, stderr=sp.DEVNULL)

    cmd = ["docker", "run", "--network", "host"]
    for key in docker_env_keys:
        cmd += ["-e", key]
    cmd += ["--name", DOCKER_CONTAINER_NAME, DOCKER_CONTAINER_NAME]

    sp.run(cmd, env=run_env, check=True)

try:
    args = parse_args()

    test_case = normalize_test_case(args.test_case)
    if not test_case:
        test_case = choose_test_case_interactive()

    db_type = normalize_db(args.db)
    if not db_type:
        db_type = choose_db_interactive()

    db_config = db_connection_config(db_type)
    print(f"Running with {db_config['label']}")
    print()

    # 8 cores available - usually a few connections per core is where the optimal amount lives;
    # here, we are stress/load testing - it's not about the best absolute amount; better to use too many than too few connections
    # Empirically, MySQL benefits from more connections
    queries_to_execute = optional_env("QUERIES_TO_EXECUTE")
    queries_rate = optional_env("QUERIES_RATE")

    run_test_in_docker(test_case, db_config, queries_to_execute, queries_rate)

    print()
    print("Tests have finished running, exporting results to a file...")

    results_file = result_file_path(test_case, db_config["db_type_name"], queries_rate, args.output_dir)
    with results_file.open("w", encoding="utf-8") as out:
        sp.run(["docker", "logs", DOCKER_CONTAINER_NAME], stdout=out, stderr=sp.STDOUT, check=False)

    print()
    print(f"Results exported to the {results_file} file")
except KeyboardInterrupt:
    print("Process interrupted by user, exiting")
except Exception as e:
    print(str(e))
    sys.exit(-1)
