import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

df = pd.read_csv('clean/region_month.csv')
print("Dataset size:", df.shape)
print("\nColumn names :")
print(df.columns.tolist())
print("\nFirst 5 rows of the dataset :")
print(df.head())

print("\nConflict and Food price data : ")
print(
    df[[
        "country",
        "region_name",
        "month",
        "conflict_events",
        "price_millet"
    ]].head(10).to_string(index=False)
)
high_conflict = df[df['conflict_events'] >=5]
print("\nMonths with high conflict:")
print("Number of observattions:",len(high_conflict))

print(
    high_conflict[[
        "country",
        "region_name",
        "month",
        "conflict_events",
        "price_millet"
    ]].head(10).to_string(index=False)
)
#checking millet price 
print("\nMissing millet prices: ")
print(df["price_millet"].isna().sum())

print("\nHigh-conflict months with available millet prices:")
print(high_conflict["price_millet"].notna().sum())

print("\nHigh-conflict months with missing millet prices:")
print(high_conflict["price_millet"].isna().sum())

print("\nRegions with at least one high-conflict month:")
print(
    high_conflict[
        ["country", "region_code", "region_name"]
    ].drop_duplicates().to_string(index=False)
)
first_escalation = (
    high_conflict
    .sort_values(["country","region_code","month"])
    .drop_duplicates(subset=["country","region_code"])
)
print("\nFirst high conflict month for each region:")
print(
    first_escalation[[
        "country",
        "region_name",
        "month",
        "conflict_events",
    ]].to_string(index=False)
)
df["month_date"] = pd.to_datetime(df["month"]+"-01")
first_escalation["escalation_date"] = pd.to_datetime(first_escalation["month"]+"-01")

#attach escalation dates to all monthly observation
check=df.merge(first_escalation[["country","region_code","escalation_date"]],on=["country","region_code"],how="inner")

check["relative_month"] = (
    (check["month_date"].dt.year -
     check["escalation_date"].dt.year) * 12
    + check["month_date"].dt.month
    - check["escalation_date"].dt.month
)

# Count available millet prices before and after
before = check[check["relative_month"].between(-12, -1)]
after = check[check["relative_month"].between(1, 12)]

group_cols = ["country", "region_code"]

before_counts = before.groupby(group_cols)["price_millet"].count()
after_counts = after.groupby(group_cols)["price_millet"].count()

coverage = pd.concat(
    [before_counts.rename("before"),
     after_counts.rename("after")],
    axis=1
).fillna(0).astype(int)

print("\nPrice observations before and after escalation:")
print(coverage.to_string())

print("\nRegions with complete 12-month price data:")
print(((coverage["before"] == 12) &
       (coverage["after"] == 12)).sum())
from pathlib import Path
#select the 13 regions with complete price coverage 
valid_regions = coverage[
    (coverage["before"] == 12) &
    (coverage["after"] == 12)
].reset_index()[["country", "region_code"]]

#keep observations from these regions 
plot_data = check.merge(
        valid_regions,
        on=["country","region_code"],
        how="inner"
        )

#keep 12 months before, the event month , and 12 months after
plot_data = plot_data[
    plot_data["relative_month"].between(-12, 12)
].copy()

#calculate each regions average price before high conflict 
baseline = (
    plot_data[plot_data["relative_month"].between(-12, -1)]
    .groupby(["country", "region_code"])["price_millet"]
    .mean()
    .rename("baseline_price")
)
plot_data = plot_data.join(
    baseline,
    on=["country", "region_code"]
)
#convert prices to an index for an fairer comparison 
plot_data["price_index"] = (
    plot_data["price_millet"] / 
    plot_data["baseline_price"]*100
) 

#Average the index price across the regions 
trend = (
    plot_data.groupby("relative_month")["price_index"]
    .mean()
)

#Draw the line chart
plt.figure(figsize=(10,6) )

plt.plot(trend.index,
         trend.values,
         marker='o',
         linewidth=2)

plt.axvline(0, linestyle="--", label="First high-conflict month")
plt.axhline(100, linestyle= ":", label = "pre-conflict reference= 100")

plt.title("Millet prices around the first high conflict month")
plt.xlabel("Months relative to first month with 5+ conflict events")
plt.ylabel("Millet price index (pre-preiod average =100)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

#save the chart
Path("figures").mkdir(exist_ok=True)

plt.savefig(
    "figures/conflict_chart_a_draft.png",
dpi=300
)

plt.close()
print("\nChart a draft saved successsfully !!!")

#Identify calmer regions for comparison
#find the maximum monthly conflict count for every region

region_conflict=(
    df.groupby(["country", "region_code"])["conflict_events"]
    .max()
    .reset_index()
)
#select regions that never recorded 5 or more
#conflict events in a month during the dataset period 
calm_regions = region_conflict[
    region_conflict["conflict_events"] < 5  
]

print("\nNumber of calmer regions by country :")
print(
    calm_regions.groupby("country")["region_code"]
    .nunique()
    .to_string()
)
print("\nTotal calmer regions :", len(calm_regions))
#Build calm regions compariosn series

# STEP 8: Build the calmer-region comparison

df["month_dt"] = pd.to_datetime(df["month"] + "-01")

# Use only the 13 regions with complete price data
events = first_escalation.merge(
    valid_regions,
    on=["country", "region_code"],
    how="inner"
)

events["event_month_dt"] = pd.to_datetime(
    events["month"] + "-01"
)

calm_rows = []

for _, event in events.iterrows():

    # Find calmer regions in the same country
    same_country_calm = calm_regions[
        calm_regions["country"] == event["country"]
    ]["region_code"]

    for region_code in same_country_calm:

        temp = df[
            (df["country"] == event["country"]) &
            (df["region_code"] == region_code)
        ].copy()

        # Align dates with the conflict region
        temp["rel_month"] = (
            (temp["month_dt"].dt.year -
             event["event_month_dt"].year) * 12
            + temp["month_dt"].dt.month
            - event["event_month_dt"].month
        )

        # Keep 12 months before and 12 months after
        temp = temp[
            temp["rel_month"].between(-12, 12)
        ].copy()

        # Require complete price data
        if (
            len(temp) != 25
            or temp["rel_month"].nunique() != 25
            or temp["price_millet"].isna().any()
        ):
            continue

        # Calculate baseline price
        pre_avg = temp[
            temp["rel_month"].between(-12, -1)
        ]["price_millet"].mean()

        if pd.isna(pre_avg) or pre_avg <= 0:
            continue

        temp["price_index"] = (
            temp["price_millet"] / pre_avg * 100
        )

        temp["event_id"] = (
            event["country"] + "_" + event["region_code"]
        )

        calm_rows.append(
            temp[[
                "event_id",
                "rel_month",
                "price_index"
            ]]
        )

if not calm_rows:
    raise ValueError("No eligible calmer-region price data found.")

calm_panel = pd.concat(calm_rows, ignore_index=True)

# Average controls within each event, then across events
calm_avg = (
    calm_panel
    .groupby(["event_id", "rel_month"])["price_index"]
    .mean()
    .groupby("rel_month")
    .mean()
)

print("\nConflict regions:", len(events))
print(
    "Conflict events with eligible calmer-region comparisons:",
    calm_panel["event_id"].nunique()
)

# STEP 9: Create the comparison chart

plt.figure(figsize=(10, 6))

plt.plot(
    trend.index,
    trend.values,
    marker="o",
    linewidth=2,
    label="High-conflict regions"
)

plt.plot(
    calm_avg.index,
    calm_avg.values,
    marker="s",
    linestyle="--",
    linewidth=2,
    label="Calmer regions"
)

plt.axvline(
    0,
    color="gray",
    linestyle="--",
    label="First high-conflict month"
)

plt.axhline(
    100,
    color="gray",
    linestyle=":",
    label="Pre-period average = 100"
)

plt.title("Millet Prices: High-Conflict vs Calmer Regions")
plt.xlabel("Months relative to conflict escalation")
plt.ylabel("Millet price index (12-month pre-period = 100)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

# Save Chart A
Path("figures").mkdir(exist_ok=True)

plt.savefig(
    "figures/chartA_conflict_vs_calm.png",
    dpi=300,
    bbox_inches="tight"
)

print("\nComparison Chart A saved successfully!")

#Inspecting market level data 
market_df = pd.read_csv("clean/market_month_full.csv")

print("\nMarket dataset size :", market_df.shape)
print("\nMarket dataset colums:")
print(market_df.columns.tolist())

print("\nFirst 3 market obeservations:")
print(market_df.head(3).to_string(index=False))
plt.close()

#Prepare market data for chart B
#millet observation from 2024 

millet_map = market_df[
    (market_df["food"] == "millet") &
    (market_df["year"] == 2024)
].copy()


#remove rows without prices / coordinates 
millet_map = millet_map.dropna(
    subset=["price_lcu", "latitude", "longitude"]
)
#calculate easch countrys median millet price in 2024
millet_map["national_median"] = (
    millet_map.groupby("country")["price_lcu"]
    .transform("median")
)


#Calculate percentage diffecrence from national median
millet_map["difference_pct"] = (
    (millet_map["price_lcu"] -
     millet_map["national_median"]) /
    millet_map["national_median"] * 100
)

print("\n2024 millet observations:", len(millet_map))

print("\nCountries with millet prices:")
print(millet_map["country"].value_counts())

print("\nUnique markets:", millet_map["market_id"].nunique())

#Geographic price differences

# Keep valid, positive millet prices
millet_map = millet_map[
    millet_map["price_lcu"] > 0
].copy()

# National median for each country AND month
millet_map["national_median"] = (
    millet_map.groupby(["country", "month"])["price_lcu"]
    .transform("median")
)

# Difference from the national monthly median (%)
millet_map["difference_pct"] = (
    (millet_map["price_lcu"] / millet_map["national_median"] - 1)
    * 100
)

# One point per market:median difference across 2024
map_points = (
    millet_map.groupby(
        [
            "country", "region_code", "market_id",
            "market", "latitude", "longitude"
        ],
        as_index=False
    )
    .agg(
        difference_pct=("difference_pct", "median"),
        months_available=("month", "nunique")
    )
)

print("\nUnique market locations:", len(map_points))

#Draw market locations
fig, ax = plt.subplots(figsize=(13, 7))

scatter = ax.scatter(
    map_points["longitude"],
    map_points["latitude"],
    c=map_points["difference_pct"].clip(-50, 50),
    cmap="RdBu_r",
    vmin=-50,
    vmax=50,
    s=38,
    edgecolors="black",
    linewidths=0.3,
    alpha=0.9
)

# Label the countries
for country, group in map_points.groupby("country"):
    ax.text(
        group["longitude"].median(),
        group["latitude"].median() + 0.5,
        country,
        fontsize=9,
        fontweight="bold",
        ha="center"
    )

colorbar = fig.colorbar(scatter, ax=ax, shrink=0.8)
colorbar.set_label(
    "Median difference from national monthly median (%)"
)

ax.set_title(
    "Millet Market Prices Relative to National Medians (2024)"
)

ax.set_xlabel("Longitude (degrees)")
ax.set_ylabel("Latitude (degrees)")
ax.grid(alpha=0.2)

plt.tight_layout()

Path("figures").mkdir(exist_ok=True)

plt.savefig(
    "figures/chartB_millet_price_map_draft.png",
    dpi=300,
    bbox_inches="tight"
)

print("\nChart B draft saved successfully!")

plt.show()
