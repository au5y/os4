# Game plan: Tasks 1 & 2

Sources are tagged in line by number, e.g. [[1]](references.md#ref-1), and listed in [references.md](references.md).

# Task 1 approach:
-- Determine SAU function(s). I used the slope and point slope form to come up with SAU function. 
 Note that SAU function is the rule that I used to measure x into a utility score (U). 

# Passenger trips/day SAU function( x = trips/day) & U<sub>m</sub> means utility slope 
 | x1   |   x2 | U1  |  U2 |
 | :--- | ---: | :-- | --: |
 | 0    |  500 | 0   | 0.2 |
 | 500  | 1000 | 0.2 | 0.4 |
 | 1000 | 1500 | 0.4 | 0.8 |
 | 1500 | 2000 | 0.8 | 1.0 |

For the purposes of validation, calculate the function formula for changes X & change U:

+ 0 to 500 -- U<sub>m</sub> (0.2-0)/(500-0) = 0.0004 | equation <sub>1</sub> -- U = 0.0004x (AM: slopes are plain numbers, so I dropped the trailing "x" from every U<sub>m</sub> in this doc; the "x" belongs only in the equations)

+ 500 to 1000 -- U<sub>m</sub> (0.4-0.2)/(1000-500) = 0.0004 | equation <sub>2</sub> -- U = 0.2 + 0.0004 (x - 500) 

+ 1000 to 1500 -- U<sub>m</sub> (0.8-0.4)/(1500-1000) = 0.0008 | equation <sub>3</sub> -- U = 0.4 + 0.0008 (x - 1000)

+ 1500 to 2000 -- U<sub>m</sub> (1.0-0.8)/(2000-1500) = 0.0004 | equation <sub>4</sub> --  U = 0.8 + 0.0004 (x - 1500)

From the above SAU functions, we can deviate U<sub>case c</sub> at 750 passenger trips/day 

750 is between 500 to 1000, use equation <sub>2</sub> to calculate U<sub>case c</sub>

U<sub>case c</sub> = 0.2 + 0.0004(750-500) = 0.3

+ U<sub>case a</sub> = 0.4 @ 1000 passenger trips/day ** In appendix A

+ U<sub>case b</sub> = 1.0 @ 2000 passenger trips/day ** in appendix A

+ U<sub>case c</sub> = 0.3 @ 750 passenger trips/day ** Calculated 

# Peak passenger throughput SAU function( x = passenger trips/hour) & U<sub>m</sub> means utility slope 
 | x1  |  x2 | U1  |  U2 |
 | :-- | --: | :-- | --: |
 | 0   |  50 | 0   | 0.2 |
 | 50  | 100 | 0.2 | 0.5 |
 | 100 | 150 | 0.5 | 0.9 |
 | 150 | 200 | 0.9 | 1.0 |

For the purposes of validation, calculate the function formula for changes X & change U:

+ 0 to 50 -- U<sub>m</sub> (0.2-0)/(50-0) = 0.004 | equation <sub>1</sub> -- U = 0.004x

+ 50 to 100 -- U<sub>m</sub> (0.5-0.2)/(100-50) = 0.006 | equation <sub>2</sub> -- U = 0.2 + 0.006 (x - 50) 

+ 100 to 150 -- U<sub>m</sub> (0.9-0.5)/(150-100) = 0.008 | equation <sub>3</sub> -- U = 0.5 + 0.008 (x - 100)

+ 150 to 200 -- U<sub>m</sub> (1.0-0.9)/(200-150) = 0.002 (AM: i think slope is wrong as written, U1 here is 0.9 not 0.0; 0.002 is right) | equation <sub>4</sub> --  U = 0.9 + 0.002 (x - 150)

From the above SAU functions, we can deviate U<sub>case a</sub> at 75 passenger trips/hour & U<sub>case c</sub>  at 75 passenger trips/hour 

75 is between 50 to 100, use equation <sub>2</sub> to calculate U<sub>case a</sub> & U<sub>case c</sub>

# Peak passenger throughput (passenger trips/hour)

U<sub>case a</sub> = 0.2 + 0.006(75-50) = 0.35 ** Calculated

U<sub>case b</sub> = 0.5 @ 100 passenger trips/hour ** in appendix A (AM: this line had case A's formula copied in; 100 is a table point so no equation is needed)

U<sub>case c</sub> = 0.2 + 0.006(75-50) = 0.35 ** calculated

# Average wait time, at MIT/kendall square node (minutes) SAU function( x = minutes) & U<sub>m</sub> means utility slope 
 | x1  |  x2 | U1   |   U2 |
 | :-- | --: | :--- | ---: |
 | 0   |   5 | 1    | 0.95 |
 | 5   |  10 | 0.95 | 0.75 |
 | 10  |  15 | 0.75 |  0.4 |
 | 15  |  20 | 0.4  |  0.2 |
 | 20  |  30 | 0.2  |    0 |

For the purposes of validation, calculate the function formula for changes X & change U:

+ 0 to 5 -- U<sub>m</sub> (0.95-1)/(5-0) = -0.01 | equation <sub>1</sub> -- U = 1 - 0.01x

+ 5 to 10 -- U<sub>m</sub> (0.75-0.95)/(10-5) = -0.04 | equation <sub>2</sub> -- U = 0.95 - 0.04 (x - 5) 

+ 10 to 15 -- U<sub>m</sub> (0.4-0.75)/(15-10) = -0.07 | equation <sub>3</sub> -- U = 0.75 - 0.07 (x - 10)

+ 15 to 20 -- U<sub>m</sub> (0.2-0.4)/(20-15) = -0.04 | equation <sub>4</sub> --  U = 0.4 - 0.04 (x - 15)

+ 20 to 30 -- U<sub>m</sub> (0-0.2)/(30-20) = -0.02 | equation <sub>5</sub> (AM: was numbered 4 twice) --  U = 0.2 - 0.02 (x - 20)

From the above SAU functions, we can derive U<sub>case a</sub> at 8 min, U<sub>case b</sub> at 12 min & U<sub>case c</sub> at 6 min (AM: this line was copied from the throughput section, which said 75 passenger trips/hour)

8 is between 5 to 10, use equation <sub>2</sub> to calculate U<sub>case a</sub> 
12 is between 10 to 15, use equation <sub>3</sub> to calculate U<sub>case b</sub> 
6 is between 5 to 10, use equation <sub>2</sub> to calculate U<sub>case c</sub> 

# Average wait time ( minutes)

U<sub>case a</sub> = 0.95 - 0.04(8-5) = 0.83 (AM: sign was +, slope is negative; 0.83 is right) ** Calculated

U<sub>case b</sub> = 0.75 - 0.07(12-10) = 0.61 (AM: sign was +, slope is negative; 0.61 is right) ** Calculated

U<sub>case c</sub> = 0.95 - 0.04(6-5) = 0.91 (AM: sign was +, slope is negative; 0.91 is right) ** calculated

# Availability (dml4)
 | x1  |  x2 | U1  |  U2 |
 | :-- | --: | :-- | --: |
 | 0   | 0.2 | 0   | 0.2 |
 | 0.2 | 0.4 | 0.2 | 0.4 |
 | 0.4 | 0.6 | 0.4 | 0.6 |
 | 0.6 | 0.8 | 0.6 | 0.8 |
 | 0.8 | 1.0 | 0.8 | 1.0 |

+ 0 to 0.2 -- U<sub>m</sub> (0.2-0)/(0.2-0) = 1 | equation <sub>1</sub> -- U = 0 + 1(x-0)
+ 0.2 to 0.4 -- U<sub>m</sub> (0.4-0.2)/(0.4-0.2) = 1 | equation <sub>2</sub> -- U = 0.2 + 1(x-0.2)
+ 0.4 to 0.6 -- U<sub>m</sub> (0.6-0.4)/(0.6-0.4) = 1 | equation <sub>3</sub> -- U = 0.4 + 1(x-0.4)
+ 0.6 to 0.8 -- U<sub>m</sub> (0.8-0.6)/(0.8-0.6) = 1 | equation <sub>4</sub> -- U = 0.6 + 1(x-0.6)
+ 0.8 to 1 -- U<sub>m</sub> (1-0.8)/(1-0.8) = 1 | equation <sub>5</sub> -- U = 0.8 + 1(x-0.8)

From the above SAU functions, we can derive U<sub>case a</sub> at 0.7, U<sub>case b</sub> at 0.6 & U<sub>case c</sub> at 0.8 availability (dml4).

0.7 is between 0.6 to 0.8, use equation <sub>4</sub> to calculate U<sub>case a</sub> 

U<sub>case a</sub> = 0.6 + 1(0.7-0.6) = 0.7 ** Calculated

U<sub>case b</sub> = 0.6 ** in appendix A

U<sub>case c</sub> = 0.8 ** in appendix A

**Table 1: Attribute weights**

| Attribute        | Weight |
| :--------------- | -----: |
| Passenger volume |   0.15 |
| Peak throughput  |   0.25 |
| Average wait     |   0.35 |
| Availability     |   0.25 |

# Multi-attribute utility (MAU)
For reference: *w* = weight; *U* = utility score.

**Formula**

MAU = *w*<sub>volume</sub> × *U*<sub>volume</sub> + *w*<sub>peak throughput</sub> × *U*<sub>peak throughput</sub> + *w*<sub>average wait</sub> × *U*<sub>average wait</sub> + *w*<sub>availability</sub> × *U*<sub>availability</sub>

MAU<sub>case a</sub> = (0.15) × (0.40) + (0.25) × (0.35) + (0.35) × (0.83) + (0.25) × (0.70) = 0.613

MAU<sub>case b</sub> = (0.15) × (1.00) + (0.25) × (0.50) + (0.35) × (0.61) + (0.25) × (0.60) = 0.6385 ≈ 0.639

MAU<sub>case c</sub> = (0.15) × (0.30) + (0.25) × (0.35) + (0.35) × (0.91) + (0.25) × (0.80) = 0.651

# Final results

**Table 2: Utility scores and MAU for Cases A, B, and C**

| Case | Passenger volume utility | Peak throughput utility | Average wait utility | Availability utility |   MAU |
| :--: | -----------------------: | ----------------------: | -------------------: | -------------------: | ----: |
|  A   |                     0.40 |                    0.35 |                 0.83 |                 0.70 | 0.613 |
|  B   |                     1.00 |                    0.50 |                 0.61 |                 0.60 | 0.639 |
|  C   |                     0.30 |                    0.35 |                 0.91 |                 0.80 | 0.651 |

`src/os4/utility.py` reproduces every value in Table 2 (`evaluate_cases()`; checked in `tests/test_utility.py`). `python -m os4` writes the computed table to [outputs/task1_cases.md](../outputs/task1_cases.md) (this will only link if the code has been run).

# For Task 1 - validation 

Here are my thoughts 
    1. Incorporate test scenarios 
        - Use MOE # 1, 4, , & 8 to test and analyze the Utility outcome. 
    2. We can use the equations and reproduce the data - we can either start with x and look for U or the other way around.

# Our MOEs from OS-3 assignment. - Test scenarios
 MOE #4 pickup waits:
   - EZride shuttle 8- 12 minutes 
        - Start with the lower end of the range of wait times @ 8 minutes. 
        
            I am going to reference equation <sub>2</sub> 0.95 - 0.04 (x - 5) since 8 minutes is between 5- 10 minutes. 

        U <sub>@ 8 minutes test</sub> = 0.95 - 0.04 (8 - 5) = 0.83

      - Start with the upper end of the range of wait times @ 12 minutes. I am going to reference equation <sub>3</sub> U = 0.75 - 0.07 (x - 10) since 12 minutes is between 10- 15 minutes. 

      U <sub>@ 12 minutes test</sub> = 0.75 - 0.07 (12 - 10) = 0.61

- Across the range from 8 to 12 minutes pickup wait time, utility drops by 0.83 - 0.61 = 0.22 ** important for us to note in the write up. Our MOE #4 EZride wait times are also wait times for Case A and Case B. Therefore scenario is valid. 

  (AM: EZRide's 8–12 minutes is a *headway*, how often a shuttle comes [[18]](references.md#ref-18), not how long a rider waits. The *Transit Operations and Capacity* page defines headway as "the time between vehicles past a given point" [[5]](references.md#ref-5) (see the Appendix). A rider who arrives at a random time waits on average half the headway, so EZRide's average wait is about **4–6 minutes**, not 8–12. On equation <sub>1</sub>/<sub>2</sub> that is U = 1 − 0.01(4) = **0.96** at 4 min and U = 0.95 − 0.04(6 − 5) = **0.91** at 6 min. So EZRide scores *better* than Cases A (0.83) and B (0.61), not the same; the 8- and 12-minute utilities above are correct for Cases A and B but don't represent EZRide. Our OS3A MOE #4 baseline lists EZRide "every 8–12 min", which is where the headway got read as a wait. The model's wait time (Q12) uses the same headway / 2 rule.)

SAU function validation Table 4

| Measure | Utility bounds | Direction | Equation check (x → U) | Inverse check (U → x) | Cases (A, B, C) |
|----------|----------|----------|----------|----------|----------|
| Passenger volume | U = 0 at 0 trips/day; U = 1 at 2000 trips/day | Increasing | Returns all 5 points in the Appendix A table | U = 0.40, 1.00, 0.30 → 1000, 2000, 750 | 1000 → 0.40; 2000 → 1.00; 750 → 0.30 |
| Peak throughput | U = 0 at 0 trips/hr; U = 1 at 200 trips/hr | Increasing | Returns all 5 points in the Appendix A table | U = 0.35, 0.50, 0.35 → 75, 100, 75 | 75 → 0.35; 100 → 0.50; 75 → 0.35 |
| Average wait time | U = 0 at 30 min; U = 1 at 0 min | Decreasing | Returns all 6 points in the Appendix A table | U = 0.83, 0.61, 0.91 → 8, 12, 6 | 8 → 0.83; 12 → 0.61; 6 → 0.91 |
| Availability | U = 0 at 0; U = 1 at 1.0 | Increasing (U = x) | Returns all 6 points in the Appendix A table | U = 0.70, 0.60, 0.80 → 0.7, 0.6, 0.8 | 0.7 → 0.70; 0.6 → 0.60; 0.8 → 0.80 |
| MOE #4 pickup wait time (EZRide) | Same curve as average wait time: U = 1 at 0 min; U = 0 at 30 min | Decreasing | Headways of 8 and 12 min give U = 0.83 and 0.61, the same as Cases A and B; as average waits (half the headway, 4–6 min) U = 0.96–0.91 | U = 0.96, 0.91 → 4, 6 min | Headway 8, 12 min → average wait 4, 6 min |

Every check is automated in `tests/test_utility.py`: table points (`test_sau_reproduces_table_points`), bounds (`test_sau_clamps_to_unit_interval`), direction (`test_sau_is_monotone`), x → U for the cases (`test_case_saus_match_hand_calc`), and U → x with `utility.sau_inverse` (`test_sau_inverse_recovers_case_inputs`, plus `test_sau_inverse_round_trips` over each whole curve). The inverse also reads targets off a curve: U = 0.9 needs 1,750 trips/day, 150 trips/hr, a 6.25 min wait, or 0.9 availability.

(AM: Yonis added the MOE #4 row in parallel; merged here. Its bounds and direction follow the wait-time curve (U falls from 1 at 0 min to 0 at 30 min), and EZRide's 8–12 min are headways, so its average wait is 4–6 min; see the note under the MOE #4 check above.)



**How to use this doc:** open questions for the team are marked **❓ Q#**. Write the decision under **Answer:** (replace _TBD_) and initial it. Lines marked **decided (from OS3A)** adopt the answer proposed by `resources/OS3A_H2_Team13.pdf` [[2]](references.md#ref-2); override them if the team disagrees.

---

## Team decisions needed first (these block Task 2)

D1–D6 are complete (✅): the default shown is the decision the team agreed on, with details in Q1–Q6 (D5: fixed 18 km/h e-bike assist; D6: A3 inside the boundary).

| #   | Decision                                                                                       | Why it matters                                                              | Suggested default                                                                                                                            |
| --- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 ✅ | **Service-area boundary and node network** (Lechmere/Cambridge Crossing, Kendall/MIT, Central) | Sets trip distances, which set cycle time, throughput and wait              | 3 nodes. Measured road distances: Lechmere–Kendall 1.9 km, Kendall–Central 1.6 km, Lechmere–Central 3.3 km (see Q1).                        |
| D2 ✅ | **Primary operating scenario** (pull from an OS3 report, with a sentence on why)               | The model has to show it meets this scenario                                | Weekday a.m.-peak, on-demand last-mile service from a Kendall hub to Lechmere and Central, using small road EVs and/or e-bikes; demand from Appendix B (see Q2). |
| D3 ✅ | **Speed limit and achieved speed**                                                             | Caps average road speed; at a ~21 km/h cap about half the road variants hit it, so bigger motors buy no speed | Posted 20 mph (32 km/h) in Kendall and Central squares and on most local streets; arterials 25 mph unless posted. Signals and congestion hold peak speeds near 13 mph (~21 km/h), so use that as the average-speed cap. See Q3. |
| D4 ✅ | **Demand outside MIT/Kendall**                                                                 | Appendix B only gives Kendall-origin demand                                 | Model Kendall only as the design node (where the SAU wait time is measured) and use the Appendix B demand as is (see Q4).        |
| D5 ✅ | **What the e-bike speed equation does**                                                        | `700·P/W` gives about 5–8 km/h for bikes with a rider, which is unrealistic | Add rider pedal power (~0.1 kW) or use a fixed assisted speed (~18–20 km/h, under the 20 mph class-1/2 cap). Must be justified on the slide. |
| D6 ✅ | **Autonomy level vs. scenario**                                                                | The constraints tie L3/L4/L5 to where vehicles operate [[1]](references.md#ref-1), [[3]](references.md#ref-3)                      | Primary scenario inside the boundary → A3 allowed. Leave A4/A5 in the vector for the Task 4 scenario that goes outside the boundary.         |

## Assumptions Made

> **Q1 / D1, decided (boundary from OS3A; distances measured):** The OS3A boundary (Fig. 1) [[2]](references.md#ref-2) runs from Central Sq in the west, north through East Cambridge, east to Cambridge Crossing, and south along the Charles/MIT. That matches the assignment, so the **boundary is settled.** OS3A also puts South Station/Boston in the *context* boundary, which is outside the system. That is useful for a Task 4 scenario.

> **Node distances (measured Nov. 1, 2026).** Station coordinates from OpenStreetMap via Nominatim [[22]](references.md#ref-22): Lechmere 42.37128, −71.07615; Kendall/MIT 42.36242, −71.08572; Central 42.36532, −71.10356. Road and bike routes from OSRM on OpenStreetMap data [[23]](references.md#ref-23), [[24]](references.md#ref-24), both directions (one-way streets make them differ). Road vehicles use the mean of the two driving directions; bikes use the mean of the two bike directions (1.6 / 1.6 / 3.1 km).
>
> | Pair | Straight line | Drive (each direction) | Bike (each direction) | **Model distance** | Time at 21 km/h |
> | --- | --- | --- | --- | --- | --- |
> | Lechmere–Kendall | 1.26 km | 1.65 / 2.11 km | 1.58 / 1.63 km | **1.9 km** | 5.4 min |
> | Kendall–Central | 1.50 km | 1.60 / 1.60 km | 1.64 / 1.63 km | **1.6 km** | 4.6 min |
> | Lechmere–Central | 2.35 km | 3.62 / 2.91 km | 2.99 / 3.17 km | **3.3 km** | 9.4 min |
>
> **Finding:** Lechmere–Central breaks the 7-minute in-boundary travel-time requirement [[1]](references.md#ref-1) at the ~21 km/h achieved speed (Q3): 8.3 min even in the shorter direction. Meeting it needs ~28 km/h average on that link, which needs dedicated lanes or signal priority on that link (routing via Kendall is longer, 3.5 km). Google Maps was not checked (no API key).

> **Q2 / D2, decided (from OS3A):** OS3A points to **weekday a.m.-peak last-mile service from Kendall T** (MOE 1 sets the a.m. peak as its measurement condition; MOE 4 covers demand-responsive pickups). MIT P&T [[15]](references.md#ref-15) asked for *"small on-demand EV shuttles from a central hub"* and warned that empty shuttles are not financially viable. Proposal: on-demand small road EVs and/or e-bikes from a Kendall hub serving Lechmere and Central. OS3B is not in the repo yet; check whether it suggests something different.

> **Q3 / D3, decided:** The posted limit is **20 mph (32 km/h) inside our boundary**. Kendall and Central are two of the five squares the City dropped from 25 to 20 mph in 2018 (Safer Squares) [[6]](references.md#ref-6), and Residential Safety Zones (2019–21) put about 80% of city streets at 20 mph under MGL c.90 §18B [[7]](references.md#ref-7), [[9]](references.md#ref-9). Arterials stay at the 25 mph citywide default (Cambridge opted into MGL c.90 §17C in 2016 [[7]](references.md#ref-7); Cambridge Traffic Regulations §5.1 [[8]](references.md#ref-8)) unless posted lower, and state-run DCR roads such as Memorial Drive keep their own limits.
> **Achieved speed is lower than posted** because of the traffic signals and congestion. No Kendall-specific measurement exists, so use the closest proxies: INRIX's 2024 scorecard puts the average downtown Boston trip at 13 mph [[10]](references.md#ref-10); TomTom puts Boston's rush-hour average at 22.4 km/h ≈ 13.9 mph [[11]](references.md#ref-11); and the MBTA #1 bus on Mass Ave, with its stops, averages about 6 mph [[12]](references.md#ref-12). **Model choice:** cap road-vehicle average speed at ~21 km/h (13 mph) in the primary scenario and show 32 km/h (the posted limit, e.g. dedicated lanes with signal priority) as a sensitivity. Bikes use the fixed assisted speed from Q5 (18–20 km/h), which is already below the posted limit and the 20 mph class 1/2 e-bike assist cap.

> **Q4 / D4, decided (from OS3A):** Model the Kendall node only and use the Appendix B demand as is. OS3A gives scale but no per-node demand: 74,000 employees, 6,878 daily Red Line riders at Kendall, and a mode split of 26% walk / 29% MBTA / 22% bike / 22% drive [[2]](references.md#ref-2), [[13]](references.md#ref-13). Appendix B's ~1,790 trips/day is about 26% of Kendall T boardings, so it reads as a plausible last-mile capture. We can cite that as validation for using Appendix B as is.

> **Q5 / D5, decided (from OS3A):** Use a fixed assisted e-bike speed of ~18–20 km/h instead of the formula, and show the formula value alongside it on the slide. **OS3A gives us a validation anchor.** The interviewee [[14]](references.md#ref-14) rides South Station → Draper (2–2.5 mi) in a reliable 13–15 min, about **15–18 km/h door to door**, and an e-bike saves only ~3 min because of traffic and red lights. That supports a **fixed assisted speed of ~18–20 km/h** over the formula. The interview also says e-bikes help most on inclines and for riders with injuries, which is the comfort and accessibility case for bikes.

> **Q6 / D6, decided (from OS3A):** OS3A's constraints are the real problem here: MA law requires a human at the wheel [[20]](references.md#ref-20), no AV test permits are active, and Optimus Ride shut down in 2022 [[19]](references.md#ref-19). Public opposition to AVs is 75% statewide against our MOE 5 target of under 25%. L3 road vehicles need dedicated lanes, but OS3A found bike and curb lanes routinely blocked by trucks and rideshares. Proposal: A3 inside the boundary for the primary scenario, with A4/A5 only in the Task 4 scenario. Flag deployment realism for Task 5. E-bikes come with L4 built in and ride in the already-growing bike network, which is a point in their favor.

---

## Task 1: MAU (1 slide + backup)

**Method** (from lecture, MATE): piecewise-linear SAUs that interpolate the Appendix A points and clamp outside the table range, combined into an **additive weighted MAU**:

$$U = \sum_i k_i\,u_i(x_i), \quad \sum k_i = 1$$

with k = {volume 0.15, peak 0.25, wait 0.35, availability 0.25} (Yonis's Table 1).

**Hand calculation (Yonis, "Task 1 approach" at the top of this doc).** For each SAU, Yonis wrote one point-slope equation per table segment, U = U<sub>1</sub> + U<sub>m</sub>(x − x<sub>1</sub>) with slope U<sub>m</sub> = (U<sub>2</sub> − U<sub>1</sub>)/(x<sub>2</sub> − x<sub>1</sub>), then used the equation for the segment each case falls in. This is the same linear interpolation the code uses, so the two are independent checks of each other:

| Case value | How Yonis got it | Code / workbook |
| --- | --- | --- |
| Volume A (1000), B (2000); throughput B (100); availability B (0.6), C (0.8) | Read directly from Appendix A (table points) | `test_sau_reproduces_table_points` |
| Volume C (750) | Equation 2: 0.2 + 0.0004(750 − 500) = 0.30 | `sau()` gives 0.30 |
| Throughput A, C (75) | Equation 2: 0.2 + 0.006(75 − 50) = 0.35 | `sau()` gives 0.35 |
| Wait A (8), B (12), C (6) | Equations 2, 3, 2: 0.83, 0.61, 0.91 | `sau()` gives 0.83, 0.61, 0.91 |
| Availability A (0.7) | Equation 4: 0.6 + 1(0.7 − 0.6) = 0.70 | `sau()` gives 0.70 |

The slope column on the workbook's SAU sheet reproduces every U<sub>m</sub> in Yonis's equations, and the code reproduces his Table 2 exactly: **A 0.613, B 0.639 (0.6385 unrounded), C 0.651**, ranking C > B > A. Use Yonis's Table 2 as the results table on the slide.

**Interpretation for the slide.** C has the lowest volume yet ranks highest, because wait time carries the largest weight (0.35) and C has the shortest wait. B has the highest volume but the longest wait and lowest availability. All three cases fall within about 0.04 of each other, so the ranking depends on the weights (see the sensitivity check below).

**Code: `src/os4/utility.py`**
- `sau(attribute, x)`: `np.interp` over the `sau_*.csv` points (handles the decreasing wait curve; clamps automatically).
- `mau(volume, peak, wait, availability, weights=None)`: vectorized so the tradespace can call it on arrays.
- `evaluate_cases()`: returns a DataFrame for `mau_test_cases.csv`.
- `load_weights(weight_set)`, `compare_weight_sets()` and `weighted_mau(values, weights)`: the Appendix A, `os3a_reweight` and `os3a_extended` weight sets (Q8).

**Outputs (`python -m os4`):** `outputs/task1_cases.csv` / `.md`, `outputs/task1_mau.csv` (MAU and rank under each weight set), `outputs/task1_weight_sensitivity.csv`, the two figures, and the Excel backup `outputs/os4_model.xlsx`. The workbook's SAU and MAU cells are live formulas (interpolation via named ranges, weighted sums, `RANK`) with the Python values and a `diff` column beside them.

**Verification (tests in `tests/test_utility.py`):**
- Every SAU returns its table points exactly, is monotone, and clamps to [0, 1].
- Best on every attribute → 1.0, worst → 0.0, and the weights sum to 1.
- Cases A/B/C match Yonis's hand calculations: each SAU value (`test_case_saus_match_hand_calc`) and each MAU (`test_cases_match_hand_calc`).
- Validity: the MAU ranks a "meets every Table 1 requirement" point (1500, 150, 5, 0.75) above each of the cases. A sensitivity check sweeps each weight ±0.1 to show when the A/B/C ranking flips. This doubles as the "would we change the weights?" evidence.

**Discussion (reflection the assignment asks for).** Q7 maps Appendix A to our OS3A MOEs, Q8 proposes new weights, and the proposed attributes below cover travel time (the 7-minute requirement). Still open: the OS3B operational objectives (Q22), outside-boundary wait (the 20-minute requirement, which belongs to the Task 4 scenario), and whether 0.35 on wait at a single node is too narrow.

> **Q7, decided (from OS3A):** OS3A MOE mapping (Table 3). OS3B was an individual assignment, so it doesn't block this: each member adds the operational objectives from their own OS3B as a bullet below (Q22).
> - **MOE 4 pickup wait (<15 min)** ↔ the wait-time MoP (0.35). Direct match. Note the targets differ: OS3A says 15 min, Table 1 says 5 min.
> - **MOE 1 allocated commute time / predictability** ↔ availability (partial). Reliability was the interviewee's #1 theme ("Red Line is the weakest link").
> - **MOE 7 regional talent access** and **MOE 2 bike share** ↔ passenger volume and throughput (indirect).
> - **MOE 3 serious crashes, MOE 6 stop announcements, MOE 5 AV opposition, MOE 8 curb access**: no Appendix A counterpart. OS3A already treats MOE 3 and MOE 6 as **pass/fail screens**, not weighted attributes.

> **Q8, decided (from OS3A):** Propose new weights of **volume 0.10 / peak 0.25 / wait 0.35 / availability 0.30.** Wait stays largest because MOE 4 is a direct match. Weight moves from volume to availability because reliability (MOE 1) dominated the stakeholder evidence while volume traces only indirectly. Keep safety and accessibility as pass/fail screens rather than weights, consistent with OS3A. With these weights the MAUs are A 0.628 / B 0.619 / C 0.676, so the ranking changes from C > B > A to C > A > B. In code this is the `os3a_reweight` set in `data/mau_weights_proposed.csv`.

**Proposed additional attributes (team assumption, from the Q7 mapping).** Two of our OS3A MOEs have no Appendix A counterpart but can be computed by the Task 2 model, so we propose adding them as SAUs. Cases A–C don't report these levels, so the Task 1 results stay on the four Appendix A attributes; the extended MAU scores the Task 2+ architectures.

| Attribute | Traces to | SAU points (x → U) | Computed from |
| --- | --- | --- | --- |
| In-boundary travel time (min) | Table 1 (7 min max between any two locations) [[1]](references.md#ref-1); OS3A MOE 1 (predictable commute time) | 0 → 1.0, 4 → 0.95, 7 → 0.8, 10 → 0.5, 15 → 0.2, 20 → 0 | Link distance (Q1) ÷ achieved speed (Q3). At 21 km/h: 5.4 / 4.6 / 9.4 min, so only Lechmere–Central misses 7 min |
| Bike share of served trips | OS3A MOE 2 (bike commute share, 11% baseline) | 0 → 0, 0.11 → 0.3, 0.25 → 0.6, 0.5 → 0.9, 1.0 → 1.0 | Bike trips ÷ total served trips |

Safety (MOE 3), stop announcements (MOE 6) and accessibility (Q21) stay **pass/fail screens**, not weighted attributes. Extended weights (`os3a_extended`): keep the `os3a_reweight` priorities for the Appendix A four, scaled by 0.75, and give 0.25 to the new pair: **volume 0.08 / peak 0.18 / wait 0.27 / availability 0.22 / travel time 0.15 / bike share 0.10.** Wait plus travel time (0.42) then covers the door-to-door experience behind MOE 1 and MOE 4.

---

## Task 2: system model (3 slides + backup)

**Status (first pass, for review).** `scenario.primary_scenario()`, `vehicle.py`, `fleet.py` and `model.py` are implemented; `python -m os4` writes `outputs/task2_variants.csv` (1,578 feasible vehicles) and `outputs/task2_architectures.csv` (the 5-architecture table). Defaults used until the team decides, each tagged in the code:
- **Q11 (decided):** peak throughput = the demand actually served, min(capacity, peak demand) (`throughput_measure="served"`).
- **Q12:** demand-weighted wait over the day: headway / 2 at the Kendall hub, scaled by 1 / (1 − ρ) as demand nears capacity, capped at 30 min. Bikes return to the hub after each trip and use the same model.
- **Q13 deadhead (decided for now):** 1.0. Every vehicle returns to Kendall empty, because Appendix B only gives Kendall-origin demand.
- **Q14 (decided):** availability = *service* availability: the chance the vehicles in service can carry each hour's demand, averaged over the day by demand. The Appendix B vehicle availability is still reported as `vehicle_availability`.
- **Travel time (decided):** the average Kendall trip (1.75 km road, 1.6 km bike) ÷ speed, weighted by each part's share of trips; 5.0 min for a capped road fleet. The longest link (Lechmere–Central, 9.4 min) is left for later.
- **Fleet grid (Q10, decided):** road 5–300 step 5, bikes 25–750 step 25 (about 7.4 million architectures with removable batteries).
- **Load factor:** Appendix B's 0.75 stays the baseline; Task 3 also shows the Pareto front at 25 / 50 / 75 / 100% in one chart, because 0.75 is optimistic for large on-demand vehicles.
- **Cost (Q15, assumption):** vehicle capital cost only for now; operating cost (staff, swap labor) is not modeled.
- **Bike speed (Q5):** 18 km/h fixed assist, the low end of 18–20 km/h.

**Findings to discuss:**
- **E-bike availability is 0.14–0.42 under Appendix B,** far below the 0.75 benchmark. Small batteries (0.5–3 kWh) and slow chargers mean bikes charge much longer than they ride. A bike-only fleet needs ~150 bikes to cover the peak. Battery swapping would be a justified deviation worth proposing.
- **Large shuttles look cheapest** (4 × C6 for $351k vs 12 × C2 for $718k) because Appendix B's 0.75 load factor fills a 16-seat shuttle with 12 riders per trip. For on-demand service at 150 trips/h that is optimistic; consider a lower load factor for big chassis, or a load factor tied to demand per departure.
- **The 21 km/h cap binds for 55% of road variants,** so motors above M2 rarely buy speed on small chassis.
- **MAU saturates once demand is met:** with served throughput (capped at 150 trips/h, U = 0.90), volume capped at 1,790 trips/day (U = 0.916), and service availability near 1 for almost every fleet that meets the thresholds, the MAU has a ceiling of 0.962. The front climbs quickly, then runs flat for hundreds of architectures that differ only by seconds of wait, so in practice the choice is the cheapest fleet that meets demand.
- **Removable e-bike batteries (team proposal, a justified Appendix B deviation; kept as an alternate pathway next to fixed batteries):** bikes can swap packs in 5 min (assumed) instead of charging in place, with k spare packs per bike pooled across the fleet (0.5–3). Availability = min( U/(U+s), (1+k)·U/(U+s+C+0.25) ); each spare adds its battery and a charger slot to the bike cost. A B2 bike goes from 0.42 availability at $4,500 to 0.90 at $6,150 with 1.5 spares. Task 3 is run with and without the option: **with it, bikes take the Pareto front** (29 bike-only + 12 mixed, cheapest feasible 25 × B3 with 2 spares at $177,500); without it the front is all road-only. Swap labor is not counted (Q15). Open for the group: adopt it, keep it as a what-if, or tie it to a scenario; and whether the availability attribute means vehicle or service availability (Q14).
- **Requirements screening:** architectures that miss a Table 1 threshold (1,500 trips/day, 150 trips/h peak, 50 trips/h off-peak) are dropped from the tradespace before scoring: 1,921 of 278,004, which removes all 23 cheap bike-only and small-fleet points from the Pareto front. The "desired" goals are flags only, because **no architecture meets the 7-minute travel goal** (Lechmere–Central takes ≥ 9.4 min at 21 km/h).

### Design vector

| Decision        | Road options               | Bike options                |
| --------------- | -------------------------- | --------------------------- |
| Chassis / frame | C1–C8                      | B1–B3                       |
| Battery         | P1–P7 (weight ≤ ⅓ chassis) | E1–E3 (weight ≤ ½ frame)    |
| Charger         | G1–G3                      | G1–G2                       |
| Motor           | M1–M4                      | K1–K3                       |
| Autonomy        | A3/A4/A5                   | fixed L4 (in frame cost)    |
| Fleet size      | N_road: e.g. 0–60, step 5  | N_bike: e.g. 0–300, step 25 |

Feasible vehicle variants after the battery constraint:
- **Road:** C1–C2 → P1–P4; C3–C4 → P1–P5; C5 → P1–P6; C6–C7 → P1–P6; C8 → P1–P7. That gives 43 chassis/battery pairs × 3 chargers × 4 motors × 3 autonomy levels = **1,548**.
- **Bike:** B1, B2 → E1 only; B3 → E1–E3. That gives 5 frame/battery pairs × 2 × 3 = **30**.

Crossing these with fleet sizes is the "MASSIVE" space the recitation warns about. Task 2's model handles all of them. Pruning (dominated vehicle variants, such as a bigger motor with no speed gain once the speed cap binds) belongs to Task 3, but the vehicle-level table should make that pruning trivial.

> **Q10, decided:** One road variant plus one bike variant per architecture. Fleet-size grid: **road 5–300 step 5, bikes 25–750 step 25** (team decision). OS3A argues against large, half-empty shuttles (MIT P&T quote [[15]](references.md#ref-15)) and in favor of more e-bikes (the interviewee's #1 request; Ames/Main Bluebikes already need valet service).

### Layer 1: vehicle model, `src/os4/vehicle.py` (Appendix B, as given)
For each feasible variant compute: total weight (+100 kg × pax), cost, Wh/km, range, speed (capped at D3), charge time, up-time, down-time and **availability**. Return one tidy DataFrame with one row per variant.
- Apply the e-bike modification from D5. Keep the original formula alongside it so the justification can show both.

### Layer 2: fleet/operations model, `src/os4/fleet.py`
Inputs: vehicle row(s), N_road, N_bike, scenario (network distances from Q1: 1.9 / 1.6 / 3.3 km, demand profile, speed limit). Proposed equations (based on the Wikibooks transit-capacity pages from Appendix B [[4]](references.md#ref-4), [[5]](references.md#ref-5)):
- **Cycle time** per trip = (trip distance + empty repositioning distance) / speed + dwell (60 s). Trip distance is 1.75 km for road vehicles and 1.6 km for bikes (Q13). At 21 km/h a 1.75 km trip takes 5.0 min plus 1 min dwell, before deadhead.
- **Per-vehicle capacity** = (60 / cycle_min) × pax × 0.75 load factor. A bike carries pax = 1 (2 for B3) and its repositioning leg runs autonomously.
- **Effective fleet** = N × availability, since vehicles that are charging carry no passengers.
- **Fleet throughput** (trips/h) = Σ effective vehicles × per-vehicle capacity. **Peak throughput MoP** = min(capacity, offered peak demand), or capacity alone. Decide which and document it, because the SAU runs to 200 while Appendix B demand peaks at 150.
- **Daily passenger volume** = Σ over the 2-hour bins of min(demand_h, capacity) × 2.
- **Average wait at Kendall:** headway/2 when vehicles are plentiful, where headway = 60 / (vehicle departures/h at the node). When demand exceeds capacity, add a queueing penalty (an M/M/c-style or simple backlog term) so wait rises steeply. For bikes, use time for the nearest idle bike to self-deliver, based on the idle-bike density over the service area.
- **Availability MoP:** per-vehicle Appendix B availability. For a mixed fleet, use the capacity-weighted average. Compare against the 0.75 benchmark.
- **Fleet cost** = Σ vehicle cost × N. State that charging infrastructure and operations cost are excluded, or add them as an assumption.

> **Q11, decided:** peak throughput is the demand the fleet actually serves, min(capacity, peak demand), so it caps at 150 trips/h (U = 0.90). Capacity is still used for the Table 1 thresholds.

> **Q12, decided (from OS3A):** Use an on-demand wait model rather than a fixed-route headway model. The exact formula and the bike self-delivery model are still open. MOE 4 explicitly covers *demand-responsive* pickups, so an on-demand wait model fits better than a fixed-route headway model. Anchors: EZRide runs every 8–12 min (≈ 4–6 min average wait) [[18]](references.md#ref-18), and MBTA buses every 15–30 min [[17]](references.md#ref-17).

> **Q13, decided (OS3A + measured distances):** Average trip length **1.75 km** for road vehicles, the mean of the two Kendall-origin links from Q1 (Kendall–Lechmere 1.9 km, Kendall–Central 1.6 km), since the Appendix B demand starts at Kendall (Q4). Bikes use 1.6 km (both Kendall bike links). Travel time is measured on this average trip. **Deadhead 1.0** (empty return to Kendall), kept for now.

> **Q14, decided:** availability is **service availability**: P(capacity of the vehicles in service ≥ demand) in each 2-hour bin, averaged over the day weighted by demand. Each vehicle is in service with its Appendix B availability a, independently, so the capacity in service has mean Σ N·a·c and variance Σ N·a·(1−a)·c² (c = one vehicle's trips/h); the probability uses the normal approximation (Excel: `NORM.S.DIST`). Spare vehicles raise it, so a pool of 42%-available bikes can still serve almost every rider.

> **Q15, decided (assumption):** vehicle capital cost only for now, as the tradespace axis; operating cost (staff, Level 3 attendants, battery-swap labor) is not modeled. MIT P&T's "not financially viable" concern and EZRide's funding from ~25 member firms are noted qualitatively.

### Layer 3: glue, `src/os4/model.py` (new)
`evaluate(architecture, scenario) -> dict` returns the MoPs, MAU and cost. Tasks 3 and 4 call this with a different scenario object, so put scenarios in `data/scenarios.yaml` or a dataclass rather than in constants.

### Verification & validation (needed for the slide)
- **Hand-calc check:** one road and one bike variant worked by hand (in a spreadsheet), matched by the code to 1e-9.
- **Robustness sweep:** every feasible variant × fleet-size grid produces no NaN, inf or negative values, and availability stays in (0, 1). This is the assignment's "doesn't break down" requirement.
- **Monotonicity tests:** throughput rises with N, wait falls with N, cost is linear in N, and N = 0 gives zero throughput and an infinite or maxed-out wait that is handled.
- **Constraint tests:** infeasible battery/chassis pairs are excluded.
- **Validation / anchor:** compare to real systems, such as Bluebikes trips and dock density in Cambridge, and the MBTA CT2/EZRide shuttle headways and fleet sizes. Show that the model lands in a plausible range. Show that the primary scenario's demand (150/h peak, sum ≈ 1,790 trips/day) is met by at least one architecture.

> **Q16, decided (from OS3A):** OS3A already has anchors with citations: **EZRide 8–12 min headways** [[18]](references.md#ref-18), **MBTA buses 15–30 min** [[17]](references.md#ref-17), **5 daytime MIT shuttles**, **18 Bluebikes stations** in Kendall, **6,878 Red Line riders/day**, and **Red Line 89% on-time within 5 min** [[16]](references.md#ref-16). Reuse the OS3A references.

### Deliverable: 5-architecture table
Pick 5 that span the space: (1) small road-only fleet of C2 cars, (2) large road shuttles (C6/C7), (3) bike-only, (4) mixed road + bike, (5) a high-autonomy (A5) or long-range variant. Columns: composition, N, component IDs, speed, range, throughput, wait, availability, vehicle cost, fleet cost, plus the MAU for free.

> **❓ Q17 / A:** Which five architectures, components and N for the Task 2 table, and how to size them? **Austin will pick**, using the ~50 highlighted candidates in the results explorer (`outputs/site/`). The current five in `model.representative_architectures` are hand-picked placeholders (11–60% spare capacity).
> **Answer:** _TBD (Austin)_

### Model export
Use `python -m os4` to write `outputs/os4_model.xlsx` (with tabs for inputs, the SAU/MAU tables, the vehicle variants, the 5 architectures, and the hand-calc check) and make it the ZIP submission. The Excel file holds model data and formulas only; text responses go in the slide deck.

---

## Open items from the 2026-11-01 review

> **B, decided (alternate pathways):** keep both e-bike battery options, fixed (Appendix B) and removable (team proposal), and report both; the group chooses later.

> **C, decided:** keep Appendix B's 0.75 load factor as the baseline and show the Pareto front at 25 / 50 / 75 / 100% in one chart (`task3_load_factor_fronts.png`).

> **D, decided:** travel time is the average Kendall trip; the longest link (Lechmere–Central) is left for later.

> **E, decided (assumption):** vehicle capital cost only (Q15).

> **❓ F:** Task 3 reference architecture (chosen before looking at the tradespace, as Task 3 asks). **Open.**
> **Answer:** _TBD_

> **❓ G:** The three Pareto architectures for the Task 3 table. **Open**; review them in the results explorer.
> **Answer:** _TBD_

> **❓ H:** The proposed travel-time and bike-share SAU curves (extended MAU). **Open**; shown for review on the explorer's Task 1 page.
> **Answer:** _TBD_

> **❓ I:** Extra sensitivity runs (32 km/h posted speed, 0.5 deadhead). Needed? The load-factor chart already covers the "what-if" the rubric asks about.
> **Answer:** _TBD_

## Questions raised by OS3A

> **⏸ Q20 (on hold):** Task 4 scenario: (a) Red Line shutdown [[21]](references.md#ref-21), with trips leaving the boundary toward Boston (forces A4/A5), or (b) winter, when commuters switch from bikes to the Red Line. Held until Tasks 2–3 are settled.

> **Q21, decided for the primary scenario:** no accessibility screen for now. OS3A notes no wheelchair-accessible AVs exist and e-bikes serve no one with a mobility disability; revisit for Task 5.

> **❓ Q22:** OS3B was individual. Each member: add the operational objectives from your OS3B under Q7 so the Task 1 reflection can cite them.
> **Answer:** _TBD (each member)_

## Suggested split & order
1. **Decisions:** D1–D6 and Q10–Q15 are settled (Q12's exact wait formula is the default in `fleet.py`). Open: Q17/A (Austin picks the five), the items under "Open items from the 2026-11-01 review" below, and Q22 (each member's OS3B).
2. **Task 1:** `utility.py` and its tests, plus the slide (1 person, small).
3. **Vehicle layer:** `vehicle.py`, its tests, and the hand-calc spreadsheet (1 person).
4. **Fleet layer:** `fleet.py` and the scenario config, which carries the most modeling judgment (1–2 people).
5. **Integrate:** `model.py`, the 5-architecture table, the xlsx export, and the Task 2 slides.

Steps 2–4 can run in parallel once the vehicle-row DataFrame columns are agreed.

> **Q19, decided:** Python only, with the Excel backup (`outputs/os4_model.xlsx`, live formulas) for the submission.

---

## Appendix: Fundamentals of Transportation extracts

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

- **Capacity:** `fleet.vehicle_capacity_per_h` is C<sub>route</sub> = f · N<sub>car</sub> · C<sub>car</sub> per vehicle, with f = 60 / cycle time, N<sub>car</sub> = 1, and C<sub>car</sub> = pax × the Appendix B load factor (0.75).
- **Cycle time:** `fleet.cycle_time_min` follows the sample problem: running time at the average speed plus dwell, with the empty return leg in place of the inbound trip (Q13 deadhead).
- **Headway:** the wait model (Q12) starts from headway / 2, with headway = 60 / departures per hour at the Kendall hub.
- **Fleet sizing (open question for the group):** load management gives a cited rule. Departures needed f ≥ P / (X · 1 · C<sub>car</sub>); vehicles needed N = f × cycle / 60 / availability. For the C2 car (4 pax × 0.75 = 3 riders per trip, 11-min cycle, availability 0.922) at P = 150 trips/h: X = 1 gives f ≥ 50/h and N = 10, the model's minimum fleet; X = 0.8 gives f ≥ 62.5/h and N = 13. X is the planner's choice (0.90 in the example), so choosing X is choosing how much headroom every architecture gets.
- The *Network Design and Frequency* page also gives Mohring's cost-minimizing frequency, f = √(VOT · p / (2 · C · T)), which trades waiting time against operating cost. It is not in the assignment's extracts, and we don't model operating cost (Q15).
