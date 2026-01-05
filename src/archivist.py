import sqlite3
import json
import os
import glob
from src.normalizer import MODALITY_MAP

DB_PATH = 'data/orchestrator.db'
SPECIES_VAULT_DIR = 'data/vault'
FAMILY_VAULT_DIR = 'data/family_vault'

def init_graph_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS nodes")
    c.execute("DROP TABLE IF EXISTS edges")
    c.execute('''
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT CHECK(type IN ('species', 'family', 'order', 'modality', 'sub_type'))
        )
    ''')
    c.execute('''
        CREATE TABLE edges (
            source TEXT,
            target TEXT,
            relationship TEXT,
            attributes JSON,
            PRIMARY KEY (source, target, relationship)
        )
    ''')
    conn.commit()
    conn.close()

class GraphArchivist:
    def __init__(self):
        init_graph_db()
        self.conn = sqlite3.connect(DB_PATH)
        self.c = self.conn.cursor()

    def add_node(self, node_id, name, node_type):
        self.c.execute("INSERT OR IGNORE INTO nodes (id, name, type) VALUES (?, ?, ?)", 
                      (node_id, name, node_type))

    def add_edge(self, source, target, relationship, attributes=None):
        attr_json = json.dumps(attributes) if attributes else None
        self.c.execute("INSERT OR IGNORE INTO edges (source, target, relationship, attributes) VALUES (?, ?, ?, ?)",
                      (source, target, relationship, attr_json))

    def process_species(self):
        files = glob.glob(os.path.join(SPECIES_VAULT_DIR, '*.json'))
        print(f"Processing {len(files)} species files...")
        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                identity = data.get('identity', {})
                name = identity.get('common_name') or identity.get('scientific_name')
                tax = identity.get('taxonomy', {})
                
                order = tax.get('order')
                family = tax.get('family')
                if order: self.add_node(f"order:{order}", order, 'order')
                if family:
                    self.add_node(f"family:{family}", family, 'family')
                    if order: self.add_edge(f"family:{family}", f"order:{order}", 'MEMBER_OF')
                
                self.add_node(f"species:{name}", name, 'species')
                if family: self.add_edge(f"species:{name}", f"family:{family}", 'MEMBER_OF')

                for mod in data.get('sensory_modalities', []):
                    domain = MODALITY_MAP.get(mod.get('modality_domain'), mod.get('modality_domain'))
                    sub_type = MODALITY_MAP.get(mod.get('sub_type'), mod.get('sub_type'))
                    
                    if domain:
                        self.add_node(f"modality:{domain}", domain, 'modality')
                        self.add_edge(f"species:{name}", f"modality:{domain}", 'HAS_SENSE', 
                                     attributes={'source': 'species_data'})
                        if sub_type and sub_type != domain:
                            self.add_node(f"sub_type:{sub_type}", sub_type, 'sub_type')
                            self.add_edge(f"sub_type:{sub_type}", f"modality:{domain}", 'INSTANCE_OF')
                            self.add_edge(f"species:{name}", f"sub_type:{sub_type}", 'HAS_SENSE',
                                         attributes=mod.get('quantitative_data'))
            except Exception as e:
                print(f"Error processing species {filepath}: {e}")

    def process_families(self):
        files = glob.glob(os.path.join(FAMILY_VAULT_DIR, '*.json'))
        print(f"Processing {len(files)} family files...")
        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                family = data.get('family_name')
                order = data.get('order_name')
                if not family: continue
                
                self.add_node(f"family:{family}", family, 'family')
                if order:
                    self.add_node(f"order:{order}", order, 'order')
                    self.add_edge(f"family:{family}", f"order:{order}", 'MEMBER_OF')

                for mod_name, mod_data in data.get('sensory_modalities', {}).items():
                    if mod_data.get('presence') == 'unknown': continue
                    domain = MODALITY_MAP.get(mod_name, mod_name)
                    self.add_node(f"modality:{domain}", domain, 'modality')
                    self.add_edge(f"family:{family}", f"modality:{domain}", 'HAS_SENSE', 
                                 attributes={'prevalence': mod_data.get('presence')})
            except Exception as e:
                print(f"Error processing family {filepath}: {e}")

    def run(self):
        self.process_species()
        self.process_families()
        self.conn.commit()
        self.conn.close()
        print("Archiving complete. Graph ready.")

if __name__ == "__main__":
    archivist = GraphArchivist()
    archivist.run()
