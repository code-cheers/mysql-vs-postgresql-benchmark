# SQL 数据库性能测试（MySQL vs PostgreSQL）

本项目用于在本地 Docker 环境下，对 MySQL 和 PostgreSQL 进行压测与对比。

## 环境要求

* Docker
* Bash
* Python 3（用于 `run_test.py` 和 `plot_results.py`）
* `matplotlib`（用于生成图表）

安装 `matplotlib`：
```bash
python3 -m pip install matplotlib
```

## 一键流程（Makefile）

`Makefile` 已封装以下能力：
* 创建并启动 MySQL / PostgreSQL
* 构建测试镜像
* 执行压测并将结果保存到 `result/`
* 生成 MySQL vs PostgreSQL 对比图

完整执行（推荐）：
```bash
make compare
```

此命令会依次执行：
1. `make db-up`
2. `make tests-build`
3. `make benchmark-query`
4. `make plot`

## 常用命令

查看可用目标：
```bash
make help
```

仅启动数据库：
```bash
make db-up
```

仅构建测试镜像：
```bash
make tests-build
```

运行默认查询基准（两类查询 x 两个数据库），结果写入 `result/`：
```bash
make benchmark-query
```

只跑 MySQL 的按 ID 查询：
```bash
make benchmark-query DB=mysql TEST=by-id
```

运行单个测试用例（`TEST_CASE` 对应 `run_test.py` 的编号）：
```bash
make run-case DB=postgresql TEST_CASE=2
```

指定输出目录：
```bash
make benchmark-query RESULT_DIR=result
make plot RESULT_DIR=result
```

## 输出结果

执行后会在 `result/` 下生成：
* 原始日志：`*.txt`
* 汇总 CSV：`benchmark_summary.csv`
* 对比图：`mysql_vs_postgresql_comparison.png`

图中包含：
* **Actual QPS**（越高越好）
* **P99 延迟**（越低越好）

## 手动脚本方式（不走 Makefile）

启动数据库：
```bash
./build_and_run_mysql.bash
./build_and_run_postgresql.bash
```

构建测试镜像：
```bash
./build_performance_tests.bash
```

交互式运行单个测试（结果默认写入 `result/`）：
```bash
./run_test.py
```

运行查询脚本（结果写入 `result/`）：
```bash
./run_query_tests.bash
```

## 可调参数

可通过环境变量覆盖测试参数：
```bash
export QUERIES_TO_EXECUTE=<总查询次数>
export QUERIES_RATE=<每秒查询数>
export DATA_SOURCE_CONNECTION_POOL_SIZE=<连接池大小>
export DB_HOST=<数据库主机，默认 localhost>
```

## Schema

数据库 schema 示例见：
* `postgresql/schema.sql`
* `mysql/schema.sql`
