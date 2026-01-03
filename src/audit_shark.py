import sqlite3
import json

DB_NAME = 'sensory_graph.db'

def audit_shark():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT raw_data FROM animals WHERE common_name = 'Great White Shark'")
    row = cursor.fetchone()

    if row:
        data = json.loads(row['raw_data'])
        print(json.dumps(data, indent=2))

        # specific verification logic
        modalities = data.get('sensory_modalities', [])
        found_electric = False
        found_ampullae = False

        for m in modalities:
            if m.get('stimulus_type') == 'Electric Field':
                found_electric = True
                mech = m.get('mechanism', {}).get('description', '')
                if 'Ampullae of Lorenzini' in mech:
                    found_ampullae = True

        if found_electric and found_ampullae:
            print("\nAUDIT PASSED: Electric Field and Ampullae of Lorenzini found.")
        else:
            print("\nAUDIT FAILED: Missing Electric Field or Ampullae of Lorenzini.")

    else:
        print("Great White Shark not found.")

    conn.close()

if __name__ == "__main__":
    audit_shark()
