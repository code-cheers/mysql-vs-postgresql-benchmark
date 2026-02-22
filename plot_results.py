#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from pathlib import Path


TEST_CASE_RE = re.compile(r"Test case\s+([A-Z0-9_]+)\s+with\s+(MYSQL|POSTGRESQL)", re.MULTILINE)
ACTUAL_QPS_RE = re.compile(r"Actual queries rate:\s*([0-9]+)/s", re.MULTILINE)
MEAN_MS_RE = re.compile(r"Mean:\s*([0-9.]+)\s*ms", re.MULTILINE)
P99_MS_RE = re.compile(r"Percentile 99:\s*([0-9.]+)\s*ms", re.MULTILINE)
P999_MS_RE = re.compile(r"Percentile 99.9:\s*([0-9.]+)\s*ms", re.MULTILINE)


def parse_args():
    parser = argparse.ArgumentParser(description="Plot MySQL vs PostgreSQL benchmark results")
    parser.add_argument("--input-dir", default="result", help="Directory with benchmark .txt logs")
    parser.add_argument("--output-dir", default="result", help="Directory to store generated chart/csv")
    return parser.parse_args()


def parse_result_file(path):
    text = path.read_text(encoding="utf-8", errors="replace")

    test_case_match = TEST_CASE_RE.search(text)
    actual_qps_match = ACTUAL_QPS_RE.search(text)
    mean_match = MEAN_MS_RE.search(text)
    p99_match = P99_MS_RE.search(text)
    p999_match = P999_MS_RE.search(text)

    if not test_case_match or not actual_qps_match or not mean_match or not p99_match or not p999_match:
        return None

    return {
        "test_case": test_case_match.group(1),
        "db": test_case_match.group(2),
        "actual_qps": int(actual_qps_match.group(1)),
        "mean_ms": float(mean_match.group(1)),
        "p99_ms": float(p99_match.group(1)),
        "p999_ms": float(p999_match.group(1)),
        "source_file": path.name,
    }


def grouped_values(cases, lookup, db_name, metric):
    values = []
    missing = []
    for test_case in cases:
        row = lookup.get((test_case, db_name))
        if row is None:
            values.append(0.0)
            missing.append(True)
        else:
            values.append(float(row[metric]))
            missing.append(False)
    return values, missing


def annotate_bars(ax, bars, values, missing, integer=False):
    for idx, bar in enumerate(bars):
        x = bar.get_x() + bar.get_width() / 2
        y = bar.get_height()
        if missing[idx]:
            label = "n/a"
        elif integer:
            label = str(int(round(values[idx])))
        else:
            label = f"{values[idx]:.3f}"
        ax.text(x, y, label, ha="center", va="bottom", fontsize=8, rotation=90)


def write_summary_csv(rows, output_csv):
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["test_case", "db", "actual_qps", "mean_ms", "p99_ms", "p999_ms", "source_file"],
        )
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r["test_case"], r["db"])):
            writer.writerow(row)


def main():
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        print(f"Input directory does not exist: {input_dir}")
        sys.exit(1)

    rows = []
    for path in sorted(input_dir.glob("*.txt")):
        row = parse_result_file(path)
        if row:
            rows.append(row)

    if not rows:
        print(f"No parseable benchmark logs found in {input_dir}")
        sys.exit(1)

    lookup = {(r["test_case"], r["db"]): r for r in rows}
    cases = sorted({r["test_case"] for r in rows})

    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("matplotlib is required. Install with: python3 -m pip install matplotlib")
        sys.exit(1)

    x = list(range(len(cases)))
    width = 0.36

    mysql_qps, mysql_qps_missing = grouped_values(cases, lookup, "MYSQL", "actual_qps")
    pg_qps, pg_qps_missing = grouped_values(cases, lookup, "POSTGRESQL", "actual_qps")
    mysql_p99, mysql_p99_missing = grouped_values(cases, lookup, "MYSQL", "p99_ms")
    pg_p99, pg_p99_missing = grouped_values(cases, lookup, "POSTGRESQL", "p99_ms")

    fig, (ax_qps, ax_p99) = plt.subplots(2, 1, figsize=(15, 10), constrained_layout=True)

    mysql_qps_bars = ax_qps.bar([i - width / 2 for i in x], mysql_qps, width, label="MySQL")
    pg_qps_bars = ax_qps.bar([i + width / 2 for i in x], pg_qps, width, label="PostgreSQL")
    ax_qps.set_title("Actual Queries Rate (higher is better)")
    ax_qps.set_ylabel("QPS")
    ax_qps.set_xticks(x)
    ax_qps.set_xticklabels(cases, rotation=25, ha="right")
    ax_qps.legend()
    ax_qps.grid(axis="y", alpha=0.3)
    annotate_bars(ax_qps, mysql_qps_bars, mysql_qps, mysql_qps_missing, integer=True)
    annotate_bars(ax_qps, pg_qps_bars, pg_qps, pg_qps_missing, integer=True)

    mysql_p99_bars = ax_p99.bar([i - width / 2 for i in x], mysql_p99, width, label="MySQL")
    pg_p99_bars = ax_p99.bar([i + width / 2 for i in x], pg_p99, width, label="PostgreSQL")
    ax_p99.set_title("P99 Latency (lower is better)")
    ax_p99.set_ylabel("ms")
    ax_p99.set_xticks(x)
    ax_p99.set_xticklabels(cases, rotation=25, ha="right")
    ax_p99.legend()
    ax_p99.grid(axis="y", alpha=0.3)
    annotate_bars(ax_p99, mysql_p99_bars, mysql_p99, mysql_p99_missing, integer=False)
    annotate_bars(ax_p99, pg_p99_bars, pg_p99, pg_p99_missing, integer=False)

    output_png = output_dir / "mysql_vs_postgresql_comparison.png"
    fig.savefig(output_png, dpi=160)

    output_csv = output_dir / "benchmark_summary.csv"
    write_summary_csv(rows, output_csv)

    print(f"Chart generated: {output_png}")
    print(f"Summary CSV generated: {output_csv}")


if __name__ == "__main__":
    main()
