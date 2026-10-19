"""Measure end-to-end latency of the three Nobel queries and plot a box plot.

Run (next to client.py and the *_pb2.py files):
    export GRPC_TARGET=<host>.run.app:443
    python benchmark.py                 # 100 calls per query -> latencies.csv + latency_boxplot.png
    python benchmark.py --plot-only     # re-draw the plot from latencies.csv
Options: --n 100  --category physics  --keyword genetics  --first Marie --last Curie
"""
import argparse
import csv
import os
import statistics
import time

# WSL has no IPv6 route; the native resolver avoids grpc trying IPv6 first.
os.environ.setdefault("GRPC_DNS_RESOLVER", "native")

CSV_PATH = "latencies.csv"
PNG_PATH = "latency_boxplot.png"
LABELS = ["Category", "Motivation", "Laureate name"]


def make_channel(grpc, target):
    if target.endswith(":443"):
        return grpc.secure_channel(target, grpc.ssl_channel_credentials())
    return grpc.insecure_channel(target)


def run(args):
    import grpc
    import category_pb2, category_pb2_grpc
    import laureate_pb2, laureate_pb2_grpc
    import motivation_pb2, motivation_pb2_grpc

    target = os.environ.get("GRPC_TARGET", "localhost:50051")
    print(f"Target: {target}  |  {args.n} calls per query")

    with make_channel(grpc, target) as channel:
        cat = category_pb2_grpc.CategoryServiceStub(channel)
        mot = motivation_pb2_grpc.MotivationServiceStub(channel)
        lau = laureate_pb2_grpc.LaureateServiceStub(channel)

        queries = {
            "Laureate name": lambda: lau.FindLaureate(
                laureate_pb2.LaureateRequest(firstname=args.first, surname=args.last),
                timeout=30),
            "Category": lambda: cat.CountLaureates(
                category_pb2.CategoryRequest(category=args.category), timeout=30),
            "Motivation": lambda: mot.CountByKeyword(
                motivation_pb2.KeywordRequest(keyword=args.keyword), timeout=30),

        }

        # One untimed call each: opens the TLS/HTTP2 connection and wakes a
        # cold Cloud Run instance, so it doesn't distort the first sample.
        for name, call in queries.items():
            call()

        rows = []
        for name, call in queries.items():
            try:

                for i in range(1, args.n + 1):
                    t0 = time.perf_counter()
                    call()
                    ms = (time.perf_counter() - t0) * 1000
                    rows.append((name, i, ms))
                print(f"  {name}: done")
            except grpc.RpcError as e:
                print(f"\nWarm-up failed for '{name}': {e.code().name}: {e.details()}")
                raise SystemExit(1)

    with open(CSV_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query", "run", "latency_ms"])
        w.writerows(rows)
    print(f"Saved {CSV_PATH}")


def plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = {k: [] for k in LABELS}
    with open(CSV_PATH) as f:
        for r in csv.DictReader(f):
            data[r["query"]].append(float(r["latency_ms"]))

    print(f"\n{'Query':<15}{'n':>5}{'min':>9}{'median':>9}{'mean':>9}{'p95':>9}{'max':>9}  (ms)")
    for k in LABELS:
        v = sorted(data[k])
        p95 = v[min(len(v) - 1, int(round(0.95 * len(v))) - 1)]
        print(f"{k:<15}{len(v):>5}{v[0]:>9.1f}{statistics.median(v):>9.1f}"
              f"{statistics.mean(v):>9.1f}{p95:>9.1f}{v[-1]:>9.1f}")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.boxplot([data[k] for k in LABELS], tick_labels=LABELS, patch_artist=True,
               boxprops=dict(facecolor="#476e31", color="#222"),
               medianprops=dict(color="#111", linewidth=1.5),
               whiskerprops=dict(color="#222"), capprops=dict(color="#222"),
               flierprops=dict(marker="o", markersize=4, markerfacecolor="#999",
                               markeredgecolor="#555"))
    ax.set_ylabel("End-to-end delay (ms)")
    ax.set_title("Client (laptop) to Cloud Run: latency per query, "
                 f"{len(data[LABELS[0]])} runs each")
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    fig.tight_layout()
    fig.savefig(PNG_PATH, dpi=200)
    print(f"Saved {PNG_PATH}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--category", default="physics")
    p.add_argument("--keyword", default="genetics")
    p.add_argument("--first", default="Marie")
    p.add_argument("--last", default="Curie")
    p.add_argument("--plot-only", action="store_true")
    a = p.parse_args()
    if not a.plot_only:
        run(a)
    plot()
