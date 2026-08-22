#!/usr/bin/env python3
"""
APKMirror Helper using cloudscraper & BeautifulSoup
Replicates the reliable download mechanism used by crimera/twitter-apk
"""
import sys
import os
import re
import argparse
import cloudscraper
from bs4 import BeautifulSoup

def get_scraper():
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    })
    return scraper

def sanitize_version(version: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]+', '-', version).strip('-').lower()

def get_pkg_name(scraper, base_url: str) -> str:
    r = scraper.get(base_url)
    if r.status_code != 200:
        raise Exception(f"Failed to fetch {base_url}: {r.status_code}")
    soup = BeautifulSoup(r.content, "html.parser")
    link = soup.find("a", {"class": "accent_color", "href": re.compile(r"id=")})
    if link and "href" in link.attrs:
        m = re.search(r"id=([^&\"'#]+)", link["href"])
        if m:
            return m.group(1)
    # Default for twitter
    if "twitter" in base_url.lower():
        return "com.twitter.android"
    raise Exception("Package name not found")

def get_versions_list(scraper, base_url: str) -> list[str]:
    r = scraper.get(base_url)
    if r.status_code != 200:
        raise Exception(f"Failed to fetch {base_url}: {r.status_code}")
    soup = BeautifulSoup(r.content, "html.parser")
    versions = []
    for span in soup.find_all("span", {"class": "infoSlide-value"}):
        text = span.get_text(strip=True)
        if text and "beta" not in text.lower() and "alpha" not in text.lower():
            versions.append(text)
    return versions

def find_version_page(scraper, base_url: str, version: str):
    app_slug = base_url.rstrip('/').split('/')[-1]
    v_slug = sanitize_version(version)
    
    candidates = [
        f"{base_url.rstrip('/')}/{app_slug}-{v_slug}-release/",
        f"{base_url.rstrip('/')}/x-{v_slug}-release/",
        f"{base_url.rstrip('/')}/{app_slug}-{v_slug}/",
        f"{base_url.rstrip('/')}/x-{v_slug}/",
    ]
    for url in candidates:
        try:
            r = scraper.get(url)
            if r.status_code == 200 and ("table" in r.text or "variants" in r.text.lower()):
                return url, r
        except Exception:
            pass

    r = scraper.get(base_url)
    if r.status_code == 200:
        soup = BeautifulSoup(r.content, "html.parser")
        for a in soup.find_all("a", href=True):
            if v_slug in a["href"].lower() and "apk-download" not in a["href"]:
                full_url = "https://www.apkmirror.com" + a["href"] if a["href"].startswith("/") else a["href"]
                r2 = scraper.get(full_url)
                if r2.status_code == 200:
                    return full_url, r2

    raise Exception(f"Could not find APKMirror page for version '{version}' at {base_url}")

def download_file(scraper, direct_url: str, referer: str, out_path: str):
    dir_name = os.path.dirname(out_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    headers = {"Referer": referer}
    print(f"Downloading from {direct_url} -> {out_path}", file=sys.stderr)
    with scraper.get(direct_url, stream=True, headers=headers) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
    print(f"Downloaded successfully: {out_path} ({os.path.getsize(out_path)} bytes)", file=sys.stderr)

def download_apkmirror(base_url: str, version: str, output: str, arch: str = "all", dpi: str = ""):
    scraper = get_scraper()
    
    version_url, resp = find_version_page(scraper, base_url, version)
    print(f"Found version page: {version_url}", file=sys.stderr)
    
    soup = BeautifulSoup(resp.content, "html.parser")
    table = soup.find("div", {"class": "table"})
    if not table:
        raise Exception(f"Variants table not found on {version_url}")
    
    rows = table.find_all("div", recursive=False)[1:]
    variants = []
    for row in rows:
        cells = row.find_all("div", {"class": "table-cell"}, recursive=False)
        if not cells:
            continue
        
        badge = row.find("span", {"class": "apkm-badge"})
        is_bundle = bool(badge and badge.text.strip().upper() == "BUNDLE")
        
        link_el = row.find("a", {"class": "accent_color"})
        if not link_el or not link_el.get("href"):
            continue
        
        variant_arch = "universal"
        if len(cells) > 1:
            variant_arch = cells[1].get_text(strip=True).lower()
        
        href = link_el["href"]
        variant_url = "https://www.apkmirror.com" + href if href.startswith("/") else href
        variants.append({
            "is_bundle": is_bundle,
            "url": variant_url,
            "arch": variant_arch
        })
    
    if not variants:
        raise Exception(f"No variants found for {version}")
    
    selected = None
    target_arch = arch.lower() if arch else "all"
    
    for v in variants:
        if v["is_bundle"]:
            if target_arch in ("all", "both") or target_arch in v["arch"] or "universal" in v["arch"]:
                selected = v
                break
    
    if not selected:
        for v in variants:
            if target_arch in ("all", "both") or target_arch in v["arch"] or "universal" in v["arch"]:
                selected = v
                break
                
    if not selected:
        selected = variants[0]
        
    print(f"Selected variant (bundle={selected['is_bundle']}, arch={selected['arch']}): {selected['url']}", file=sys.stderr)
    
    r_variant = scraper.get(selected["url"])
    if r_variant.status_code != 200:
        raise Exception(f"Failed to fetch variant page: {selected['url']}")
    
    soup_var = BeautifulSoup(r_variant.content, "html.parser")
    dl_btn = soup_var.find("a", {"class": "downloadButton"})
    if not dl_btn or not dl_btn.get("href"):
        raise Exception(f"Download button not found on {selected['url']}")
    
    dl_page_href = dl_btn["href"]
    dl_page_url = "https://www.apkmirror.com" + dl_page_href if dl_page_href.startswith("/") else dl_page_href
    
    r_dl = scraper.get(dl_page_url)
    if r_dl.status_code != 200:
        raise Exception(f"Failed to fetch download page: {dl_page_url}")
    
    soup_dl = BeautifulSoup(r_dl.content, "html.parser")
    direct_link = soup_dl.find("a", {"rel": "nofollow"})
    if not direct_link or not direct_link.get("href"):
        raise Exception(f"Direct download link not found on {dl_page_url}")
    
    direct_href = direct_link["href"]
    direct_url = "https://www.apkmirror.com" + direct_href if direct_href.startswith("/") else direct_href
    
    actual_output = output
    if selected["is_bundle"]:
        if not actual_output.endswith(".apkm"):
            actual_output = f"{output}.apkm"
    
    download_file(scraper, direct_url, dl_page_url, actual_output)
    print(actual_output)
    return actual_output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APKMirror Helper")
    parser.add_argument("url", nargs="?", help="APKMirror app URL")
    parser.add_argument("version", nargs="?", help="App version")
    parser.add_argument("output", nargs="?", help="Output file path")
    parser.add_argument("arch", nargs="?", default="all", help="Target architecture")
    parser.add_argument("dpi", nargs="?", default="", help="Target DPI")
    parser.add_argument("--pkg-name", dest="pkg_url", help="Get package name for URL")
    parser.add_argument("--versions", dest="versions_url", help="Get version list for URL")
    
    args = parser.parse_args()
    scraper = get_scraper()
    
    if args.pkg_url:
        print(get_pkg_name(scraper, args.pkg_url))
        sys.exit(0)
    elif args.versions_url:
        for v in get_versions_list(scraper, args.versions_url):
            print(v)
        sys.exit(0)
        
    if not args.url or not args.version or not args.output:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    try:
        download_apkmirror(args.url, args.version, args.output, args.arch, args.dpi)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
