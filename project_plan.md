# G1 + A2 Plan: Food Prices in the Sahel

## Topic

Food prices and food insecurity in the Sahel: how conflict, rainfall and global shocks show up in local market prices, and whether price rises come before worsening hunger.

**Audience (pick one):** food security analysts at WFP or NGOs, or cash-assistance programme officers who set and adjust aid amounts.

## Candidate datasets (one per person)

| Person | Dataset | Source and licence | What's in it | Coverage |
|---|---|---|---|---|
| A | WFP food prices | WFP via HDX, CC BY-IGO | 16 columns: date, region, district, market, market ID, latitude, longitude, food category, food, food ID, unit, price flag, price type, currency, price, US dollar price | to 2026 |
| B | UCDP conflict events | UCDP via HDX, CC BY-IGO | 50 columns: date, region, coordinates, sides involved, type of violence, deaths (best, low, high) | to end of 2024 |
| C | Cadre Harmonisé food insecurity (West Africa's equivalent of IPC) | West and Central Africa food security working group via HDX, CC BY | 61 columns: population in phases 1–5 per district, current and projected, plus consumption, livelihood and nutrition indicators | 2014–2026, twice a year |
| D | Subnational rainfall (based on CHIRPS) | WFP via HDX, CC BY | Rainfall every 10 days per region and district, long-term average, % of normal | 1981–Oct 2026 |

Optional context: FAO Food Price Index (global benchmark), World Bank indicators, displacement data (Danish Refugee Council, IOM).


## Downloaded data (Project Data folder)

All raw files are in `Info Visualization/Project Data/raw` (about 176 MB, downloaded 24 Oct 2026).

| Folder | Contents | Countries |
|---|---|---|
| `wfp_prices` | Food prices plus a market list (names, coordinates) | Mali, Burkina Faso, Niger, Chad, Senegal |
| `ucdp_conflict` | Conflict events to end of 2024 | all 5 |
| `rainfall` | Rainfall every 10 days by region and district, 1981–Oct 2026 | all 5 |
| `cadre_harmonise` | Food insecurity phases for West and Central Africa, 2014–2026, plus the documentation PDF | covers all 5 |
| `boundaries` | Official region and district boundaries as GeoJSON (zipped), for maps and for placing conflict events in regions | all 5 |
| `fao` | FAO Food Price Index, monthly from 1990, the global benchmark | world |

**Extra files:**

- `raw/MANIFEST.csv` lists every file with its source link, licence and download date. Use it for G1 source links and the G3 repository.
- `download_data.py` downloads everything again from HDX (`python3 download_data.py`), so everyone can get identical files. The FAO file isn't included because FAO's link changes monthly. `raw/fao/SOURCE.txt` explains where to get it.

**Before opening the files:**

- The WFP, rainfall and UCDP CSVs load normally: the first row is the header and data starts on row 2.
- In the FAO CSV, the header (Date, Food Price Index, Meat, …) is on row 3 and row 4 is blank. Load with `pd.read_csv(f, skiprows=2)`, then drop empty rows and the empty columns.
- The Cadre Harmonisé file covers 19 countries. Filter on `adm0_name` and keep rows with `usethisperiod == "Y"`. Some areas (for example Bamako) have finer-level rows, so don't double count when totalling a region.
- The boundary zips need unzipping before use. The Burkina Faso and Senegal ones are large (about 23 MB) because they include detailed district levels.

## Processing each dataset

Checked against the downloaded files for all 5 countries. Do every step in a script (not by hand in Excel) so the dataset can be rebuilt and published in the G3 repository.

**Common target for everything:** country code (ISO3) + region code (admin level 1, one standard format per country) + month (`YYYY-MM`).

### A. WFP food prices (`wfp_prices`)

1. **Combine** the 5 country files into one table and add a country column (Mali, Burkina Faso, Niger, Chad, Senegal).
2. **Filter rows:**
   - keep `pricetype == "Retail"` (Burkina Faso and Niger also have wholesale rows, priced per 100 kg)
   - keep the shared time window (2015–2024)
   - drop rows that aren't food: wages (`Wage (...)`), livestock (`Livestock (...)`) and Chad's exchange-rate rows (unit `USD/LCU`)
3. **Pick the foods.** Keep the staples recorded across most markets: millet, sorghum, maize, local rice, imported rice, cowpeas (`Beans (niebe)`), and optionally vegetable oil and wheat flour. Chad mostly records pasta, okra, oil, garlic, salt and sugar rather than grains, so decide whether to drop it or treat it separately.
4. **Standardise names and units.** Merge name variants (for example `Maize`, `Maize (white)` and `Maize (local)`, or `Sorghum` and `Sorghum (white)`) only if the team agrees they're the same product. Keep only per-kg prices, or convert (`500 G` × 2, `100 KG` ÷ 100). Oil is per litre: keep it separate.
5. **Dates:** WFP dates are mid-month (`2015-01-15`), so convert them to `2015-01`.
6. **Currency:** keep `price` in CFA francs (XOF for Mali, Burkina Faso, Niger and Senegal, XAF for Chad, both pegged to the euro at the same rate). Optionally add an index column (each series / its 2015 or 2019 average × 100) for comparing foods with different price levels.
7. **Apply the missing-data rule:** count months reported per market × food in the window and keep series above the agreed threshold (for example 80%). Record how many markets and series survive per country and region: this goes in G1 Part 4.
8. **Region code:** WFP gives region *names* (`admin1`) that need mapping to codes (see "Region lookup table" below). Markets also have latitude and longitude, used for the map.

**Result:** `prices_market_month`, one row per market × food × month.

### B. UCDP conflict events (`ucdp_conflict`)

1. **Combine** the 5 country files.
2. **Filter:** shared window (2015–2024). Note that Senegal's file ends in 2021 with few events and Burkina Faso's starts in 2016, so Senegal works as a low-conflict comparison.
3. **Location precision:** `where_prec` says how exactly each event is located (1 = exact place, 2 = within 25 km, 3 = district, 4 = region, 5 = vaguer area such as "northern Mali", 6 = country only, 7 = international). **Keep 1–4** for regional counts. Report how many events were dropped.
4. **Region code:** UCDP's `adm_1` names add " region" ("Gao region") and in Mali include newer regions (Ménaka, Timetrine). Either:
   - assign each event to a region by its coordinates using the old region boundaries in `raw/boundaries_old` (section F), or
   - strip " region" from `adm_1` and map Ménaka → Gao (checked: all 245 Ménaka events fall inside old Gao).
5. **Dates:** use `date_start` → month. Events lasting longer than a month (where `date_end` is later) are rare, so assign them to the start month and note it.
6. **Aggregate** to region × month: number of events, deaths (`best` = best estimate), and both split by `type_of_violence` (1 = government vs armed group, 2 = between armed groups, 3 = violence against civilians).
7. **Fill gaps:** region-months with no events should be **0**, not missing.

**Result:** `conflict_region_month`.

### C. Cadre Harmonisé (`cadre_harmonise`)

1. **Filter:** `adm0_name` in the 5 countries, `usethisperiod == "Y"`, and `chtype` = current (lowercase it first: some rows say "Current" with a capital).
2. **Fix name inconsistencies:** for example Burkina Faso has both `Boucle Du Mouhoun` and `Boucle du Mouhoun`. Use codes (`adm1_pcod2`) instead of names wherever possible.
3. **Avoid double counting:** some areas have rows at a finer level (Bamako has commune-level rows). Keep one level per area before totalling.
4. **Aggregate districts to regions:** sum the population in each phase (`phase1`–`phase5`, `phase35`) and the total population. Then compute the **share in phase 3 or worse** (`phase35 / population`). If you also want a region-level phase, decide the rule (for example the worst district phase) and write it down.
5. **Periods:** each row has a period label (`reference_label`: Sep–Dec or Jan–May) and year (`reference_year`). Keep that as a season key. To join with monthly data, give each month in the period the same value (Sep, Oct, Nov, Dec all get the Sep–Dec analysis), or aggregate monthly data up to these seasons. Never interpolate between analyses.
6. **Projected rows** (the Jun–Aug lean season is only ever projected): if used at all, keep them in a separate column labelled as forecasts.

**Result:** `ch_region_season` (and optionally spread to `ch_region_month`).

### D. Rainfall (`rainfall`)

1. **Combine** the 5 country files, keep `adm_level == 1` (regions). Level 2 is districts, which could be useful later for maps.
2. **Columns:** one row per region per dekad (10-day period, dated the 1st, 11th and 21st). `rfh` = rainfall in mm for that dekad, `rfh_avg` = long-term average for that dekad, `rfq` = rainfall as % of normal. `r1h`/`r3h` are 1- and 3-month rolling totals.
3. **Monthly totals:** sum `rfh` over the 3 dekads of each month, and sum `rfh_avg` the same way. Then compute **% of normal = rainfall / normal × 100**.
4. **Seasonal totals:** the rainy season is roughly June–September. A rainy-season total per region and year is useful for comparing with prices in the following lean season.
5. **Quality:** `version` is `final` or `prelim`. Preliminary values only appear for the most recent dekads. Drop them or flag them.

**Result:** `rain_region_month`.

### E. FAO Food Price Index (`fao`)

1. Load with the header on row 3, drop blank rows and empty columns.
2. Keep `Date` (already `YYYY-MM`), the overall index and the cereals and oils indices.
3. World-level only: it joins to every region on month.

**Result:** `fao_month`.

### F. Boundaries (`boundaries` and `boundaries_old`)

Mali and Burkina Faso recently reorganised their regions, so the newest official boundary files (`raw/boundaries`) don't match the data. **Use these files:**

| Country | Data uses | Boundary file to use |
|---|---|---|
| Mali | 9 old regions | `raw/boundaries_old/geoBoundaries-MLI-ADM1.geojson` (9 regions); ADM2 = 50 districts (cercles) |
| Burkina Faso | 13 old regions | `raw/boundaries_old/geoBoundaries-BFA-ADM1.geojson` (13 regions); ADM2 = 45 provinces |
| Niger, Chad, Senegal | current regions | `raw/boundaries` (official HDX files, unzip first) |

- Source of the old files: [geoBoundaries](https://www.geoboundaries.org), CC BY 4.0. Each comes with a `_simplified` version, which is smaller and better for D3 web maps.
- The geoBoundaries files have **no HDX region codes**. Join on region names through the lookup table (`shapeName`). Note that Mali "Koulikouro" = "Koulikoro".
- **Checked:** every WFP market (Mali 242, Burkina Faso 67) falls inside the region its `admin1` name says. UCDP events in Mali labelled "Ménaka region" fall inside old Gao region (245 events, 2015–2024).
- District files (ADM2) match the Cadre Harmonisé district names (Mali 51, Burkina Faso 45) for district-level hunger maps.

### Region lookup table (build this first)

One small table per country, `country, region_code, name_wfp, name_ch, name_ucdp, name_boundary`, so every dataset can be translated to the same code. Differences found:

- **Spelling and case:** accents (`Tillaberi` / `Tillabéri`, `Thies` / `Thiès`), hyphens (`Chari Baguirmi` / `Chari-Baguirmi`), upper case in the Chad boundaries and in the Burkina Faso WFP data (`BOUCLE DU MOUHOUN`), Mali `Tombouctou` / `Timbuktu`.
- **Code formats:** Niger rainfall and boundaries use `NE001`, the Cadre Harmonisé uses `NE01`. Chad uses `TCD01` versus `TD01`. The numbers match: convert by adding a 0 for Niger and replacing `TD` with `TCD` for Chad (checked against names).
- **Mali, Senegal, Burkina Faso:** codes match between the Cadre Harmonisé and rainfall (Burkina Faso only with the old 13 regions).

## Combining into the final dataset

1. **Build the region lookup table** (above).
2. **Process each dataset** to its result table (A–E).
3. **Create a complete grid:** every region × every month in the window, so missing months are visible instead of silently absent.
4. **Join onto the grid** by `country + region_code + month`:
   - prices: aggregate `prices_market_month` to region level, for example the **median** price per food across the region's markets (the median resists outlier markets). Also keep **the number of markets reporting** as a column.
   - `conflict_region_month` (gaps filled with 0)
   - `rain_region_month`
   - `ch_region_month` (the season value repeated over its months), or keep a separate season-level table
   - `fao_month`, joined on month only
5. **Add calculated columns** if useful: monthly or yearly % price change, price index (base = 100), price gap between imported and local rice, rainfall anomaly in the previous rainy season, months since the last conflict event. Check with the TA whether calculated columns count toward the 10 variables.
6. **Check the result:**
   - row count (at least 10,000) and column count (at least 10)
   - spot-check a few region-months against the raw files
   - count missing values per column (this goes in G1 Part 4)

**Final outputs (in `Project Data/clean`):**

| Table | One row per | Used for |
|---|---|---|
| `prices_market_month.csv` | market × food × month | maps of markets, market-level charts, G3 |
| `region_month.csv` | region × month (prices wide by food + conflict + rain + Cadre Harmonisé + FAO) | most A2 questions, linked G3 views |
| `ch_region_season.csv` | region × Cadre Harmonisé season | questions about hunger phases |

Plus a **variable table** (name, description, type: categorical, ordinal or quantitative, unit, source) for G1 Part 4.

**Shared window:** 2015–2024 for anything involving conflict (UCDP ends in 2024). Price, rainfall and Cadre Harmonisé questions can run to 2026.

## Shared rules to agree on

- [ ] Countries: Mali, Burkina Faso, Niger, Senegal, Chad
- [ ] Time window: 2015–2024
- [ ] Retail prices only
- [ ] Missing-data rule (for example, keep series with at least 80% of months)
- [ ] Standard units (per kg) and food names
- [ ] Currency: CFA francs, or index to a base period (base = 100)

## Research question directions (the team writes the actual questions)

At least 4 needed, one per person, no overlaps. Each A2 chart must be a different type.

- Seasonal patterns by food and region (lean-season price rise)
- Prices before and after conflict starts in a region, and how long the effect lasts
- Local versus imported rice: how global shocks (2022) reach local markets
- Rainfall shortfall versus later price rises
- Do price rises come before a worse Cadre Harmonisé phase?
- Which markets moved together during the 2022 spike, and which stayed stable?

## Chart ideas

Map of markets, calendar heatmap (food × month), event-aligned lines, correlation heatmap of markets, slope or dumbbell charts, scatter plot of rainfall against price change, horizon chart or small multiples.

**G3 idea:** a map of markets linked both ways with a time-series view (click a market, brush a period), plus a conflict timeline and a seasonal heatmap. Requirements to cover: at least 4 techniques including a complex one, 3 interactions, 2 views linked both ways, tooltips.

## Limitations to note in G1

- Correlation is not causation: 2022 combined conflict, drought and global price shocks.
- The Cadre Harmonisé is twice-yearly, so it can't be matched month by month.
- Conflict areas have more missing prices, which is a bias.
- UCDP ends in 2024.

## Meeting agenda (about 1 hour)

1. Confirm the region and countries (5 min)
2. Choose the audience (10 min)
3. Assign candidate datasets A–D (5 min)
4. Agree the shared rules above (15 min)
5. Write research questions and assign owners (20 min)
6. Deadlines: shared dataset, A2 drafts, team PDF with a buffer before TUWEL (5 min)

## Assignment checklist

**G1 (one team PDF):** topic and motivation · target audience · at least 4 candidate datasets (one paragraph each with a link) · final dataset (justification, cleaning, variable table with types, missing values and biases; at least 10,000 rows and 10 variables) · at least 4 research questions · all A2 charts, each with its author's name.

**A2 (one PDF per person):** 2 charts of different types, each with a research question, a high-resolution figure (title, labels, units, legend), and a 1–2 paragraph design rationale.

## Sources

- WFP food prices: https://data.humdata.org/dataset/global-wfp-food-prices
- UCDP Mali: https://data.humdata.org/dataset/ucdp-data-for-mali
- Cadre Harmonisé: https://data.humdata.org/dataset/cadre-harmonise
- Rainfall Mali: https://data.humdata.org/dataset/mli-rainfall-subnational
- Mali boundaries (new): https://data.humdata.org/dataset/cod-ab-mli
- Old Mali and Burkina Faso boundaries: https://www.geoboundaries.org (CC BY 4.0)
- ACLED terms: https://acleddata.com/eula
