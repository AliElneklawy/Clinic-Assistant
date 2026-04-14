import re
import xml.etree.ElementTree as ET
from enum import Enum

import requests
from requests import Request

from src.settings.logger import get_logger

logger = get_logger(__name__)


class SectionCodes(Enum):
    USE_CASES = "34067-9"
    SIDE_EFFECTS = "34084-4"


class DrugSearchService:
    def __init__(self):
        self.search_url = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"

    def find_best_drug_match(self, drug_name: str):
        params = {"drug_name": drug_name, "pagesize": 20}

        resp: Request = requests.get(self.search_url, params=params, timeout=20)
        if resp.status_code != 200:
            return None, None

        data = resp.json().get("data", [])
        drug_name_lower = drug_name.lower()

        for item in data:
            if drug_name_lower in item["title"].lower():
                return item["setid"], item["title"]

        if data:
            return data[0]["setid"], data[0]["title"]

        return None, None

    def extract_paragraphs(self, section: ET.Element, namespaces: dict[str, str]):
        paragraphs = section.findall(".//v3:paragraph", namespaces)
        text = " ".join("".join(p.itertext()).strip() for p in paragraphs)
        return text

    def clean_text(self, text):
        text = re.sub(r"\btable\s*\d+.*?(?=\.)", "", text, flags=re.I)
        text = re.sub(r"\d+\s*\([^)]*\)", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    # def to_bullets(self, text, max_bullets=5):
    #     sentences = re.split(r"(?<=[.!?]) +", text)
    #     bullets = [f"- {s.strip()}" for s in sentences if len(s.strip()) > 20]
    #     return "\n".join(bullets[:max_bullets])

    def get_drug_info(self, drug_name: str):
        drug_name = drug_name.strip("O")
        setid, title = self.find_best_drug_match(drug_name)

        if not setid:
            return "No drug found."

        logger.info(f"Drug Found: {title}")

        xml_url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"
        response = requests.get(xml_url, timeout=20)

        if response.status_code != 200:
            return "Failed to fetch drug label."

        root = ET.fromstring(response.content)
        namespaces = {"v3": "urn:hl7-org:v3"}

        results = {
            "Use Cases": "Section not found.",
            "Side Effects": "Section not found.",
        }

        for section in root.findall(".//v3:section", namespaces):
            code_elem = section.find("v3:code", namespaces)

            if code_elem is None:
                continue

            code = code_elem.get("code")

            if code == SectionCodes.USE_CASES.value:
                text = self.extract_paragraphs(section, namespaces)
                results["Use Cases"] = self.clean_text(text)

            elif code == SectionCodes.SIDE_EFFECTS.value:
                text = self.extract_paragraphs(section, namespaces)
                results["Side Effects"] = self.clean_text(text)

        return results


if __name__ == "__main__":
    drug_service = DrugSearchService()
    drug = "Sitagliptin"
    info = drug_service.get_drug_info(drug)

    if isinstance(info, dict):
        print("\nUse Cases:")
        print((info["Use Cases"]))

        print("\nSide Effects:")
        print((info["Side Effects"]))
    else:
        print(info)
