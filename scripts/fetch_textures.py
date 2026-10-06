# Download the CC0 textures used by the v3 scenes (Poly Haven API, 1k JPG maps) into assets/textures/<id>/.
# Every asset downloaded here is listed with source URL and license in CREDITS.md (written by this script too).
#   python scripts/fetch_textures.py
import json, os, sys, urllib.request

ASSETS = {
    # id: (used for, maps)
    "aerial_sand": ("scene 5/12 dune sand grain", ["Diffuse", "nor_gl", "Displacement"]),
    "coast_sand_01": ("scene 6 lagoon sand bed, scene 12 flats", ["Diffuse", "nor_gl"]),
    "aerial_rocks_02": ("scene 7 canyon rock", ["Diffuse", "nor_gl", "Displacement"]),
    "rocky_terrain_03": ("scene 7 scree / talus", ["Diffuse", "nor_gl"]),
    "snow_field_aerial": ("scene 1/8 snow", ["Diffuse", "nor_gl"]),
    "snow_02": ("scene 4 frost, scene 8 powder", ["Diffuse", "nor_gl"]),
    "pine_bark": ("conifer trunks (scenes 1, 8), tree trunks (scene 9)", ["Diffuse", "nor_gl"]),
    "aerial_grass_rock": ("scene 9 lawn / verge", ["Diffuse", "nor_gl"]),
    "forest_ground_04": ("scene 10 soil rows, scene 9 path edges", ["Diffuse", "nor_gl"]),
    "gravel_road": ("scene 9 path gravel, scene 2 ballast", ["Diffuse", "nor_gl"]),
    "brown_mud_02": ("scene 10 dirt road ruts", ["Diffuse", "nor_gl"]),
}
ROOT = os.path.join("assets", "textures")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "about-you-render/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    os.makedirs(ROOT, exist_ok=True)
    rows = []
    for aid, (use, maps) in ASSETS.items():
        try:
            files = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
            info = json.loads(get(f"https://api.polyhaven.com/info/{aid}"))
        except Exception as e:
            print("skip", aid, e)
            continue
        d = os.path.join(ROOT, aid)
        os.makedirs(d, exist_ok=True)
        got = []
        for m in maps:
            if m not in files:
                print("  no map", aid, m)
                continue
            res = files[m].get("1k") or files[m].get("2k")
            entry = res.get("jpg") or res.get("png")
            url = entry["url"]
            ext = os.path.splitext(url)[1]
            out = os.path.join(d, f"{m.lower()}{ext}")
            if not os.path.exists(out):
                data = get(url)
                open(out, "wb").write(data)
            got.append((m, url, os.path.getsize(out)))
            print(aid, m, os.path.getsize(out))
        authors = ", ".join(info.get("authors", {}).keys())
        rows.append((aid, info.get("name", aid), authors, use, got))
    json.dump([dict(id=a, name=n, authors=au, use=u, files=[dict(map=m, url=url, bytes=b) for m, url, b in g]) for a, n, au, u, g in rows],
              open(os.path.join(ROOT, "manifest.json"), "w"), indent=1)
    print("manifest written", len(rows))


if __name__ == "__main__":
    main()
