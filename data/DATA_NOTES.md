# Blast fragmentation dataset: notes

**Files:** `blast_master_110.csv` (110 blasts, 16 columns), `rock_types.csv` (the three rock classes), `cost_assumptions.csv` (hole, explosive and prices)

## Source
- Hudaverdi, T., Kulatilake, P.H.S.W. & Kuzu, C. (2011). Prediction of blast fragmentation using multivariate analysis procedures. *International Journal for Numerical and Analytical Methods in Geomechanics*, 35, 1318–1333.
- Kulatilake, P.H.S.W. et al. (2010), Tables 1, 2, 4 and 5 (the original blast database this compilation builds on).
- CSV compiled and cross-checked in the public repository `mobashshir-ubn-zainuddin/Rock-fragmentation-analysis-post-blasting` (GitHub), from a transcription in `pranjalkaushik-in/Blast-Design-and-Rock-Properties`.

## Corrections already applied (checked against Kulatilake et al. 2010)
- Blast Oz7: powder factor corrected from 0.53 to 0.70 kg/m³.
- Blast Ad22: E kept at 16.9 GPa (all Akdaglar blasts share this value).

## Columns
| Column | Meaning | Unit |
|---|---|---|
| blast_id | blast identifier | – |
| site, mine, country, rock_type | where the blast was fired | – |
| E_group | G1 if E ≥ 40 GPa, otherwise G2 (used in the original paper) | – |
| paper_split | train (97) / validation (13) as in the 2011 paper | – |
| S_B | spacing ÷ burden | – |
| H_B | bench height ÷ burden | – |
| B_D | burden ÷ hole diameter | – |
| T_B | stemming ÷ burden | – |
| Pf | powder factor | kg/m³ |
| XB | in-situ block size | m |
| E | elastic modulus of the rock | GPa |
| X50 | median fragment size (target) | m |

## Things to know
- E is a single value per site, so it identifies the mine.
- Reocin-UG is the only underground site; its stemming ratios (T_B up to 4.67) are much higher than the bench sites.
- The compilation is a third-party transcription. Before publishing results formally, spot-check a few rows against the original paper (available through the CSU library).

## rock_types.csv
One row per rock class, built from the median design at one representative site:
| Class | Site | Rock | E (GPa) | Bench (m) |
|---|---|---|---|---|
| Soft | Akdaglar | Sandstone (aggregate quarry) | 16.9 | 8.6 |
| Medium | Mrica | Andesite | 32 | 20.1 |
| Hard | Murgul | Dacite (copper mine) | 50 | 7.4 |

Enusa (E = 60 GPa) was not used as the hard class: its 3.7 m bench is too short for the bench ÷ burden limit with a 102 mm hole.

## cost_assumptions.csv
Typical values, not the mines' real contracts: 102 mm hole, ANFO (850 kg/m³, RWS 100), $1.00/kg explosive, $15/m drilling, $15 accessories per hole, subdrill 0.3 × burden, drilling accuracy 0.2 m. Targets: X50 ≤ 0.30 m and at most 5% of fragments over 1.0 m.
