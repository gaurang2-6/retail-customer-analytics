"""Render the README charts from reports/retail.duckdb.

Run from the repo root after `python -m retail.run`:
    python analysis/make_figures.py
"""
from pathlib import Path

import duckdb
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "reports" / "retail.duckdb"
FIG_DIR = ROOT / "reports" / "figures"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"     # categorical slot 1
ORANGE = "#eb6834"   # categorical slot 2
BLUE_RAMP = ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 10, "text.color": INK, "axes.labelcolor": INK_2,
    "xtick.color": INK_2, "ytick.color": INK_2, "axes.edgecolor": GRID,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def gbp_millions(x, _):
    return f"£{x / 1e6:.1f}M"


def month_axis(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))


def save(fig, name):
    fig.savefig(FIG_DIR / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote reports/figures/{name}")


def monthly_revenue(con):
    df = con.sql("SELECT invoice_month, revenue, is_partial_month FROM monthly_kpis ORDER BY 1").df()
    full, partial = df[~df.is_partial_month], df[df.is_partial_month]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(full.invoice_month, full.revenue, color=BLUE, linewidth=2)
    # Dec 2011 only covers 1–9 Dec: dashed connector and a hollow marker so it isn't read as a crash.
    ax.plot(df.invoice_month.iloc[-2:], df.revenue.iloc[-2:], color=BLUE, linewidth=1.5, linestyle=":")
    ax.scatter(partial.invoice_month, partial.revenue, s=40, facecolor=SURFACE, edgecolor=BLUE, linewidth=1.5, zorder=3)
    ax.annotate("Dec 2011: 9 days only", (partial.invoice_month.iloc[0], partial.revenue.iloc[0]),
                xytext=(-10, 14), textcoords="offset points", ha="right", color=INK_2, fontsize=9)
    for _, row in full.loc[full.groupby(full.invoice_month.dt.year).revenue.idxmax()].iterrows():
        if row.invoice_month.year in (2010, 2011):
            ax.annotate(f"{row.invoice_month:%b %Y}\n£{row.revenue / 1e6:.2f}M", (row.invoice_month, row.revenue),
                        xytext=(0, 8), textcoords="offset points", ha="center", va="bottom", color=INK, fontsize=9)
    ax.yaxis.set_major_locator(mtick.MultipleLocator(5e5))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(gbp_millions))
    ax.set_ylim(0, df.revenue.max() * 1.25)
    month_axis(ax)
    ax.set_title("Monthly revenue: flat year on year, with a Sep–Nov peak")
    save(fig, "monthly_revenue.png")


def new_customers(con):
    df = con.sql("""SELECT invoice_month, new_customers FROM monthly_kpis
                    WHERE invoice_month > DATE '2009-12-01' AND NOT is_partial_month ORDER BY 1""").df()
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.bar(df.invoice_month, df.new_customers, width=22, color=BLUE)
    ax.set_title("New customers per month: acquisition halved in 2011")
    ax.set_ylabel("first-time customers")
    month_axis(ax)
    totals = {y: df[(df.invoice_month.dt.year == y) & (df.invoice_month.dt.month <= 11)].new_customers.sum()
              for y in (2010, 2011)}
    ax.text(0.99, 0.95, f"Jan–Nov 2010: {totals[2010]:,}\nJan–Nov 2011: {totals[2011]:,}  "
            f"({100 * (totals[2011] / totals[2010] - 1):+.0f}%)",
            transform=ax.transAxes, ha="right", va="top", color=INK, fontsize=9)
    save(fig, "new_customers.png")


def rfm_segments(con):
    df = con.sql("SELECT segment, customer_pct, revenue_pct FROM rfm_segments ORDER BY revenue_pct").df()
    y = np.arange(len(df))
    h = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.barh(y + h / 2, df.customer_pct, height=h - 0.04, color=BLUE, label="share of customers")
    ax.barh(y - h / 2, df.revenue_pct, height=h - 0.04, color=ORANGE, label="share of revenue")
    for yi, c, r in zip(y, df.customer_pct, df.revenue_pct):
        ax.text(c + 0.8, yi + h / 2, f"{c:.0f}%", va="center", color=INK_2, fontsize=8)
        ax.text(r + 0.8, yi - h / 2, f"{r:.0f}%", va="center", color=INK, fontsize=8)
    ax.set_yticks(y, df.segment)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="lower right", frameon=False)
    ax.set_title("RFM segments: 23% of customers (Champions) bring 70% of revenue")
    save(fig, "rfm_segments.png")


def cohort_heatmap(con):
    df = con.sql("""SELECT cohort_month, months_since_first, retention_pct FROM cohort_retention
                    WHERE cohort_month BETWEEN DATE '2010-01-01' AND DATE '2011-11-01'
                      AND months_since_first BETWEEN 1 AND 12""").df()
    grid = df.pivot(index="cohort_month", columns="months_since_first", values="retention_pct")
    grid = grid.reindex(columns=range(1, 13))
    sizes = con.sql("""SELECT DISTINCT cohort_month, cohort_size FROM cohort_retention
                       WHERE cohort_month BETWEEN DATE '2010-01-01' AND DATE '2011-11-01'""").df()
    sizes = sizes.set_index("cohort_month").cohort_size.reindex(grid.index)

    cmap = LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    cmap.set_bad(SURFACE)
    vmax = 40
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.imshow(np.ma.masked_invalid(grid.values), cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v = grid.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if v > vmax * 0.55 else INK)
    ax.set_xticks(range(12), range(1, 13))
    ax.set_yticks(range(len(grid)), [f"{m:%b %Y}  (n={n:,})" for m, n in zip(grid.index, sizes)], fontsize=8)
    ax.set_xlabel("months since first purchase")
    ax.grid(False)
    ax.tick_params(length=0)
    ax.set_title("Cohort retention (%): share of each month's new customers who buy again")
    save(fig, "cohort_retention.png")


def retention_curve(con):
    df = con.sql("SELECT months_since_first, retention_pct, cohorts FROM retention_curve "
                 "WHERE months_since_first BETWEEN 1 AND 18 ORDER BY 1").df()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(df.months_since_first, df.retention_pct, color=BLUE, linewidth=2, marker="o", markersize=5)
    for k in (1, 12):
        r = df[df.months_since_first == k].iloc[0]
        label = "month 1" if k == 1 else "month 12: annual reorder"
        ax.annotate(f"{label}\n{r.retention_pct:.1f}%", (k, r.retention_pct), xytext=(4 if k == 1 else 0, 10),
                    textcoords="offset points", ha="left" if k == 1 else "center", va="bottom", color=INK, fontsize=9)
    ax.set_xticks(df.months_since_first)
    ax.set_ylim(0, df.retention_pct.max() * 1.35)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_xlabel("months since first purchase")
    ax.set_title("Average retention curve (cohorts Jan 2010 – Nov 2011, weighted by size)")
    save(fig, "retention_curve.png")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    for fn in (monthly_revenue, new_customers, rfm_segments, cohort_heatmap, retention_curve):
        fn(con)
    con.close()


if __name__ == "__main__":
    main()
