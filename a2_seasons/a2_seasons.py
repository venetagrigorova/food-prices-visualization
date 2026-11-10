"""A2, research question 1 (seasons) + Cadre Harmonise.

RQ: How strong is the lean-season price rise, does it differ by food and region,
and does it line up with the lean-season peak in food insecurity reported by the
Cadre Harmonise?

Reads only the team's clean tables (run clean_data.py first):
    clean/market_month_full.csv   prices (final dataset)
    clean/ch_region_season.csv    Cadre Harmonise, region x season

Writes (next to this script):
    fig_a_seasonal_heatmap.png    Chart A: heatmap food x month + CH strip
    fig_b_region_dotplot.png      Chart B: dot plot of the millet lean-season rise per region,
                                  coloured by Cadre Harmonise lean-season phase 3+ share
    numbers.txt                   every number quoted in the write-up

Run from the project folder:  python a2_seasons/a2_seasons.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm, Normalize
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
CLEAN = HERE.parent / "clean"

# ---- rules for this analysis (change here, rerun) ----
MIN_MONTHS_PER_YEAR = 10          # a series-year needs >= 10 monthly prices to get a seasonal index
BASE_MONTHS = [1, 2, 3]           # post-harvest baseline: Jan-Mar
LEAN_MONTHS = [7, 8, 9]           # lean-season peak: Jul-Sep
MIN_MONTHS_IN_WINDOW = 2          # a series-year needs >= 2 of the 3 months in each window
MIN_SERIES_YEARS = 10             # a region needs >= 10 millet series-years to be shown in chart B

FOOD_LABEL = {"millet": "Millet", "sorghum": "Sorghum", "maize": "Maize", "cowpeas": "Cowpeas",
              "rice_local": "Local rice", "rice_imported": "Imported rice"}
COUNTRY_ORDER = ["Niger", "Chad", "Burkina Faso", "Mali", "Senegal"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# colours: reference palette of the dataviz guidelines (blue <-> grey <-> red diverging, blue sequential)
TEXT, TEXT2, SURFACE, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3df"
DIVERGING = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#e34948"])
SEQUENTIAL = LinearSegmentedColormap.from_list(
    "seq", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": TEXT,
                     "axes.labelcolor": TEXT2, "xtick.color": TEXT2, "ytick.color": TEXT2,
                     "axes.edgecolor": GRID, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                     "savefig.facecolor": SURFACE})

out = []
def note(s):
    print(s); out.append(s)


# ---------------- data ----------------
m = pd.read_csv(CLEAN / "market_month_full.csv")
m = m[~m.outlier_flag].copy()
m["series"] = m.market_id.astype(str) + "_" + m.food
note(f"price rows (outliers excluded): {len(m):,}")

# seasonal index: price / mean price of the same series in the same calendar year x 100.
# Dividing by the same year's mean removes inflation and multi-year trends (e.g. the 2022 spike),
# so only the within-year shape remains.
g = m.groupby(["series", "year"]).price_lcu
m["months_in_year"] = g.transform("size")
m["year_mean"] = g.transform("mean")
s = m[m.months_in_year >= MIN_MONTHS_PER_YEAR].copy()
s["seasonal_index"] = s.price_lcu / s.year_mean * 100
note(f"rows with a seasonal index: {len(s):,} in {s.groupby(['series','year']).ngroups:,} series-years, "
     f"{s.series.nunique()} series, {s.market_id.nunique()} markets")

# lean-season rise per series-year: mean Jul-Sep / mean Jan-Mar - 1
def window_mean(months):
    w = s[s.month_of_year.isin(months)].groupby(["series", "year"]).price_lcu
    return w.mean().where(w.size() >= MIN_MONTHS_IN_WINDOW)

keys = s.drop_duplicates(["series", "year"]).set_index(["series", "year"])[
    ["food", "country", "region_code", "region_name", "market"]]
rise = keys.assign(rise_pct=(window_mean(LEAN_MONTHS) / window_mean(BASE_MONTHS) - 1) * 100).dropna()
note(f"series-years with a lean-season rise: {len(rise):,}")
note("lean-season rise Jul-Sep vs Jan-Mar, median % by food (n series-years):")
for food, d in rise.groupby("food").rise_pct:
    note(f"  {FOOD_LABEL[food]:14s} {d.median():5.1f}%  (IQR {d.quantile(.25):.1f} to {d.quantile(.75):.1f}, n={len(d)})")

# Cadre Harmonise: share of population in phase 3+ by season (population-weighted, 2015-2024).
ch = pd.read_csv(CLEAN / "ch_region_season.csv")
ch = ch[ch.reference_year.between(2015, 2024)]
ch = ch[~((ch.chtype == "current") & (ch.reference_label == "Jun-Aug"))]   # 13 rows: BFA June-2020 update only
season_share = (ch.groupby(["chtype", "reference_label"])
                .apply(lambda d: d.phase35.sum() / d.population_analysed.sum() * 100, include_groups=False))
note("Cadre Harmonise, % of analysed population in phase 3+ (5 countries, 2015-2024, pooled):")
for k, v in season_share.items():
    note(f"  {k[1]} ({k[0]}): {v:.1f}%")

# ---------------- chart A: heatmap food x month + Cadre Harmonise strip ----------------
heat = s.groupby(["food", "month_of_year"]).seasonal_index.median().unstack()
n_series = s.groupby("food").series.nunique()
amplitude = heat.max(axis=1) - heat.min(axis=1)
heat = heat.loc[amplitude.sort_values(ascending=False).index]
note("chart A, median seasonal index (yearly mean = 100):")
note(heat.round(1).to_string())

fig = plt.figure(figsize=(12, 7.2))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 5.2], width_ratios=[40, 1], hspace=0.08, wspace=0.03,
                      left=0.15, right=0.91, top=0.76, bottom=0.12)
ax_ch, ax = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0])
cax = fig.add_subplot(gs[1, 1])

norm = TwoSlopeNorm(vmin=88, vcenter=100, vmax=112)
im = ax.imshow(heat.values, cmap=DIVERGING, norm=norm, aspect="auto")
for i in range(heat.shape[0]):
    for j in range(12):
        v = heat.values[i, j]
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=9,
                color="white" if abs(v - 100) > 8 else TEXT)
ax.set_xticks(range(12), MONTHS)
ax.set_yticks(range(heat.shape[0]), [f"{FOOD_LABEL[f]}  ({n_series[f]})" for f in heat.index])
ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.set_xticks(np.arange(-.5, 12), minor=True); ax.set_yticks(np.arange(-.5, heat.shape[0]), minor=True)
ax.grid(which="minor", color=SURFACE, linewidth=2); ax.tick_params(which="minor", length=0)
# lean season frame (Jun-Sep)
ax.add_patch(Rectangle((4.5, -0.5), 4, heat.shape[0], fill=False, edgecolor=TEXT, linewidth=2,
                       linestyle="--", zorder=10, clip_on=False))
ax.set_xlabel("Month   (dashed frame = lean season, June-September)")
ax.set_ylabel("Food  (number of market series)")

cb = fig.colorbar(im, cax=cax)
cb.set_label("Seasonal price index\n(same market & year average = 100)", color=TEXT2)
cb.outline.set_visible(False)

# Cadre Harmonise strip, on the same month axis
ax_ch.set_xlim(-0.5, 11.5); ax_ch.set_ylim(0, 1); ax_ch.axis("off")
ch_norm = Normalize(0, 12)
for (x0, x1, key, label) in [(-0.5, 4.5, ("current", "Jan-May"), "Jan-May (current)"),
                             (4.5, 7.5, ("projected", "Jun-Aug"), "Jun-Aug (projected)"),
                             (7.5, 11.5, ("current", "Sep-Dec"), "Sep-Dec (current)")]:
    v = season_share[key]
    ax_ch.add_patch(Rectangle((x0 + 0.04, 0.05), x1 - x0 - 0.08, 0.9, color=SEQUENTIAL(ch_norm(v))))
    col = "white" if v > 6 else TEXT
    ax_ch.text((x0 + x1) / 2, 0.63, f"{v:.1f}%", ha="center", va="center", fontsize=12, fontweight="bold", color=col)
    ax_ch.text((x0 + x1) / 2, 0.27, label, ha="center", va="center", fontsize=8.5, color=col)
ax_ch.text(-0.6, 0.5, "Cadre Harmonisé:\n% in phase 3+\n(crisis or worse)", ha="right", va="center",
           fontsize=9, color=TEXT2)

fig.suptitle("Grain prices peak in August-September, in the same season the\nCadre Harmonisé counts the most people in crisis",
             x=0.03, ha="left", fontsize=14, fontweight="bold", y=0.975)
fig.text(0.03, 0.85, "Median seasonal price index per month (each market's price divided by its own average for that year), "
         "Mali, Burkina Faso,\nNiger, Senegal and Chad, 2015-2024. Top strip: share of the population in Cadre Harmonisé "
         "phase 3 (crisis) or worse, pooled 2015-2024.", ha="left", va="center", fontsize=9.5, color=TEXT2)
fig.text(0.03, 0.025, "Sources: WFP food prices (HDX, CC BY-IGO); Cadre Harmonisé (CILSS / HDX, CC BY). Series-years with "
         "fewer than 10 monthly prices and the 12 flagged outliers excluded.\nJune-August is only ever a projection in "
         "the Cadre Harmonisé; it is compared with current estimates for the other months.",
         ha="left", fontsize=8, color=TEXT2)
fig.savefig(HERE / "fig_a_seasonal_heatmap.png", dpi=300)
plt.close(fig)

# ---------------- chart B: dot plot per region, colour = CH lean-season share ----------------
mil = rise[rise.food == "millet"].reset_index()
reg = (mil.groupby(["country", "region_code", "region_name"]).rise_pct
       .agg(median="median", q25=lambda x: x.quantile(.25), q75=lambda x: x.quantile(.75), n="size")
       .reset_index())
markets = mil.groupby("region_code").series.nunique().rename("n_markets")
reg = reg.merge(markets, on="region_code")
dropped = reg[reg.n < MIN_SERIES_YEARS]
reg = reg[reg.n >= MIN_SERIES_YEARS]
note(f"chart B: {len(reg)} regions shown, {len(dropped)} dropped (< {MIN_SERIES_YEARS} millet series-years): "
     + ", ".join(dropped.region_name))

proj = ch[(ch.chtype == "projected") & (ch.reference_label == "Jun-Aug")]
ch_reg = proj.groupby("region_code").share_phase35.mean().rename("ch_lean")
reg = reg.merge(ch_reg, on="region_code", how="left")
rho, pval = spearmanr(reg["median"], reg.ch_lean)
note(f"chart B: Spearman correlation, region median millet rise vs mean projected Jun-Aug phase 3+ share: "
     f"{rho:.2f}, p = {pval:.3f} (n={len(reg)})")
note(reg.sort_values("median").round(1).to_string(index=False))

reg["country"] = pd.Categorical(reg.country, COUNTRY_ORDER, ordered=True)
reg = reg.sort_values(["country", "median"], ascending=[True, False])
counts = reg.country.value_counts().reindex(COUNTRY_ORDER)

fig = plt.figure(figsize=(9.5, 14))
gs = fig.add_gridspec(len(COUNTRY_ORDER), 1, height_ratios=counts.values + 1.2, hspace=0.25,
                      left=0.25, right=0.80, top=0.885, bottom=0.07)
ch_max = 25
ch_norm = Normalize(0, ch_max)
axes = []
for k, country in enumerate(COUNTRY_ORDER):
    ax = fig.add_subplot(gs[k], sharex=axes[0] if axes else None)
    axes.append(ax)
    d = reg[reg.country == country].reset_index(drop=True)
    y = np.arange(len(d))
    ax.hlines(y, d.q25, d.q75, color="#bdbcb6", linewidth=2.5, zorder=1)
    ax.scatter(d["median"], y, s=90, c=SEQUENTIAL(ch_norm(d.ch_lean.clip(upper=ch_max))),
               edgecolor=SURFACE, linewidth=1.5, zorder=3)
    ax.set_yticks(y, [f"{r} ({mk} mkts)" for r, mk in zip(d.region_name, d.n_markets)], fontsize=9)
    ax.set_ylim(len(d) - 0.4, -0.6)
    ax.axvline(0, color=TEXT2, linewidth=1)
    med_all = mil[mil.country == country].rise_pct.median()
    ax.axvline(med_all, color=TEXT2, linewidth=1, linestyle=":")
    ax.set_title(f"{country}  -  country median {med_all:.0f}%", loc="left", fontsize=10.5,
                 fontweight="bold", color=TEXT, pad=4)
    ax.grid(axis="x", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    if k < len(COUNTRY_ORDER) - 1:
        ax.tick_params(labelbottom=False)
axes[-1].set_xlabel("Millet price rise, lean season (Jul-Sep) vs. after harvest (Jan-Mar) of the same year, %")
axes[-1].xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
axes[0].set_xlim(-15, 60)

cax = fig.add_axes([0.84, 0.35, 0.022, 0.3])
cb = fig.colorbar(plt.cm.ScalarMappable(norm=ch_norm, cmap=SEQUENTIAL), cax=cax, extend="max")
cb.set_label("Cadre Harmonisé: % of population\nin phase 3+ in June-August\n(projected, mean 2015-2024)", color=TEXT2)
cb.outline.set_visible(False)
cb.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))

fig.suptitle("Millet's lean-season jump is largest in Niger and eastern Chad,\nbut crisis levels follow it only loosely",
             x=0.03, ha="left", fontsize=14, fontweight="bold", y=0.985)
fig.text(0.03, 0.925, f"Dot = median rise across markets and years 2015-2024; bar = middle 50% of market-years. "
         f"Dotted line = country median.\nDot colour = Cadre Harmonisé lean-season share in crisis or worse.\n"
         f"Rank correlation across the {len(reg)} regions: Spearman ρ = {rho:.2f} (p = {pval:.2f}), a weak link.",
         ha="left", va="center", fontsize=9.5, color=TEXT2)
fig.text(0.03, 0.025, "Sources: WFP food prices (HDX, CC BY-IGO); Cadre Harmonisé (CILSS / HDX, CC BY). "
         f"Regions with fewer than {MIN_SERIES_YEARS} millet market-years not shown.\n"
         "A year counts if the market reported at least 10 months, and at least 2 months in each window. Prices are nominal.",
         ha="left", fontsize=8, color=TEXT2)
fig.savefig(HERE / "fig_b_region_dotplot.png", dpi=300)
plt.close(fig)

(HERE / "numbers.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
