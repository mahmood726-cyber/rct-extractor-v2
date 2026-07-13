"""
recovery — the "better than the published MA" axes, deterministic and triangulated.

Every value carries provenance + confidence and FAILS CLOSED. The two axes that matter most:

1. SE TRIANGULATION. The standard error can be recovered from (a) the CI, (b) the p-value,
   (c) the test statistic. A well-reported trial gives >=2 routes. AGREEMENT corroborates;
   DISAGREEMENT beyond tolerance is a CAUGHT ERROR (a mis-parsed CI, a one- vs two-sided p,
   a wrong statistic), not noise. We return every route + a flag.

2. IMPUTATION-UNCERTAINTY PROPAGATION. When an SD is imputed from an IQR/range (Wan 2014,
   Luo 2018), it is an ESTIMATE with its own sampling variance. Nearly every published MA
   treats the imputed SD as KNOWN, which makes the study weight too large and the pooled CI
   too narrow. Propagating Var(sd_hat) into the study variance widens the interval correctly.
   This is a place we are straightforwardly better than the literature.

Ratio effects are handled on the log scale. All functions are pure; no I/O.
"""
import math
from statistics import NormalDist

_Z = {0.90: 1.6448536269514722, 0.95: 1.959963984540054, 0.99: 2.5758293035489004}
_ndist = NormalDist()

def _z(level): return _Z.get(round(level, 2), _ndist.inv_cdf(1 - (1 - level) / 2))


# ---------------- SE triangulation ----------------
def se_from_ci(lo, hi, level=0.95, log_scale=False):
    if lo is None or hi is None or hi <= lo:
        return None
    if log_scale:
        if lo <= 0 or hi <= 0:
            return None
        return (math.log(hi) - math.log(lo)) / (2 * _z(level))
    return (hi - lo) / (2 * _z(level))

def se_from_p(effect, p, log_scale=False, two_sided=True):
    """SE of the (log) effect from a two-sided p-value and the point estimate."""
    if p is None or effect is None or not (0 < p < 1):
        return None
    est = math.log(effect) if log_scale else effect
    null = 0.0 if not log_scale else 0.0     # ratio null is 1 -> log 1 = 0
    pp = p / 2 if two_sided else p
    z = _ndist.inv_cdf(1 - pp)
    if z == 0:
        return None
    return abs(est - null) / z

def se_from_t(effect, t, log_scale=False):
    if t in (None, 0) or effect is None:
        return None
    est = math.log(effect) if log_scale else effect
    return abs(est) / abs(t)

def triangulate_se(effect=None, ci=None, p=None, t=None, level=0.95, log_scale=False,
                   rel_tol=0.15):
    """Return {routes, se, agree, spread, provenance, confidence}. Fails closed: if the
    routes disagree beyond rel_tol the value is FLAGGED (agree=False), not silently averaged."""
    routes = {}
    if ci:
        routes["ci"] = se_from_ci(ci[0], ci[1], level, log_scale)
    if p is not None:
        routes["p"] = se_from_p(effect, p, log_scale)
    if t is not None:
        routes["t"] = se_from_t(effect, t, log_scale)
    vals = [v for v in routes.values() if v and v > 0]
    if not vals:
        return {"routes": routes, "se": None, "agree": None, "spread": None,
                "provenance": "none", "confidence": 0.0}
    lo, hi = min(vals), max(vals)
    spread = (hi - lo) / hi if hi > 0 else 0.0
    agree = len(vals) < 2 or spread <= rel_tol
    se = sum(vals) / len(vals)
    conf = 0.5 if len(vals) < 2 else (0.95 if agree else 0.2)
    return {"routes": routes, "se": se, "agree": agree, "spread": spread,
            "provenance": "+".join(k for k, v in routes.items() if v),
            "confidence": conf}


# ---------------- SD imputation with propagated uncertainty ----------------
def sd_from_iqr(q1, q3, n):
    """Wan 2014 (median/IQR, method 2): SD ~= IQR / (2*Phi^-1((0.75n-0.125)/(n+0.25)))."""
    if None in (q1, q3, n) or n < 1 or q3 < q1:
        return None
    denom = 2 * _ndist.inv_cdf((0.75 * n - 0.125) / (n + 0.25))
    return (q3 - q1) / denom if denom > 0 else None

def sd_from_range(lo, hi, n):
    """Wan 2014 (min/max, method 1): SD ~= range / (2*Phi^-1((n-0.375)/(n+0.25)))."""
    if None in (lo, hi, n) or n < 2 or hi < lo:
        return None
    denom = 2 * _ndist.inv_cdf((n - 0.375) / (n + 0.25))
    return (hi - lo) / denom if denom > 0 else None

def var_of_sd_estimate(sd, n):
    """Sampling variance of an SD estimate ~ sd^2 / (2(n-1)). Used to propagate imputation
    uncertainty: an imputed SD is not known, it is estimated."""
    if sd is None or n is None or n <= 1:
        return None
    return sd * sd / (2 * (n - 1))


# ---------------- pooling with vs without imputation uncertainty ----------------
def _dl_pool(yi, vi):
    """Random-effects DerSimonian-Laird pool. Returns (mu, se_mu, tau2)."""
    k = len(yi)
    w = [1 / v for v in vi]
    mu_fe = sum(wi * y for wi, y in zip(w, yi)) / sum(w)
    Q = sum(wi * (y - mu_fe) ** 2 for wi, y in zip(w, yi))
    c = sum(w) - sum(wi * wi for wi in w) / sum(w)
    tau2 = max(0.0, (Q - (k - 1)) / c) if c > 0 else 0.0
    wr = [1 / (v + tau2) for v in vi]
    mu = sum(wi * y for wi, y in zip(wr, yi)) / sum(wr)
    se = math.sqrt(1 / sum(wr))
    return mu, se, tau2

def pool_compare_imputation(yi, vi, imputed_extra_var):
    """Pool twice: (naive) treating imputed SDs as known vs (correct) adding each study's
    imputation variance to its vi. Returns both CIs + the width inflation. `imputed_extra_var`
    is a per-study additive variance (0 for directly-reported studies)."""
    z = _z(0.95)
    mu0, se0, t0 = _dl_pool(yi, vi)
    vi2 = [v + e for v, e in zip(vi, imputed_extra_var)]
    mu1, se1, t1 = _dl_pool(yi, vi2)
    w0, w1 = 2 * z * se0, 2 * z * se1
    return {
        "naive": {"mu": mu0, "ci": (mu0 - z * se0, mu0 + z * se0), "ci_width": w0, "tau2": t0},
        "propagated": {"mu": mu1, "ci": (mu1 - z * se1, mu1 + z * se1), "ci_width": w1, "tau2": t1},
        "ci_width_inflation": (w1 / w0 - 1) if w0 > 0 else None,
    }
