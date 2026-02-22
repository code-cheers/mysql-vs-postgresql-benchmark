#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"
RESULTS_DIR="${RESULTS_DIR:-result}"
mkdir -p "${RESULTS_DIR}"

usage() {
  cat <<'EOF'
Usage:
  ./run_query_tests.bash [mysql|postgresql|both] [by-id|sorted-pages|both]

Examples:
  ./run_query_tests.bash
  ./run_query_tests.bash mysql by-id
  ./run_query_tests.bash postgresql sorted-pages

Optional:
  RESULTS_DIR=result ./run_query_tests.bash
EOF
}

db_target="${1:-both}"
test_target="${2:-both}"

case "${db_target}" in
  mysql|postgresql|both) ;;
  *)
    usage
    exit 1
    ;;
esac

case "${test_target}" in
  by-id|sorted-pages|both) ;;
  *)
    usage
    exit 1
    ;;
esac

run_single_test() {
  local db="$1"
  local test="$2"

  local db_option
  local db_name
  local test_option
  local test_case_name
  local queries_to_execute
  local queries_rate

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

  case "${test}" in
    by-id)
      test_option=2
      test_case_name="select_users_by_id"
      queries_to_execute=500000
      queries_rate=50000
      ;;
    sorted-pages)
      test_option=3
      test_case_name="select_sorted_by_id_user_pages"
      queries_to_execute=50000
      queries_rate=5000
      ;;
    *)
      echo "Unsupported test: ${test}"
      exit 1
      ;;
  esac

  echo
  echo "=== Running ${test_case_name} on ${db_name} (${queries_rate} qps, ${queries_to_execute} queries) ==="

  (
    export QUERIES_TO_EXECUTE="${queries_to_execute}"
    export QUERIES_RATE="${queries_rate}"
    ./run_test.py --test-case "${test_option}" --db "${db_option}" --output-dir "${RESULTS_DIR}"
  )

  local result_file="${RESULTS_DIR}/${test_case_name}_${db_name}_${queries_rate}_qps.txt"
  if [[ ! -f "${result_file}" ]]; then
    result_file="${RESULTS_DIR}/${test_case_name}_${db_name}.txt"
  fi

  echo "Result file: ${result_file}"
  rg -n "Total test duration|Actual queries rate|Mean:|Percentile 99:|Percentile 99.9:" "${result_file}" || true
}

declare -a dbs=()
declare -a tests=()

if [[ "${db_target}" == "both" ]]; then
  dbs=("mysql" "postgresql")
else
  dbs=("${db_target}")
fi

if [[ "${test_target}" == "both" ]]; then
  tests=("sorted-pages" "by-id")
else
  tests=("${test_target}")
fi

for test in "${tests[@]}"; do
  for db in "${dbs[@]}"; do
    run_single_test "${db}" "${test}"
  done
done

echo
echo "Done."
