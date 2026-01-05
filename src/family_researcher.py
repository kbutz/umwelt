import os
import json
import wikipediaapi
import requests
from src.models import FamilySensoryProfile
from src.gemini_adapter import GeminiAdapter

WIKI_USER_AGENT = "UmweltProject/1.0 (contact@example.com)"

FAMILY_SYSTEM_PROMPT = """
ROLE: You are an expert Evolutionary Biologist and Sensory Ecologist.
OBJECTIVE: Synthesize shared sensory traits across a biological family. You are identifying the "sensory bauplan" of the lineage.

THE 5 GOLDEN RULES FOR FAMILY RESEARCH:
1. Distinguish Prevalence: Use "common" for traits present in most members, "rare" for specialized adaptations, and "unknown" where data is missing.
2. Inference Transparency: If a trait is known for a few key species but likely applies to the family, mark it as inferred and name the species.
3. Evolutionary Context: Note if a sense has been lost (e.g., vision in subterranean families) or highly specialized.
4. Scale Awareness: Family-level research is "zoomed out." Focus on the capabilities that define the family's niche.
5. Structured Uncertainty: If you are unsure, lower the 'confidence' flag. It is better to be uncertain than to over-generalize.

OUTPUT FORMAT:
You must output strictly valid JSON matching this structure:

{
  "family_name": "FamilyName",
  "order_name": "OrderName",
  "sensory_modalities": {
    "modality_name": {
      "presence": "common | rare | unknown",
      "notes": "Description of the sense in this family.",
      "inferred_from_species": ["Species A", "Species B"],
      "frequency_range_hz": { "min": float, "max": float }
    }
  },
  "confidence": "LOW | MEDIUM | HIGH",
  "sources": ["Source URL 1", "Source URL 2"]
}

No markdown. Just pure JSON.
"""

class FamilyResearcher:
    def __init__(self):
        self.wiki = wikipediaapi.Wikipedia(user_agent=WIKI_USER_AGENT, language='en')
        self.adapter = GeminiAdapter()

    def resolve_family_metadata(self, family_name):
        """Fetch GBIF ID and representative species on the fly."""
        print(f"  🌐 Resolving metadata for {family_name}...")
        url = "https://api.gbif.org/v1/species/match"
        params = {"name": family_name, "rank": "FAMILY", "strict": True}
        gbif_id = None
        reps = []
        try:
            resp = requests.get(url, params=params)
            data = resp.json()
            gbif_id = data.get("usageKey")
            
            if gbif_id:
                # Get reps
                search_url = "https://api.gbif.org/v1/species/search"
                search_params = {"higherTaxonKey": gbif_id, "rank": "SPECIES", "status": "ACCEPTED", "limit": 3}
                s_resp = requests.get(search_url, params=search_params)
                reps = [s.get("canonicalName") for s in s_resp.json().get("results", []) if "canonicalName" in s]
        except Exception as e:
            print(f"  ⚠ Metadata resolution error: {e}")
            
        return gbif_id, reps

    def get_wiki_content(self, name):
        page = self.wiki.page(name)
        if page.exists():
            content = f"WIKIPEDIA: {name}\n"
            content += page.summary[:2000]
            sensory_keywords = ['sense', 'sensory', 'hearing', 'vision', 'smell', 'echolocation',
                               'electroreception', 'magnetoreception', 'detection', 'perception']
            for section in page.sections:
                if any(k in section.title.lower() for k in sensory_keywords):
                    content += f"\n\nSection: {section.title}\n{section.text[:1000]}"
            return content
        return ""

    def research_family(self, family_name, gbif_id=None, order_name=None, representative_species=[]):
        # 0. On-demand resolution if data is missing
        if not gbif_id or not representative_species:
            resolved_id, resolved_reps = self.resolve_family_metadata(family_name)
            gbif_id = gbif_id or resolved_id
            representative_species = representative_species or resolved_reps

        print(f"🧬 Researching Family: {family_name} (ID: {gbif_id})")
        
        # 1. Gather Context
        context_parts = []
        sources = []
        
        family_wiki = self.get_wiki_content(family_name)
        if family_wiki:
            context_parts.append(family_wiki)
            sources.append(f"https://en.wikipedia.org/wiki/{family_name}")
        
        for species in representative_species[:3]:
            species_wiki = self.get_wiki_content(species)
            if species_wiki:
                context_parts.append(f"--- Context from Representative Species: {species} ---\n{species_wiki}")
                sources.append(f"https://en.wikipedia.org/wiki/{species.replace(' ', '_')}")
        
        if not context_parts:
            print(f"  ⚠ No context found for family {family_name}")
            return None

        context = "\n\n".join(context_parts)
        
        # 2. LLM Synthesis
        raw_json = self.adapter.research_animal(family_name, context, FAMILY_SYSTEM_PROMPT)
        
        if not raw_json:
            return None

        try:
            data_dict = json.loads(raw_json)
            if order_name and not data_dict.get("order_name"):
                data_dict["order_name"] = order_name
            if gbif_id and not data_dict.get("gbif_id"):
                data_dict["gbif_id"] = gbif_id
            
            validated_data = FamilySensoryProfile(**data_dict)
            return validated_data
        except Exception as e:
            print(f"❌ Failed to parse or validate family data: {e}")
            return None
