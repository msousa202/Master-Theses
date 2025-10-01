import pandas as pd, numpy as np, re, sys, warnings
from pathlib import Path
from scipy.stats import ttest_rel, wilcoxon, friedmanchisquare, kruskal, mannwhitneyu
from sklearn.utils import resample
import pingouin as pg                          # pip install pingouin
import scikit_posthocs as sp
warnings.filterwarnings("ignore", category=RuntimeWarning)

FILE = "data/Exploring AI-Driven Decision-Making in Business Contexts(1-119).xlsx"
OUT  = Path("results")                               # where CSVs will be written
LEVELS = ["Strategic", "Tactical", "Operational"]
AGENTS = ["AI", "Human"]                       # assumes both were rated

# ------------------------------------------------------------------
# 1. helper functions
# ------------------------------------------------------------------
def likert_1to5(x):
    """Return 1-5 float or NaN."""
    if pd.isna(x): return np.nan
    m = re.search(r"([1-5])", str(x))
    return float(m.group(1)) if m else np.nan

def abcd_or_likert(x):
    """Convert A-D → 1-4, else fall back to Likert."""
    if pd.isna(x): return np.nan
    s = str(x).strip()
    if s and s[0] in "ABCD":
        return {"A":1,"B":2,"C":3,"D":4}[s[0]]
    return likert_1to5(x)

def cronbach_alpha(df):
    """Simple α; rows = respondents, cols = items."""
    k = df.shape[1]
    item_var = df.var(axis=0, ddof=1)
    tot_var  = df.sum(axis=1).var(ddof=1)
    return (k / (k-1)) * (1 - item_var.sum()/tot_var) if k>1 else np.nan

LABELS = {(1.00,2.49):"Low", (2.50,3.49):"Moderate", (3.50,5.00):"High"}
def label(m): 
    return next((lab for (lo,hi),lab in LABELS.items() if lo<=m<=hi), np.nan)

def first_col(df, substrings):
    for c in df.columns:
        if any(ss.lower() in c.lower() for ss in substrings):
            return c
    return None

# 2. Explicit mapping from (level, criterion, agent) to column names
# COLUMN_MAP  •  level ➜ criterion ➜ agent ➜ list-of-column-names-
COLUMN_MAP = {

    # ────────────────────────────────────────────────────────────
    # 1 ▸ STRATEGIC  (Senior-level, AlphaTech market-entry case)
    # ────────────────────────────────────────────────────────────
    "Strategic": {

        "Goal Alignment": {
            "AI": [
                "The proposed strategy aligns well with AlphaTech's long-term organizational goals.",
                "This decision incorporates critical market and competitor data."
            ],
            "Human": []
        },

        # (reverse-code both items ⇒ higher number = **more** feasible)
        "Implementation Feasibility": {
            "AI": [
                "How do you perceive the financial risk of this market entry?",
                "How likely is it that this strategy will encounter regulatory or compliance barriers?"
            ],
            "Human": []
        },

        "Trust / Confidence": {
            "AI": [
                "I trust an AI system to provide fair and unbiased strategic recommendations.",
                "I can understand how an AI would arrive at its strategic suggestions."
            ],
            "Human": []
        },

        "Ethical Soundness": {
            "AI": [
                "The recommended strategy adequately safeguards stakeholder interests (employees, customers, society).",
                "Potential ethical issues (e.g., environmental impact) have been sufficiently addressed."
            ],
            "Human": []
        },

        "Adaptability": {
            "AI": [
                "Our organization can swiftly adapt if market conditions change post-decision.",
                "We have the infrastructure to pivot if the strategy proves suboptimal."
            ],
            "Human": []
        }
    },

    # ────────────────────────────────────────────────────────────
    # 2 ▸ TACTICAL  (Middle-level, Beta Manufacturing allocation case)
    # ────────────────────────────────────────────────────────────
    "Tactical": {

        "Goal Alignment": {
            "AI": [
                "To what extent does the proposed resource allocation plan support Beta Manufacturing's medium-term operational goals?"
            ],
            "Human": []
        },

        "Implementation Feasibility": {
            "AI": [
                "How feasible is it to implement this resource allocation plan considering current staffing levels and operational capacity?",
                "How effectively does the AI-generated plan incorporate practical constraints (e.g., staffing levels, machine downtime)?"
            ],
            "Human": []
        },

        "Trust / Confidence": {
            "AI": [
                "Based on the AI-generated recommendations, how practical and trustworthy do you find these suggestions for day-to-day planning?",
                "How clear and transparent is the rationale provided by the AI for its resource allocation decisions?",
                "How confident are you in implementing the AI-generated resource allocation plan as-is, without major modifications?"
            ],
            "Human": []
        },

        "Ethical Soundness": {
            "AI": [
                "How well does the plan address ethical and stakeholder implications (e.g., workload fairness, compliance)?",
                "To what extent does the AI consider social and ethical factors (e.g., fair distribution of workload, sustainability)?",
                "How fair do you believe the AI-generated resource allocation plan is from the employees' perspective?2"
            ],
            "Human": []
        },

        "Adaptability": {
            "AI": [
                "How adaptable is the resource allocation plan in response to sudden changes in resource constraints?",
                "How responsive is the AI-generated plan to external shocks such as supply chain disruptions and labor shortages?",
                "How adaptable is the allocation strategy if market conditions shift significantly?"
            ],
            "Human": []
        }
    },

    # ────────────────────────────────────────────────────────────
    # 3 ▸ OPERATIONAL  (Low-level, Omega Services scheduling case)
    # ────────────────────────────────────────────────────────────
    "Operational": {

        "Goal Alignment": {
            "AI": [
                "The proposed plan adequately covers all weekly requirements",
                "This decision effectively addresses immediate operational goals (e.g., throughput, error reduction)."
            ],
            "Human": []
        },

        "Implementation Feasibility": {
            "AI": [
                "This solution is practically feasible given current staff availability and skills.",
                "The plan remains within budget and resource constraints for daily operations."
            ],
            "Human": []
        },

        "Trust / Confidence": {
            "AI": [
                "The AI-generated proposal offers a timely solution that can be implemented quickly",
                "Using the AI's suggestions reduces the time spent on repetitive scheduling or inventory tasks"
            ],
            "Human": []
        },

        "Ethical Soundness": {
            "AI": [
                "The plan ensures fair workload distribution and respects employee well-being",
                "Customer satisfaction or safety standards are adequately addressed"
            ],
            "Human": []
        },

        "Adaptability": {
            "AI": [
                "To what extent do you believe that implementing an AI agent can enhance efficiency in operational decision-making?"
            ],
            "Human": []
        },

        "Consistency of Feedback": {
            "AI": [
                "The plan follows established standard operating procedures (SOPs)",
                "This decision aligns with routine or repetitive tasks in our day-to-day processes"
            ],
            "Human": []
        }
    }
}

# Add reverse-coding mapping after COLUMN_MAP
REVERSE_CODED_ITEMS = {
    ("Strategic", "Implementation Feasibility", "AI"): [
        "How do you perceive the financial risk of this market entry?",
        "How likely is it that this strategy will encounter regulatory or compliance barriers?"
    ],
    ("Tactical", "Implementation Feasibility", "AI"): [
        "How effectively does the AI-generated plan incorporate practical constraints (e.g., staffing levels, machine downtime)?"
    ],
    ("Tactical", "Trust / Confidence", "AI"): [
        "How confident are you in implementing the AI-generated resource allocation plan as-is, without major modifications?"
    ],
    ("Operational", "Implementation Feasibility", "AI"): [
        "The plan remains within budget and resource constraints for daily operations."
    ]
}

def reverse_code_score(x):
    """Reverse code a score (6 - x for 1-5 scale, 5 - x for 1-4 scale)."""
    if pd.isna(x): return np.nan
    return 6 - x if x <= 5 else 5 - x

# ------------------------------------------------------------------
# 3. build a long dataframe: one row per respondent × agent × level
# ------------------------------------------------------------------
records = []
xl = pd.ExcelFile(FILE)
for level in LEVELS:
    sheet = pd.read_excel(xl, sheet_name=level)
    print(f"\n[INFO] Columns in sheet '{level}':\n", list(sheet.columns))
    n_resp = sheet.shape[0]
    parser = abcd_or_likert if level=="Tactical" else likert_1to5
    
    for crit in COLUMN_MAP.get(level, {}):
        for agent in AGENTS:
            cols = COLUMN_MAP[level][crit].get(agent, [])
            missing = [c for c in cols if c not in sheet.columns]
            if missing:
                print(f"[WARNING] Columns not found for {level} - {crit} - {agent}: {missing}")
            used_cols = [c for c in cols if c in sheet.columns]
            print(f"[DEBUG] Level: {level}, Criterion: {crit}, Agent: {agent}")
            print(f"         Columns used: {used_cols}")
            if not used_cols:
                print(f"[WARNING] No columns found for {level} - {crit} - {agent}")
                continue
            
            # Process scores
            sub = sheet[used_cols].map(parser)
            
            # Apply reverse-coding where needed
            key = (level, crit, agent)
            if key in REVERSE_CODED_ITEMS:
                for rc in REVERSE_CODED_ITEMS[key]:
                    if rc in sub.columns:
                        print(f"[INFO] Reverse-coding column: {rc}")
                        sub[rc] = sub[rc].apply(reverse_code_score)
            
            score = sub.mean(axis=1, skipna=True)
            for sid, val in score.dropna().items():
                records.append([sid, agent, level, crit, val])

long = (pd.DataFrame(records, columns=["ID","Agent","Level","Criterion","Score"])
        .dropna())

# ------------------------------------------------------------------
# 4. reliability check (Cronbach's α)
# ------------------------------------------------------------------
alpha_rows = []
for level in LEVELS:
    for crit in COLUMN_MAP.get(level, {}):
        for agent in AGENTS:
            cols = COLUMN_MAP[level][crit].get(agent, [])
            used_cols = [c for c in cols if c in xl.parse(level).columns]
            if not used_cols:
                continue
            parser = abcd_or_likert if level=="Tactical" else likert_1to5
            items = xl.parse(level)[used_cols].map(parser)
            alpha = cronbach_alpha(items)
            alpha_rows.append([level, crit, agent, round(alpha,2), len(used_cols)])
reliability = pd.DataFrame(alpha_rows, columns=["Level","Criterion","Agent","Alpha","Items"])

# ------------------------------------------------------------------
# 5. descriptive stats & labels
# ------------------------------------------------------------------
desc = (long.groupby(["Agent","Level","Criterion"])
             .agg(N = ("Score","count"),
                  Mean = ("Score","mean"),
                  Median = ("Score","median"),
                  Q1 = ("Score", lambda x: x.quantile(0.25)),
                  Q3 = ("Score", lambda x: x.quantile(0.75)),
                  SD   = ("Score","std"))
             .reset_index())
desc["IQR"] = desc["Q3"] - desc["Q1"]
desc["Label"] = desc["Mean"].apply(label)
desc.to_csv(OUT/"summary_table.csv", index=False)

# ------------------------------------------------------------------
# 6. inferential tests: AI vs Human per criterion × level
# ------------------------------------------------------------------
tests = []
for lvl in LEVELS:
    for crit in COLUMN_MAP[lvl]:
        ai  = long.query("Agent=='AI' & Level==@lvl & Criterion==@crit")
        hu  = long.query("Agent=='Human' & Level==@lvl & Criterion==@crit")
        # align by respondent
        merged = ai.merge(hu, on=["ID","Level","Criterion"], suffixes=("_AI","_HU"))
        if merged.empty: continue
        
        # Wilcoxon signed-ranks test
        w, p = wilcoxon(merged["Score_AI"], merged["Score_HU"])
        
        # Calculate rank-biserial correlation
        n = len(merged)
        r = abs(w) / (n * (n + 1) / 2)  # rank-biserial correlation
        
        tests.append([lvl, crit, merged.shape[0], "Wilcoxon", round(w,2), round(p,4), round(r,2)])
infer = pd.DataFrame(tests, columns=["Level","Criterion","N","Test","Stat","p","Rank_Biserial"])
infer.to_csv(OUT/"inferential_stats.csv", index=False)

# ------------------------------------------------------------------
# 7. Kruskal-Wallis test for comparing across decision-making levels
# ------------------------------------------------------------------
kruskal_results = []
for agent in AGENTS:
    for crit in set(long["Criterion"]):
        data = long.query("Agent==@agent & Criterion==@crit")
        if data.empty: continue
        
        # Prepare data for Kruskal-Wallis test
        groups = [grp["Score"].values for name, grp in data.groupby("Level")]
        
        # Ensure we have groups to compare
        if len(groups) < 2: continue
        
        # Perform Kruskal-Wallis test
        h_stat, p_val = kruskal(*groups)
        
        # Calculate Epsilon-squared
        n = sum(len(g) for g in groups)
        epsilon_squared = (h_stat - len(groups) + 1) / (n - len(groups))
        
        kruskal_results.append([agent, crit, len(groups), round(h_stat, 2), round(p_val, 4), round(epsilon_squared, 2)])

kruskal_df = pd.DataFrame(kruskal_results, 
                         columns=["Agent", "Criterion", "k", "H", "p", "Epsilon_Squared"])
kruskal_df.to_csv(OUT/"kruskal_test.csv", index=False)

# ------------------------------------------------------------------
# 8. Post-hoc pairwise comparisons (Mann-Whitney with Bonferroni correction)
# ------------------------------------------------------------------
posthoc_results = []
for agent in AGENTS:
    for crit in set(long["Criterion"]):
        data = long.query("Agent==@agent & Criterion==@crit")
        if data["Level"].nunique() < 2: continue

        # Get all unique levels for this agent-criterion combination
        levels = data["Level"].unique()
        n_comparisons = len(levels) * (len(levels) - 1) // 2  # Number of pairwise comparisons
        
        # Perform Mann-Whitney tests for all pairwise comparisons
        comparisons = []
        for i, level1 in enumerate(levels):
            for j, level2 in enumerate(levels):
                if i < j:  # To avoid duplicates and self-comparisons
                    group1 = data[data["Level"] == level1]["Score"].values
                    group2 = data[data["Level"] == level2]["Score"].values
                    
                    # Mann-Whitney U test
                    u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
                    
                    # Apply Bonferroni correction
                    p_corrected = min(p_val * n_comparisons, 1.0)
                    
                    comparisons.append([agent, crit, f"{level1} vs {level2}", 
                                     round(u_stat, 2), round(p_val, 4), 
                                     round(p_corrected, 4), n_comparisons])
        
        posthoc_results.extend(comparisons)

posthoc_df_final = pd.DataFrame(posthoc_results,
                         columns=["Agent","Criterion","Comparison","U_statistic","p_uncorrected","p_bonferroni","n_comparisons"])
posthoc_df_final.to_csv(OUT/"posthoc_comparisons.csv", index=False)

# ------------------------------------------------------------------
# 9. pretty version of Comparative Performance Matrix --------------
pivot = (desc.pivot_table(index="Criterion",
                          columns=["Level","Agent"],
                          values=["Median","IQR"], aggfunc="first")
              .reindex(index=sorted(COLUMN_MAP["Operational"].keys())))
print("\n==== Comparative Performance Matrix (Median and IQR) ====\n")
print(pivot.to_string())

print("\nFiles saved:")
for f in ["summary_table.csv","inferential_stats.csv","kruskal_test.csv","posthoc_comparisons.csv", "decision_variance_by_tier.csv"]:
    print("  •", OUT/f)

# ------------------------------------------------------------------
# 10. Decision Variance analysis (for Appendix C)
# ------------------------------------------------------------------

def decision_variance(series):
    """MAD ÷ median, per §3.3.3."""
    med = np.nanmedian(series)
    mad = np.nanmedian(np.abs(series - med))
    return mad / med if med else np.nan

def bootstrap_ci(series, n_boot=10_000):
    """BCa-style percentile CI for DV."""
    boot = [decision_variance(resample(series, replace=True)) for _ in range(n_boot)]
    return np.nanpercentile(boot, [2.5, 97.5])

dv_rows = []
for (lvl, ag), grp in long.groupby(["Level", "Agent"]):
    dv_val = decision_variance(grp["Score"])
    ci_low, ci_high = bootstrap_ci(grp["Score"])
    n_resp = grp["ID"].nunique()
    dv_rows.append([lvl, ag, n_resp,
                    round(dv_val, 3), round(ci_low, 3), round(ci_high, 3)])

dv_df = pd.DataFrame(dv_rows,
                     columns=["Level", "Agent", "N", "DV", "CI_lower", "CI_upper"])
dv_df.to_csv(OUT / "decision_variance_by_tier.csv", index=False)

print("\n==== Decision-variance by tier (saved to Appendix C) ====\n")
print(dv_df.to_string(index=False))

