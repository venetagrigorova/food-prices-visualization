# G1 + A2 Plan: Food Prices in the Sahel

## Topic

Food prices and food insecurity in the Sahel: how conflict, rainfall and global shocks show up in local market prices, and whether price rises come before worsening hunger.

## Target audience

**Cash-assistance programme officers** at WFP and NGOs: the people who decide how much money families get each month in cash transfers.

- **What they know:** the region, the local foods and how cash programmes work. They are not data specialists.
- **What they want to learn:** when and where food gets more expensive, how much, and whether a price jump is a normal seasonal rise or something new (conflict, a bad harvest, world prices).
- **Why it matters to them:** if millet costs 30% more, the same transfer buys 30% less food. They have to decide when to raise the amount and for which regions.
- **Why interactive:** each officer covers one region and a few foods. They need to filter to their own markets, compare with neighbouring regions, and check rain and conflict for the same months, which a static report can't do for everyone at once.

We chose them over food security analysts because they make a concrete decision from prices, which every chart can be tied to.

## Candidate datasets (one per person)

| Person | Dataset | Source and licence | What's in it | Coverage |
|---|---|---|---|---|
| A | WFP food prices | WFP via HDX, CC BY-IGO | 16 columns: date, region, district, market, market ID, latitude, longitude, food category, food, food ID, unit, price flag, price type, currency, price, US dollar price | to 2026 |
| B | UCDP conflict events | UCDP via HDX, CC BY-IGO | 50 columns: date, region, coordinates, sides involved, type of violence, deaths (best, low, high) | to end of 2024 |
| C | Cadre Harmonisé food insecurity (West Africa's equivalent of IPC) | West and Central Africa food security working group via HDX, CC BY | 61 columns: population in phases 1–5 per district, current and projected, plus consumption, livelihood and nutrition indicators | 2014–2026, twice a year |
| D | Subnational rainfall (based on CHIRPS) | WFP via HDX, CC BY | Rainfall every 10 days per region and district, long-term average, % of normal | 1981–Oct 2026 |

Optional context: FAO Food Price Index (global benchmark, already included), World Bank indicators, displacement data (Danish Refugee Council, IOM).

## Data and cleaning: status

**Done.** Raw files are in `raw/` (about 178 MB, downloaded 24 Oct 2026). `clean_data.py` turns them into the tables in `clean/`.

```
python3 -m venv data-viz && source data-viz/bin/activate
pip install -r requirements.txt
python3 clean_data.py          # about 30 seconds
```

- **The team's rules are the constants at the top of `clean_data.py`** (countries, years, missing-data rule, foods). To change a rule, change it there and rerun. Never edit files in `clean/` by hand.
- `clean/log.txt` has every count (rows dropped, series kept, missing values). Copy from it for G1 Part 4.
- `clean/variables.csv` is the variable table (name, type, unit, description, % missing) for G1 Part 4.
- `raw/MANIFEST.csv` lists every raw file with its source link, licence and download date. `download_data.py` downloads it all again from HDX.

### Output tables

| Table | One row per | Rows × columns | Used for |
|---|---|---|---|
| **`market_month_full.csv`** | market × food × month, plus region context (conflict, rain, Cadre Harmonisé, FAO) | **102,811 × 33** | **The final dataset for G1 Part 4.** Most A2 charts. |
| `region_month.csv` | region × month: median price per food, number of markets, conflict by type, rain, Cadre Harmonisé, FAO | 8,040 × 36 | Region-level charts, G3 linked views. **Below 10,000 rows, so not the "final dataset".** |
| `conflict_events.csv` | UCDP event | 4,262 × 16 | Event maps, timelines |
| `ch_region_season.csv` | region × Cadre Harmonisé season (current and projected) | 1,921 × 19 | Hunger-phase questions |
| `regions.csv` | region | 67 × 4 | Codes and names, for joining with maps |

**Final dataset coverage:** 252 markets, 950 market × food series, 5 countries, 6 staple foods, 2015–2024.

| Country | Markets | Series | Foods with data |
|---|---|---|---|
| Burkina Faso | 63 | 270 | all 6 |
| Mali | 68 | 289 | all 6 |
| Niger | 53 | 201 | millet, sorghum, maize, imported rice (no cowpeas, no local rice) |
| Senegal | 41 | 128 | millet, sorghum, maize, local rice, imported rice (no cowpeas) |
| Chad | 27 | 62 | millet, sorghum, maize, imported rice (local rice: 1 market only) |

## Shared rules (proposed, already used by the script)


- [ ] **Countries:** Mali, Burkina Faso, Niger, Senegal, Chad. Chad is weakest (27 markets, fewer foods) but usable; it can be filtered out per chart.
- [ ] **Time window:** 2015–2024 (UCDP ends in 2024)
- [ ] **Retail prices only**
- [ ] **Foods:** millet, sorghum, maize, local rice, imported rice, cowpeas, per kg
- [ ] **Missing-data rule:** keep a market × food series if it reports **at least 60% of months** and has **no gap longer than 12 months**. (80% would leave Senegal with 88 series and Chad with 50; a 6-month gap limit would remove almost all of Senegal, which had a country-wide pause of about 8 months.)
- [ ] **Outliers:** flagged in `outlier_flag`, **never removed**. Only 12 prices are flagged. Some extreme prices are real: Djibo (Burkina Faso) in late 2022 at 6× normal during the blockade is not flagged and is kept.
- [ ] **Currency:** CFA francs (`price_lcu`), plus `price_index` (each series' 2019 average = 100) for comparing foods and countries
- [ ] **Comparing countries or foods:** use `price_index`, not CFA francs (price levels differ a lot between foods)
- [ ] **Averaging over markets:** use the median, not the mean, so one odd market doesn't pull the result
- [ ] **Weak data:** don't use Senegal on its own for 2022 (collection pause) or Chad for rice (too few markets). Every chart says which countries it includes.

## How each dataset was cleaned

Region code everywhere = the HDX code (`ML05`, `BF46`, `NE001`, `SN10`, `TCD18`). Time = month (`YYYY-MM`).

### Regions

67 regions (Burkina Faso 13, Mali 9, Niger 8, Senegal 14, Chad 23), with names taken from the Cadre Harmonisé.

- Names are matched after removing case, accents, hyphens and the word "region" (`Tillabéri region` = `TILLABERI`). Two spellings are fixed by hand (`Koulikouro`, `Barh El Gazal`).
- The Cadre Harmonisé writes `NE01` and `TD01`; converted to `NE001` and `TCD01`.
- **Mali and Burkina Faso use the old regions** (9 and 13). The new official boundary files on HDX don't match the data: Burkina Faso's has the 17 new regions, and Mali's reuses codes (`ML09` is Taoudenni there but Bamako in the Cadre Harmonisé and rainfall data). The old boundaries come from geoBoundaries (`raw/boundaries_old`).

### WFP prices

1. Combine the 5 countries, drop the 38 "National Average" rows (not a market).
2. Chad market 2280 "Oum Hadjer" has no location: use that of market 5623 "Oumhadjer" (same town, Batha region).
3. Keep retail, 2015–2024, and the 6 staple foods per kg. **One raw name per food and country**, because Chad records several variants in the same market and month (merging them gave 403 clashes). Chad uses `Sorghum (red)` and `Maize (white)`, Burkina Faso `Sorghum (white)` and `Maize (white)`, Senegal `Maize (local)`. Senegal's imported maize is a different product and is left out.
4. Apply the missing-data rule: 950 of 2,064 series kept.
5. Flag outliers: price more than 3× or less than 1/3 of the series' 13-month rolling median. A rolling median follows sustained real spikes like Djibo, but catches single odd values (e.g. Filingue imported rice at 45 CFA, Mandelia millet at 15 CFA).
6. Add `price_index` (2019 = 100), month-on-month and year-on-year % change (empty when the earlier month is missing, never filled in).

### Rainfall

1. Keep region level, drop preliminary values (only the latest weeks of 2026, outside the window anyway).
2. Monthly total = sum of the three 10-day values, the same for the long-term average.
3. `rain_anomaly_mm` = rainfall − normal. `rain_pct_normal` only where the normal is at least 10 mm: **in dry months the raw "% of normal" shows 100% because it is 0 mm ÷ 0 mm**, which is meaningless.
4. `prev_rainy_season_pct_normal` gives every month the last finished June–September rainy season (Oct–Dec: this year's, Jan–Sep: last year's).

### UCDP conflict

1. 4,853 events in 2015–2024. Load with pandas, never Excel: some text fields contain line breaks.
2. Drop the 585 events (12%) located only vaguely (`where_prec` 5–7).
3. **Place events in regions by their coordinates**, not by UCDP's region names, which mix old and new regions (Ménaka, Timetrine, Borkou-Ennedi-Tibesti) and are missing for 101 events. Checked: placement agrees with UCDP's names for Mali, and all 246 Ménaka events land in old Gao. 6 events just outside their country's borders are dropped. 4,262 events kept.
4. 105 events lasting into a later month are counted in their start month.
5. Count events and deaths per region and month, also split by type of violence. Region-months without events are **0**, not missing.
6. Senegal has only 4 events in 10 years: use it as the "no conflict" comparison and say so.

### Cadre Harmonisé

1. Keep the 5 countries, `usethisperiod == "Y"`, 2015–2024. `chtype` is lower-cased (it is spelled both ways).
2. **One level per area, so nothing is counted twice** (131 rows dropped): finer rows (e.g. Bamako communes, Niamey arrondissements) are used only when the round has no district row for that area, and Chad's region-only rows only when the round has no district rows.
3. 64 rows are areas not analysed in that round (no phase data). They are left out of the share instead of counting as "0 people in crisis". `pct_population_analysed` shows how much of a region was covered (21 region-seasons are partly covered).
4. Sum districts to regions. Main measure: **`share_phase35`** = % of the population in phase 3 or worse. (The region's worst district phase is also kept, but it hardly varies: only 12 district rows ever reach phase 4.)
5. In the monthly tables each current analysis is repeated over its months (Jan–May, Sep–Dec). **June–August only ever has projections**, kept separately as `ch_proj_share_phase35` in `region_month`. Never interpolate between analyses.
6. **Missing current seasons:** Mali Jan–May 2022, Niger Jan–May 2024, Burkina Faso Sep–Dec 2024 (Burkina Faso stopped publishing). Show these as gaps.

### FAO Food Price Index

Header on row 3 of the CSV. Keeps the overall, cereals and oils indices (2014–2016 = 100), world level, joined on month only. The FAO file isn't in `download_data.py` because FAO's link changes monthly: see `raw/fao/SOURCE.txt`.

### Combining

- `market_month_full`: prices plus region context on `region_code + month`, FAO on month.
- `region_month`: every region × month (67 × 120), so missing months are visible. Price per food = **median across the region's markets** (it resists outlier markets), plus the number of markets reporting.

### Missing values in the final dataset (for G1 Part 4)

| Variable | Missing | Why |
|---|---|---|
| `price_index` | 0.9% | series with fewer than 6 months of data in 2019 |
| `pct_change_mom` | 6.0% | previous month not reported |
| `pct_change_yoy` | 16.2% | same month last year not reported (always empty in a series' first 12 months) |
| `ch_share_phase35` | 29.0% | June–August is never analysed "current" (25% of months), plus the missing seasons above |

In `region_month`, 87% of region-months have at least one price; Chad only 67%.

## Research questions

One per person (4 people). Each owner makes two A2 charts of **different types**: a main chart and a follow-up. The 8 chart types don't repeat across the team. Fill in the names at the meeting.

| # | Owner | Research question | Chart A | Chart B (follow-up) | Data notes |
|---|---|---|---|---|---|
| 1 | | **Seasons:** how much do staple prices rise in the lean season, and where is it worst? | Heatmap: month × food (or × region), colour = price index | Small multiples (one line chart per country): did the seasonal rise get bigger after 2020? | Millet is about 20% higher in Aug–Sep than in January. Matters for when transfers go up. |
| 2 | | **Conflict:** do prices in a region rise faster after conflict there increases than in calmer regions? | Line chart lined up on the month violence escalated, 12 months before to 12 after, vs. calm regions | Map of markets coloured by how far their prices moved from the national median | Agree how to define "escalation" (e.g. first month with 5+ events). Correlation, not proof. Senegal is the low-conflict comparison. |
| 3 | | **World prices:** did the 2022 global spike reach imported rice more than local grains? | Line chart of imported rice, local rice and millet index vs. the FAO world index, 2019–2024 | Dumbbell chart: 2021 vs. 2022 price per country and food | Use Mali, Burkina Faso, Senegal (Niger has no local rice, Chad too few markets). |
| 4 | | **Rain:** are prices higher after a poor rainy season? | Scatter plot: last rainy season (% of normal) vs. year-on-year millet price change, one dot per region and year | Box plot of price changes by rain category (dry / normal / wet) | Use `prev_rainy_season_pct_normal` and `pct_change_yoy`. Agree the cut-offs for dry and wet (e.g. below 90%, above 110%). |

**Possible follow-up (not assigned):** are regions with bigger price rises more likely to have more people in crisis at the next Cadre Harmonisé analysis? (connected scatter or slope chart). Mention it in G1 and keep it for G3.

## Chart ideas for G3

**G3 idea:** a map of markets linked both ways with a time-series view (click a market, brush a period), plus a conflict timeline and a seasonal heatmap. The four questions above already give the pieces. Requirements to cover: at least 4 techniques including a complex one, 3 interactions, 2 views linked both ways, tooltips.

## Limitations to note in G1

- Correlation is not causation: 2022 combined conflict, drought and global price shocks.
- The Cadre Harmonisé is twice-yearly, so it can't be matched month by month, and June–August is only projected.
- Conflict areas have more missing prices, which is a bias: the worst-hit markets are the ones most likely to drop out (e.g. Chad, northern Mali).
- Coverage is uneven: Burkina Faso and Mali have many more series than Senegal and Chad, and some foods are missing in some countries.
- UCDP ends in 2024 and records only events with at least one death, so low-level violence is not counted.
- Prices are nominal (not adjusted for inflation). Inflation in the CFA zone is fairly low, but say so.


## Assignment checklist

**G1 (one team PDF):** topic and motivation · target audience · at least 4 candidate datasets (one paragraph each with a link) · final dataset (justification, cleaning, variable table with types, missing values and biases; at least 10,000 rows and 10 variables) · at least 4 research questions · all A2 charts, each with its author's name.

**A2 (one PDF per person):** 2 charts of different types, each with a research question, a high-resolution figure (title, labels, units, legend), and a 1–2 paragraph design rationale.

## Sources

- WFP food prices: https://data.humdata.org/dataset/global-wfp-food-prices
- UCDP Mali: https://data.humdata.org/dataset/ucdp-data-for-mali
- Cadre Harmonisé: https://data.humdata.org/dataset/cadre-harmonise
- Rainfall Mali: https://data.humdata.org/dataset/mli-rainfall-subnational
- FAO Food Price Index: https://www.fao.org/worldfoodsituation/foodpricesindex/en/
- Mali boundaries (new): https://data.humdata.org/dataset/cod-ab-mli
- Old Mali and Burkina Faso boundaries: https://www.geoboundaries.org (CC BY 4.0)
- ACLED terms: https://acleddata.com/eula
