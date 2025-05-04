#!/usr/bin/env python3
# coding: utf-8
"""
抓取多个 GAF 承包商详情页 —— 含 About Us
"""

import json, re, cloudscraper, requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import time
import random

URLS = [
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/matawan/us-roofing-siding-inc-1141909",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/new-hyde-park/preferred-exterior-corp-1004859",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/wayne/matute-roofing-1113654",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/elmwood-park/donnys-home-improvement-1139561",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/ramsey/the-great-american-roofing-company-1001655",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/westbury/john-goess-roofing-inc-1003844",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/garfield/jersey-roofing-llc-1141159",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/montville/blue-nail-exteriors-1113999",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/nutley/american-roofing-and-siding-1005677",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/iselin/grapevine-pro-1130919",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/valley-stream/brothers-aluminum-home-improvements-corp-1100696",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/bronx/ak-gatsios-inc-1101267",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/dumont/complete-roof-systems-1002688",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/florham-park/american-home-contractors-inc-1005149",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/bronx/rh-renovation-llc-1143942",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/staten-island/bb-contracting-corp-1116738",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/totowa/mnt-roofing-siding-1107024",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/staten-island/golden-key-construction-group-inc-1143894",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/south-plainfield/hammer-exteriors-llc-1124727",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/bergenfield/future-remodeling-1148691",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/pompton-plains/reisch-roofing-and-construction-llc-1118403",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/cedar-grove/all-professional-remodeling-group-llc-1001104",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/brooklyn/nyc-general-pro-roofing-inc-1125170",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/nj/emerson/kelly-exteriors-1104793",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/new-rochelle/mcleod-brothers-inc-1000796",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/elmsford/arm-roofing-1000079",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/franklin-square/all-site-roofing-1124078",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/staten-island/all-seasons-roofing-llc-1135593",
    "https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/brooklyn/as-construction-son-inc-1120367"
]

OFFLINE_FILE = "Preferred Exterior Corp _ GAF Residential Roofers.html"


def fetch_html(url: str, fallback: str) -> str:
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False},
        delay=10,
    )
    try:
        r = scraper.get(url, timeout=30)
        r.raise_for_status()
        if r.status_code == 403 or "Access Denied" in r.text:
            raise RuntimeError("blocked")
        print(f"[i] 在线抓取成功: {url}")
        return r.text
    except Exception:
        print(f"[!] 在线抓取失败，改用离线文件: {url}")
        with open(fallback, encoding="utf-8") as f:
            return f.read()


def extract_data(html: str) -> Dict:
    soup = BeautifulSoup(html, "lxml")

    data = {"name": soup.h1.get_text(strip=True)}

    # -------- About us --------
    about = soup.select_one("section.about-us-block .about-us-block__description")
    if about:
        data["about_us"] = about.get_text(" ", strip=True)

    # -------- 评分 & 评论 --------
    rt_txt = soup.find(string=re.compile(r"\(\d+\)"))
    if rt_txt:
        m = re.search(r"(\d+(?:\.\d+)?)\s*\((\d+)\)", rt_txt.parent.get_text())
        if m:
            data["rating"], data["reviews"] = float(m[1]), int(m[2])

    # -------- 地址、电话 --------
    addr = soup.select_one("address")
    if addr:
        data["address"] = addr.get_text(" ", strip=True)
    tel = soup.select_one('a[href^="tel:"]')
    if tel:
        data["phone"] = re.sub(r"[^\d()\- ]", "", tel.get_text()).strip()

    # -------- 认证 --------
    certs = soup.select("h2:-soup-contains('Certifications') + div h3")
    data["certifications"] = [c.get_text(strip=True) for c in certs]

    # -------- 详情表 --------
    for label, key in {
        "Years in Business": "years_in_business",
        "Number of Employees": "number_of_employees",
        "Contractor ID": "contractor_id",
        "State License Number": "state_license_number",
    }.items():
        node = soup.find("h3", string=label)
        if node:
            data[key] = node.find_next("p").get_text(strip=True)

    return data


def scrape_contractors() -> List[Dict[str, Any]]:
    """Scrape contractor data from GAF website"""
    contractors = []
    
    # List of contractor URLs to scrape
    urls = [
        "https://www.gaf.com/en-us/contractor-locator/contractor/12345",
        "https://www.gaf.com/en-us/contractor-locator/contractor/67890",
        # Add more URLs as needed
    ]
    
    for url in urls:
        try:
            # Add random delay to avoid being blocked
            time.sleep(random.uniform(1, 3))
            
            # Send request
            response = requests.get(url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract contractor information
            contractor = {}
            
            # -------- Ratings & Reviews --------
            rating_elem = soup.find('div', class_='rating')
            if rating_elem:
                contractor['rating'] = rating_elem.text.strip()
            
            # -------- Address & Phone --------
            contact_elem = soup.find('div', class_='contact-info')
            if contact_elem:
                contractor['address'] = contact_elem.find('p', class_='address').text.strip()
                contractor['phone'] = contact_elem.find('p', class_='phone').text.strip()
            
            # -------- Certifications --------
            certs_elem = soup.find('div', class_='certifications')
            if certs_elem:
                contractor['certifications'] = [cert.text.strip() for cert in certs_elem.find_all('li')]
            
            # -------- Details Table --------
            details_table = soup.find('table', class_='contractor-details')
            if details_table:
                for row in details_table.find_all('tr'):
                    key = row.find('th').text.strip().lower().replace(' ', '_')
                    value = row.find('td').text.strip()
                    contractor[key] = value
            
            # Add URL
            contractor['url'] = url
            
            contractors.append(contractor)
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            continue
    
    return contractors


def main():
    results = []
    for url in URLS:
        html = fetch_html(url, OFFLINE_FILE)
        result = extract_data(html)
        results.append(result)
    
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main() 