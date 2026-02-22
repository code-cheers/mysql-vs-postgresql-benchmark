SHELL := /bin/bash

RESULT_DIR ?= result
DB ?= both
TEST ?= both
TEST_CASE ?= 2
PYTHON ?= python3
PLOT_PYTHON ?= $(shell if [ -x ./.venv/bin/python ]; then echo ./.venv/bin/python; else echo $(PYTHON); fi)

.PHONY: help db-mysql db-postgresql db-up tests-build prepare run-case insert-both benchmark-query plot compare

help:
	@echo "Targets:"
	@echo "  make db-mysql                     # build + run MySQL container"
	@echo "  make db-postgresql                # build + run PostgreSQL container"
	@echo "  make db-up                        # build + run both DBs"
	@echo "  make tests-build                  # build performance tests Docker image"
	@echo "  make prepare                      # db-up + tests-build"
	@echo "  make run-case DB=mysql TEST_CASE=2 [RESULT_DIR=result]"
	@echo "  make insert-both [RESULT_DIR=result]   # run INSERT_USERS for MySQL + PostgreSQL and plot insert comparison"
	@echo "  make benchmark-query [DB=both] [TEST=both] [RESULT_DIR=result]"
	@echo "  make plot [RESULT_DIR=result]     # build comparison charts from result logs"
	@echo "  make compare [RESULT_DIR=result]  # prepare + benchmark-query + plot"

db-mysql:
	./build_and_run_mysql.bash

db-postgresql:
	./build_and_run_postgresql.bash

db-up: db-mysql db-postgresql

tests-build:
	./build_performance_tests.bash

prepare: db-up tests-build

run-case:
	@if [[ "$(DB)" != "mysql" && "$(DB)" != "postgresql" ]]; then \
		echo "DB must be mysql or postgresql for run-case"; \
		exit 1; \
	fi
	@mkdir -p "$(RESULT_DIR)"
	QUERIES_TO_EXECUTE="$(QUERIES_TO_EXECUTE)" \
	QUERIES_RATE="$(QUERIES_RATE)" \
	DATA_SOURCE_CONNECTION_POOL_SIZE="$(DATA_SOURCE_CONNECTION_POOL_SIZE)" \
	./run_test.py --test-case "$(TEST_CASE)" --db "$(DB)" --output-dir "$(RESULT_DIR)"

insert-both:
	@mkdir -p "$(RESULT_DIR)" "$(RESULT_DIR)/insert_only"
	QUERIES_TO_EXECUTE=500000 QUERIES_RATE=10000 \
	./run_test.py --test-case 1 --db mysql --output-dir "$(RESULT_DIR)"
	QUERIES_TO_EXECUTE=500000 QUERIES_RATE=10000 \
	./run_test.py --test-case 1 --db postgresql --output-dir "$(RESULT_DIR)"
	cp -f "$(RESULT_DIR)/insert_users_mysql_10000_qps.txt" "$(RESULT_DIR)/insert_users_postgresql_10000_qps.txt" "$(RESULT_DIR)/insert_only/"
	MPLBACKEND=Agg "$(PLOT_PYTHON)" ./plot_results.py --input-dir "$(RESULT_DIR)/insert_only" --output-dir "$(RESULT_DIR)/insert_only"

benchmark-query:
	@mkdir -p "$(RESULT_DIR)"
	RESULTS_DIR="$(RESULT_DIR)" ./run_query_tests.bash "$(DB)" "$(TEST)"

plot:
	@mkdir -p "$(RESULT_DIR)"
	MPLBACKEND=Agg "$(PLOT_PYTHON)" ./plot_results.py --input-dir "$(RESULT_DIR)" --output-dir "$(RESULT_DIR)"

compare: prepare benchmark-query plot
