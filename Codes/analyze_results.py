import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import re

RESULTS_DIR = "results_batched"


def load_all():
    dfs = []

    for path in glob.glob(os.path.join(RESULTS_DIR, "*.csv")):
        fname = os.path.basename(path)

        # Detect reporting interval from filename
        interval = None
        if "1" in fname and "interval" in fname:
            interval = 1
        elif "10" in fname and "interval" in fname:
            interval = 10
        elif "30" in fname and "interval" in fname:
            interval = 30

        # Detect loss %
        loss = None
        if "0pct" in fname:
            loss = 0
        elif "5pct" in fname:
            loss = 5
        elif "15pct" in fname:
            loss = 15

        df = pd.read_csv(path)

        # Convert duplicate flag
        df["duplicate_flag_int"] = (
            df["duplicate_flag"].astype(str).str.upper().map({"TRUE": 1, "FALSE": 0}).fillna(0)
        )

        df["reporting_interval"] = interval
        df["loss_pct"] = loss
        df["source"] = fname

        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)


def plot_bytes_per_report(df):
    df_int = df[df["reporting_interval"].notna()]
    grouped = df_int.groupby("reporting_interval")["bytes_per_report"].mean()

    print("\n=== BYTES PER REPORT ===")
    print(grouped)

    plt.figure()
    plt.plot(grouped.index, grouped.values, marker="o")
    plt.xlabel("Reporting Interval (seconds)")
    plt.ylabel("Average Bytes Per Report")
    plt.title("bytes_per_report vs reporting_interval")
    plt.grid(True)
    plt.savefig("bytes_per_report_vs_reporting_interval.png", dpi=200)
    print("Saved: bytes_per_report_vs_reporting_interval.png")


def plot_duplicate_rate(df):
    df_loss = df[df["loss_pct"].notna()]
    grouped = df_loss.groupby("loss_pct")["duplicate_flag_int"].mean()

    print("\n=== DUPLICATE RATE ===")
    print(grouped)

    plt.figure()
    plt.plot(grouped.index, grouped.values, marker="o")
    plt.xlabel("Loss (%)")
    plt.ylabel("Duplicate Rate")
    plt.title("duplicate_rate vs loss")
    plt.grid(True)
    plt.savefig("duplicate_rate_vs_loss.png", dpi=200)
    print("Saved: duplicate_rate_vs_loss.png")


if __name__ == "__main__":
    df = load_all()
    print(f"Loaded {len(df)} total rows from CSV files.")

    plot_bytes_per_report(df)
    plot_duplicate_rate(df)

    print("\nAll plots generated successfully.")
