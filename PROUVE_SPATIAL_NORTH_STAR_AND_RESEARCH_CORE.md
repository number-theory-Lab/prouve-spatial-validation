# PROUVÉ Spatial — North Star & Research Core

**Status:** Strategic project charter for the Development Copy  
**Date:** 23 November 2026  
**Purpose:** Preserve the research mission and prevent the project from collapsing into a map-digitizing application.

> This charter does not replace or modify the frozen Research Baseline V0.4.1, the V0.5.2 release, or the separately scoped Enhalus research branch. It records how the core Prouvé decision framework is intended to govern spatial applications.

## 1. The mission is not to build a map app

PROUVÉ Spatial is intended to become a **spatial decision and optimization framework**. A map, mobile interface, GPS import, GeoTIFF viewer, and project-storage system are supporting instruments. They help the user provide spatial evidence and carry a decision into the field; they are not the research contribution by themselves.

The central question is:

**Given a spatial objective, a set of real-world constraints, imperfect evidence, and limited resources, what feasible spatial plan best satisfies the objective—and what can be proved or certified about the quality and limitations of that plan?**

The system should not merely calculate an area or display coordinates. It should help answer a decision question, compare feasible alternatives, quantify the cost of constraints, and explain the evidence behind its recommendation.

## 2. Preserve the original Prouvé decision logic

The original Prouvé research handoff defines the core workflow as:

**Reference → Selection → Loss Evaluation → Constraint Design**

Its spatial interpretation is:

1. **Reference / Objective:** Define the desired outcome, units, target region, objective function, and evidence used to establish the target.
2. **Selection / Feasibility:** Construct the set of admissible spatial plans or candidate placements under geometry, ecological/operational rules, access, resource limits, and exclusions.
3. **Loss Evaluation:** Measure how far each feasible plan is from the reference objective; report objective loss, coverage shortfall, resource cost, risk, or other clearly defined penalties.
4. **Constraint Design:** Study how restrictions change the best achievable result; compare relaxed and constrained problems, quantify constraint-induced loss where mathematically justified, and design admissible choices that reduce worst-case loss.

The one-dimensional quadratic/lattice results are part of Prouvé's mathematical foundation. They do **not automatically prove** a general two-dimensional or ecological optimizer. Any spatial extension needs its own precise model, mathematical justification, and benchmark validation.

## 3. What the spatial engine must do

The research engine—not the user interface—must eventually be responsible for:

- accepting a valid spatial domain and coordinate reference system;
- representing obstacles, exclusion zones, setbacks, boundaries, and access limitations;
- defining the decision unit and admissible candidate configurations;
- applying spacing, resource, capacity, and operational constraints;
- searching or optimizing feasible placements and/or layouts;
- comparing the result against transparent baseline methods;
- reporting objective values, constraint effects, uncertainty, sensitivity, and limitations;
- attaching reproducible evidence: input provenance, model/algorithm version, parameters, candidate family, solver settings, bounds, and verification status.

The system must distinguish:
- a **feasible plan** from an optimal plan;
- the best plan found in a finite search from a globally certified optimum;
- a bound over a specific model family from a bound over all possible spatial configurations;
- a geometric calculation from an agronomic or ecological recommendation;
- a model prediction from an independently validated field outcome.

## 4. Existing work: what is real and what is missing

### Existing archived research code

- The archived V0.2 Geometry Engine computes geometric usable area after boundary setbacks and obstacle buffers. Its own output explicitly states that placement optimization was not performed and maximum plant count was not proven.
- The archived V0.4 Optimization Engine searches a specified rectangular crop-row lattice over orientations and phase parameters, compares selected layouts, and calculates an upper bound for that specified lattice family.
- That upper bound is not a proof of global optimality over arbitrary unconstrained point placements.
- The current V0.5.2 Development Copy browser app primarily provides mapping, boundary capture/editing, coordinate and survey-data workflows, GeoTIFF preparation, and local persistence. It does not yet constitute the complete research decision engine and must not be described as if it does.

### Main missing integration

The central missing step is to turn the separate geometry and optimization research into a validated, clearly specified decision pipeline that accepts verified spatial inputs and returns a defensible plan plus an auditable decision/evidence report.

Do not mistake successful app interaction, a clear image overlay, or correct area arithmetic for proof that the spatial optimization contribution is novel or useful.

## 5. Application scope and branch separation

PROUVÉ is a framework, while each application is a test case. Application scopes must be versioned and kept separate.

- Earlier agricultural-plot work supplied a practical test bed for boundary geometry, usable area, crop-row spacing, and placement-lattice experiments.
- The later Enhalus acoroides research branch proposes a first focused restoration-planning application. This branch must use species- and protocol-specific biological definitions, not blindly reuse agricultural planting assumptions.
- The current V0.5.2 Development Copy remains an agricultural-plot mapping and field-data workflow prototype. Its tests do not validate a seagrass restoration planner.
- The user and domain experts must explicitly define the actual restoration unit (for example seed, seedling, shoot, rhizome fragment, or plug) before the engine models the placement decision.

The application branch must never redefine or erase the underlying Prouvé mission.

## 6. Research direction for the Enhalus acoroides flagship case

The candidate end-to-end workflow is:

**Site evidence → Suitability / exclusion analysis → Constrained allocation → Field execution → Monitoring → Evidence update → Re-planning**

The research should investigate whether this integrated workflow can add defensible decision value by connecting:

- species-specific site conditions and local ecological thresholds;
- uncertainty, source, date, scale, and positional accuracy for every evidence layer;
- excluded areas and practical constraints;
- constrained allocation of biologically defined planting units;
- field records and location-aware execution;
- repeated measurements such as survival, shoot formation, cover/density, and rhizome expansion;
- updates to the plan when observations change the estimated suitability or risk.

This is a **candidate research direction**, not a confirmed novelty claim. Existing literature already contains seagrass habitat-suitability modelling, GIS decision support, planting-distance experiments, spatial planting optimization for other seagrass contexts, and spatial monitoring. The potential contribution must therefore be tested against the literature and suitable baselines; it cannot be claimed merely because the project combines maps and formulas.

## 7. What could make PROUVÉ nationally significant

National-level potential must come from a reproducible and transferable research contribution, not from the number of app features.

The required evidence pathway is:

1. **A precise research problem:** define the spatial decision, decision unit, objective, constraints, uncertainty, and operating context.
2. **A defensible mathematical formulation:** specify variables, admissible set, objective, hard constraints, soft penalties, and the conditions under which guarantees hold.
3. **A meaningful algorithmic contribution:** demonstrate what the Prouvé engine adds beyond area-per-unit estimates, fixed grids, expert layouts, random layouts, greedy methods, or existing spatial optimizers.
4. **Correctness and certificates:** verify feasibility; compare small cases with exhaustive enumeration; establish valid lower/upper bounds or optimality gaps for exactly stated problem classes; record solver tolerances and reproducibility data.
5. **Fair benchmarks:** use the same input, objective, constraints, and compute budget wherever possible. Do not claim superiority from incomparable scenarios.
6. **Independent domain validation:** have agronomists/ecologists and field practitioners review biological or operational assumptions; use real observations and controls.
7. **Practical value:** measure whether recommendations improve resource use, placement quality, coverage, field time, survival, or another pre-registered outcome.
8. **Transferability:** test new sites and conditions; report when the model should abstain because data quality or uncertainty is inadequate.

No claim of national adoption, field effectiveness, or global novelty is justified until its corresponding evidence exists.

## 8. Product architecture: the app is one layer

The long-term architecture should keep responsibilities separate:

- **Evidence and data layer:** boundaries, imagery, surveys, environmental observations, source lineage, coordinate systems, uncertainty.
- **Spatial model layer:** domain geometry, candidate locations/configurations, exclusions, operational and ecological constraints.
- **Prouvé decision/optimization core:** reference objective, feasible-set construction, constrained search/optimization, loss and constraint-cost analysis.
- **Evidence/certificate layer:** feasibility checks, bounds, optimality status, sensitivities, assumptions, data/model hashes, and reproducible run records.
- **Field workflow layer:** map UI, navigation/field notes, observations, exports, and monitoring updates.

The UI should call the engine; it should not be mistaken for the engine.

## 9. Immediate priorities — in order

1. Preserve the V0.5.2 app as a boundary/data-capture prototype and complete its safety/usability validation without presenting it as the final innovation.
2. Recover and audit the archived V0.2 Geometry Engine and V0.4 Optimization Engine, their test data, objective, search domain, guarantees, and limitations.
3. Define one flagship spatial decision problem precisely. For the Enhalus branch, confirm the biological planting unit and candidate site variables with domain experts before writing the optimization objective.
4. Build a single reproducible engine interface connecting verified spatial inputs to feasible plans and evidence certificates.
5. Add benchmark baselines and independent validation before making novelty or superiority claims.

## 10. Strategic rule

Whenever a proposed feature does not strengthen the chain

**Evidence → Model → Feasible Decision → Loss / Constraint Analysis → Certificate → Field Feedback**

it is a supporting feature, not the core contribution.

Whenever an optimization claim cannot state its candidate set, constraints, objective, and proof scope, it must be labelled as a search result or heuristic—not as a proven optimum.

**The purpose of PROUVÉ is to make constrained spatial decisions explainable, measurable, and verifiable. The application is only the means by which people use that capability.**
