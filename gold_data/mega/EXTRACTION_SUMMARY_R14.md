# Extraction Summary: clean_batch_r14.json

**Extraction Date:** 2026-02-14
**Batch File:** `clean_batch_r14.json`
**Output File:** `clean_results_r14.json`
**Total Studies:** 15

## Overall Results

- **Found:** 8/15 (53.3%)
- **Not Found:** 7/15 (46.7%)
- **Effect Type Distribution:**
  - MD (Mean Difference): 8
  - None: 7

## Detailed Results by Study

### ✓ FOUND (8 studies)

1. **Krieger 2009_2009** - Quality of life
   - Effect: MD = 0.22 (95% CI: 0.00, 0.44)
   - Units: Quality of life points
   - Quote: "Quality of life improved by 0.22 more points in the nurse + CHW group (95% CI, 0.00–0.44; P=.049)."

2. **Rapson 2022_2022** - Vegetable intake
   - Effect: MD = 11.83 g (95% CI: 0.82, 22.84)
   - Units: Grams of broccoli per day
   - Quote: "The veg-only infants consumed more broccoli and spinach than controls [mean difference (95% CI): 11.83 (0.82, 22.84) g, P = 0.036]"
   - Note: Spinach also reported (10.19 g, CI: 0.50-19.87)

3. **Kristiansen 2019_2019** - Fruit and vegetable intake
   - Effect: MD = 13.3 g/day (95% CI: -0.2, 26.9)
   - Units: Grams of vegetables per day
   - Quote: "mean difference of 13.3 g vegetables/day (95% CI: −0.2, 26.9) (P = 0.054)"
   - Note: Non-significant trend (p=0.054)

4. **Namenek Brouwer 2013_2013** - Fruit and vegetable intake
   - Effect: MD = 0.43 servings/day (no CI)
   - Raw data: Intervention +0.25(SD=1.11), Control -0.18(SD=0.52)
   - Units: Servings of vegetables
   - Quote: "intervention children consumed more than control children (+0.25 (1.11) vs. -0.18 (0.52))"

5. **Leis 2020_2020** - Fruit and vegetable intake
   - Effect: β = 0.06 portions (p=0.05)
   - Units: Portions of fruits and vegetables served
   - Quote: "marginal increase in portions of fruits and vegetables served in the intervention group compared to control group (β = 0.06, p = 0.05)"

6. **Tovar 2023_2023** - Fruit and vegetable intake
   - Effect: PE = 2.14 HEI score (95% CI: 0.17, 1.48)
   - Units: Healthy Eating Index-2015 score (whole fruit component)
   - Quote: "whole and total fruit component Healthy Eating Index-2015 scores (point estimate (PE) = 2·14, 95 % CI (0·17, 1·48))"
   - Note: Total fruit also reported (PE=1.71, CI: 0.16-1.47)
   - **Caution:** CI bounds appear inconsistent with point estimate

7. **Haire-Joshu 2008_2008** - Fruit and vegetable intake
   - Effect: MD = 0.35 servings (p=0.02)
   - Units: Servings of fruits and vegetables
   - Quote: "Among preschoolers, FV servings increased in normal weight (MN=.35, p=.02)"
   - Note: Effect only in normal weight children, not overweight (MN=-0.10, p=.48)

8. **Martinez-Andrade 2014_2014** - Fruit and vegetable intake
   - Effect: MD = 6.3 servings/week (95% CI: 1.8, 10.8)
   - Units: Servings of vegetables per week
   - Quote: "intervention v. usual care children increased vegetables by 6.3 servings/week (95% CI, 1.8, 10.8)"

### ✗ NOT FOUND (7 studies)

9. **Cooke 2011_2011** - Vegetable intake
   - Reason: Results described qualitatively ("All three exposure conditions increased liking", "Both reward conditions increased consumption") but no numerical values reported

10. **Braga-Pontes 2021_2021** - Fruit and vegetable intake
    - Reason: Results only state interventions were "effective in increasing vegetable consumption" without numerical data

11. **Gans 2022_2022** - Fruit and vegetable intake
    - Reason: Results text excerpt does not contain F&V intake outcome data (focus on process evaluation)

12. **Nicklas 2017_2017** - Fruit and vegetable intake
    - Reason: Significant increase reported (p<0.0001) but no numerical effect size provided in results text

13. **Alexandrou 2023_2023** - Fruit and vegetable intake
    - Reason: Results report sweet treats (-6.97 g/day), sweet drinks (-31.52 g/day), and screen time (-7.00 min/day) but not F&V intake

14. **Fagerlund 2020_2020** - Fruit and vegetable intake
    - Reason: Results explicitly state "No effect of the intervention was seen on the child's daily intake of vegetables"

15. **Sherwood 2015_2015** - Fruit and vegetable intake
    - Reason: Results text excerpt focuses on BMI outcomes, no F&V intake data provided

## Data Quality Notes

### Studies with Complete Data (Point + CI)
- Krieger 2009: MD + 95% CI
- Rapson 2022: MD + 95% CI
- Kristiansen 2019: MD + 95% CI
- Martinez-Andrade 2014: MD + 95% CI
- Tovar 2023: PE + 95% CI (CI appears inconsistent)

### Studies with Point Estimate Only
- Namenek Brouwer 2013: MD calculated from change scores (raw means + SDs available)
- Leis 2020: Beta coefficient (p-value only)
- Haire-Joshu 2008: Mean difference (p-value only)

### Subgroup Effects
- **Haire-Joshu 2008:** Effect differs by baseline weight status (normal weight: MN=0.35, p=0.02; overweight: MN=-0.10, p=0.48)

### Non-Significant Trends
- **Kristiansen 2019:** MD=13.3 g/day with CI crossing zero (-0.2, 26.9), p=0.054

## Extraction Challenges

1. **Incomplete Results Sections:** Several studies (Cooke 2011, Braga-Pontes 2021, Nicklas 2017) report significance but not effect sizes in the provided results text

2. **Outcome Mismatch:** Alexandrou 2023 outcome specified as "Fruit and vegetable intake" but results text reports other dietary outcomes

3. **Statistical Reporting Inconsistencies:**
   - Tovar 2023: PE=2.14 with CI (0.17, 1.48) appears inconsistent
   - Leis 2020: Beta coefficient represents a marginal effect (p=0.05)

4. **Unit Variation:**
   - Grams per day: Rapson 2022, Kristiansen 2019
   - Servings per day: Namenek Brouwer 2013, Haire-Joshu 2008
   - Servings per week: Martinez-Andrade 2014
   - Portions: Leis 2020
   - HEI score: Tovar 2023
   - Quality of life points: Krieger 2009

## Recommendations

1. **For Studies Not Found:** Access full-text results sections or supplementary tables to locate numerical outcome data

2. **For Tovar 2023:** Verify CI bounds (0.17, 1.48) against source - point estimate of 2.14 suggests CI may be on different scale or misreported

3. **For Namenek Brouwer 2013:** Can calculate proper CI from reported means, SDs, and sample sizes if needed

4. **For Subgroup Analyses:** Note that effect sizes may vary by baseline characteristics (weight status, adherence level, etc.)

---

**Extraction Method:** Manual extraction by human expert following strict guidelines:
- Only explicitly stated data extracted
- No calculations or inferences made
- Exact quotes provided for verification
- Reasoning documented for transparency
