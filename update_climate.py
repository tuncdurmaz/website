"""
update_climate.py
-----------------
Fetches authoritative climate data and writes climate_data.json that the
dashboard reads on each page load.

Sources:
  • CO2  — NOAA GML, Mauna Loa monthly + annual means
  • CH4  — NOAA GML, global monthly + annual means
  • N2O  — NOAA GML, global monthly + annual means
  • Temp — NASA GISS GISTEMP v4 land-ocean (1951–1980 baseline)
  • Ice  — NSIDC Sea Ice Index v3, Arctic September extent

Design notes:
  • Standard library only — no requests/pandas (matches update_prices.py).
  • Each fetcher is wrapped in try/except. On failure, the previous value
    for that section of climate_data.json is preserved.
  • Outputs are pre-shaped for the front-end (no transformation needed
    in dashboard.html). Each block has 'annual' (sparse year/value pairs)
    and 'latest' (most recent observation with month if available).
"""

import json
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path

JSON_PATH = Path(__file__).parent / 'climate_data.json'
UA = {'User-Agent': 'Mozilla/5.0 (climate-dashboard updater; +https://www.tuncdurmaz.com)'}


def http_get(url, timeout=30):
    """Fetch a URL and return decoded text. Raises on error."""
    req = urllib.request.Request(url, headers=UA)
    ctx = ssl.create_default_context()
    # Some hosts on GitHub runners struggle with strict cert validation; mirror
    # the permissive behaviour used in update_prices.py for consistency.
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='replace')


def parse_noaa_annual(text, value_col=1):
    """NOAA annual-mean CSVs: comment lines starting with '#', then
       whitespace- or comma-separated rows of: year, mean, [unc]."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Files use either commas or whitespace
        parts = [p for p in line.replace(',', ' ').split() if p]
        if len(parts) < value_col + 1:
            continue
        try:
            year = int(parts[0])
            value = float(parts[value_col])
        except ValueError:
            continue
        rows.append((year, value))
    return rows


def parse_noaa_monthly(text):
    """NOAA monthly CSVs. Returns [(year, month, value), ...].
       Columns vary; we read year, month, and the 'average' column.
       Mauna Loa CO2: year,month,decimal,average,deseasonalized,...
       CH4/N2O global monthly: year,month,decimal,average,sdev,ncount,...
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p for p in line.replace(',', ' ').split() if p]
        if len(parts) < 4:
            continue
        try:
            year = int(parts[0])
            month = int(parts[1])
            avg = float(parts[3])
        except ValueError:
            continue
        if avg < 0:  # NOAA uses -99.99 etc. for missing
            continue
        rows.append((year, month, avg))
    return rows


def sparse_years(rows, every=None):
    """Decimate annual data for chart readability while keeping the latest year.
       Default thinning depends on the span."""
    if not rows:
        return []
    rows = sorted(rows)
    if every is None:
        span = rows[-1][0] - rows[0][0]
        every = 2 if span <= 50 else 5 if span <= 100 else 10
    last_year = rows[-1][0]
    return [(y, v) for (y, v) in rows if (y % every == 0) or y == last_year]


def extend_with_ytd(annual, monthly):
    """Append year-to-date averages for any year present in monthly data but
       beyond the last annual-mean entry. NOAA's annual-mean CSVs only list
       completed years, so the chart line otherwise stops well short of 'now'.
       Returns a new annual list (without modifying inputs)."""
    if not monthly:
        return list(annual)
    by_year = {}
    for (y, m, v) in monthly:
        by_year.setdefault(y, []).append(v)
    last_annual_year = annual[-1][0] if annual else 0
    out = list(annual)
    for y in sorted(by_year):
        if y > last_annual_year:
            ytd = sum(by_year[y]) / len(by_year[y])
            out.append((y, ytd))
    return out


# ────────────────────────────────────────────────────────────────
# Fetchers — each returns the shape expected in climate_data.json
# ────────────────────────────────────────────────────────────────


def fetch_co2():
    annual_txt = http_get('https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.csv')
    monthly_txt = http_get('https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv')

    annual_full = parse_noaa_annual(annual_txt)
    monthly = parse_noaa_monthly(monthly_txt)
    if not annual_full or not monthly:
        raise RuntimeError('co2: empty NOAA data')
    extended = extend_with_ytd(annual_full, monthly)
    annual = sparse_years(extended, every=2)
    latest_y, latest_m, latest_v = monthly[-1]
    return {
        'source': 'NOAA GML — Mauna Loa',
        'unit': 'ppm',
        'annual': [{'year': y, 'value': round(v, 2)} for y, v in annual],
        'latest': {'year': latest_y, 'month': latest_m, 'value': round(latest_v, 2)},
    }


def fetch_ch4():
    annual_txt = http_get('https://gml.noaa.gov/webdata/ccgg/trends/ch4/ch4_annmean_gl.csv')
    monthly_txt = http_get('https://gml.noaa.gov/webdata/ccgg/trends/ch4/ch4_mm_gl.csv')

    annual_full = parse_noaa_annual(annual_txt)
    monthly = parse_noaa_monthly(monthly_txt)
    if not annual_full or not monthly:
        raise RuntimeError('ch4: empty NOAA data')
    extended = extend_with_ytd(annual_full, monthly)
    annual = sparse_years(extended, every=2)
    latest_y, latest_m, latest_v = monthly[-1]
    return {
        'source': 'NOAA GML — global marine surface',
        'unit': 'ppb',
        'annual': [{'year': y, 'value': round(v, 1)} for y, v in annual],
        'latest': {'year': latest_y, 'month': latest_m, 'value': round(latest_v, 1)},
    }


def fetch_n2o():
    annual_txt = http_get('https://gml.noaa.gov/webdata/ccgg/trends/n2o/n2o_annmean_gl.csv')
    monthly_txt = http_get('https://gml.noaa.gov/webdata/ccgg/trends/n2o/n2o_mm_gl.csv')

    annual_full = parse_noaa_annual(annual_txt)
    monthly = parse_noaa_monthly(monthly_txt)
    if not annual_full or not monthly:
        raise RuntimeError('n2o: empty NOAA data')
    extended = extend_with_ytd(annual_full, monthly)
    annual = sparse_years(extended, every=2)
    latest_y, latest_m, latest_v = monthly[-1]
    return {
        'source': 'NOAA GML — global marine surface',
        'unit': 'ppb',
        'annual': [{'year': y, 'value': round(v, 2)} for y, v in annual],
        'latest': {'year': latest_y, 'month': latest_m, 'value': round(latest_v, 2)},
    }


def fetch_temp():
    """NASA GISTEMP v4 land-ocean.
       The CSV file uses one of two formats depending on year:
         • integer hundredths of °C (e.g. '127' for +1.27°C) — historical
         • decimal °C (e.g. '1.27')                          — newer rows
       Auto-detect per-row by looking for a decimal point.
    """
    text = http_get('https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv')
    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(',')]
        if not parts or len(parts) < 14:
            continue
        try:
            year = int(parts[0])
            j_d = parts[13]  # Jan–Dec annual mean
            if j_d in ('', '*', '***'):
                continue
            val = float(j_d) if '.' in j_d else float(j_d) / 100.0
        except ValueError:
            continue
        if year < 1880 or abs(val) > 10:  # sanity: anomaly shouldn't exceed ±10°C
            continue
        rows.append((year, val))
    if not rows:
        raise RuntimeError('temp: empty GISS data')
    rows.sort()
    annual = sparse_years(rows, every=5)
    return {
        'source': 'NASA GISS — GISTEMP v4 (land-ocean)',
        'unit': '°C',
        'baseline': '1951–1980',
        'annual': [{'year': y, 'value': round(v, 2)} for y, v in annual],
        'latest': {'year': rows[-1][0], 'value': round(rows[-1][1], 2)},
    }


def _parse_nsidc_monthly_sep(text):
    """Parse the NSIDC monthly September CSV (one row per year)."""
    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(',')]
        if not parts or parts[0].lower().startswith('year'):
            continue
        try:
            year = int(parts[0])
            extent = float(parts[4])  # year, mo, data-type, region, extent, area
        except (ValueError, IndexError):
            continue
        if extent <= 0:  # NSIDC uses -9999 etc. for missing
            continue
        rows.append((year, extent))
    return rows


def _parse_nsidc_daily_to_sept(text):
    """Parse the NSIDC daily extent CSV and compute Arctic September monthly means.
       Daily file header: 'Year, Month, Day, Extent, Missing, Source Data'.
       Used as a fallback when the monthly file lags."""
    by_year = {}
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 4:
            continue
        if not parts[0].isdigit():
            continue
        try:
            y = int(parts[0]); m = int(parts[1]); ext = float(parts[3])
        except (ValueError, IndexError):
            continue
        if m != 9 or ext <= 0:
            continue
        by_year.setdefault(y, []).append(ext)
    return sorted((y, sum(vs) / len(vs)) for y, vs in by_year.items())


def _parse_arctic_api_yearly(text):
    """Parse global-warming.org Arctic API payload into yearly means."""
    payload = json.loads(text)
    rows = payload.get('arcpiclice') or []
    by_year = {}

    for row in rows:
        try:
            year = int(row.get('year'))
            extent = float(row.get('extent'))
        except (TypeError, ValueError):
            continue
        if extent <= 0:
            continue
        by_year.setdefault(year, []).append(extent)

    return sorted((y, sum(vs) / len(vs)) for y, vs in by_year.items())


def _try_fetch_rows(label, urls, parser):
    """Try multiple URLs for the same dataset and return (rows, detail)."""
    failures = []
    for url in urls:
        try:
            rows = parser(http_get(url))
            if rows:
                latest = rows[-1][0]
                return rows, f'{label}: {url} (latest {latest})'
            failures.append(f'{url} -> empty data')
        except Exception as e:
            failures.append(f'{url} -> {e}')
    raise RuntimeError(f'{label} failed: ' + '; '.join(failures))


def fetch_ice():
    """Arctic September extent with resilient fallbacks.
       Try known NSIDC URL variants first, then fall back to the same
       Arctic API the front-end already uses."""
    monthly_urls = [
        'https://noaadata.apps.nsidc.org/NOAA/G02135/north/monthly/data/N_09_extent_v3.0.csv',
        'https://noaadata.apps.nsidc.org/NOAA/G02135/north/monthly/data/N_09_extent_v3.csv',
        'https://noaadata.apps.nsidc.org/NOAA/G02135/north/monthly/data/N_09_extent.csv',
    ]
    daily_urls = [
        'https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v3.0.csv',
        'https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v3.csv',
        'https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily.csv',
    ]
    arctic_api_url = 'https://global-warming.org/api/arctic-api'

    rows = []
    used = []
    try:
        rows, detail = _try_fetch_rows('monthly', monthly_urls, _parse_nsidc_monthly_sep)
        used.append(detail)
    except Exception as e:
        used.append(str(e))

    current_year = datetime.utcnow().year
    needs_daily = (not rows) or (rows[-1][0] < current_year - 1)
    if needs_daily:
        try:
            daily_rows, detail = _try_fetch_rows('daily', daily_urls, _parse_nsidc_daily_to_sept)
            existing = {y for y, _ in rows}
            added = [(y, v) for y, v in daily_rows if y not in existing]
            rows = sorted(rows + added)
            used.append(f'{detail}; added {len(added)} years; latest {rows[-1][0] if rows else "?"}')
        except Exception as e:
            used.append(str(e))

    if not rows:
        try:
            rows = _parse_arctic_api_yearly(http_get(arctic_api_url))
            if rows:
                used.append(f'arctic-api: {arctic_api_url} (latest {rows[-1][0]})')
        except Exception as e:
            used.append(f'arctic-api failed: {arctic_api_url} -> {e}')

    if not rows:
        raise RuntimeError(f'ice: no data ({"; ".join(used)})')

    rows.sort()
    annual = sparse_years(rows, every=3)
    source = 'global-warming.org — Arctic API' if any(d.startswith('arctic-api:') for d in used) else 'NSIDC — Sea Ice Index, Arctic September extent'
    return {
        'source': source,
        'detail': '; '.join(used),
        'unit': 'million km²',
        'annual': [{'year': y, 'value': round(v, 2)} for y, v in annual],
        'latest': {'year': rows[-1][0], 'value': round(rows[-1][1], 2)},
    }


# ────────────────────────────────────────────────────────────────
# Orchestration
# ────────────────────────────────────────────────────────────────

FETCHERS = {
    'co2':  fetch_co2,
    'ch4':  fetch_ch4,
    'n2o':  fetch_n2o,
    'temp': fetch_temp,
    'ice':  fetch_ice,
}


def main():
    # Load prior data so a single source failure does not blank a section
    try:
        data = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    updates = []
    errors = []

    for key, fetch in FETCHERS.items():
        try:
            data[key] = fetch()
            latest = data[key]['latest']
            tag = f"{latest['year']}"
            if 'month' in latest:
                tag += f".{latest['month']:02d}"
            updates.append(f"{key}={latest['value']} {data[key]['unit']} ({tag})")
        except Exception as e:
            errors.append(f"{key}: {e}")
            # Leave existing block (if any) untouched

    if updates:
        data['last_updated'] = datetime.utcnow().strftime('%B %d, %Y (%H:%M UTC)')

    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    print("Climate data update complete.")
    for u in updates:
        print("  ✓", u)
    for e in errors:
        print("  ✗", e)

    # Non-zero exit only if EVERY source failed
    return 0 if updates else 1


if __name__ == '__main__':
    raise SystemExit(main())
