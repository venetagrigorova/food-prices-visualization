# G2 Plan: Project Proposal

## Goal

One PDF with sections 0–5 (Basic Information, Project Overview, Data Description, Task Analysis, Design Sketches, Usage Scenario).

**Deadline:** ___ (fill in)

A first draft of every section is already written in LaTeX (`Information_Visualization__Group_Assignment_2/main.tex`, to be uploaded to Overleaf). Each person checks, edits and owns their part. Everyone must be able to explain the whole proposal.

## The design in short

Four linked views, filtered by country and food:

| View | What it shows |
|---|---|
| A: Map | regions coloured by the selected measure, markets as dots (price vs. national median) |
| B: Time series | price index of the selected region, its markets, national median and world cereal index, with tracks below for conflict, rain and people in crisis; brush to select a period |
| C: Seasonal heatmap | years × months, colour = price compared with that year's average, plus a "normal season" row (2015–2019) |
| D: Scatter plot | one dot per region: price change in the selected period vs. share of people in crisis at the next Cadre Harmonisé analysis |

Links: click a region in A or D and all views update. Click a market in A and its line is highlighted in B (and the other way round). Brush a period in B and A and D update.

## Who does what

| Person | View (sketch + justification in 4.2) | Report section |
|---|---|---|
| **Veneta** | B: time series, plus Sketch 3 (brushing a period) | 2 Data Description |
| **Emon** | A: map, plus Sketch 2 (clicking a region) | 3 Task Analysis |
| **Ahmad** | D: scatter plot, plus the rain track in B | 5 Usage Scenario |
| **Amira** | C: seasonal heatmap, plus Sketch 1 (full layout) | 0–1 Overview, 4.1 Interface overview, final merge and compile |

Why: each view matches what that person made in G1 (Veneta: world prices and the cleaning script, Emon: market map, Ahmad: rain scatter plot, Amira: seasonal heatmap). Sections cut across the views, so everyone has to know more than their own part. The usage scenario uses all four views, so it also works as a check that the views fit together.

Optional: if Amira's share is too large, Ahmad also takes 4.1.

## Steps

1. **Team meeting (about 1 hour):** agree on the four views, the interactions and the layout. Sketch the layout together. Amira draws the clean version (Sketch 1).
2. **Individual work:** draw your sketch, edit your section and your view's paragraph in 4.2.
3. **Numbers:** if you change a number, recompute it from the files in `clean/` and write down how.
4. **Merge:** Amira merges everything in Overleaf and compiles.
5. **Final read:** everyone reads the whole PDF once and comments before submission.

## Rules for the sketches

- **No generative AI.** Hand-drawn is preferred; PowerPoint, Figma etc. are allowed.
- Maximum **five sketches** in total. Planned: 3 (layout, click a region, brush a period). Two more are possible.
- Include all titles, widgets, legends and axis labels. Annotations must be readable.
- Scan or export in high resolution as PNG and use these file names (the LaTeX already includes them):
  - `sketch1_layout.png`
  - `sketch2_select_region.png`
  - `sketch3_brush_period.png`

## Checklist per person

**Veneta (Data Description)**
- [ ] Source links are correct
- [ ] Dataset and attribute tables match `clean/` (types, counts, ranges)
- [ ] Derived attributes: agree which ones are really needed
- [ ] Preprocessing: every filter has a reason
- [ ] Sketch 3 + justification of view B

**Emon (Task Analysis)**
- [ ] Domain tasks D1–D5 make sense for a cash-assistance officer
- [ ] Abstract tasks T1–T5 use the Brehmer & Munzner terms correctly
- [ ] At least 5 distinct attributes, mapping table complete
- [ ] Sketch 2 + justification of view A

**Ahmad (Usage Scenario)**
- [ ] Scenario uses every view and matches the final design
- [ ] Every number in it is rechecked in the data
- [ ] Motivation at the start and takeaways at the end are clear
- [ ] Justification of view D

**Amira (Overview, 4.1, merge)**
- [ ] Overview and target users are specific and match G1
- [ ] Interface overview matches the sketches
- [ ] Sketch 1 + justification of view C
- [ ] PDF compiles, all sketches are readable, sections are in the required order

## Open points for the meeting

- Are four views realistic to build this semester, or should one be dropped?
- Are the team e-mail addresses (`e<student number>@student.tuwien.ac.at`) correct?
- Deadline and date for the final read.
