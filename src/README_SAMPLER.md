# Taxonomy Sampler: Perceptual Strategy Coverage

## Goal
The goal of the Sampler is to bootstrap a "Web of Senses" by sampling independent perceptual strategies across the entire Animalia kingdom. Instead of attempting taxonomic completeness, we aim for **epistemic diversity**—ensuring the research queue represents the widest possible variety of sensory evolutions.

## Methodology: "Top N Families per Order"
We sample the top 3–5 families from every biological Order in Animalia. This strategy is chosen to:
1. **Distribute Ignorance Evenly**: Prevents overfitting to well-studied groups (like Mammals) while ensuring obscure branches of life are represented.
2. **Maximize Tractability**: Bounds the initial research queue to ~1,500–2,500 species, rather than millions.
3. **Target Sensory Innovation**: Families often represent distinct ecological niches where sensory strategies diverge (e.g., deep-sea vs. terrestrial).

## Scoring Heuristic (The "Prominence" Score)
Families within an order are ranked by a heuristic score:
`Score = sqrt(SpeciesCount) + WikiBonus`

*   **Biological Richness (SpeciesCount)**: Families with more species often imply higher ecological diversity.
*   **Documentation (WikiBonus)**: A flat +5 bonus is applied if the family has a Wikipedia page. This ensures we prefer families that are well-documented enough for LLM research.

## Representative Species Selection
For each selected family, we pick a representative species using a "Wiki-First" priority:
1.  **Priority 1**: The most "prominent" species (by GBIF observation) that *also* has a Wikipedia page.
2.  **Priority 2**: The primary "Accepted" species from the GBIF backbone (fallback).

This ensures the Researcher (LLM) has a high-quality text context to work with.

## Traceability
Each added species is tagged in the `research_queue` with a `taxonomy_source` string indicating:
- The Order and Family it represents.
- The reason/score for the family's selection.
- The method used to pick the specific species.
