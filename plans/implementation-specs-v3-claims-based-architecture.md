# Project Directive: The "Web of Senses" Engine (Production Spec)

**To**: Jules (Lead Developer)
**From**: Architecture Team
**Subject**: FINAL BUILD SPECS - The Epistemic Sensory Graph

## Executive Summary

We are building a Claims-Based Knowledge Graph of animal sensory systems. Unlike traditional databases, we do not force biology into standardized columns. We extract Sensory Claims backed by evidence lists.

- **Core Logic**: Polymorphism > Standardization.
- **Data Integrity**: If a sense is unknown, it is omitted (not null).
- **Epistemology**: We track how we know something (Evidence), not just what we know.

## 1. The Schema (v4.0 - Production Ready)

Changes: Added `stimulus_type` for physical grounding, split `mechanism` for granularity, and converted `evidence` to a list to handle conflicting data.

```json
{
  "identity": {
    "common_name": "String",
    "scientific_name": "String",
    "taxonomy": {
      "class": "String",
      "order": "String"
    }
  },
  "sensory_modalities": [
    {
      "modality_domain": "String (e.g., 'Mechanoreception', 'Chemoreception', 'Photoreception')",
      "sub_type": "String (e.g., 'Echolocation', 'Seismic Sensitivity', 'UV Vision')",
      "stimulus_type": "String (e.g., 'Pressure Wave', 'Electromagnetic Field', 'Volatile Compound')",

      "quantitative_data": {
        "min": Number_or_Null,
        "max": Number_or_Null,
        "unit": "String (e.g., 'Hz', 'nm', 'uV/cm')",
        "context": "String (e.g., 'Physiological Limit', 'Communication Range', 'Behavioral Threshold')"
      },

      "mechanism": {
        "level": "String (e.g., 'Anatomical', 'Cellular', 'Neural', 'Genetic')",
        "description": "String (e.g., 'Cryptochrome-mediated radical pair reaction')"
      },

      "evidence": [
        {
          "source_type": "String (e.g., 'Behavioral Audiogram', 'Genetic Inference', 'Review Paper')",
          "citation": "String",
          "note": "String (Optional, e.g., 'Contested by 2023 study')"
        }
      ]
    }
  ],
  "meta": {
    "data_quality_flag": "String (e.g., 'High_Evidence', 'Inferred_Only', 'Contested')"
  }
}
```

## 2. The "Scientific Reviewer" System Prompt

**Role**: You are an expert Sensory Biologist and Data Curator.

**Objective**: Extract independent sensory claims from text. You are creating a graph of phenomenology (how the animal experiences the world).

### The 5 Golden Rules:

1. **Anti-Anthropocentrism**: Do not ignore a sense because it is weak or irrelevant to humans. If an animal senses humidity, magnetic fields, or electrostatic pressure, extract it.

2. **Context is King**: You must distinguish between what an animal can detect vs. what it uses for communication.
   - **Bad**: "Range: 20-20k Hz"
   - **Good**: "Range: 20-20k Hz (Context: Physiological Limit)"

3. **Mechanism Granularity**: Distinguish between "having the gene" (Genetic) and "using the organ" (Anatomical).

4. **Handling Disputes**: If sources disagree (e.g., Magnetoreception in humans), create one modality entry but include multiple items in the `evidence` list representing the conflict.

5. **Null Protocol**: If a specific threshold is unknown, omit the `quantitative_data` block entirely. Do not guess.

## 3. Implementation Architecture

### A. The Search Strategy (Deep Dive)

The Agent must perform multi-stage research to fill the complex schema.

1. **Broad Sweep**: `"{animal} sensory biology umwelt review"` (identifies modality types).
2. **Targeted Drill-Down**: `"{animal} {modality} mechanism anatomical"` (fills mechanism).
3. **Threshold Hunt**: `"{animal} {modality} threshold audiogram sensitivity"` (fills quantitative data).

### B. Post-Processing Logic (claim_linker.py)

1. **Normalization**: Convert all units to standard base units (kHz -> Hz, mm -> nm) after extraction.
2. **Claim Density Check**: Calculate `claims_per_species`. If "Human" has 20 claims and "Vaquita" has 1, flag this imbalance for the visualization layer (so we don't assume the Vaquita is "sensory-poor").

### C. The Seed List (The "Stress Test")

- **Bottlenose Dolphin**: (Test: High-precision behavioral acoustics).
- **Great White Shark**: (Test: Non-human modality dominance - Electroreception).
- **Monarch Butterfly**: (Test: Migratory multi-modal integration - UV + Magnetic).
- **Naked Mole Rat**: (Test: "Weird" physiology - Acid insensitivity/Thermal oddities).
- **Human**: (Test: Anthropocentric bias check).

## 4. Immediate Next Steps for Jules

1. Initialize `sensory_graph.db` with the new Schema (using JSONB storage for the `sensory_modalities` list to allow querying).
2. Run the Seed List through the Agent.
3. **Manual Audit**: Print the JSON for "Great White Shark" and verify that `stimulus_type` correctly identifies "Electric Fields" and that evidence lists the Ampullae of Lorenzini correctly.

## Final Word to User

This directive is complete. It addresses the "Claim Explosion" risk by adding the density check in post-processing, and it solves the "False Precision" risk by adding the `context` field.

Would you like me to now generate the Python Code for `claim_linker.py` (the post-processor), or are you ready to deploy this to Jules?
