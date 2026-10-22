"""Calibrated Kuz-Ram blast model: the same equations as notebooks/Blasting_Proj.ipynb.

Kept separate from the Streamlit page so it can be imported and tested on its own.
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"


def load():
    df = pd.read_csv(DATA / "blast_master_110.csv")
    rocks = pd.read_csv(DATA / "rock_types.csv")
    assume = pd.read_csv(DATA / "cost_assumptions.csv")
    A = {r.parameter: (float(r.value) if r.parameter != "explosive" else r.value) for r in assume.itertuples()}
    return df, rocks, A


class BlastModel:
    def __init__(self, df, rocks, A):
        self.df, self.A = df, A
        self.D_MM = A["hole_diameter"]
        self.D_M = self.D_MM / 1000
        self.q_per_m = A["explosive_density"] * np.pi * self.D_M ** 2 / 4  # kg of explosive per metre of hole
        self.rocks = rocks.copy()
        self.rocks[["A", "A_min", "A_max"]] = [self.site_A(s) for s in self.rocks.site]
        # search grid: kept inside the ranges seen in the data
        self.PF_GRID = np.round(np.arange(df.Pf.min(), df.Pf.max() + 1e-9, 0.01), 2)
        self.BD_GRID = np.round(np.arange(max(25, df.B_D.min()), min(40, df.B_D.max()) + 1e-9, 0.25), 2)
        self.SB_GRID = np.round(np.arange(1.0, 1.5 + 1e-9, 0.05), 2)
        self.PF, self.BD, self.SB = np.meshgrid(self.PF_GRID, self.BD_GRID, self.SB_GRID, indexing="ij")

    # --- Kuz-Ram -------------------------------------------------------------
    def kuzram_X50_cm(self, A_rock, Pf, Q):
        return A_rock * Pf ** -0.8 * Q ** (1 / 6) * (115 / self.A["explosive_RWS"]) ** (19 / 30)

    def site_A(self, site):
        g = self.df[self.df.site == site]
        B = g.B_D * self.D_M
        Q = g.Pf * B * (g.S_B * B) * (g.H_B * B)
        A_each = g.X50 * 100 / self.kuzram_X50_cm(1.0, g.Pf, Q)
        return A_each.median(), A_each.min(), A_each.max()

    # --- one design (or a whole grid of designs) -----------------------------
    def evaluate(self, Pf, B_D, S_B, rock, A_scale=1.0, c_exp=None, c_drill=None):
        A = self.A
        c_exp = A["explosive_price"] if c_exp is None else c_exp
        c_drill = A["drilling_cost"] if c_drill is None else c_drill
        B = B_D * self.D_M
        S = S_B * B
        H = rock.bench_height_m
        J = A["subdrill_ratio"] * B
        T = rock.T_B_median * B
        V = B * S * H
        Q = Pf * V
        L_needed = Q / self.q_per_m
        L_free = H + J - T
        X50 = self.kuzram_X50_cm(rock.A * A_scale, Pf, Q) / 100
        L = np.minimum(L_needed, L_free)
        n = (2.2 - 14 * B / self.D_MM) * (1 - A["drilling_accuracy_W"] / B) * ((1 + S_B) / 2) * (L / H)
        over = np.exp(-0.693 * (A["oversize_limit"] / X50) ** n) * 100
        cost = Pf * c_exp + ((H + J) * c_drill + A["accessories_per_hole"]) / V
        return dict(X50_cm=X50 * 100, oversize_pct=over, cost=cost, n=n, fits=L_needed <= L_free,
                    H_B=H / B, Q_kg=Q, L_needed=L_needed, L_free=L_free, B=B, S=S)

    def feasible(self, e, target_cm=None, max_over=None):
        target_cm = self.A["target_X50"] * 100 if target_cm is None else target_cm
        max_over = self.A["max_oversize"] if max_over is None else max_over
        return ((e["X50_cm"] <= target_cm) & (e["oversize_pct"] <= max_over) & e["fits"]
                & (e["H_B"] >= 2) & (e["H_B"] <= self.df.H_B.max()))

    def optimise(self, rock, target_cm=None, max_over=None, **kw):
        e = self.evaluate(self.PF, self.BD, self.SB, rock, **kw)
        ok = self.feasible(e, target_cm, max_over)
        if not ok.any():
            return None
        i = np.unravel_index(np.argmin(np.where(ok, e["cost"], np.inf)), ok.shape)
        best = {k: float(np.asarray(v)[i]) for k, v in e.items()}
        best.update(Pf=float(self.PF[i]), B_D=float(self.BD[i]), S_B=float(self.SB[i]))
        edges = [name for name, grid, v in (("Pf", self.PF_GRID, self.PF[i]), ("B/D", self.BD_GRID, self.BD[i]),
                                             ("S/B", self.SB_GRID, self.SB[i])) if v in (grid[0], grid[-1])]
        best["on_boundary"] = ", ".join(edges) or "no"
        return best

    def frontier(self, rock, targets=np.arange(10, 61, 1.0), max_over=None, **kw):
        """Cheapest cost for each X50 target (the cost vs fragment-size trade-off)."""
        e = self.evaluate(self.PF, self.BD, self.SB, rock, **kw)
        ok = self.feasible(e, target_cm=1e9, max_over=max_over)
        x50, c = e["X50_cm"][ok], e["cost"][ok]
        return pd.DataFrame({"X50 target (cm)": targets,
                             "cheapest cost ($/m³)": [c[x50 <= t].min() if (x50 <= t).any() else np.nan for t in targets]})
