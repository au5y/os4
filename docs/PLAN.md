# OS4 model plan

How the team's model works, and every decision and assumption behind it. Sources are tagged in line by number, e.g. [[1]](references.md#ref-1), and listed in [references.md](references.md).

**How the questions are laid out.** Every modeling question is numbered Q1–Q27 in the order it comes up, and code that depends on one is tagged with its number (e.g. `PLAN.md Q18`). Each question has a heading that states the question (with an anchor, so `[Q18](#q18)` links to it), then:

- **Answer:** what the model does, labeled with where the answer came from:
  - **Decision (Austin, date)** or **Decision (team, date):** a choice and who made it, when that was recorded.
  - **Decision:** a choice with no owner recorded.
  - **From OS3A:** adopted from our OS3A report [[2]](references.md#ref-2).
  - **Assumption:** a modeling simplification we state as a limitation.
  - **Deviation from Appendix B:** where we changed the assignment's equations.
- **Discussion:** the evidence and reasoning behind the answer.

| # | Question | # | Question |
| --- | --- | --- | --- |
| [Q1](#q1) | Operating scenario | [Q15](#q15) | Removable e-bike batteries |
| [Q2](#q2) | Boundary and node distances | [Q16](#q16) | Riders per e-bike trip |
| [Q3](#q3) | Trip length and empty return | [Q17](#q17) | Peak throughput |
| [Q4](#q4) | Road speed | [Q18](#q18) | Wait model |
| [Q5](#q5) | Demand | [Q19](#q19) | Availability attribute |
| [Q6](#q6) | E-bike speed | [Q20](#q20) | Travel time |
| [Q7](#q7) | Autonomy level | [Q21](#q21) | Cost |
| [Q8](#q8) | Accessibility | [Q22](#q22) | Utilization ceilings |
| [Q9](#q9) | MOE mapping | [Q23](#q23) | Anchors |
| [Q10](#q10) | Team weights | [Q24](#q24) | The five Task 2 architectures |
| [Q11](#q11) | Travel time as an attribute | [Q25](#q25) | Tools |
| [Q12](#q12) | Bike share as an attribute | [Q26](#q26) | Task 3 reference architecture |
| [Q13](#q13) | Energy and fleet size as attributes | [Q27](#q27) | Load factor |
| [Q14](#q14) | Architectures and fleet grid | | |

---

## 1. Operating scenario

The primary scenario, **standard weekday demand**, is a weekday on-demand last-mile service from a hub at Kendall T to Lechmere and Central, using small road EVs and/or e-bikes. It lives in `scenario.primary_scenario()`, separate from the design vector, so later tasks can rerun the same architectures under a different scenario.

| Input | Value | Question |
| --- | --- | --- |
| Nodes | Lechmere / Cambridge Crossing, Kendall / MIT, Central | [Q2](#q2) |
| Demand | Appendix B as given: Kendall-origin trips, 1,790 trips/day, peak 150 trips/h (8:00–14:00) | [Q5](#q5) |
| Trip length | 1.75 km by road, 1.6 km by bike | [Q3](#q3) |
| Empty return (deadhead) | 1.0: every trip returns to Kendall empty | [Q3](#q3) |
| Road speed | Capped at 21 km/h average (achieved, not posted) | [Q4](#q4) |
| Bike speed | Fixed 18 km/h with assist | [Q6](#q6) |
| Dwell | 60 s per trip (Appendix B) | |
| Autonomy | A3 is allowed inside the boundary | [Q7](#q7) |

**Why vehicles start at Kendall and return empty.** Appendix B gives demand only for trips that start at Kendall. Each vehicle therefore cycles all day: leave the hub with riders, drop them off, return empty, repeat. That one assumption sets the cycle time, the wait (measured at the hub), and each vehicle's capacity.

#### <a id="q1"></a>Q1. What service does the system provide, and when?

**Answer (Decision, Austin, 2026-11-03; service type From OS3A):** **standard weekday demand**: on-demand last-mile service from a hub at Kendall T, scored over Appendix B's full weekday (twelve 2-hour bins, 1,790 trips/day) and sized for its 8:00–14:00 peak of 150 trips/h.

**Discussion.** OS3A's MOE 1 sets the a.m. peak as its measurement condition, and MOE 4 covers demand-responsive pickups. MIT Parking & Transportation [[15]](references.md#ref-15) asked for *"small on-demand EV shuttles from a central hub"* and warned that empty shuttles are not financially viable. The scenario was first framed as the a.m. peak only, but Table 1's thresholds (1,500 trips/day, 50 trips/h off-peak) and the Appendix A volume SAU (trips/day) can only be checked over the whole day. The peak still sizes the fleet: it carries 900 of the 1,790 daily trips, and capacity that covers 150 trips/h covers every other bin.

#### <a id="q2"></a>Q2. Where is the system boundary, and how far apart are its nodes?

**Answer (From OS3A; distances Decision, measured 2026-11-01):** the OS3A boundary, which matches the assignment. Node distances are the mean of the two directions of each OpenStreetMap route (table below).

**Discussion.** The OS3A boundary [[2]](references.md#ref-2) runs from Central Square in the west, north through East Cambridge, east to Cambridge Crossing, and south along the Charles and MIT. OS3A puts South Station and Boston in the *context* boundary, outside the system.

Station coordinates come from OpenStreetMap via Nominatim [[22]](references.md#ref-22): Lechmere 42.37128, −71.07615; Kendall/MIT 42.36242, −71.08572; Central 42.36532, −71.10356. Road and bike routes come from OSRM on OpenStreetMap data [[23]](references.md#ref-23), [[24]](references.md#ref-24), in both directions; one-way streets make them differ.

| Pair | Straight line | Drive (each direction) | Bike (each direction) | **Road model** | **Bike model** | Road time at 21 km/h |
| --- | --- | --- | --- | --- | --- | --- |
| Lechmere–Kendall | 1.26 km | 1.65 / 2.11 km | 1.58 / 1.63 km | **1.9 km** | **1.6 km** | 5.4 min |
| Kendall–Central | 1.50 km | 1.60 / 1.60 km | 1.64 / 1.63 km | **1.6 km** | **1.6 km** | 4.6 min |
| Lechmere–Central | 2.35 km | 3.62 / 2.91 km | 2.99 / 3.17 km | **3.3 km** | **3.1 km** | 9.4 min |

Google Maps was not checked (no API key). Lechmere–Central would break the 7-minute travel-time requirement [[1]](references.md#ref-1) at 21 km/h (8.3 min even in the shorter direction), but the primary scenario has no trips on that link.

#### <a id="q3"></a>Q3. How long is a trip, and do vehicles return empty?

**Answer (Decision):** road trips average **1.75 km** and bike trips **1.6 km**. **Assumption:** deadhead 1.0, so every vehicle returns to Kendall empty.

**Discussion.** 1.75 km is the plain mean of the two Kendall road links (1.9 and 1.6 km, [Q2](#q2)); both Kendall bike links are 1.6 km. **Assumption:** the plain mean splits riders evenly between Lechmere and Central (Appendix B gives no destinations), and both ends are station coordinates, not real pickup and drop-off points. The empty return is conservative: half of all driving carries no one.

#### <a id="q4"></a>Q4. What average speed do road vehicles reach?

**Answer (Decision):** **the model caps road-vehicle average speed at 21 km/h (13 mph).**

**Discussion.** The posted limit inside the boundary is **20 mph (32 km/h)**. Kendall and Central are two of the five squares the City dropped from 25 to 20 mph in 2018 [[6]](references.md#ref-6), and Residential Safety Zones (2019–21) put about 80% of city streets at 20 mph [[7]](references.md#ref-7), [[9]](references.md#ref-9). Arterials keep the 25 mph citywide default unless posted lower [[7]](references.md#ref-7), [[8]](references.md#ref-8). Signals and congestion hold achieved speed well below posted, and no Kendall-specific measurement exists. The closest proxies: INRIX puts the average downtown Boston trip at 13 mph [[10]](references.md#ref-10), TomTom puts Boston's rush-hour average at 22.4 km/h [[11]](references.md#ref-11), and the MBTA #1 bus averages about 6 mph with its stops [[12]](references.md#ref-12). The cap binds for 55% of road variants, so bigger motors on small chassis rarely buy speed. **Sensitivity:** `outputs/task3_speed_sensitivity.md` reruns the model with the cap at the 20 mph posted limit (32.2 km/h).

#### <a id="q5"></a>Q5. What demand does the system serve?

**Answer (From OS3A):** the Kendall node only, with Appendix B demand as given.

**Discussion.** OS3A gives scale but no per-node demand: 74,000 employees, 6,878 daily Red Line riders at Kendall, and a mode split of 26% walk / 29% MBTA / 22% bike / 22% drive [[2]](references.md#ref-2), [[13]](references.md#ref-13). Appendix B's 1,790 trips/day is about 26% of Kendall T boardings, a plausible last-mile share.

#### <a id="q6"></a>Q6. How fast do e-bikes go?

**Answer (From OS3A; Deviation from Appendix B):** a **fixed assisted speed of 18 km/h**. The Appendix B formula's value is reported alongside it.

**Discussion.** Appendix B's `700·P/W` gives 5–8 km/h for a bike with a rider, which is unrealistic. 18 km/h is the low end of 18–20 km/h and under the 20 mph class 1/2 assist cap. The validation anchor is the OS3A interview [[14]](references.md#ref-14): South Station to Draper (2–2.5 mi) in a reliable 13–15 min, about 15–18 km/h door to door. An e-bike saves only about 3 min, because of traffic and red lights. **Sensitivity:** `outputs/task3_speed_sensitivity.md` reruns the model with the formula speed: availability rises (a slow bike drains its battery more slowly), but trips take 12–101 min.

#### <a id="q7"></a>Q7. What autonomy level is allowed?

**Answer (From OS3A):** A3 inside the boundary. A4 and A5 stay in the design vector for scenarios that leave the boundary. E-bikes have L4 built into the frame cost.

**Discussion.** Massachusetts law requires a human at the wheel [[20]](references.md#ref-20), no AV test permits are active, and Optimus Ride shut down in 2022 [[19]](references.md#ref-19). Public opposition to AVs is 75% statewide, against our MOE 5 target of under 25%.

#### <a id="q8"></a>Q8. Is accessibility screened?

**Answer (Decision):** no accessibility screen in the primary scenario.

**Discussion.** OS3A notes that no wheelchair-accessible AVs exist and that e-bikes serve no one with a mobility disability.

---

## 2. Task 1: multi-attribute utility

### Method

Each single-attribute utility (SAU) is piecewise linear between the Appendix A points and clamps outside the table. The SAUs combine into an additive multi-attribute utility (MAU):

$$U = \sum_i k_i\,u_i(x_i), \quad \sum k_i = 1$$

| Attribute | Appendix A weight |
| --- | ---: |
| Passenger volume (trips/day) | 0.15 |
| Peak throughput (trips/h) | 0.25 |
| Average wait at Kendall (min) | 0.35 |
| Availability | 0.25 |

### Hand calculation (Yonis)

For each segment of each SAU, the slope is U<sub>m</sub> = (U<sub>2</sub> − U<sub>1</sub>) / (x<sub>2</sub> − x<sub>1</sub>), and the point-slope equation is U = U<sub>1</sub> + U<sub>m</sub>(x − x<sub>1</sub>). Each case uses the equation for the segment its value falls in. This is the same linear interpolation the code uses, so the hand calculation and the code check each other.

**Passenger volume** (x = trips/day)

| Segment | x<sub>1</sub>–x<sub>2</sub> | U<sub>1</sub>–U<sub>2</sub> | Slope U<sub>m</sub> | Equation |
| --- | --- | --- | --- | --- |
| 1 | 0–500 | 0–0.2 | 0.0004 | U = 0.0004x |
| 2 | 500–1000 | 0.2–0.4 | 0.0004 | U = 0.2 + 0.0004(x − 500) |
| 3 | 1000–1500 | 0.4–0.8 | 0.0008 | U = 0.4 + 0.0008(x − 1000) |
| 4 | 1500–2000 | 0.8–1.0 | 0.0004 | U = 0.8 + 0.0004(x − 1500) |

Case A (1000) = 0.40 and Case B (2000) = 1.00 are table points. Case C (750), equation 2: 0.2 + 0.0004(750 − 500) = **0.30**.

**Peak throughput** (x = trips/h)

| Segment | x<sub>1</sub>–x<sub>2</sub> | U<sub>1</sub>–U<sub>2</sub> | Slope U<sub>m</sub> | Equation |
| --- | --- | --- | --- | --- |
| 1 | 0–50 | 0–0.2 | 0.004 | U = 0.004x |
| 2 | 50–100 | 0.2–0.5 | 0.006 | U = 0.2 + 0.006(x − 50) |
| 3 | 100–150 | 0.5–0.9 | 0.008 | U = 0.5 + 0.008(x − 100) |
| 4 | 150–200 | 0.9–1.0 | 0.002 | U = 0.9 + 0.002(x − 150) |

Cases A and C (75), equation 2: 0.2 + 0.006(75 − 50) = **0.35**. Case B (100) = 0.50 is a table point.

**Average wait** (x = minutes; utility falls as wait rises)

| Segment | x<sub>1</sub>–x<sub>2</sub> | U<sub>1</sub>–U<sub>2</sub> | Slope U<sub>m</sub> | Equation |
| --- | --- | --- | --- | --- |
| 1 | 0–5 | 1–0.95 | −0.01 | U = 1 − 0.01x |
| 2 | 5–10 | 0.95–0.75 | −0.04 | U = 0.95 − 0.04(x − 5) |
| 3 | 10–15 | 0.75–0.4 | −0.07 | U = 0.75 − 0.07(x − 10) |
| 4 | 15–20 | 0.4–0.2 | −0.04 | U = 0.4 − 0.04(x − 15) |
| 5 | 20–30 | 0.2–0 | −0.02 | U = 0.2 − 0.02(x − 20) |

Case A (8), equation 2: 0.95 − 0.04(8 − 5) = **0.83**. Case B (12), equation 3: 0.75 − 0.07(12 − 10) = **0.61**. Case C (6), equation 2: 0.95 − 0.04(6 − 5) = **0.91**.

**Availability** (U = x: slope 1 on every segment from 0 to 1)

Case A (0.7), equation 4: 0.6 + 1(0.7 − 0.6) = **0.70**. Case B (0.6) = 0.60 and Case C (0.8) = 0.80 are table points.

Austin's corrections to the first draft: wait-time equations had a + sign where the slope is negative, the throughput case B line had case A's formula, and two equations shared a number. All final values above were already right.

### Results

MAU<sub>A</sub> = 0.15 × 0.40 + 0.25 × 0.35 + 0.35 × 0.83 + 0.25 × 0.70 = **0.613**
MAU<sub>B</sub> = 0.15 × 1.00 + 0.25 × 0.50 + 0.35 × 0.61 + 0.25 × 0.60 = **0.639** (0.6385)
MAU<sub>C</sub> = 0.15 × 0.30 + 0.25 × 0.35 + 0.35 × 0.91 + 0.25 × 0.80 = **0.651**

| Case | Volume utility | Throughput utility | Wait utility | Availability utility | MAU |
| :--: | ---: | ---: | ---: | ---: | ---: |
| A | 0.40 | 0.35 | 0.83 | 0.70 | 0.613 |
| B | 1.00 | 0.50 | 0.61 | 0.60 | 0.639 |
| C | 0.30 | 0.35 | 0.91 | 0.80 | 0.651 |

The ranking is C > B > A. C has the lowest volume but ranks highest, because wait carries the largest weight (0.35) and C has the shortest wait. B has the highest volume but the longest wait and the lowest availability. All three are within about 0.04 of each other, so the ranking depends on the weights.

`src/os4/utility.py` reproduces every value (`evaluate_cases()`), and `python -m os4` writes the table to `outputs/task1_cases.md`.

### Validation

| Measure | Bounds | Direction | x → U | U → x | Cases A, B, C |
| --- | --- | --- | --- | --- | --- |
| Passenger volume | U = 0 at 0; U = 1 at 2000 trips/day | Increasing | All 5 table points | 0.40, 1.00, 0.30 → 1000, 2000, 750 | 0.40, 1.00, 0.30 |
| Peak throughput | U = 0 at 0; U = 1 at 200 trips/h | Increasing | All 5 table points | 0.35, 0.50, 0.35 → 75, 100, 75 | 0.35, 0.50, 0.35 |
| Average wait | U = 1 at 0; U = 0 at 30 min | Decreasing | All 6 table points | 0.83, 0.61, 0.91 → 8, 12, 6 | 0.83, 0.61, 0.91 |
| Availability | U = 0 at 0; U = 1 at 1.0 | Increasing (U = x) | All 6 table points | 0.70, 0.60, 0.80 → 0.7, 0.6, 0.8 | 0.70, 0.60, 0.80 |

Every check runs in `tests/test_utility.py`: table points, clamping to [0, 1], monotonicity, the case values (x → U), and the inverse (U → x, `utility.sau_inverse`). The MAU ranks a point that meets every Table 1 requirement (1500, 150, 5, 0.75) above each case. A sensitivity sweep moves each weight ±0.1 and shows where the A/B/C ranking flips.

**Test scenario: OS3A MOE 4 pickup wait (EZRide).** EZRide runs every 8–12 min [[18]](references.md#ref-18). On the wait curve, 8 and 12 min score 0.83 and 0.61, the same as Cases A and B. But 8–12 min is EZRide's **headway** (time between shuttles [[5]](references.md#ref-5)), not the wait. A rider arriving at a random time waits half the headway on average, so EZRide's average wait is **4–6 min**, U = 0.96–0.91: better than Cases A and B. The model's wait ([Q18](#q18)) uses the same headway / 2 rule.

### Weights and attributes

#### <a id="q9"></a>Q9. How do our OS3A MOEs map to the Appendix A attributes?

**Answer (From OS3A):** two direct or partial matches (wait, availability), two indirect (volume, throughput), and four MOEs with no counterpart, kept as screens or left out.

**Discussion.**
- **MOE 4 pickup wait (under 15 min)** ↔ average wait (0.35). Direct match. The targets differ: OS3A says 15 min, Table 1 says 5 min.
- **MOE 1 commute time and predictability** ↔ availability (partial). Reliability was the interviewee's top theme ("Red Line is the weakest link").
- **MOE 7 regional talent access** and **MOE 2 bike share** ↔ passenger volume and throughput (indirect).
- **MOE 3 serious crashes, MOE 5 AV opposition, MOE 6 stop announcements, MOE 8 curb access:** no Appendix A counterpart. MOE 3 and MOE 6 stay **pass/fail screens**, not weighted attributes, as in OS3A.

#### <a id="q10"></a>Q10. Should the team re-weight the Appendix A attributes?

**Answer (From OS3A):** yes, as a second weight set, `os3a_reweight`: volume 0.10, throughput 0.25, wait 0.35, availability 0.30. Task 3 plots both weight sets. In code: `data/mau_weights_proposed.csv`.

**Discussion.**

| Attribute | Appendix A | `os3a_reweight` | Why |
| --- | ---: | ---: | --- |
| Passenger volume | 0.15 | **0.10** | Traces only indirectly to our MOEs ([Q9](#q9)) |
| Peak throughput | 0.25 | 0.25 | |
| Average wait | 0.35 | 0.35 | Stays largest: MOE 4 is a direct match |
| Availability | 0.25 | **0.30** | Reliability (MOE 1) dominated the stakeholder evidence |

Case MAUs become A 0.628 / B 0.619 / C 0.676, so the ranking changes from C > B > A to **C > A > B**.

#### <a id="q11"></a>Q11. Should travel time be a weighted attribute?

**Answer (Decision, Austin, 2026-11-03):** no. The 7-minute requirement stays a pass/fail flag (`meets_travel_goal`), and the SAU is kept for a scenario with longer trips.

**Discussion.** Travel time traces to Table 1 (7 min maximum) [[1]](references.md#ref-1) and OS3A MOE 1, and has an SAU (`data/sau_travel_time.csv`: 0 → 1.0, 4 → 0.95, 7 → 0.8, 10 → 0.5, 15 → 0.2, 20 → 0). On Kendall trips it barely varies: a road vehicle at the speed cap takes 5.0 min and a bike 5.3 min. On the Pareto front it spans 5.0–6.6 min (SAU 0.90–0.82), at most 0.012 of MAU at a 0.15 weight. Only slow road variants score low, and their longer cycle already costs them throughput and wait. Every front architecture passes the 7-minute flag.

#### <a id="q12"></a>Q12. Should bike share be a weighted attribute?

**Answer (Decision, team, 2026-11-01):** no. Its SAU (`data/sau_bike_share.csv`) and the `bike_share` column are kept.

**Discussion.** It rewarded a type of solution (fleets with bikes) rather than an outcome, it doesn't match MOE 2 (commuters' own cycling), and it works against accessibility ([Q8](#q8)).

#### <a id="q13"></a>Q13. Should energy per passenger-km or fleet size be attributes?

**Answer (Decision, Austin, 2026-11-03):** no; both were removed.

**Discussion.**
- **Fleet size:** what matters is that vehicles beyond what demand needs only add cost, and cost is already the tradespace's other axis. Those fleets fall off the Pareto front on their own; a fleet-size SAU would count cost twice.
- **Energy per passenger-km:** it depended on every vehicle in service cycling all day whether or not anyone rides (the [Q18](#q18) assumption), so it measured that assumption more than the vehicles.

---

## 3. Task 2: system model

### Design vector

| Decision | Road options | Bike options |
| --- | --- | --- |
| Chassis / frame | C1–C8 | B1–B3 |
| Battery | P1–P7 (weight ≤ ⅓ chassis) | E1–E3 (weight ≤ ½ frame) |
| Charger | G1–G3 | G1–G2 |
| Motor | M1–M4 | K1–K3 |
| Autonomy | A3 / A4 / A5 | L4, built into the frame |
| Spare battery packs | — | none, or 0.5–3 per bike ([Q15](#q15)) |
| Fleet size | 1–300 | 5–250 |

After the battery-weight constraint, 1,548 road variants (43 chassis/battery pairs × 3 chargers × 4 motors × 3 autonomy levels) and 30 bike variants (5 frame/battery pairs × 2 chargers × 3 motors) are feasible.

#### <a id="q14"></a>Q14. Which architectures and fleet sizes are enumerated?

**Answer (Decision, team, revised 2026-11-01; bikes capped at 250, Austin, 2026-11-03):** each architecture has at most one road variant and one bike variant. Fleet sizes use steps that widen as fleets grow: **road 1–15 step 1, 20–50 step 5, 60–100 step 10, 125–300 step 25; bikes 5–50 step 5, 75–250 step 25.**

**Discussion.** The grid was revised from road 5–300 step 5 and bikes 25–750 step 25 because the EZRide anchor ([Q23](#q23)) showed that 1–4 bus fleets meet the thresholds below the old grid's cheapest point. Past the knee, cost rises linearly with N while utility is flat, so coarse steps there lose nothing. Bike fleets above 250 (the grid used to run to 750) only extended the flat tail of the front, so they were cut to shorten the run.

### Vehicle layer (`vehicle.py`)

Appendix B as given, for every feasible variant: total weight (+100 kg per passenger), cost, Wh/km, range, speed (capped, [Q4](#q4)), charge time, up-time = range / speed, down-time = charge time + 0.25 h, and availability = up-time / (up-time + down-time).

#### <a id="q15"></a>Q15. How can e-bikes reach useful availability?

**Answer (Decision, team, 2026-11-01; Deviation from Appendix B):** model both pathways: fixed batteries (Appendix B as given) and removable batteries swapped at the hub, with k spare packs per bike. This is our candidate for the rubric's "Above & Beyond: Excellency in Modeling".

**Discussion.** **E-bike availability is 0.14–0.42 under Appendix B,** far below the 0.75 benchmark. Small batteries (0.5–3 kWh) and slow chargers mean bikes charge much longer than they ride. **Assumption:** the formula assumes a vehicle rides nonstop until its battery is empty. Real bikes sit idle most of the day and could charge then, so it understates bike availability.

With removable batteries, a bike swaps packs in 5 min (**Assumption**) instead of charging in place, with k spare packs per bike pooled across the fleet (0.5, 1, 1.5, 2 or 3). Availability = min( U/(U+s), (1+k)·U/(U+s+C+0.25) ): the bike is limited either by the swap itself or by the supply of charged packs. Each spare adds its battery and a charger slot to the bike's cost. A B2 bike goes from 0.42 availability at $4,500 to 0.90 at $6,150 with 1.5 spares. **Decision (team, 2026-11-01):** swap labor is not counted ([Q21](#q21)), stated as a limitation.

#### <a id="q16"></a>Q16. How many riders does an e-bike carry per trip?

**Answer (Decision, Austin, 2026-11-01; Deviation from Appendix B):** **1-seat bikes (B1, B2) carry 1 rider; 2-seat bikes (B3) carry 2 riders every 3 trips** (4/3 riders, load factor 0.67) (`Scenario.bike_load_factors`). Road vehicles keep Appendix B's 0.75.

**Discussion.** Appendix B's 0.75 load factor gives a 1-seat bike 0.75 riders per trip, which is impossible: an on-demand bike only moves with someone on it, and its empty return is already the deadhead. The 2-seat share is optimistic, since most trips carry one person.

### Fleet layer (`fleet.py`)

Equations follow the *Fundamentals of Transportation* extracts in the appendix [[4]](references.md#ref-4), [[5]](references.md#ref-5).

- **Cycle time** = trip × (1 + deadhead) / speed + 60 s dwell. A road vehicle at 21 km/h: 2 × 1.75 km / 21 km/h = 10 min, plus 1 min dwell = 11 min.
- **Capacity per vehicle** = (60 / cycle time) × seats × load factor (0.75 for road; [Q16](#q16) for bikes).
- **Vehicles in service** = N × availability, since charging vehicles carry no one.
- **Fleet capacity** = Σ vehicles in service × capacity per vehicle.
- **Daily passenger volume** = Σ over the 2-hour demand bins of min(demand, capacity) × 2.
- **Fleet cost** = Σ vehicle cost × N.

#### <a id="q17"></a>Q17. What counts as peak throughput?

**Answer (Decision):** **the demand served,** min(capacity, peak demand), so it caps at 150 trips/h (U = 0.90).

**Discussion.** A fleet can't carry riders who aren't there, so capacity beyond demand earns no utility. Capacity alone is still used for the Table 1 thresholds.

#### <a id="q18"></a>Q18. How is the average wait computed?

**Answer (From OS3A; formula Decision):** an on-demand wait at the Kendall hub: wait = headway / 2 × 1 / (1 − ρ), where headway = 60 / departures per hour and ρ = demand / capacity, capped at 30 min and weighted by demand over the day. **Assumption:** every vehicle in service cycles all day, with no idle time or rebalancing.

**Discussion.** OS3A's MOE 4 covers demand-responsive pickups. Bikes return to the hub after each trip and use the same model. The EZRide anchor ([Q23](#q23)) shows the queue factor overstates the wait for large vehicles.

#### <a id="q19"></a>Q19. What does the availability attribute measure?

**Answer (Decision):** **service availability:** the chance that the vehicles in service can carry each 2-hour bin's demand, averaged over the day by demand. The Appendix B vehicle availability is still reported as `vehicle_availability`.

**Discussion.** Each vehicle is in service with its Appendix B availability a, independently, so capacity in service has mean Σ N·a·c and variance Σ N·a·(1−a)·c² (c = one vehicle's trips/h). The probability uses the normal approximation (Excel: `NORMSDIST`). Spare vehicles raise it, so a large pool of 42%-available bikes can still serve almost every rider.

#### <a id="q20"></a>Q20. How is travel time computed?

**Answer (Decision):** the average Kendall trip (1.75 km road, 1.6 km bike) ÷ speed, weighted by each part's share of trips.

**Discussion.** A capped road fleet takes 5.0 min, inside Table 1's 7-minute requirement. It is reported, not weighted ([Q11](#q11)).

#### <a id="q21"></a>Q21. What does cost include?

**Answer (Assumption):** vehicle capital only. Operating cost (staff, A3 attendants, battery-swap labor) is not modeled.

**Discussion.** MIT P&T's "not financially viable" concern and EZRide's funding from about 25 member firms are noted qualitatively.

### Feasibility screens

Architectures that fail a screen are dropped before scoring.

- **Table 1 thresholds:** at least 1,500 trips/day, 150 trips/h at the peak, and 50 trips/h off-peak. The "desired" goals (5-min wait, 7-min travel, 0.75 availability benchmark) are reported as pass/fail flags, not screens.
- **Utilization ceilings** ([Q22](#q22)).

#### <a id="q22"></a>Q22. How many rides per day can one vehicle realistically give?

**Answer (Decision, Austin, 2026-11-01):** **at most 15 riders per bike per day** and **at most 25 rides per car per day** (road chassis of 1–6 seats, C1–C3); no ceiling for shuttles and buses. The model reports riders per vehicle per day (`fleet.trips_per_vehicle_day`) and screens against the ceilings (`Scenario.max_bike_trips_per_day`, `Scenario.max_car_trips_per_day`).

**Discussion.** The model lets every vehicle cycle all day, so cheap fleets can claim more rides per vehicle than any real system.
- **Bikes:** Bluebikes run about 2.4–2.6 trips per bike per day (2024 [[28]](references.md#ref-28), [[29]](references.md#ref-29)), Citi Bike 3.3 (2024 [[25]](references.md#ref-25)) and 5.2 (2014 [[26]](references.md#ref-26)); 3–5 is typical. Citi Bike e-bikes ran about 15 a day in 2018 [[27]](references.md#ref-27), the busiest observed case.
- **Cars:** set at Waymo's observed rate of about 24 (250,000 paid rides a week [[32]](references.md#ref-32) on over 1,500 vehicles [[33]](references.md#ref-33), spring 2025). NYC yellow taxis ran 14.0 and Uber/Lyft 11.2 in 2024 [[31]](references.md#ref-31).
- **Shuttles and buses:** MBTA buses carry about 300–320 weekday riders per bus [[30]](references.md#ref-30), in line with the model.
- **Not adopted:** a utilization factor X on every architecture's capacity (the load-management ratio in the appendix).
- **Sensitivity:** `outputs/task3_speed_sensitivity.md` reruns the model with both ceilings off. Bike-only and small-car fleets shrink (75 bikes at 24 riders a day; 7 cars at 57 rides a day), and with removable batteries 40 bikes reach MAU 0.960 for $202,000 at 45 riders per bike per day.

### Anchors and architectures

#### <a id="q23"></a>Q23. Which of today's services anchor the tradespace?

**Answer (From OS3A; vehicle choice Decision):** EZRide, the MBTA bus and the MIT daytime shuttles, run through the same model and plotted on every tradespace (`data/anchors.csv`). Each uses the cheapest vehicle of the right size that reaches the speed cap and the 0.75 availability benchmark.

**Discussion.**

| Anchor | Basis | Model fleet | Cost | MAU | Meets thresholds |
| --- | --- | --- | --- | --- | --- |
| EZRide | Every 10 min, midpoint of 8–12 [[18]](references.md#ref-18) | 2 × C8-P1-G3-M4-A3 | $191,200 | 0.834 | Yes |
| MBTA bus | Every 15 min, frequent end of 15–30 [[17]](references.md#ref-17) | 1 × C8-P1-G3-M4-A3 | $95,600 | 0.365 | No (misses the peak) |
| MIT daytime shuttles | Known fleet of 5 [[15]](references.md#ref-15); 14 seats, so C6 (16 seats, **Assumption**) | 5 × C6-P1-G3-M3-A3 | $373,250 | 0.954 | Yes, but dominated |

**Finding: the EZRide anchor checks the wait model.** Its model headway is 6.9 min (headway / 2 = 3.5 min), but the reported wait is 10.1 min, because the 1 / (1 − ρ) queue factor triples it with two buses at 76% of capacity at the peak. Real EZRide riders wait about 4–6 min. The factor treats each bus as serving one rider at a time; a 30-seat bus boards everyone waiting, so the model overstates the wait for large vehicles.

#### <a id="q24"></a>Q24. Which five architectures go in the Task 2 table?

**Answer (Decision, Austin, 2026-11-01):**

| # | Fleet | Cost | MAU (Appendix A) |
| --- | --- | --- | --- |
| 1 | 24 × C2-P2-G3-M2-A3 (small cars) | $1,435,200 | 0.961 |
| 2 | 4 × C6-P4-G3-M3-A3 (large shuttles) | $350,600 | 0.946 |
| 3 | 150 × B2-E1-G2-K2 (bike-only) | $675,000 | 0.962 |
| 4 | 8 × C2-P2-G3-M2-A3 + 115 × B2-E1-G2-K2 (mixed) | $995,900 | 0.962 |
| 5 | 6 × C4-P5-G3-M2-A5 (A5, long range) | $784,800 | 0.893 |

**Discussion.** Fleets 1 and 4 (originally 12 × C2, and 8 × C2 + 60 × B2) failed the utilization ceilings ([Q22](#q22)) and were sized up with the same vehicles.

**Finding: large shuttles look cheapest** (4 × C6 for $351k vs. 24 × C2 for $1.44M), because Appendix B's 0.75 load factor fills a 16-seat shuttle with 12 riders per trip. For on-demand service at 150 trips/h that is optimistic, which is why Task 3 shows a load-factor sweep ([Q27](#q27)).

### Verification

- **Hand calculation:** one road and one bike variant worked by hand, matched by the code to 1e-9.
- **Robustness sweep:** every feasible variant × fleet size gives no NaN, inf or negative values, and availability stays in (0, 1).
- **Monotonicity:** throughput rises with N, wait falls with N, cost is linear in N, and N = 0 is handled.
- **Constraints:** infeasible battery/chassis pairs are excluded.
- **Vectorized model:** `tradespace.tradespace` matches `model.evaluate` on sampled architectures (`tests/test_tradespace.py`).

#### <a id="q25"></a>Q25. What tools carry the model?

**Answer (Decision):** **Python only,** with the Excel backup `outputs/media/os4_model.xlsx` (live formulas checked against Python) for the submission.

**Discussion.** Text responses go in the slide deck.

---

## 4. Task 3: tradespace

`tradespace.py` scores every architecture on the [Q14](#q14) grid: about 1.0 million feasible with fixed batteries and 2.1 million with removable batteries. Dominated vehicle variants are pruned first (e.g. a bigger motor with no speed gain), so every road vehicle in the space is A3. Both battery cases are plotted with the Appendix A MAU and with `os3a_reweight`.

| Case | Front (road / bike / mixed) | Cheapest feasible | First front point with MAU ≥ 0.94 |
| --- | --- | --- | --- |
| Fixed batteries | 3 / 12 / 411 | $182,200 | 2 × C8 + 20 × B1, 0.942 at $259,200 |
| Removable batteries | 3 / 19 / 417 | $182,200 | 2 × C8 + 20 × B1, 0.942 at $259,200 |

#### <a id="q26"></a>Q26. What is the Task 3 reference architecture?

**Answer (Decision, Austin):** **6 × C4-P2-G3-M2-A3** small on-demand shuttles, $430,800, MAU 0.932 (`model.reference_architecture`), chosen from design reasoning before reading the tradespace, as Task 3 asks.

**Discussion.**
- C4 (8 seats) is the "small on-demand EV shuttles from a central hub" MIT P&T asked for [[15]](references.md#ref-15), and avoids half-empty large shuttles.
- A3 is the minimum inside the boundary ([Q7](#q7)); M2 is the smallest motor that reaches the speed cap ([Q4](#q4)); G3 is the fastest charger, for availability; P2 is the smallest pack that covers a service day (about 18 h × 21 km/h ≈ 380 km).
- Fleet size from load management at the peak [[5]](references.md#ref-5): f ≥ 150 / (0.90 × 8 × 0.75) = 27.8 departures/h, so N = 27.8 × 11 min / 60 / 0.904 = 5.6 → 6. X = 0.90 is the textbook example's value.

On the tradespace the reference is **dominated:** 3 × C7 + 5 × B1 reach the same MAU for $254,950. The model can't see why the reference chose 8 seats: every road vehicle runs at the fixed 0.75 load factor, so a larger vehicle is always more capacity per dollar.

#### <a id="q27"></a>Q27. How sensitive is the front to the road load factor?

**Answer (Decision):** Appendix B's 0.75 stays the baseline, and one chart shows the Pareto front at 25 / 50 / 75 / 100% (`task3_load_factor_fronts.png`).

**Discussion.** 0.75 is optimistic for large on-demand vehicles ([Q24](#q24)). The sweep varies road vehicles only; bikes keep their riders per trip ([Q16](#q16)).

### Findings

- **The MAU levels off once demand is met.** Served throughput caps at 150 trips/h (U = 0.90) and volume at 1,790 trips/day (U = 0.916), and service availability is near 1 for almost every fleet that meets the thresholds. The Appendix A ceiling is 0.962 (0.967 with `os3a_reweight`). Past the knee, architectures differ only by seconds of wait, so the practical choice is the cheapest fleet that meets demand.
- **Both fronts are mostly small mixed fleets:** 1–3 buses or shuttles plus bikes.
- **MIT shuttles are dominated:** 3 × C7 + 20 × B1 match their MAU for $306,950, vs. $373,250.

---

## 5. Task 4: second operating scenario (candidates)

The candidates are presets in the Model Lab (`python -m os4.lab`, `src/os4/lab/presets.py`), each with its assumptions listed on the page; numbers marked PLACEHOLDER are for the team to set:

- **Red Line disruption, shuttle to Boston:** about 5 km trips outside the boundary, so A4/A5 only and Table 1's 20-min outside wait goal; peak demand ×1.5.
- **Point-to-point network:** trips between all three stops (average 2.27 km road), empty return 0.33.
- **Winter:** road cap 18 km/h, bike assist 12 km/h, battery range ×0.75 (new `Scenario.range_factor`).
- **A.m. rush only:** demand 6:00–12:00 only, volume threshold scaled to that window, ceilings off.

**Decision pending (team):** which candidate becomes the Task 4 scenario.

---


## Appendix: *Fundamentals of Transportation* extracts

Transcribed from the extracts appended to the assignment (OS4 PDF pp. 10–11) [[1]](references.md#ref-1), which reproduce sections of the Wikibooks *Fundamentals of Transportation* pages [[4]](references.md#ref-4), [[5]](references.md#ref-5). Wikibooks text is licensed CC BY-SA 4.0.

### Frequency determination (*Network Design and Frequency* [[4]](references.md#ref-4))

There are a number of ways that planners may determine a reasonable frequency of service on a route. The most common methods are:

- **Policy headways.** Many transit agencies will determine specific headways that meet policy goals, usually related to providing a minimum level of service along a route when demand on the route is low. This could include 30-minute or 60-minute headways, for example.
- **Minimum headways.** As discussed in the unit on transit operations, bus and rail systems have minimum headways, based on capacity limitations. In cases when demand on a route is very high, these minimum headways can be used to assign the maximum frequencies on the route.
- **Load management.** In many cases where policy headways or minimum headways do not apply, the typical way of determining frequencies is based on managing load at the *peak load point* along the route. The peak load point is that point along the route that experiences the largest number of passengers per hour. Let X be the highest allowable ratio of demand to supply (volume to capacity), with values between 0 and 1 (with 1 when volume = capacity). Then:

$$\frac{P}{f \cdot N_{car} \cdot C_{car}} \le X \quad\text{or}\quad f \ge \frac{P}{X \cdot N_{car} \cdot C_{car}}$$

with P = volume at peak load point (passengers/hr); X = maximum allowable volume-to-capacity ratio, 0 ≤ X ≤ 1; N<sub>car</sub> = number of cars in a train (= 1 for buses); C<sub>car</sub> = number of passengers per car.

For a bus route operated with 55-passenger buses, a demand of 360 passengers per hour past the peak load point, and an allowable load factor of X = 0.90, the frequency must be

$$f \ge \frac{360\ \text{passengers/hr}}{0.90 \cdot 1 \cdot (55\ \text{passengers/bus})} = 7.27\ \text{buses/hr}$$

This would give the planner options for this route such as 7.5 buses/hr (8-min headways) or 8 buses/hr (7.5-min headways), or even higher frequencies.

### Capacity (*Transit Operations and Capacity* [[5]](references.md#ref-5))

Capacity in transit operations is measured as the maximum number of passengers that can be carried past a single point on a fixed route, in a given period of time. The most common measure of capacity is in terms of passengers per hour.

In transit operations, we define the time between vehicles past a given point as the *headway* (or time headway), usually in minutes. The inverse of the headway is called the *frequency*, essentially capturing the number of vehicles per unit time past a certain point on a route, usually measured in vehicles per hour.

$$\text{Frequency (veh/hr)}\quad f = \frac{60\ \text{min/hr}}{h} \qquad\qquad \text{Headway (in min)}\quad h = \frac{60\ \text{min/hr}}{f}$$

As an example, a route with a 10-minute headway has a frequency of 6 vehicles per hour.

With this in mind, the capacity of a transit route is given as the product of the frequency and the maximum number of persons per vehicle:

$$\text{Capacity (passengers/hr) on the route} = C_{route} = f \cdot N_{car} \cdot C_{car}$$

where f = frequency on the route (veh/hr); N<sub>car</sub> = number of cars per train (= 1 for bus); C<sub>car</sub> = maximum number of persons per car (or bus).

As examples, a bus route with a frequency of 6 buses/hr and a maximum of 55 persons on each bus has a capacity of 330 passengers per hour. A rail line with a frequency of 15 trains/hr (4 min headways) with 6 cars per train and a maximum of 150 persons per car has a capacity of 13,500 passengers per hour.

### Sample problem (*Transit Operations and Capacity* [[5]](references.md#ref-5))

**Problem:** A transit agency has an existing 8.5-mile bus route (in one direction) where the average speed "between" stops is 16.9 miles per hour. The route has 22 stops along the route. If the average dwell time at each stop is 18 seconds, what is the average bus speed along the route as a whole? And, if a 5-minute layover is required at the far end of the route, what is the total round-trip travel time? Assume the time for the inbound trip is identical in time to the outbound trip.

**Solution:**
- Total travel time = (8.5 mi) / (16.9 mi/hr) + (22 stops)·(18 sec/stop)·(1 hr / 3600 sec) = 0.613 hr = 37 minutes (rounded up to the nearest minute)
- The average speed = (8.5 mi / 0.613 hr) = 13.9 mph.
- The total round-trip time = 37 min + 5 min layover + 37 min = 79 min

### How the model uses these

- **Capacity:** `fleet.vehicle_capacity_per_h` is C<sub>route</sub> = f · N<sub>car</sub> · C<sub>car</sub> per vehicle, with f = 60 / cycle time, N<sub>car</sub> = 1, and C<sub>car</sub> = seats × the vehicle's load factor: Appendix B's 0.75 for road vehicles; for e-bikes, riders per trip by seats ([Q16](#q16)).
- **Cycle time:** `fleet.cycle_time_min` follows the sample problem: running time at the average speed plus dwell, with the empty return leg in place of the inbound trip ([Q3](#q3)).
- **Headway:** the wait model ([Q18](#q18)) starts from headway / 2, with headway = 60 / departures per hour at the Kendall hub.
- **Fleet sizing:** load management gives departures needed f ≥ P / (X · 1 · C<sub>car</sub>) and vehicles needed N = f × cycle / 60 / availability. For the C2 car (4 seats × 0.75 = 3 riders per trip, 11-min cycle, availability 0.922) at P = 150 trips/h: X = 1 gives f ≥ 50/h and N = 10, the capacity-only minimum; X = 0.8 gives f ≥ 62.5/h and N = 13. The model uses X = 0.90 only to size the reference architecture ([Q26](#q26)); the utilization ceilings ([Q22](#q22)) screen out overworked fleets instead, so the smallest feasible C2 fleet is 24, not 10.
- The *Network Design and Frequency* page also gives Mohring's cost-minimizing frequency, f = √(VOT · p / (2 · C · T)), which trades waiting time against operating cost. It is not in the assignment's extracts, and we don't model operating cost ([Q21](#q21)).
