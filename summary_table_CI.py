import pandas as pd
import scipy.stats as st

# Read the summary table
summary = pd.read_csv("results/summary_table.csv")

def ci95(row):
    n, mean, sd = row['N'], row['Mean'], row['SD']
    if n > 1 and pd.notna(sd):
        t_val = st.t.ppf(0.975, df=n-1)
        margin = t_val * sd / (n**0.5)
        return pd.Series({'CI_low': mean - margin, 'CI_high': mean + margin})
    else:
        return pd.Series({'CI_low': pd.NA, 'CI_high': pd.NA})

summary[['CI_low','CI_high']] = summary.apply(ci95, axis=1)

# Write the new table
summary.to_csv("results/summary_table_with_CI.csv", index=False)

print("Wrote results/summary_table_with_CI.csv with 95% confidence intervals.") 