import os
import json
import sqlite3
from src.models import FamilySensoryProfile

DB_PATH = 'data/orchestrator.db'
FAMILY_VAULT_DIR = 'data/family_vault'

class FamilyAggregator:
    def __init__(self):
        os.makedirs(FAMILY_VAULT_DIR, exist_ok=True)

    def save_profile(self, profile: FamilySensoryProfile):
        if profile.gbif_id:
            filename = f"{profile.gbif_id}_{profile.family_name}.json"
        else:
            filename = f"{profile.family_name}.json"
            
        filepath = os.path.join(FAMILY_VAULT_DIR, filename)
        
        # Cross-link with species data if available
        profile = self.augment_with_species_links(profile)
        
        if os.path.exists(filepath):
            print(f"  📂 Existing family profile found for {profile.family_name}. Merging...")
            with open(filepath, 'r') as f:
                existing_dict = json.load(f)
            
            new_dict = profile.model_dump()
            
            # 1. Update basic fields if they are missing in existing
            for key in ['gbif_id', 'order_name']:
                if not existing_dict.get(key) and new_dict.get(key):
                    existing_dict[key] = new_dict[key]
            
            # 2. Merge Sensory Modalities
            existing_modalities = existing_dict.get('sensory_modalities', {})
            for mod_name, new_mod_data in new_dict.get('sensory_modalities', {}).items():
                if mod_name not in existing_modalities:
                    existing_modalities[mod_name] = new_mod_data
                else:
                    # Merge existing modality data
                    existing_mod = existing_modalities[mod_name]
                    
                    # Merge inferred_from_species
                    existing_reps = set(existing_mod.get('inferred_from_species', []))
                    new_reps = set(new_mod_data.get('inferred_from_species', []))
                    existing_mod['inferred_from_species'] = list(existing_reps.union(new_reps))
                    
                    # Append notes if they are different
                    new_note = new_mod_data.get('notes', '')
                    if new_note and new_note not in existing_mod.get('notes', ''):
                        existing_mod['notes'] = (existing_mod.get('notes', '') + " | " + new_note).strip(" | ")
                    
                    # Prefer higher presence confidence or just keep existing if it's 'common'
                    if new_mod_data.get('presence') == 'common':
                        existing_mod['presence'] = 'common'
                    
                    # Update frequency range if new one is more expansive (simplified)
                    # (In a real system we'd do more complex range merging)
            
            # 3. Merge Sources
            existing_sources = set(existing_dict.get('sources', []))
            new_sources = set(new_dict.get('sources', []))
            existing_dict['sources'] = list(existing_sources.union(new_sources))
            
            # 4. Update metadata
            existing_dict['generated_at'] = new_dict['generated_at']
            
            final_data = FamilySensoryProfile(**existing_dict)
        else:
            final_data = profile

        with open(filepath, 'w') as f:
            f.write(final_data.model_dump_json(indent=2))
        print(f"📁 Family profile saved to {filepath}")

    def augment_with_species_links(self, profile: FamilySensoryProfile):
        """Find species in our vault that belong to this family and add them as supporting data."""
        # This is a placeholder for future cross-linking logic
        # For now, we'll check the DB for processed species in this family
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            # Look for species in this family that have been COMPLETED
            # We don't have family in the research_queue table yet, but we can search for it in GBIF_Expansion_...
            # Actually, let's just use the taxonomy_source which often contains the family name
            family_pattern = f"%{profile.family_name}%"
            c.execute("""
                SELECT animal_name 
                FROM research_queue 
                WHERE status = 'COMPLETED' 
                AND taxonomy_source LIKE ?
            """, (family_pattern,))
            species = [r[0] for r in c.fetchall()]
            
            # If we find species, we could add them to the profile metadata or specific modalities
            # For now, let's just log it.
            if species:
                print(f"  🔗 Linked {len(species)} species records to {profile.family_name}")
        except Exception as e:
            print(f"  ⚠ Cross-linking failed: {e}")
        finally:
            conn.close()
            
        return profile

if __name__ == "__main__":
    pass
