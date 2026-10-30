# Game plan: Tasks 1 & 2

Branch: `tasks-1-2-model`. Due **Thu Nov 12, 10:00am**. Task 1 is worth 10% and Task 2 is worth 25%.
Tasks 3–6 come later, but Task 2 has to produce everything they will need: (design vector, fleet size, scenario) → (4 MoPs, cost).

**How to use this doc:** questions for the team are marked **❓ Q#**. Lines marked **From OS3A** are proposed answers drawn from `resources/OS3A_H2_Team13.pdf`; confirm or override them. Write the decision under **Answer:** (replace _TBD_) and initial it.

---

## Team decisions needed first (these block Task 2)

| # | Decision | Why it matters | Suggested default |
|---|----------|----------------|-------------------|
| D1 | **Service-area boundary and node network** (Lechmere/Cambridge Crossing, Kendall/MIT, Central) | Sets trip distances, which set cycle time, throughput and wait | 3 nodes. Lechmere–Kendall ≈ 1.5 km, Kendall–Central ≈ 1.5 km, Lechmere–Central ≈ 2.5 km. Measure the real distances on a map. |
| D2 | **Primary operating scenario** (pull from an OS3 report, with a sentence on why) | The model has to show it meets this scenario | Weekday commuter service: road vehicles in dedicated lanes inside the boundary, demand from Appendix B |
| D3 | **Posted speed limit** | Caps average speed, so most motors will hit the cap | 25 mph ≈ 40 km/h on arterials (Cambridge defaults to 20 mph on many city streets, so check and cite) |
| D4 | **Demand outside MIT/Kendall** | Appendix B only gives Kendall-origin demand | Use Kendall as the design node (that is where the SAU wait time is measured). Optionally scale it for the other nodes. |
| D5 | **What the e-bike speed equation does** | `700·P/W` gives about 5–8 km/h for bikes with a rider, which is unrealistic | Add rider pedal power (~0.1 kW) or use a fixed assisted speed (~18–20 km/h, under the 20 mph class-1/2 cap). Must be justified on the slide. |
| D6 | **Autonomy level vs. scenario** | The constraints tie L3/L4/L5 to where vehicles operate | Primary scenario inside the boundary → A3 allowed. Leave A4/A5 in the vector for the Task 4 scenario that goes outside the boundary. |

> **❓ Q1:** D1: Which nodes and boundary do we use, and what are the measured node-to-node distances (km)?
> **Answer:** _TBD_
> **From OS3A:** The OS3A boundary (Fig. 1) runs from Central Sq in the west, north through East Cambridge, east to Cambridge Crossing, and south along the Charles/MIT. That matches the assignment, so the **boundary is settled; only the distances remain.** OS3A also puts South Station/Boston in the *context* boundary, which is outside the system. That is useful for a Task 4 scenario.

> **❓ Q2:** D2: What is our primary operating scenario, which OS3 report does it come from, and why did we pick it?
> **Answer:** _TBD_
> **From OS3A:** OS3A points to **weekday a.m.-peak last-mile service from Kendall T** (MOE 1 sets the a.m. peak as its measurement condition; MOE 4 covers demand-responsive pickups). MIT P&T asked for *"small on-demand EV shuttles from a central hub"* and warned that empty shuttles are not financially viable. Proposal: on-demand small road EVs and/or e-bikes from a Kendall hub serving Lechmere and Central. OS3B is not in the repo yet; check whether it suggests something different.

> **❓ Q3:** D3: What speed limit do we use (and what is the source)? Is it the same for road vehicles and bikes?
> **Answer:** _TBD_
> **From OS3A:** OS3A does not give a speed limit, so this stays open. Look up the Cambridge 20 mph default and the Main St/Broadway limits.

> **❓ Q4:** D4: Do we model only the Kendall node, or scale the Appendix B demand to Lechmere and Central? If we scale it, by what factors?
> **Answer:** _TBD_
> **From OS3A:** OS3A gives scale but no per-node demand: 74,000 employees, 6,878 daily Red Line riders at Kendall, and a mode split of 26% walk / 29% MBTA / 22% bike / 22% drive. Appendix B's ~1,790 trips/day is about 26% of Kendall T boardings, so it reads as a plausible last-mile capture. We can cite that as validation for using Appendix B as is.

> **❓ Q5:** D5: How do we fix e-bike speed: add rider pedal power, use a fixed assisted speed, or keep the formula as given? Which number do we use?
> **Answer:** _TBD_
> **From OS3A:** **OS3A gives us a validation anchor.** The interviewee rides South Station → Draper (2–2.5 mi) in a reliable 13–15 min, about **15–18 km/h door to door**, and an e-bike saves only ~3 min because of traffic and red lights. That supports a **fixed assisted speed of ~18–20 km/h** over the formula. The interview also says e-bikes help most on inclines and for riders with injuries, which is the comfort and accessibility case for bikes.

> **❓ Q6:** D6: Which autonomy levels are allowed in the primary scenario? Do we also allow travel outside the boundary, which would force A4/A5?
> **Answer:** _TBD_
> **From OS3A:** OS3A's constraints are the real problem here: MA law requires a human at the wheel, no AV test permits are active, and Optimus Ride shut down in 2022. Public opposition to AVs is 75% statewide against our MOE 5 target of under 25%. L3 road vehicles need dedicated lanes, but OS3A found bike and curb lanes routinely blocked by trucks and rideshares. Proposal: A3 inside the boundary for the primary scenario, with A4/A5 only in the Task 4 scenario. Flag deployment realism for Task 5. E-bikes come with L4 built in and ride in the already-growing bike network, which is a point in their favor.

---

## Task 1: MAU (1 slide + backup)

**Method** (from lecture, MATE): piecewise-linear SAUs that interpolate the Appendix A points and clamp outside the table range, combined into an **additive weighted MAU**:

$$U = \sum_i k_i\,u_i(x_i), \quad \sum k_i = 1$$

with k = {volume 0.15, peak 0.25, wait 0.35, availability 0.25}.

**Expected results** (hand-checked; the code must reproduce them):

| Case | u_vol | u_peak | u_wait | u_avail | **MAU** |
|---|---|---|---|---|---|
| A | 0.40 | 0.35 | 0.83 | 0.70 | **0.613** |
| B | 1.00 | 0.50 | 0.61 | 0.60 | **0.639** |
| C | 0.30 | 0.35 | 0.91 | 0.80 | **0.651** |

The interesting point for the slide is that C has the lowest volume yet ranks highest, because wait time carries the largest weight (0.35). All three cases fall within about 0.04 of each other, so their ranking depends on the weights.

**Code: `src/os4/utility.py`**
- `sau(attribute, x)`: `np.interp` over the `sau_*.csv` points (handles the decreasing wait curve; clamps automatically).
- `mau(volume, peak, wait, availability, weights=None)`: vectorized so the tradespace can call it on arrays.
- `evaluate_cases()`: returns a DataFrame for `mau_test_cases.csv`.

**Verification (tests in `tests/test_utility.py`):**
- Every SAU returns its table points exactly, is monotone, and clamps to [0, 1].
- Best on every attribute → 1.0, worst → 0.0, and the weights sum to 1.
- Cases A/B/C match the table above.
- Validity: the MAU ranks a "meets every Table 1 requirement" point (1500, 150, 5, 0.75) above each of the cases. A sensitivity check sweeps each weight ±0.1 to show when the A/B/C ranking flips. This doubles as the "would we change the weights?" evidence.

**Discussion items (needs the team's OS3A MoEs / OS3B objectives):** whether safety, travel time (the 7-minute requirement) and outside-boundary wait (the 20-minute requirement) are missing from the MoPs; whether 0.35 on wait at a single node is too narrow; propose new weights if so.

> **❓ Q7:** Which MoEs from our OS3A and which operational objectives from our OS3B should we compare against Appendix A? Please paste them here or link them.
> **Answer:** _TBD_
> **From OS3A:** OS3A MOE mapping (Table 3):
> - **MOE 4 pickup wait (<15 min)** ↔ the wait-time MoP (0.35). Direct match. Note the targets differ: OS3A says 15 min, Table 1 says 5 min.
> - **MOE 1 allocated commute time / predictability** ↔ availability (partial). Reliability was the interviewee's #1 theme ("Red Line is the weakest link").
> - **MOE 7 regional talent access** and **MOE 2 bike share** ↔ passenger volume and throughput (indirect).
> - **MOE 3 serious crashes, MOE 6 stop announcements, MOE 5 AV opposition, MOE 8 curb access**: no Appendix A counterpart. OS3A already treats MOE 3 and MOE 6 as **pass/fail screens**, not weighted attributes.
> - OS3B operational objectives are still missing. Who has our OS3B?

> **❓ Q8:** Do we propose new weights? If so, what values (they must sum to 1), and what is the one-line rationale for each?
> **Answer:** _TBD_
> **From OS3A:** Starting proposal from OS3A: **volume 0.10 / peak 0.25 / wait 0.35 / availability 0.30.** Wait stays largest because MOE 4 is a direct match. Weight moves from volume to availability because reliability (MOE 1) dominated the stakeholder evidence while volume traces only indirectly. Keep safety and accessibility as pass/fail screens rather than weights, consistent with OS3A. Run the weight sweep before committing to these numbers.

> **❓ Q9:** Linear interpolation between the Appendix A points (default), or fit a smooth curve? Linear is simpler and reproduces the given points exactly.
> **Answer:** _TBD_

---

## Task 2: system model (3 slides + backup)

### Design vector

| Decision | Road options | Bike options |
|---|---|---|
| Chassis / frame | C1–C8 | B1–B3 |
| Battery | P1–P7 (weight ≤ ⅓ chassis) | E1–E3 (weight ≤ ½ frame) |
| Charger | G1–G3 | G1–G2 |
| Motor | M1–M4 | K1–K3 |
| Autonomy | A3/A4/A5 | fixed L4 (in frame cost) |
| Fleet size | N_road: e.g. 0–60, step 5 | N_bike: e.g. 0–300, step 25 |

Feasible vehicle variants after the battery constraint:
- **Road:** C1–C2 → P1–P4; C3–C4 → P1–P5; C5 → P1–P6; C6–C7 → P1–P6; C8 → P1–P7. That gives 43 chassis/battery pairs × 3 chargers × 4 motors × 3 autonomy levels = **1,548**.
- **Bike:** B1, B2 → E1 only; B3 → E1–E3. That gives 5 frame/battery pairs × 2 × 3 = **30**.

Crossing these with fleet sizes is the "MASSIVE" space the recitation warns about. Task 2's model handles all of them. Pruning (dominated vehicle variants, such as a bigger motor with no speed gain once the speed cap binds) belongs to Task 3, but the vehicle-level table should make that pruning trivial.

> **❓ Q10:** What fleet-size ranges and step sizes do we use for road vehicles and bikes? Should a mixed fleet allow more than one road variant at a time? The default is one road variant plus one bike variant per architecture.
> **Answer:** _TBD_
> **From OS3A:** OS3A argues against large, half-empty shuttles (MIT P&T quote) and in favor of more e-bikes (the interviewee's #1 request; Ames/Main Bluebikes already need valet service). That points toward small chassis (C1–C4) plus bikes. Make sure the bike fleet range reaches Bluebikes scale (18 stations in Kendall).

### Layer 1: vehicle model, `src/os4/vehicle.py` (Appendix B, as given)
For each feasible variant compute: total weight (+100 kg × pax), cost, Wh/km, range, speed (capped at D3), charge time, up-time, down-time and **availability**. Return one tidy DataFrame with one row per variant.
- Apply the e-bike modification from D5. Keep the original formula alongside it so the justification can show both.

### Layer 2: fleet/operations model, `src/os4/fleet.py`
Inputs: vehicle row(s), N_road, N_bike, scenario (network distances, demand profile, speed limit). Proposed equations (based on the Wikibooks transit-capacity pages from Appendix B):
- **Cycle time** per trip = (trip distance + empty repositioning distance) / speed + dwell (60 s).
- **Per-vehicle capacity** = (60 / cycle_min) × pax × 0.75 load factor. A bike carries pax = 1 (2 for B3) and its repositioning leg runs autonomously.
- **Effective fleet** = N × availability, since vehicles that are charging carry no passengers.
- **Fleet throughput** (trips/h) = Σ effective vehicles × per-vehicle capacity. **Peak throughput MoP** = min(capacity, offered peak demand), or capacity alone. Decide which and document it, because the SAU runs to 200 while Appendix B demand peaks at 150.
- **Daily passenger volume** = Σ over the 2-hour bins of min(demand_h, capacity) × 2.
- **Average wait at Kendall:** headway/2 when vehicles are plentiful, where headway = 60 / (vehicle departures/h at the node). When demand exceeds capacity, add a queueing penalty (an M/M/c-style or simple backlog term) so wait rises steeply. For bikes, use time for the nearest idle bike to self-deliver, based on the idle-bike density over the service area.
- **Availability MoP:** per-vehicle Appendix B availability. For a mixed fleet, use the capacity-weighted average. Compare against the 0.75 benchmark.
- **Fleet cost** = Σ vehicle cost × N. State that charging infrastructure and operations cost are excluded, or add them as an assumption.

> **❓ Q11:** Is the peak-throughput MoP the fleet's capacity, or served demand (min of capacity and demand)? Note that the SAU rewards up to 200/h but demand peaks at 150/h.
> **Answer:** _TBD_

> **❓ Q12:** Which wait-time model do we use: headway/2 plus a queue penalty when overloaded, a full M/M/c queue, or something else? How do we model bike self-delivery time?
> **Answer:** _TBD_
> **From OS3A:** MOE 4 explicitly covers *demand-responsive* pickups, so an on-demand wait model fits better than a fixed-route headway model. Anchors: EZRide runs every 8–12 min (≈ 4–6 min average wait), and MBTA buses every 15–30 min.

> **❓ Q13:** What is the average trip length, and what fraction of distance is empty repositioning (deadhead)? Do these differ for road vehicles and bikes?
> **Answer:** _TBD_
> **From OS3A:** OS3A suggests short in-district trips: Kendall ↔ Central for lunch, the MIT campus, and the Charles/MGH area. That implies roughly 1–2.5 km. It gives no deadhead data.

> **❓ Q14:** How do we compute availability for a mixed fleet: weighted by capacity, the minimum of the two, or by some other rule?
> **Answer:** _TBD_

> **❓ Q15:** Does cost cover vehicle capital cost only (Appendix B), or do we add charging stations, depots and operating cost?
> **Answer:** _TBD_
> **From OS3A:** MIT P&T's "not financially viable" concern, and EZRide's funding from ~25 member firms, suggest at least noting operating cost, even if the tradespace axis stays capital cost.

### Layer 3: glue, `src/os4/model.py` (new)
`evaluate(architecture, scenario) -> dict` returns the MoPs, MAU and cost. Tasks 3 and 4 call this with a different scenario object, so put scenarios in `data/scenarios.yaml` or a dataclass rather than in constants.

### Verification & validation (needed for the slide)
- **Hand-calc check:** one road and one bike variant worked by hand (in a spreadsheet), matched by the code to 1e-9.
- **Robustness sweep:** every feasible variant × fleet-size grid produces no NaN, inf or negative values, and availability stays in (0, 1). This is the assignment's "doesn't break down" requirement.
- **Monotonicity tests:** throughput rises with N, wait falls with N, cost is linear in N, and N = 0 gives zero throughput and an infinite or maxed-out wait that is handled.
- **Constraint tests:** infeasible battery/chassis pairs are excluded.
- **Validation / anchor:** compare to real systems, such as Bluebikes trips and dock density in Cambridge, and the MBTA CT2/EZRide shuttle headways and fleet sizes. Show that the model lands in a plausible range. Show that the primary scenario's demand (150/h peak, sum ≈ 1,790 trips/day) is met by at least one architecture.

> **❓ Q16:** Which real-world anchor systems do we validate against, and who will gather their data (fleet size, headway, trips/day)?
> **Answer:** _TBD_
> **From OS3A:** OS3A already has anchors with citations: **EZRide 8–12 min headways** [54], **MBTA buses 15–30 min** [45], **5 daytime MIT shuttles**, **18 Bluebikes stations** in Kendall, **6,878 Red Line riders/day**, and **Red Line 89% on-time within 5 min** [44]. Reuse the OS3A references.

### Deliverable: 5-architecture table
Pick 5 that span the space: (1) small road-only fleet of C2 cars, (2) large road shuttles (C6/C7), (3) bike-only, (4) mixed road + bike, (5) a high-autonomy (A5) or long-range variant. Columns: composition, N, component IDs, speed, range, throughput, wait, availability, vehicle cost, fleet cost, plus the MAU for free.

> **❓ Q17:** Do we agree on these 5 architectures, or swap any of them? Fill in the specific component IDs and N for each.
> **Answer:** _TBD_

### Model export
Use `python -m os4` to write `outputs/os4_model.xlsx` (with tabs for inputs, the SAU/MAU tables, the vehicle variants, the 5 architectures, and the hand-calc check) and make it the ZIP submission. The Excel file holds model data and formulas only; text responses go in the slide deck.

---

## Questions raised by OS3A

> **❓ Q20:** Task 4 scenario. OS3A suggests two candidates that are not just variations of the primary scenario: **(a) a Red Line shutdown** (the July 2026 closure; demand surges, and trips leave the boundary toward Boston, which forces A4/A5), or **(b) winter**, when the interviewee and other commuters switch from bike to Red Line, so the bike fleet loses value. Which one do we pick? Picking now lets the scenario object hold both.
> **Answer:** _TBD_

> **❓ Q21:** Accessibility. OS3A says no wheelchair-accessible AVs exist, and e-bikes serve no one with a mobility disability. Do we add an accessibility screen, for example requiring that any concept include some road vehicles? That would eliminate bike-only architectures in Task 5.
> **Answer:** _TBD_

> **❓ Q22:** Where is our OS3B? Task 1 asks us to compare against its operational objectives, and only OS3A is in `resources/`.
> **Answer:** _TBD_

## Suggested split & order
1. **Day 1 (all):** decide D1–D6 in a 30-minute meeting.
2. **Task 1:** `utility.py` and its tests, plus the slide (1 person, small).
3. **Vehicle layer:** `vehicle.py`, its tests, and the hand-calc spreadsheet (1 person).
4. **Fleet layer:** `fleet.py` and the scenario config, which carries the most modeling judgment (1–2 people).
5. **Integrate:** `model.py`, the 5-architecture table, the xlsx export, and the Task 2 slides.

Steps 2–4 can run in parallel once the vehicle-row DataFrame columns are agreed.

> **❓ Q18:** Who owns each step (Sanjay / Yonis / Austin / Robert), and what internal deadline do we set for each?
> **Answer:** _TBD_

> **❓ Q19:** Do we keep the model in Python only, or also build a spreadsheet version for the graders? The plan exports an xlsx either way.
> **Answer:** _TBD_
