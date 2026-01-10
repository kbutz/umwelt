import sqlite3
import json

DB_NAME = 'data/sensory_graph.db'

UNIT_CONVERSIONS = {
    'kHz': ('Hz', 1000),
    'MHz': ('Hz', 1e6),
    'GHz': ('Hz', 1e9),
    'mm': ('nm', 1e6),
    'cm': ('nm', 1e7),
    'm': ('nm', 1e9),
    'um': ('nm', 1000),
    'µm': ('nm', 1000),
}

def normalize_units(data):
    """
    Iterates through sensory modalities and normalizes units in quantitative_data.
    """
    if 'sensory_modalities' not in data:
        return data

    for modality in data['sensory_modalities']:
        qd = modality.get('quantitative_data')
        if qd:
            unit = qd.get('unit')
            if unit in UNIT_CONVERSIONS:
                new_unit, multiplier = UNIT_CONVERSIONS[unit]

                if qd.get('min') is not None:
                    qd['min'] = qd['min'] * multiplier

                if qd.get('max') is not None:
                    qd['max'] = qd['max'] * multiplier

                qd['unit'] = new_unit
                # Add a note about normalization? Not requested, but good practice.
                # But keeping strictly to the spec "Convert all units to standard base units".

    return data

def calculate_claim_density():
    """
    Calculates claims_per_species and flags imbalances.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT common_name, sensory_modalities FROM animals")
    rows = cursor.fetchall()

    stats = []
    for row in rows:
        modalities = json.loads(row['sensory_modalities'])
        claim_count = len(modalities)
        stats.append({
            'name': row['common_name'],
            'count': claim_count
        })

    conn.close()

    # Sort by count descending
    stats.sort(key=lambda x: x['count'], reverse=True)

    print("Claim Density Report:")
    print(f"{'Species':<20} | {'Claims':<10}")
    print("-" * 35)
    for stat in stats:
        print(f"{stat['name']:<20} | {stat['count']:<10}")

    # Check for imbalance
    if stats:
        max_claims = stats[0]['count']
        min_claims = stats[-1]['count']
        # Simple heuristic: if max is > 5x min, flag it.
        if min_claims > 0 and max_claims / min_claims > 5:
            print("\nWARNING: Significant claim imbalance detected!")
            print(f"Ratio: {max_claims/min_claims:.1f}x (Human/Vaquita bias check)")

def run_post_processing():
    conn = sqlite3.connect(DB_NAME)
    # We need to fetch, normalize, and update.
    # Since we store JSON in 'sensory_modalities', we can update that column.

    cursor = conn.cursor()
    cursor.execute("SELECT id, raw_data FROM animals")
    rows = cursor.fetchall()

    for row_id, raw_json_str in rows:
        data = json.loads(raw_json_str)
        normalized_data = normalize_units(data)

        # Update the record
        # We update both raw_data and sensory_modalities column
        sensory_modalities_json = json.dumps(normalized_data['sensory_modalities'])
        raw_data_json = json.dumps(normalized_data)

        cursor.execute('''
            UPDATE animals
            SET sensory_modalities = ?, raw_data = ?
            WHERE id = ?
        ''', (sensory_modalities_json, raw_data_json, row_id))

    conn.commit()
    conn.close()
    print("Normalization complete.")

    calculate_claim_density()

if __name__ == "__main__":
    run_post_processing()
