#!/usr/bin/env python3
"""Design research: compare surrounding relief, not just a city's altitude.

Uses Open-Meteo's documented Copernicus GLO-90 elevation endpoint. This is a
reproducible investigation, not the application's scene classifier.
"""
import json
import math
from pathlib import Path
import statistics
import urllib.parse
import urllib.request

PLACES = {
    "Indianapolis": (39.76838, -86.15804),
    "Aspen": (39.1911, -106.8175),
}
EARTH_KM = 6371.0088


def destination(latitude, longitude, bearing, distance):
    lat = math.radians(latitude)
    lon = math.radians(longitude)
    angle = distance / EARTH_KM
    direction = math.radians(bearing)
    new_lat = math.asin(math.sin(lat) * math.cos(angle)
                        + math.cos(lat) * math.sin(angle) * math.cos(direction))
    new_lon = lon + math.atan2(math.sin(direction) * math.sin(angle) * math.cos(lat),
                              math.cos(angle) - math.sin(lat) * math.sin(new_lat))
    return math.degrees(new_lat), math.degrees(new_lon)


def main():
    samples = []
    for name, (lat, lon) in PLACES.items():
        samples.append({"place": name, "radius_km": 0, "bearing": 0,
                        "latitude": lat, "longitude": lon})
        for radius in (5, 15, 40):
            for bearing in range(0, 360, 30):
                y, x = destination(lat, lon, bearing, radius)
                samples.append({"place": name, "radius_km": radius, "bearing": bearing,
                                "latitude": y, "longitude": x})
    query = urllib.parse.urlencode({
        "latitude": ",".join(f"{s['latitude']:.6f}" for s in samples),
        "longitude": ",".join(f"{s['longitude']:.6f}" for s in samples),
    })
    with urllib.request.urlopen("https://api.open-meteo.com/v1/elevation?" + query,
                                timeout=25) as response:
        data = json.load(response)
    heights = data["elevation"]
    if len(heights) != len(samples) or any(v is None for v in heights):
        raise ValueError("Incomplete elevation sample response")
    for sample, height in zip(samples, heights):
        sample["elevation_m"] = height
    summary = []
    for name in PLACES:
        values = [s["elevation_m"] for s in samples if s["place"] == name]
        deciles = statistics.quantiles(values, n=10, method="inclusive")
        summary.append({"place": name, "samples": len(values),
                        "center_elevation_m": values[0],
                        "sample_min_m": min(values), "sample_max_m": max(values),
                        "sample_p90_minus_p10_m": round(deciles[8] - deciles[0], 1)})
    project = Path(__file__).resolve().parents[3]
    output = project / "output/weather-design/terrain-samples.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "source": "https://open-meteo.com/en/docs/elevation-api",
        "method": "Center + 12 bearings at 5, 15, 40 km; discrete samples, not a terrain map",
        "summary": summary, "samples": samples,
    }, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
