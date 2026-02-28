#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"
RESULTS_DIR="${RESULTS_DIR:-result}"
QUERIES_TO_EXECUTE="${QUERIES_TO_EXECUTE:-50000}"
QUERIES_RATE="${QUERIES_RATE:-5000}"
mkdir -p "${RESULTS_DIR}"

usage() {
  cat <<'EOF'
Usage:
  ./run_update_tests.bash [mysql|postgresql|both]

Examples:
  ./run_update_tests.bash
  ./run_update_tests.bash mysql
  ./run_update_tests.bash postgresql

Optional:
  RESULTS_DIR=result QUERIES_TO_EXECUTE=50000 QUERIES_RATE=5000 ./run_update_tests.bash
EOF
}

db_target="${1:-both}"

case "${db_target}" in
  mysql|postgresql|both) ;;
  *)
    usage
    exit 1
    ;;
esac

run_single_test() {
  local db="$1"

  local db_option
  local db_name
  local test_option=4
  local test_case_name="update_user_emails_by_id"

  case "${db}" in
    mysql)
      db_option=1
      db_name="mysql"
      ;;
    postgresql)
      db_option=2
      db_name="postgresql"
      ;;
    *)
      echo "Unsupported db: ${db}"
      exit 1
      ;;
  esac

  echo
  echo "=== Running ${test_case_name} on ${db_name} (${QUERIES_RATE} qps, ${QUERIES_TO_EXECUTE} queries) ==="

  (
    export QUERIES_TO_EXECUTE="${QUERIES_TO_EXECUTE}"
    export QUERIES_RATE="${QUERIES_RATE}"
    ./run_test.py --test-case "${test_option}" --db "${db_option}" --output-dir "${RESULTS_DIR}"
  )

  local result_file="${RESULTS_DIR}/${test_case_name}_${db_name}_${QUERIES_RATE}_qps.txt"
  if [[ ! -f "${result_file}" ]]; then
    result_file="${RESULTS_DIR}/${test_case_name}_${db_name}.txt"
  fi

  echo "Result file: ${result_file}"
  rg -n "Total test duration|Actual queries rate|Mean:|Percentile 99:|Percentile 99.9:" "${result_file}" || true
}

declare -a dbs=()

if [[ "${db_target}" == "both" ]]; then
  dbs=("mysql" "postgresql")
else
  dbs=("${db_target}")
fi

for db in "${dbs[@]}"; do
  run_single_test "${db}"
done

echo
echo "Done."
