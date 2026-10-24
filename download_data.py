"""Download raw datasets for the Sahel food prices project from HDX.
Usage: python3 download_data.py   (saves into ./raw, writes ./raw/MANIFEST.csv)
"""
import csv, json, os, urllib.request, datetime

COUNTRIES = {"mali": "mli", "burkina-faso": "bfa", "niger": "ner", "chad": "tcd", "senegal": "sen"}
API = "https://data.humdata.org/api/3/action/package_show?id="
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

def package(pid):
    with urllib.request.urlopen(API + pid, timeout=60) as r:
        return json.load(r)["result"]

def want(dataset_id, resource_url):
    f = resource_url.rsplit("/", 1)[-1].lower()
    if dataset_id.startswith("wfp-food-prices"): return f.startswith("wfp_food_prices") or f.startswith("wfp_markets")
    if dataset_id.startswith("ucdp-data"): return f.endswith(".csv")
    if "rainfall" in dataset_id: return f.endswith("-full.csv")
    if dataset_id.startswith("cod-ab"): return f.endswith(".geojson.zip")
    if dataset_id == "cadre-harmonise": return f.endswith(".xlsx") or f.endswith("en.pdf")
    return False

jobs = [("cadre-harmonise", "cadre_harmonise")]
for name, iso in COUNTRIES.items():
    jobs += [(f"wfp-food-prices-for-{name}", "wfp_prices"),
             (f"ucdp-data-for-{name}", "ucdp_conflict"),
             (f"{iso}-rainfall-subnational", "rainfall"),
             (f"cod-ab-{iso}", "boundaries")]

rows = []
for pid, folder in jobs:
    try:
        p = package(pid)
    except Exception as e:
        print("FAILED", pid, e); rows.append([pid, "", "", "", "FAILED: %s" % e]); continue
    os.makedirs(os.path.join(OUT, folder), exist_ok=True)
    for r in p["resources"]:
        if not want(pid, r["url"]): continue
        fn = r["url"].rsplit("/", 1)[-1]
        dest = os.path.join(OUT, folder, fn)
        urllib.request.urlretrieve(r["url"], dest)
        size = os.path.getsize(dest)
        print(f"{folder}/{fn}  {size/1e6:.1f} MB")
        rows.append([pid, f"{folder}/{fn}", p.get("license_title"), f"https://data.humdata.org/dataset/{pid}", size])

with open(os.path.join(OUT, "MANIFEST.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["hdx_dataset", "file", "license", "source_url", "bytes"])
    w.writerow(["# downloaded", datetime.date.today().isoformat(), "", "", ""]); w.writerows(rows)
# Older boundaries (old 9 Mali / 13 Burkina Faso regions) from geoBoundaries
os.makedirs(os.path.join(OUT, "boundaries_old"), exist_ok=True)
for iso3 in ["MLI", "BFA"]:
    for lvl in ["ADM1", "ADM2"]:
        api = f"https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{lvl}/"
        with urllib.request.urlopen(api, timeout=60) as r:
            meta = json.load(r)
        for key in ["gjDownloadURL", "simplifiedGeometryGeoJSON"]:
            url = meta[key]; fn = url.rsplit("/", 1)[-1]
            dest = os.path.join(OUT, "boundaries_old", fn)
            urllib.request.urlretrieve(url, dest)
            print(f"boundaries_old/{fn}  {os.path.getsize(dest)/1e6:.1f} MB")
            rows.append([f"geoBoundaries {iso3} {lvl}", f"boundaries_old/{fn}", meta.get("boundaryLicense"), api, os.path.getsize(dest)])
with open(os.path.join(OUT, "MANIFEST.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["hdx_dataset", "file", "license", "source_url", "bytes"])
    w.writerow(["# downloaded", datetime.date.today().isoformat(), "", "", ""]); w.writerows(rows)
print("done")
