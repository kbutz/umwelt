import sqlite3
import json

DB_NAME = 'sensory_graph.db'

# Data extracted from research
seed_data = [
    {
        "identity": {
            "common_name": "Bottlenose Dolphin",
            "scientific_name": "Tursiops truncatus",
            "taxonomy": {
                "class": "Mammalia",
                "order": "Artiodactyla"
            }
        },
        "sensory_modalities": [
            {
                "modality_domain": "Mechanoreception",
                "sub_type": "Echolocation / Hearing",
                "stimulus_type": "Acoustic Pressure Wave",
                "quantitative_data": {
                    "min": None,
                    "max": 160,
                    "unit": "kHz",
                    "context": "Physiological Limit (Upper)"
                },
                "mechanism": {
                    "level": "Anatomical",
                    "description": "Auditory Bullae / Cochlear transduction (Hypertrophied auditory nerve)"
                },
                "evidence": [
                    {
                        "source_type": "Behavioral Audiogram",
                        "citation": "Houser et al. 2022, Frontiers in Marine Science",
                        "note": "Best sensitivity at 45 kHz. Upper limit > 149 kHz."
                    },
                    {
                        "source_type": "Review Paper",
                        "citation": "SeaWorld InfoBook",
                        "note": "Greatest sensitivity 40-100 kHz"
                    }
                ]
            },
            {
                "modality_domain": "Magnetoreception",
                "sub_type": "Magnetic Navigation",
                "stimulus_type": "Magnetic Field",
                "quantitative_data": None,
                "mechanism": {
                    "level": "Unknown",
                    "description": "Likely magnetite-based (inferred from behavior)"
                },
                "evidence": [
                    {
                        "source_type": "Behavioral Experiment",
                        "citation": "Kremers et al. 2014, Naturwissenschaften",
                        "note": "Dolphins approach magnetized objects with shorter latency."
                    }
                ]
            },
            {
                "modality_domain": "Electroreception",
                "sub_type": "Passive Electroreception",
                "stimulus_type": "Electric Field",
                "quantitative_data": {
                    "min": 2.4,
                    "max": 5.5,
                    "unit": "uV/cm",
                    "context": "Behavioral Threshold (DC fields)"
                },
                "mechanism": {
                    "level": "Anatomical",
                    "description": "Vibrissal Crypts"
                },
                "evidence": [
                    {
                        "source_type": "Behavioral Experiment",
                        "citation": "Hanke et al. / Czech-Damal et al. 2012 (Guiana Dolphin context)",
                        "note": "Specific sensitivity for Tursiops confirmed by recent studies (e.g. PMC10714143: 'Passive electroreception in bottlenose dolphins')."
                    }
                ]
            }
        ],
        "meta": {
            "data_quality_flag": "High_Evidence"
        }
    },
    {
        "identity": {
            "common_name": "Great White Shark",
            "scientific_name": "Carcharodon carcharias",
            "taxonomy": {
                "class": "Chondrichthyes",
                "order": "Lamniformes"
            }
        },
        "sensory_modalities": [
            {
                "modality_domain": "Electroreception",
                "sub_type": "Passive Electroreception",
                "stimulus_type": "Electric Field",
                "quantitative_data": {
                    "min": 0.005,
                    "max": None,
                    "unit": "uV/cm",
                    "context": "Physiological Threshold"
                },
                "mechanism": {
                    "level": "Anatomical",
                    "description": "Ampullae of Lorenzini (Gel-filled canals)"
                },
                "evidence": [
                    {
                        "source_type": "Review Paper",
                        "citation": "Kalmijn 1971; UC Santa Cruz News 2025",
                        "note": "Threshold cited as 5 nV/cm (0.005 uV/cm)."
                    }
                ]
            },
            {
                "modality_domain": "Mechanoreception",
                "sub_type": "Hearing",
                "stimulus_type": "Acoustic Pressure Wave / Particle Motion",
                "quantitative_data": {
                    "min": 10,
                    "max": 800,
                    "unit": "Hz",
                    "context": "Hearing Range"
                },
                "mechanism": {
                    "level": "Anatomical",
                    "description": "Inner Ear (Otoliths) / Lateral Line"
                },
                "evidence": [
                    {
                        "source_type": "General Reference",
                        "citation": "Shark Trust / SeaWorld",
                        "note": "Most sensitive to low frequencies (below 800 Hz)."
                    }
                ]
            },
            {
                "modality_domain": "Chemoreception",
                "sub_type": "Olfaction",
                "stimulus_type": "Volatile Compound / Amino Acids",
                "quantitative_data": {
                    "min": 1,
                    "max": None,
                    "unit": "ppm",
                    "context": "Detection Threshold (Blood)"
                },
                "mechanism": {
                    "level": "Anatomical",
                    "description": "Olfactory Rosettes"
                },
                "evidence": [
                    {
                        "source_type": "General Reference",
                        "citation": "Manoa Hawaii Edu / General Consensus",
                        "note": "1 ppm often cited."
                    }
                ]
            }
        ],
        "meta": {
            "data_quality_flag": "High_Evidence"
        }
    },
    {
        "identity": {
            "common_name": "Monarch Butterfly",
            "scientific_name": "Danaus plexippus",
            "taxonomy": {
                "class": "Insecta",
                "order": "Lepidoptera"
            }
        },
        "sensory_modalities": [
            {
                "modality_domain": "Photoreception",
                "sub_type": "UV Vision",
                "stimulus_type": "Electromagnetic Radiation (Light)",
                "quantitative_data": {
                    "min": 300,
                    "max": 700,
                    "unit": "nm",
                    "context": "Spectral Sensitivity"
                },
                "mechanism": {
                    "level": "Molecular",
                    "description": "Opsins / Compound Eye"
                },
                "evidence": [
                    {
                        "source_type": "Behavioral Study",
                        "citation": "Blackiston et al. 2011",
                        "note": "Can discriminate UV wavelengths."
                    }
                ]
            },
            {
                "modality_domain": "Magnetoreception",
                "sub_type": "Inclination Compass",
                "stimulus_type": "Magnetic Inclination",
                "quantitative_data": None,
                "mechanism": {
                    "level": "Molecular/Genetic",
                    "description": "Cryptochrome 1 (Cry1) mediated radical pair reaction"
                },
                "evidence": [
                    {
                        "source_type": "Genetic/Behavioral Study",
                        "citation": "Wan et al. 2021 (Nature Communications)",
                        "note": "Cry1 is essential for light-dependent inclination magnetosensing."
                    },
                    {
                        "source_type": "Review",
                        "citation": "Guerra et al. 2014",
                        "note": "Migratory orientation."
                    }
                ]
            }
        ],
        "meta": {
            "data_quality_flag": "High_Evidence"
        }
    },
    {
        "identity": {
            "common_name": "Naked Mole Rat",
            "scientific_name": "Heterocephalus glaber",
            "taxonomy": {
                "class": "Mammalia",
                "order": "Rodentia"
            }
        },
        "sensory_modalities": [
            {
                "modality_domain": "Nociception",
                "sub_type": "Acid Insensitivity",
                "stimulus_type": "Protons (Acid)",
                "quantitative_data": None,
                "mechanism": {
                    "level": "Genetic",
                    "description": "NaV1.7 voltage-gated sodium channel variant (blocked by protons)"
                },
                "evidence": [
                    {
                        "source_type": "Molecular Study",
                        "citation": "Smith et al. 2011 (Science)",
                        "note": "Evolutionary pressure selected for NaV1.7 variant."
                    }
                ]
            },
            {
                "modality_domain": "Thermoreception",
                "sub_type": "Cold Sensing",
                "stimulus_type": "Thermal Energy",
                "quantitative_data": None,
                "mechanism": {
                    "level": "Molecular",
                    "description": "TRPM8 channel (expanded cold sensing system)"
                },
                "evidence": [
                    {
                        "source_type": "Preprint/Study",
                        "citation": "BioRxiv 2025 (10.1101/2025.09.25.678629v1)",
                        "note": "Specialized cold sensing system."
                    }
                ]
            }
        ],
        "meta": {
            "data_quality_flag": "High_Evidence"
        }
    },
    {
        "identity": {
            "common_name": "Human",
            "scientific_name": "Homo sapiens",
            "taxonomy": {
                "class": "Mammalia",
                "order": "Primates"
            }
        },
        "sensory_modalities": [
            {
                "modality_domain": "Mechanoreception",
                "sub_type": "Hearing",
                "stimulus_type": "Acoustic Pressure Wave",
                "quantitative_data": {
                    "min": 20,
                    "max": 20,
                    "unit": "kHz",
                    "context": "Physiological Limit"
                },
                "mechanism": {
                    "level": "Anatomical",
                    "description": "Cochlea / Organ of Corti"
                },
                "evidence": [
                    {
                        "source_type": "Textbook",
                        "citation": "Standard Medical Consensus",
                        "note": "20Hz - 20kHz range."
                    }
                ]
            },
            {
                "modality_domain": "Photoreception",
                "sub_type": "Vision",
                "stimulus_type": "Electromagnetic Radiation",
                "quantitative_data": {
                    "min": 400,
                    "max": 700,
                    "unit": "nm",
                    "context": "Visible Spectrum"
                },
                "mechanism": {
                    "level": "Cellular",
                    "description": "Rods and Cones (Trichromatic)"
                },
                "evidence": [
                    {
                        "source_type": "Textbook",
                        "citation": "Standard Consensus",
                        "note": "Trichromatic vision."
                    }
                ]
            }
        ],
        "meta": {
            "data_quality_flag": "High_Evidence"
        }
    }
]

def populate_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for entry in seed_data:
        common_name = entry['identity']['common_name']
        scientific_name = entry['identity']['scientific_name']
        taxonomy_json = json.dumps(entry['identity']['taxonomy'])
        sensory_modalities_json = json.dumps(entry['sensory_modalities'])
        meta_json = json.dumps(entry['meta'])
        raw_data_json = json.dumps(entry)

        cursor.execute('''
            INSERT INTO animals (common_name, scientific_name, taxonomy, sensory_modalities, meta, raw_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (common_name, scientific_name, taxonomy_json, sensory_modalities_json, meta_json, raw_data_json))

    conn.commit()
    conn.close()
    print("Database populated with seed data.")

if __name__ == "__main__":
    populate_db()
