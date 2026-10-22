"""Blast design explorer: try a design, see fragment size, boulders and cost, and find the cheapest one.

Run from the repository root:  streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blast_model import BlastModel, load  # noqa: E402

st.set_page_config(page_title="Blast design explorer", page_icon="💥", layout="wide")


@st.cache_resource
def get_model():
    return BlastModel(*load())


m = get_model()
A = m.A

# ---------------- sidebar: rock class and assumptions ----------------
st.sidebar.header("Rock and assumptions")
label = {r.rock_class: f"{r.rock_class}: {r.site} ({r.rock_type})" for r in m.rocks.itertuples()}
rock_class = st.sidebar.radio("Rock class", list(label), format_func=label.get)
rock = next(r for r in m.rocks.itertuples() if r.rock_class == rock_class)

target = st.sidebar.slider("X50 target (cm, at most)", 15, 50, int(A["target_X50"] * 100))
max_over = st.sidebar.slider("Boulders over 1 m allowed (%)", 1, 15, int(A["max_oversize"]))
c_exp = st.sidebar.number_input("Explosive price ($/kg)", 0.2, 5.0, float(A["explosive_price"]), 0.05)
c_drill = st.sidebar.number_input("Drilling cost ($/m)", 3.0, 60.0, float(A["drilling_cost"]), 1.0)
A_scale = st.sidebar.slider("Rock harder/easier than calibrated (×A)", 0.8, 1.3, 1.0, 0.05)
st.sidebar.caption(f"Fixed: {A['hole_diameter']:.0f} mm hole, {A['explosive']} ({A['explosive_density']:.0f} kg/m³), "
                   f"${A['accessories_per_hole']:.0f} accessories per hole, bench {rock.bench_height_m} m.")
kw = dict(A_scale=A_scale, c_exp=c_exp, c_drill=c_drill)

# ---------------- header ----------------
st.title("Blast design explorer")
st.write(f"Calibrated Kuz-Ram model for **{rock.site}** (rock factor A = {rock.A:.2f}, "
         f"from {rock.n_blasts} real blasts). Change the design and see what happens to fragment size, boulders and cost.")

best = m.optimise(rock, target_cm=target, max_over=max_over, **kw)
now = m.evaluate(rock.Pf_median, rock.B_D_median, rock.S_B_median, rock, **kw)

# ---------------- design sliders ----------------
start = best or {"Pf": float(rock.Pf_median), "B_D": float(rock.B_D_median), "S_B": float(rock.S_B_median)}
c1, c2, c3 = st.columns(3)
Pf = c1.slider("Powder factor (kg/m³)", float(m.PF_GRID[0]), float(m.PF_GRID[-1]), float(start["Pf"]), 0.01)
B_D = c2.slider("Burden ÷ hole diameter", 20.0, 40.0, float(start["B_D"]), 0.25)
S_B = c3.slider("Spacing ÷ burden", 1.0, 1.75, float(start["S_B"]), 0.05)
e = m.evaluate(Pf, B_D, S_B, rock, **kw)
ok = bool(m.feasible(e, target, max_over))

k1, k2, k3, k4 = st.columns(4)
k1.metric("Median fragment X50", f"{e['X50_cm']:.1f} cm", f"{e['X50_cm'] - now['X50_cm']:+.1f} vs now", delta_color="off")
k2.metric("Boulders over 1 m", f"{e['oversize_pct']:.1f} %")
k3.metric("Cost", f"${e['cost']:.2f}/m³", f"{(e['cost'] / now['cost'] - 1) * 100:+.0f}% vs now", delta_color="inverse")
k4.metric("Charge fits the hole?", "Yes" if e["fits"] else "No", f"needs {e['L_needed']:.1f} m, {e['L_free']:.1f} m free", delta_color="off")

problems = []
if e["X50_cm"] > target: problems.append(f"X50 is above the {target} cm target")
if e["oversize_pct"] > max_over: problems.append(f"boulders are above {max_over}%")
if not e["fits"]: problems.append("the charge does not fit in the hole")
if not 2 <= e["H_B"] <= m.df.H_B.max(): problems.append(f"bench ÷ burden is {e['H_B']:.1f} (allowed 2 to {m.df.H_B.max():.1f})")
if ok:
    st.success("This design meets every limit.")
else:
    st.error("This design fails: " + "; ".join(problems) + ".")
st.caption(f"Pattern: burden {e['B']:.2f} m × spacing {e['S']:.2f} m, {e['Q_kg']:.0f} kg per hole, uniformity n = {e['n']:.2f}.")

# ---------------- comparison table ----------------
st.subheader("Current practice vs cheapest design vs yours")
rows = {"Current practice": (rock.Pf_median, rock.B_D_median, rock.S_B_median, now)}
if best:
    rows["Cheapest that meets the limits"] = (best["Pf"], best["B_D"], best["S_B"], best)
rows["Your design"] = (Pf, B_D, S_B, e)
table = pd.DataFrame([{"design": k, "Pf (kg/m³)": p, "B/D": b, "S/B": s, "X50 (cm)": d["X50_cm"],
                       "boulders (%)": d["oversize_pct"], "cost ($/m³)": d["cost"], "charge fits": bool(d["fits"])}
                      for k, (p, b, s, d) in rows.items()]).set_index("design")
st.dataframe(table.style.format(precision=2), width="stretch")
if best is None:
    st.warning("No design in the searched range meets these limits. Loosen the target or the boulder limit.")
elif best["on_boundary"] != "no":
    st.info(f"The cheapest design sits on the edge of the data range ({best['on_boundary']}). "
            "The true optimum may lie outside what the data covers, so treat it as a field-trial starting point.")

# ---------------- trade-off curve ----------------
st.subheader("What finer rock costs")
fr = m.frontier(rock, max_over=max_over, **kw).set_index("X50 target (cm)")
st.line_chart(fr, y="cheapest cost ($/m³)")
st.caption("Cheapest cost for each fragment-size target. Moving right accepts coarser rock; the curve flattens once the cheapest corner of the design range is reached.")

with st.expander("How this works and its limits"):
    st.markdown("""
- **X50** from Kuz-Ram: X50 = A · K^-0.8 · Q^(1/6) · (115/RWS)^(19/30), with the rock factor **A** fitted to this site's blasts.
- **Boulders** from the Rosin–Rammler curve with Cunningham's uniformity index n.
- **Cost** = Pf × explosive price + ((bench + subdrill) × drilling cost + accessories) ÷ rock per hole.
- The search covers powder factor 0.22–1.26, burden ÷ diameter 25–39 and spacing ÷ burden 1.0–1.5, inside the data.
- Not included: flyrock and vibration limits, loading and crushing cost. Kuz-Ram is typically off by 3–5 cm at these sites.
""")
