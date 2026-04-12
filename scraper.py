import pathfix  # noqa — must be first

import asyncio
import re
from datetime import datetime, date

from browser import fetch_with_browser
from deduper import content_hash, should_update
from db import upsert_scholarship, get_existing, delete_expired
from scraper_utils import parse_deadline_to_date
from bs4 import BeautifulSoup
TODAY = date.today()

SOURCES = [
    # International / Major
    {"name": "Chevening UK",                       "country": "UK",             "url": "https://www.chevening.org/scholarships/"},
    {"name": "Fulbright USA",                      "country": "USA",            "url": "https://foreign.fulbrightonline.org/"},
    {"name": "Commonwealth UK",                    "country": "UK",             "url": "https://cscuk.fcdo.gov.uk/apply/"},
    {"name": "Australia Awards",                   "country": "Australia",      "url": "https://www.australiaawards.gov.au/"},
    {"name": "DAAD Germany",                       "country": "Germany",        "url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/"},
    {"name": "Mastercard Foundation",              "country": "International",  "url": "https://mastercardfdn.org/all-programs/scholars-program/"},
    {"name": "Chinese Scholarship CSC",            "country": "China",          "url": "https://www.campuschina.org/"},
    {"name": "Korean KGSP",                        "country": "South Korea",    "url": "https://www.studyinkorea.go.kr/en/sub/gks/allnew_apply.do"},
    {"name": "MEXT Japan",                         "country": "Japan",          "url": "https://www.mext.go.jp/en/policy/education/highered/title02/detail02/sdetail02/1373897.htm"},
    {"name": "Turkiye Burslari",                   "country": "Turkey",         "url": "https://turkiyeburslari.gov.tr/en"},
    {"name": "Campus France",                      "country": "France",         "url": "https://www.campusfrance.org/en/scholarships-and-financial-aids"},
    {"name": "Taiwan ICDF",                        "country": "Taiwan",         "url": "https://www.icdf.org.tw/wSite/lp?ctNode=31499&mp=2"},
    {"name": "Aga Khan Foundation",                "country": "International",  "url": "https://www.akdn.org/our-agencies/aga-khan-foundation/international-scholarship-programme"},
    {"name": "Gates Cambridge",                    "country": "UK",             "url": "https://www.gatescambridge.org/programme/the-scholarship/"},
    {"name": "REB Rwanda",                         "country": "Rwanda",         "url": "https://www.reb.rw/index.php/scholarships"},
    # Italy
    {"name": "Italian Government MAECI",           "country": "Italy",          "url": "https://www.studiare-in-italia.it/studentistranieri/index.html"},
    {"name": "University of Bologna",              "country": "Italy",          "url": "https://www.unibo.it/en/study/tuition-fees-and-student-benefits/grants-and-scholarships"},
    {"name": "Politecnico di Torino",              "country": "Italy",          "url": "https://www.polito.it/en/education/study-at-politecnico/scholarships-and-financial-support"},
    {"name": "Politecnico di Milano",              "country": "Italy",          "url": "https://www.polimi.it/en/programmes/scholarships-and-fees/"},
    {"name": "University of Padua",                "country": "Italy",          "url": "https://www.unipd.it/en/tuition-fees-scholarships"},
    {"name": "University of Trento",               "country": "Italy",          "url": "https://www.unitn.it/en/ateneo/1791/scholarships"},
    # Europe
    {"name": "Romanian Government MFA",            "country": "Romania",        "url": "https://www.mae.ro/en/node/2123"},
    {"name": "Study in Romania",                   "country": "Romania",        "url": "https://www.studyinromania.gov.ro/"},
    {"name": "Heinrich Boll Foundation",           "country": "Germany",        "url": "https://www.boell.de/en/scholarships"},
    {"name": "Konrad Adenauer Foundation",         "country": "Germany",        "url": "https://www.kas.de/en/web/begabtenfoerderung-und-kultur/scholarships"},
    {"name": "Eiffel Excellence Scholarship",      "country": "France",         "url": "https://www.campusfrance.org/en/the-eiffel-excellence-scholarship-programme"},
    {"name": "Orange Tulip Scholarship",           "country": "Netherlands",    "url": "https://www.orangetulipscholarship.nl/"},
    {"name": "Holland Scholarship",                "country": "Netherlands",    "url": "https://www.studyinholland.nl/finances/holland-scholarship"},
    {"name": "VLIR-UOS Belgium",                   "country": "Belgium",        "url": "https://www.vliruos.be/en/scholarships/6"},
    {"name": "Swedish Institute SISGP",            "country": "Sweden",         "url": "https://si.se/en/apply/scholarships/swedish-institute-scholarships-for-global-professionals/"},
    {"name": "Norwegian Quota Scheme",             "country": "Norway",         "url": "https://www.hk-dir.no/en/grants-and-loans/quota-scheme"},
    {"name": "Stipendium Hungaricum",              "country": "Hungary",        "url": "https://stipendiumhungaricum.hu/apply/"},
    {"name": "Erasmus Mundus",                     "country": "Europe",         "url": "https://www.eacea.ec.europa.eu/scholarships/emjmd-catalogue_en"},
    {"name": "Swiss Government Excellence",        "country": "Switzerland",    "url": "https://www.sbfi.admin.ch/sbfi/en/home/education/scholarships-and-grants/swiss-government-excellence-scholarships.html"},
    {"name": "Spain AECID Scholarship",            "country": "Spain",          "url": "https://www.aecid.es/en/becas-y-lectorados"},
    {"name": "Portugal Government Scholarship",    "country": "Portugal",       "url": "https://www.dges.gov.pt/en/pagina/scholarships"},
    {"name": "Czech Government Scholarship",       "country": "Czech Republic", "url": "https://www.dzs.cz/en/programme/government-scholarships-developing-countries/"},
    # Africa — East
    {"name": "University of Nairobi",              "country": "Kenya",          "url": "https://www.uonbi.ac.ke/content/scholarships"},
    {"name": "Makerere University Uganda",         "country": "Uganda",         "url": "https://www.mak.ac.ug/scholarships"},
    {"name": "University of Dar es Salaam",        "country": "Tanzania",       "url": "https://www.udsm.ac.tz/index.php/scholarships"},
    {"name": "Aga Khan University EA",             "country": "Kenya",          "url": "https://www.aku.edu/admissions/Pages/financial-assistance.aspx"},
    {"name": "USIU Africa Kenya",                  "country": "Kenya",          "url": "https://www.usiu.ac.ke/admissions/scholarships/"},
    {"name": "Strathmore University Kenya",        "country": "Kenya",          "url": "https://strathmore.edu/admissions/scholarships/"},
    {"name": "Addis Ababa University",             "country": "Ethiopia",       "url": "https://www.aau.edu.et/academics/scholarships/"},
    # Africa — South
    {"name": "University of Cape Town",            "country": "South Africa",   "url": "https://www.uct.ac.za/main/students/postgraduate/scholarships"},
    {"name": "University of Witwatersrand",        "country": "South Africa",   "url": "https://www.wits.ac.za/study-at-wits/fees-and-funding/scholarships/"},
    {"name": "Stellenbosch University",            "country": "South Africa",   "url": "https://www.sun.ac.za/english/finaid/Pages/Bursaries.aspx"},
    {"name": "University of Pretoria",             "country": "South Africa",   "url": "https://www.up.ac.za/financial-aid"},
    {"name": "University of Botswana",             "country": "Botswana",       "url": "https://www.ub.bw/admissions/scholarships"},
    # Africa — West / North
    {"name": "University of Ghana",                "country": "Ghana",          "url": "https://www.ug.edu.gh/scholarships"},
    {"name": "Ashesi University Ghana",            "country": "Ghana",          "url": "https://www.ashesi.edu.gh/admissions/scholarships/"},
    {"name": "Cairo University Egypt",             "country": "Egypt",          "url": "https://cu.edu.eg/en/page/3044/Scholarships"},
    {"name": "Mohamed V University Morocco",       "country": "Morocco",        "url": "https://www.um5.ac.ma/um5/bourses"},
    # Africa — Continental
    {"name": "African Development Bank",           "country": "International",  "url": "https://www.afdb.org/en/topics-and-sectors/topics/gender-women-and-civil-society/afdb-jpa"},
    {"name": "African Union Commission",           "country": "International",  "url": "https://au.int/en/education"},
    {"name": "Allan Gray Orbis Foundation",        "country": "South Africa",   "url": "https://www.allangrayorbis.org/fellowship/"},
    {"name": "Equity Wings to Fly",                "country": "Kenya",          "url": "https://equitygroupfoundation.com/wings-to-fly/"},
    {"name": "Google Africa Scholarship",          "country": "International",  "url": "https://buildyourfuture.withgoogle.com/scholarships"},
    {"name": "Intra-Africa Academic Mobility",     "country": "Africa",         "url": "https://www.intra-africa.org/"},
    # Rwanda
    {"name": "ALU Rwanda",                         "country": "Rwanda",         "url": "https://www.alueducation.com/admissions/scholarships/"},
    {"name": "CMU Africa Fellowship",              "country": "Rwanda",         "url": "https://www.africa.engineering.cmu.edu/academics/financial-aid/index.html"},
    {"name": "University of Global Health Equity", "country": "Rwanda",         "url": "https://ughe.org/admissions/financial-aid/"},
    {"name": "AIMS Rwanda",                        "country": "Rwanda",         "url": "https://aims.ac.rw/admissions/scholarships/"},
    {"name": "Kepler University Rwanda",           "country": "Rwanda",         "url": "https://kepler.org/admissions/financial-aid/"},
    {"name": "University of Kigali UoK",           "country": "Rwanda",         "url": "https://uok.ac.rw/admissions/scholarships/"},
    {"name": "Kigali Independent University ULK",  "country": "Rwanda",         "url": "https://www.ulk.ac.rw/admissions/financial-aid/"},
    {"name": "Adventist University AUCA",          "country": "Rwanda",         "url": "https://www.auca.ac.rw/admissions/financial-aid/"},
    {"name": "Rwanda Education Board REB",         "country": "Rwanda",         "url": "https://www.reb.rw/index.php/scholarships"},
    {"name": "Higher Education Council HEC",       "country": "Rwanda",         "url": "https://www.hec.gov.rw/index.php/scholarships"},
    {"name": "GIZ Rwanda",                         "country": "Rwanda",         "url": "https://www.giz.de/en/worldwide/33041.html"},
    {"name": "Tony Elumelu Foundation",            "country": "International",  "url": "https://www.tonyelumelufoundation.org/teep"},
    {"name": "Jack Ma Africa Netpreneur",          "country": "International",  "url": "https://www.africaafricaprize.org/"},
]


def extract_deadline(text: str):
    patterns = [
        r"deadline[:\s]+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        r"deadline[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"apply\s+by[:\s]+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        r"apply\s+by[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"closing\s+date[:\s]+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        r"closing\s+date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"applications?\s+close[:\s]+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        r"applications?\s+close[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"open\s+until[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"due\s+date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"(\d{1,2}\s+[A-Za-z]+\s+202[6-9])",
        r"([A-Za-z]+\s+\d{1,2},?\s+202[6-9])",
        r"(202[6-9]-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_description(soup):
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"][:500]
    og = soup.find("meta", attrs={"property": "og:description"})
    if og and og.get("content"):
        return og["content"][:500]
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 60:
            return text[:500]
    return None


def is_deadline_valid(raw_deadline):
    if not raw_deadline:
        return True
    parsed = parse_deadline_to_date(raw_deadline)
    if parsed is None:
        return True
    return parsed >= TODAY


async def scrape_source(source: dict):
    url = source["url"]
    html = await fetch_with_browser(url)
    if not html or len(html) < 200:
        return None

    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(separator=" ", strip=True)
    if len(full_text) < 100:
        return None

    deadline_raw = extract_deadline(full_text)
    description = extract_description(soup)

    if not is_deadline_valid(deadline_raw):
        parsed = parse_deadline_to_date(deadline_raw)
        print(f"    ✗ EXPIRED — deadline was {parsed} (today is {TODAY})")
        return None

    parsed_date = parse_deadline_to_date(deadline_raw)
    data = {
        "name":              source["name"],
        "url":               url,
        "country":           source.get("country", ""),
        "deadline":          deadline_raw,
        "deadline_date":     parsed_date.isoformat() if parsed_date else None,
        "description":       description,
        "has_deadline_info": 1 if deadline_raw else 0,
        "last_checked":      datetime.now().isoformat(),
    }
    data["content_hash"] = content_hash(data)
    return data


async def run_scan():
    print(f"\n{'='*60}")
    print(f"  SCHOLARSHIP SCAN — {TODAY}")
    print(f"  Keeping only scholarships with deadline >= {TODAY}")
    print(f"{'='*60}\n")

    removed = delete_expired(TODAY.isoformat())
    if removed > 0:
        print(f"  Removed {removed} expired scholarship(s) from database\n")

    published = updated = skipped = failed = 0

    for i, source in enumerate(SOURCES, 1):
        print(f"[{i:02d}/{len(SOURCES)}] {source['name']} ({source['country']})")
        try:
            new_data = await scrape_source(source)
            if new_data is None:
                failed += 1
                continue

            existing = get_existing(source["name"])
            if not existing:
                upsert_scholarship(new_data)
                print(f"    NEW saved — deadline: {new_data.get('deadline') or 'open/rolling'}")
                published += 1
            elif should_update(existing, new_data):
                upsert_scholarship(new_data)
                print(f"    UPDATED — deadline: {new_data.get('deadline') or 'open/rolling'}")
                updated += 1
            else:
                print(f"    Up to date, skipped")
                skipped += 1
        except Exception as e:
            print(f"    Error: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  DONE  |  New: {published}  Updated: {updated}  Skipped: {skipped}  Failed: {failed}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run_scan())
