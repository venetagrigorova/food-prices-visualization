"""
makes the clean data in clean/ from the raw files in raw/

setup + run:
    python3 -m venv data-viz && source data-viz/bin/activate
    pip install -r requirements.txt
    python3 clean_data.py
"""
import re
import unicodedata
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAW = Path(__file__).parent / "raw"
OUT = Path(__file__).parent / "clean"

COUNTRIES = {"BFA": "Burkina Faso", "MLI": "Mali", "NER": "Niger", "SEN": "Senegal", "TCD": "Chad"}
FIRST_MONTH, LAST_MONTH = "2015-01", "2024-12"  # conflict data ends in 2024
ALL_MONTHS = pd.period_range(FIRST_MONTH, LAST_MONTH, freq="M").astype(str)
REGION_AND_MONTH = ["region_code", "month"]

# a price series (one food in one market) is kept if:
# - it has a price in at least 60% of the months
# - it's never missing for more than 12 months in a row
MIN_SHARE_OF_MONTHS = 0.6
MAX_MONTHS_MISSING_IN_A_ROW = 12

# the wfp food name to use for each food in each country
# (chad has several kinds of sorghum and maize in the same market)
FOODS = {
    "millet": {"BFA": "Millet", "MLI": "Millet", "NER": "Millet", "SEN": "Millet", "TCD": "Millet"},
    "sorghum": {"BFA": "Sorghum (white)", "MLI": "Sorghum", "NER": "Sorghum", "SEN": "Sorghum", "TCD": "Sorghum (red)"},
    "maize": {"BFA": "Maize (white)", "MLI": "Maize", "NER": "Maize", "SEN": "Maize (local)", "TCD": "Maize (white)"},
    "rice_local": {iso: "Rice (local)" for iso in COUNTRIES},
    "rice_imported": {iso: "Rice (imported)" for iso in COUNTRIES},
    "cowpeas": {iso: "Beans (niebe)" for iso in COUNTRIES},
}

# region names that are still spelled differently after simplify_name()
NAME_FIXES = {"koulikouro": "koulikoro", "barhelgazal": "barhelgazel"}

# which months each cadre harmonise season covers
SEASON_MONTHS = {"Jan-May": [1, 2, 3, 4, 5], "Jun-Aug": [6, 7, 8], "Sep-Dec": [9, 10, 11, 12]}

log_lines = []


def log(text):
    print(text)
    log_lines.append(str(text))


def save(table, name):
    table.to_csv(OUT / f"{name}.csv", index=False)
    log(f"-> {name}.csv: {len(table):,} rows x {table.shape[1]} columns")


def simplify_name(name):
    """so names from different files can be compared ('Tillabéri region' and 'TILLABERI' both -> 'tillaberi')"""
    name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    name = re.sub(r"[^a-z]", "", name.replace("region", ""))
    return NAME_FIXES.get(name, name)


def longest_gap(month_numbers):
    """most months in a row without a price, between the first and last price of a series"""
    steps = month_numbers.sort_values().diff()  # 1 = next month, 3 = two months missing
    return steps.max() - 1 if len(steps) > 1 else 0


# regions

def load_regions(hunger_raw):
    """all 67 regions (code + name), names come from the cadre harmonise file"""
    regions = (hunger_raw.groupby(["adm0_name", "region_code"]).adm1_name
               .agg(lambda names: names.mode()[0])  # most common spelling
               .reset_index()
               .rename(columns={"adm0_name": "country", "adm1_name": "region_name"}))
    regions["region_name"] = regions.region_name.str.replace("Boucle Du", "Boucle du")
    regions["iso3"] = regions.country.map({name: iso for iso, name in COUNTRIES.items()})
    return regions[["country", "iso3", "region_code", "region_name"]]


def code_by_region_name(regions):
    """(country, simplified name) -> region code, used to match region names from the other files"""
    return {(r.iso3, simplify_name(r.region_name)): r.region_code for r in regions.itertuples()}


def load_region_outlines(regions):
    """region shapes from the map files, needed to find which region a conflict event happened in"""
    code_by_name = code_by_region_name(regions)
    outlines = []
    for iso in ["MLI", "BFA"]:
        # mali and burkina faso changed their regions recently but data still uses old ones
        # we use old maps for these two countries
        # - burkina's has 17 new regions
        # - in mali's new map ML09 is taoudenni, but in our data it's bamako
        shapes = gpd.read_file(RAW / f"boundaries_old/geoBoundaries-{iso}-ADM1.geojson")
        shapes["region_code"] = [code_by_name.get((iso, simplify_name(n))) for n in shapes.shapeName]
        outlines.append(shapes.assign(iso3=iso))
    for iso in ["NER", "SEN", "TCD"]:
        with zipfile.ZipFile(RAW / f"boundaries/{iso.lower()}_admin_boundaries.geojson.zip") as z:
            shapes = gpd.read_file(z.open(f"{iso.lower()}_admin1.geojson"))
        outlines.append(shapes.assign(iso3=iso, region_code=shapes.adm1_pcode))
    outlines = pd.concat([s[["iso3", "region_code", "geometry"]].to_crs(4326) for s in outlines], ignore_index=True)
    assert outlines.region_code.isin(regions.region_code).all()
    return gpd.GeoDataFrame(outlines, crs=4326)


# food prices

def clean_prices(regions):
    prices = pd.concat([pd.read_csv(RAW / f"wfp_prices/wfp_food_prices_{iso.lower()}.csv").assign(iso3=iso)
                        for iso in COUNTRIES], ignore_index=True)
    log(f"wfp price rows: {len(prices):,}")
    prices = prices[prices.market != "National Average"]  # not a real market
    # market 2280 "oum hadjer" has no location, but it's the same town as market 5623 "oumhadjer"
    prices.loc[prices.market_id == 2280, ["admin1", "admin2", "latitude", "longitude"]] = ["Batha", "Batha-Est", 13.23, 19.24]

    prices["month"] = prices.date.str[:7]  # "2015-01-15" -> "2015-01"
    prices = prices[(prices.pricetype == "Retail") & (prices.unit == "KG")
                    & prices.month.between(FIRST_MONTH, LAST_MONTH)]
    food_by_commodity = {(iso, commodity): food for food, names in FOODS.items() for iso, commodity in names.items()}
    prices["food"] = [food_by_commodity.get(key) for key in zip(prices.iso3, prices.commodity)]
    prices = prices.dropna(subset=["food"]).copy()
    log(f"  retail staple prices {FIRST_MONTH}..{LAST_MONTH}: {len(prices):,}")
    assert not prices.duplicated(["market_id", "food", "month"]).any()

    code_by_name = code_by_region_name(regions)
    prices["region_code"] = [code_by_name.get((iso, simplify_name(name))) for iso, name in zip(prices.iso3, prices.admin1)]
    assert prices.region_code.notna().all(), prices[prices.region_code.isna()].admin1.unique()

    # missing-data rule
    # month_number counts months from year 0 (2015-01 -> 24181)
    # gap = difference between two month numbers
    prices["year"] = prices.month.str[:4].astype(int)
    prices["month_of_year"] = prices.month.str[5:].astype(int)
    prices["month_number"] = prices.year * 12 + prices.month_of_year
    months_of_series = prices.groupby(["market_id", "food"]).month_number
    prices["series_coverage"] = months_of_series.transform("nunique") / len(ALL_MONTHS)
    gap = months_of_series.transform(longest_gap)
    keep = (prices.series_coverage >= MIN_SHARE_OF_MONTHS) & (gap <= MAX_MONTHS_MISSING_IN_A_ROW)
    log(f"  series kept: {prices[keep].groupby(['market_id', 'food']).ngroups} of {months_of_series.ngroups}")
    prices = prices[keep].sort_values(["market_id", "food", "month_number"]).copy()
    log(prices.drop_duplicates(["market_id", "food"]).groupby(["iso3", "food"]).size().unstack(fill_value=0))
    log(f"  markets: {prices.market_id.nunique()} {prices.groupby('iso3').market_id.nunique().to_dict()}")

    # flag outliers but keep them, some extreme prices are real (djibo was under blockade in late 2022, 6x normal)
    # each price is compared to the median of the 13 months around it, so a long spike like djibo's
    # doesn't get flagged, only single weird values do
    typical_price = prices.groupby(["market_id", "food"]).price.transform(
        lambda p: p.rolling(13, center=True, min_periods=6).median())
    prices["outlier_flag"] = (prices.price > 3 * typical_price) | (prices.price < typical_price / 3)
    log(f"  prices flagged as outliers: {prices.outlier_flag.sum()}")

    # price index, 2019 = 100 (last normal year before covid and the 2022 spike)
    # only if the series has at least 6 prices in 2019
    price_2019 = (prices[prices.year == 2019].groupby(["market_id", "food"]).price
                  .agg(price_2019="mean", months_in_2019="count").reset_index())
    price_2019 = price_2019[price_2019.months_in_2019 >= 6]
    prices = prices.merge(price_2019[["market_id", "food", "price_2019"]], on=["market_id", "food"], how="left")
    prices["price_index"] = prices.price / prices.price_2019 * 100

    # % change vs 1 and 12 months before (empty if there was no price back then)
    for column, months_back in [("pct_change_mom", 1), ("pct_change_yoy", 12)]:
        earlier = prices[["market_id", "food", "month_number", "price"]].rename(columns={"price": "earlier_price"})
        earlier["month_number"] += months_back
        prices = prices.merge(earlier, on=["market_id", "food", "month_number"], how="left")
        prices[column] = (prices.price / prices.earlier_price - 1) * 100
        prices = prices.drop(columns="earlier_price")

    prices = prices.merge(regions, on=["iso3", "region_code"])
    prices = prices.rename(columns={"admin2": "district", "commodity": "commodity_raw",
                                    "price": "price_lcu", "usdprice": "price_usd"})
    columns = ["country", "iso3", "region_code", "region_name", "district", "market", "market_id", "latitude",
               "longitude", "food", "commodity_raw", "category", "month", "year", "month_of_year", "currency",
               "price_lcu", "price_usd", "price_index", "pct_change_mom", "pct_change_yoy", "series_coverage",
               "outlier_flag"]
    return prices[columns].round(2).sort_values(["iso3", "region_code", "market", "food", "month"])


# rainfall

def clean_rainfall(regions):
    rain = pd.concat([pd.read_csv(RAW / f"rainfall/{iso.lower()}-rainfall-subnat-full.csv") for iso in COUNTRIES])
    # level 1 = regions. prelim values are only the last few weeks of 2026 anyway
    rain = rain[(rain.adm_level == 1) & (rain.version == "final")]
    rain["month"] = rain.date.str[:7]

    # one value every 10 days, so add up the 3 values of each month
    monthly = (rain.groupby(["PCODE", "month"]).agg(rain_mm=("rfh", "sum"), normal_mm=("rfh_avg", "sum"))
               .reset_index().rename(columns={"PCODE": "region_code"}))
    assert set(monthly.region_code) == set(regions.region_code)
    monthly["rain_anomaly_mm"] = monthly.rain_mm - monthly.normal_mm
    # the raw "% of normal" says 100% in dry months because it's 0 mm / 0 mm, so skip those
    monthly["rain_pct_normal"] = (monthly.rain_mm / monthly.normal_mm * 100).where(monthly.normal_mm >= 10)

    # total rain of each rainy season (june-september) vs normal
    monthly["year"] = monthly.month.str[:4].astype(int)
    monthly["month_of_year"] = monthly.month.str[5:].astype(int)
    seasons = (monthly[monthly.month_of_year.between(6, 9)].groupby(["region_code", "year"])
               [["rain_mm", "normal_mm"]].sum().reset_index())
    seasons["prev_rainy_season_pct_normal"] = seasons.rain_mm / seasons.normal_mm * 100

    # each month gets the last rainy season that already ended: oct-dec -> this year, jan-sep -> last year
    monthly["season_year"] = monthly.year.where(monthly.month_of_year >= 10, monthly.year - 1)
    monthly = monthly.merge(seasons[["region_code", "year", "prev_rainy_season_pct_normal"]]
                            .rename(columns={"year": "season_year"}), on=["region_code", "season_year"], how="left")

    monthly = monthly[monthly.month.between(FIRST_MONTH, LAST_MONTH)]
    return monthly[REGION_AND_MONTH + ["rain_mm", "rain_anomaly_mm", "rain_pct_normal",
                                       "prev_rainy_season_pct_normal"]].round(1)


# conflict

def clean_conflict(regions):
    events = pd.concat([pd.read_csv(RAW / f"ucdp_conflict/conflict_data_{iso.lower()}.csv", low_memory=False)
                        .assign(iso3=iso) for iso in COUNTRIES], ignore_index=True)
    events["month"] = events.date_start.str[:7]  # events lasting longer count in their first month
    events = events[events.month.between(FIRST_MONTH, LAST_MONTH)]
    log(f"ucdp events {FIRST_MONTH}..{LAST_MONTH}: {len(events):,} {events.groupby('iso3').size().to_dict()}")

    # where_prec = how exactly the place is known
    # 1 = exact ... 4 = only the region
    # 5 and up = vaguer than that (e.g. "northern mali")
    log(f"  dropped, location vaguer than a region: {(events.where_prec > 4).sum()}")
    events = events[events.where_prec <= 4]

    # get the region from the coordinates, because ucdp's region names mix old and new regions
    # (ménaka, timetrine...) and some are empty
    points = gpd.GeoDataFrame(events, geometry=gpd.points_from_xy(events.longitude, events.latitude), crs=4326)
    placed = gpd.sjoin(points, load_region_outlines(regions), predicate="within")
    placed = placed[placed.iso3_left == placed.iso3_right]  # only regions of the event's own country
    placed = placed.drop_duplicates("id")  # in case region outlines overlap
    log(f"  dropped, outside every region of their country: {len(points) - len(placed)}")

    placed = placed.rename(columns={"iso3_left": "iso3", "best": "deaths_best", "low": "deaths_low", "high": "deaths_high"})
    placed["date_start"] = placed.date_start.str[:10]
    placed["date_end"] = placed.date_end.str[:10]
    return placed[["id", "iso3", "region_code", "month", "date_start", "date_end", "type_of_violence", "side_a", "side_b",
                   "where_prec", "latitude", "longitude", "deaths_best", "deaths_low", "deaths_high", "deaths_civilians"]]


def conflict_per_region_month(events, all_region_months):
    per_month = events.groupby(REGION_AND_MONTH)
    counts = pd.DataFrame({"conflict_events": per_month.size(), "conflict_deaths": per_month.deaths_best.sum(),
                           "civilian_deaths": per_month.deaths_civilians.sum()})
    # 1 = government vs armed group, 2 = between armed groups, 3 = against civilians
    for type_code, type_name in [(1, "state"), (2, "nonstate"), (3, "onesided")]:
        of_type = events[events.type_of_violence == type_code].groupby(REGION_AND_MONTH).deaths_best
        counts[f"events_{type_name}"] = of_type.size()
        counts[f"deaths_{type_name}"] = of_type.sum()
    counts = all_region_months.merge(counts.reset_index(), on=REGION_AND_MONTH, how="left")
    number_columns = counts.columns.drop(REGION_AND_MONTH)
    counts[number_columns] = counts[number_columns].fillna(0).astype(int)  # no recorded event = 0, not missing
    return counts


# hunger (cadre harmonise)

def load_hunger_data():
    hunger = pd.read_excel(RAW / "cadre_harmonise/cadre_harmonise_caf_ipc_mars26.xlsx")
    hunger = hunger[hunger.adm0_name.isin(COUNTRIES.values()) & (hunger.usethisperiod == "Y")].copy()
    # cadre harmonise uses NE01 and TD01, the other files use NE001 and TCD01
    hunger["region_code"] = (hunger.adm1_pcod2.str.replace(r"^NE", "NE0", regex=True)
                             .str.replace(r"^TD", "TCD", regex=True))
    hunger["chtype"] = hunger.chtype.str.lower()  # both "Current" and "current" occur
    return hunger


def hunger_per_region_season(hunger):
    hunger = hunger[hunger.reference_year.between(int(FIRST_MONTH[:4]), int(LAST_MONTH[:4]))].copy()
    one_analysis = ["region_code", "reference_year", "reference_label", "chtype"]
    area_columns = ["adm2_pcod2", "adm2_5_pcod2", "adm3_pcod2"]
    hunger[area_columns] = hunger[area_columns].fillna("")

    # avoid counting people twice (in hunger data some areas appear at two levels of detail)
    # bamako communes, niamey arrondissements: use the district's own row if the analysis has one, otherwise add up the parts
    # some of chad's analyses also have one row for the whole region: drop when the same analysis has district rows
    hunger["is_district"] = hunger.adm2_pcod2 != ""
    hunger["is_part"] = (hunger.adm2_5_pcod2 != "") | (hunger.adm3_pcod2 != "")
    hunger["is_whole_district"] = hunger.is_district & ~hunger.is_part
    has_whole_district = hunger.groupby(one_analysis + ["adm2_pcod2"]).is_whole_district.transform("any")
    has_districts = hunger.groupby(one_analysis).is_district.transform("any")
    double = (hunger.is_part & has_whole_district) | (~hunger.is_district & has_districts)
    log(f"cadre harmonise rows dropped to avoid double counting: {double.sum()}")
    hunger = hunger[~double]
    # a few areas appear twice, from two analysis rounds: keep the latest
    hunger = hunger.sort_values(["exercise_year", "exercise_code"]).drop_duplicates(one_analysis + area_columns, keep="last")

    # some areas were not checked in some rounds, so they have no numbers
    # leave them out of the share instead of counting them as "nobody in crisis"
    hunger["population_analysed"] = hunger.population.where(hunger.phase35.notna())
    per_analysis = hunger.groupby(one_analysis)
    regions = per_analysis.agg(population=("population", "sum"), population_analysed=("population_analysed", "sum"),
                               worst_district_phase=("phase_class", "max"), n_areas=("population", "size"))
    phases = ["phase1", "phase2", "phase3", "phase4", "phase5", "phase35"]
    regions[phases] = per_analysis[phases].sum(min_count=1)
    regions["share_phase35"] = (regions.phase35 / regions.population_analysed.where(regions.population_analysed > 0) * 100).round(2)
    regions["pct_population_analysed"] = (regions.population_analysed / regions.population * 100).round(1)
    log(f"  region-seasons only partly analysed: {(regions.pct_population_analysed < 100).sum()}")
    return regions.reset_index()


def hunger_per_month(per_season):
    # each analysis is used for every month of its season (no interpolating between seasons)
    season_months = pd.DataFrame([(label, m) for label, months in SEASON_MONTHS.items() for m in months],
                                 columns=["reference_label", "month_of_year"])
    monthly = per_season.merge(season_months, on="reference_label")
    monthly["month"] = monthly.reference_year.astype(str) + "-" + monthly.month_of_year.map("{:02d}".format)

    current = monthly[monthly.chtype == "current"].copy()
    current["ch_season"] = current.reference_label + " " + current.reference_year.astype(str)
    current = current.rename(columns={"share_phase35": "ch_share_phase35"})
    # june-august only has projections, so they get their own column
    projected = monthly[(monthly.chtype == "projected") & (monthly.reference_label == "Jun-Aug")]
    projected = projected.rename(columns={"share_phase35": "ch_proj_share_phase35"})
    return current[REGION_AND_MONTH + ["ch_share_phase35", "ch_season"]].merge(
        projected[REGION_AND_MONTH + ["ch_proj_share_phase35"]], on=REGION_AND_MONTH, how="outer")


# world prices (fao)

def load_world_prices():
    fao = pd.read_csv(RAW / "fao/food_price_indices_data.csv", skiprows=2)  # the header is on row 3
    fao = fao.dropna(subset=["Date"]).rename(columns={"Date": "month", "Food Price Index": "fao_food_index",
                                                      "Cereals": "fao_cereals_index", "Oils": "fao_oils_index"})
    fao = fao[fao.month.between(FIRST_MONTH, LAST_MONTH)]
    return fao[["month", "fao_food_index", "fao_cereals_index", "fao_oils_index"]]


# putting it together

VARIABLES = [  # name, type, unit, description
    ("country", "categorical", "", "Country"),
    ("iso3", "categorical", "", "ISO country code"),
    ("region_code", "categorical", "", "Region (admin 1) code; old regions for Mali and Burkina Faso"),
    ("region_name", "categorical", "", "Region name"),
    ("district", "categorical", "", "District (admin 2) of the market"),
    ("market", "categorical", "", "Market name"),
    ("market_id", "categorical", "", "WFP market ID"),
    ("latitude", "quantitative", "degrees", "Market latitude"),
    ("longitude", "quantitative", "degrees", "Market longitude"),
    ("food", "categorical", "", "Staple food: millet, sorghum, maize, rice_local, rice_imported, cowpeas"),
    ("commodity_raw", "categorical", "", "Food name as WFP records it"),
    ("category", "categorical", "", "WFP food category"),
    ("month", "ordinal", "YYYY-MM", "Month of the price"),
    ("year", "ordinal", "", "Year"),
    ("month_of_year", "ordinal", "1-12", "Calendar month, for seasonal patterns"),
    ("currency", "categorical", "", "XOF or XAF (Chad); both CFA francs at the same fixed rate to the euro"),
    ("price_lcu", "quantitative", "CFA francs/kg", "Retail price"),
    ("price_usd", "quantitative", "USD/kg", "Retail price in US dollars (WFP conversion)"),
    ("price_index", "quantitative", "2019 = 100", "Price relative to the market's 2019 average for that food"),
    ("pct_change_mom", "quantitative", "%", "Change from the previous month"),
    ("pct_change_yoy", "quantitative", "%", "Change from the same month a year earlier"),
    ("series_coverage", "quantitative", "0-1", "Share of months 2015-2024 this market reports this food"),
    ("outlier_flag", "categorical", "true/false", "Price over 3x or under 1/3 of its 13-month rolling median"),
    ("conflict_events", "quantitative", "count", "UCDP conflict events in the region that month"),
    ("conflict_deaths", "quantitative", "people", "UCDP best estimate of deaths in the region that month"),
    ("rain_mm", "quantitative", "mm", "Rainfall in the region that month"),
    ("rain_anomaly_mm", "quantitative", "mm", "Rainfall minus the long-term average for that month"),
    ("prev_rainy_season_pct_normal", "quantitative", "% of normal", "Last June-September rainy season vs. long-term average"),
    ("ch_share_phase35", "quantitative", "% of population", "Share of the region in Cadre Harmonise phase 3 or worse"),
    ("ch_season", "ordinal", "", "Cadre Harmonise analysis the value comes from"),
    ("fao_food_index", "quantitative", "2014-16 = 100", "FAO Food Price Index (world)"),
    ("fao_cereals_index", "quantitative", "2014-16 = 100", "FAO Cereals Price Index (world)"),
    ("fao_oils_index", "quantitative", "2014-16 = 100", "FAO Vegetable Oils Price Index (world)"),
]


def main():
    OUT.mkdir(exist_ok=True)
    hunger_raw = load_hunger_data()
    regions = load_regions(hunger_raw)
    log(f"regions: {len(regions)} {regions.groupby('iso3').size().to_dict()}")

    prices = clean_prices(regions)
    rain = clean_rainfall(regions)
    events = clean_conflict(regions)
    hunger = hunger_per_region_season(hunger_raw)
    world_prices = load_world_prices()

    # one row for every region and month, so months without data stay visible
    all_region_months = regions[["region_code"]].merge(pd.DataFrame({"month": ALL_MONTHS}), how="cross")
    region_context = (conflict_per_region_month(events, all_region_months)
                      .merge(rain, on=REGION_AND_MONTH, how="left")
                      .merge(hunger_per_month(hunger), on=REGION_AND_MONTH, how="left"))

    # final dataset: every price + what was going on in its region that month
    context_columns = ["conflict_events", "conflict_deaths", "rain_mm", "rain_anomaly_mm",
                       "prev_rainy_season_pct_normal", "ch_share_phase35", "ch_season"]
    final = (prices.merge(region_context[REGION_AND_MONTH + context_columns], on=REGION_AND_MONTH, how="left")
             .merge(world_prices, on="month", how="left"))
    assert len(final) >= 10_000 and final.shape[1] >= 10  # the assignment needs at least 10k rows and 10 columns
    assert [v[0] for v in VARIABLES] == list(final.columns)

    # region x month: median price over the region's markets
    median_prices = prices.pivot_table(index=REGION_AND_MONTH, columns="food", values="price_lcu", aggfunc="median")
    markets_reporting = prices.pivot_table(index=REGION_AND_MONTH, columns="food", values="market_id", aggfunc="nunique")
    region_month = (regions.merge(region_context, on="region_code")
                    .merge(median_prices.add_prefix("price_").reset_index(), on=REGION_AND_MONTH, how="left")
                    .merge(markets_reporting.add_prefix("n_markets_").reset_index(), on=REGION_AND_MONTH, how="left")
                    .merge(world_prices, on="month", how="left"))
    count_columns = [c for c in region_month.columns if c.startswith("n_markets_")]
    region_month[count_columns] = region_month[count_columns].fillna(0).astype(int)

    variables = pd.DataFrame(VARIABLES, columns=["variable", "type", "unit", "description"])
    variables["missing_pct"] = (final.isna().mean() * 100).round(1).to_numpy()
    log("missing values in market_month_full (%):")
    log(variables.loc[variables.missing_pct > 0, ["variable", "missing_pct"]].to_string(index=False))

    save(regions, "regions")
    save(final, "market_month_full")
    save(region_month, "region_month")
    save(events, "conflict_events")
    save(hunger.merge(regions, on="region_code"), "ch_region_season")
    save(variables, "variables")
    (OUT / "log.txt").write_text("\n".join(log_lines) + "\n")


if __name__ == "__main__":
    main()
