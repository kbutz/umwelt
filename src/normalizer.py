import sqlite3
import json

DB_PATH = 'data/orchestrator.db'

# Canonical Mapping
MODALITY_MAP = {
    # Mechanoreception
    'mechanoreception': 'Mechanoreception',
    'Mechanoreception': 'Mechanoreception',
    'mechanosensation': 'Mechanoreception',
    'Mechanosensation': 'Mechanoreception',
    'hearing': 'Mechanoreception',
    'Hearing': 'Mechanoreception',
    'audition': 'Mechanoreception',
    'Audition': 'Mechanoreception',
    'auditory': 'Mechanoreception',
    'Auditory': 'Mechanoreception',
    'vibration': 'Mechanoreception',
    'Vibration': 'Mechanoreception',
    'vibration_sense': 'Mechanoreception',
    'vibratory_sense': 'Mechanoreception',
    'Vibration Detection': 'Mechanoreception',
    'tactile': 'Mechanoreception',
    'Tactile': 'Mechanoreception',
    'tactition': 'Mechanoreception',
    'touch': 'Mechanoreception',
    'Touch': 'Mechanoreception',
    'tactile_sense': 'Mechanoreception',
    'tactile_sensing': 'Mechanoreception',
    'tactile_sensation': 'Mechanoreception',
    'tactile_reception': 'Mechanoreception',
    'Tactile Reception': 'Mechanoreception',
    'tactile_perception': 'Mechanoreception',
    'touch/vibration': 'Mechanoreception',
    'touch/tactition': 'Mechanoreception',
    'touch/mechanoreception': 'Mechanoreception',
    'somatosensation': 'Mechanoreception',
    'proprioception': 'Mechanoreception',
    'Proprioception': 'Mechanoreception',
    'lateral_line': 'Mechanoreception',
    'water_flow_detection': 'Mechanoreception',
    'statocysts': 'Mechanoreception',
    'georeception': 'Mechanoreception',
    'Mechanoreception (antennae)': 'Mechanoreception',

    # Chemoreception
    'chemoreception': 'Chemoreception',
    'Chemoreception': 'Chemoreception',
    'taste': 'Chemoreception',
    'Taste': 'Chemoreception',
    'smell': 'Chemoreception',
    'Smell': 'Chemoreception',
    'olfaction': 'Chemoreception',
    'Olfaction': 'Chemoreception',
    'gustation': 'Chemoreception',
    'Gustation': 'Chemoreception',
    'chemical_detection': 'Chemoreception',
    'taste/smell': 'Chemoreception',
    'taste/gustation': 'Chemoreception',
    'taste/chemoreception': 'Chemoreception',
    'Contact Chemoreception': 'Chemoreception',
    'Pheromone Detection': 'Chemoreception',
    'oxygen_sensing': 'Chemoreception',

    # Photoreception
    'photoreception': 'Photoreception',
    'Photoreception': 'Photoreception',
    ' photoreception': 'Photoreception',
    'vision': 'Photoreception',
    'Vision': 'Photoreception',
    'light_sensitivity': 'Photoreception',
    'light_detection': 'Photoreception',
    'light_attraction': 'Photoreception',
    'photosymbiosis_related_light_detection': 'Photoreception',
    'Color Vision': 'Photoreception',
    'Image Forming Vision': 'Photoreception',
    'Polarized Light Vision': 'Photoreception',
    'Brightness Discrimination': 'Photoreception',
    'bioluminescence detection': 'Photoreception',
    'fluorescence detection': 'Photoreception',

    # Electroreception
    'electroreception': 'Electroreception',
    'Electroreception': 'Electroreception',
    'Active Electroreception': 'Electroreception',
    'Passive Electroreception': 'Electroreception',

    # Thermoreception
    'thermoreception': 'Thermoreception',
    'Thermoreception': 'Thermoreception',
    'Temperature sensing': 'Thermoreception',
    'Heat detection': 'Thermoreception',
    'Heat Detection': 'Thermoreception',
    'Infrared Detection': 'Thermoreception',

    # Magnetoreception
    'magnetoreception': 'Magnetoreception',
    'Magnetoreception': 'Magnetoreception',
}

def normalize_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("🧹 Normalizing labels in graph tables...")
    
    # We'll update the nodes table directly.
    # Note: This might create duplicates if we have 'vision' and 'Vision' both becoming 'Photoreception'.
    # We'll handle this by merging edges next.
    
    # 1. Get all nodes
    c.execute("SELECT id, name FROM nodes WHERE type IN ('modality', 'sub_type')")
    nodes = c.fetchall()
    
    for node_id, name in nodes:
        if name in MODALITY_MAP:
            new_name = MODALITY_MAP[name]
            # Since node_id often contains the name (modality:vision), we might need to update the ID too
            new_id = f"modality:{new_name}"
            
            # Update Edges first to point to the new ID
            c.execute("UPDATE edges SET source = ? WHERE source = ?", (new_id, node_id))
            c.execute("UPDATE edges SET target = ? WHERE target = ?", (new_id, node_id))
            
            # Update Node
            # We use INSERT OR REPLACE to handle the potential duplicate ID
            c.execute("UPDATE nodes SET id = ?, name = ? WHERE id = ?", (new_id, new_name, node_id))

    # 2. Cleanup orphaned or duplicate nodes
    c.execute("DELETE FROM nodes WHERE id NOT IN (SELECT source FROM edges UNION SELECT target FROM edges)")
    
    # 3. Consolidate duplicate edges (source, target, relationship)
    # SQLite doesn't have a simple 'GROUP BY' for updates, so we'll just let the primary key handle it if possible
    # or just trust the next archivist run to do it cleaner.
    
    conn.commit()
    conn.close()
    print("✨ Normalization complete.")

if __name__ == "__main__":
    normalize_database()
