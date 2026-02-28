# MySQL vs PostgreSQL Benchmark

## 启动数据库容器（MySQL + PostgreSQL）

```bash
./build_and_run_mysql.bash
./build_and_run_postgresql.bash
```

## 执行插入压测（同时跑 MySQL 和 PostgreSQL）

```bash
make insert-both
```

插入对比输出目录：

- `result/insert_only/mysql_vs_postgresql_comparison.png`
- `result/insert_only/benchmark_summary.csv`

## 执行查询压测（参考插入的一键封装）

跑全部查询场景（`by-id` + `sorted-pages`）并出图：

```bash
make query-both
```

只跑 `by-id` 并出图：

```bash
make query-by-id
```

只跑 `sorted-pages` 并出图：

```bash
make query-sorted-pages
```

查询对比输出目录：

- `result/query_only/mysql_vs_postgresql_comparison.png`
- `result/query_only/benchmark_summary.csv`

## 执行更新压测（单场景：按主键 ID 批量更新 `email`）

跑 MySQL + PostgreSQL 并出图：

```bash
make update-both
```

只跑 MySQL 或 PostgreSQL：

```bash
make update-run DB=mysql
make update-run DB=postgresql
```

更新对比输出目录：

- `result/update_only/mysql_vs_postgresql_comparison.png`
- `result/update_only/benchmark_summary.csv`
