"""
fit_demo.py

Fit a delayed first-order response to noisy data, then test how reliable each
fitted parameter is as the measurement noise grows.

The model (like a charging RC circuit that starts after a delay):

    response(t) = 0                                       for t < delay
    response(t) = gain * (1 - exp(-(t - delay) / tau))    for t >= delay

Three unknowns: gain, delay and tau (the time constant).

What the script does
    1. Simulates noisy data from known "true" parameters.
    2. Recovers the parameters with scipy.optimize.curve_fit.
    3. Repeats the fit many times at increasing noise levels (the noise test)
       and reports how much each fitted parameter wanders.

Run:
    python3 fit_demo.py            # prints tables, saves two PNG figures
    python3 fit_demo.py --show     # also opens the figures on screen

Needs: numpy, scipy, matplotlib   (pip install numpy scipy matplotlib)
"""

import argparse

import numpy as np
from scipy.optimize import curve_fit


# ----------------------------------------------------------------------
# 1. The model
# ----------------------------------------------------------------------
def response(t, gain, delay, tau):
    """Delayed first-order step response, evaluated at every time in t."""
    out = np.zeros_like(t)              # start with zeros everywhere
    on = t >= delay                     # True where the response has begun
    out[on] = gain * (1 - np.exp(-(t[on] - delay) / tau))
    return out


# ----------------------------------------------------------------------
# 2. Simulating "measured" data
# ----------------------------------------------------------------------
def simulate(t, true_params, sigma, rng):
    """Perfect response plus Gaussian noise of standard deviation sigma."""
    clean = response(t, *true_params)
    noise = rng.normal(0, sigma, t.size)    # one random number per time point
    return clean + noise


# ----------------------------------------------------------------------
# 3. Fitting
# ----------------------------------------------------------------------
# Limits keep the fit physical: gain, delay and tau cannot be negative,
# and tau cannot collapse to zero.
LOWER = (0.0, 0.0, 0.05)
UPPER = (100.0, 10.0, 50.0)
START = (1.0, 1.0, 1.0)                 # starting guess p0 (gain, delay, tau)


def fit_once(t, y):
    """Fit the model to (t, y). Returns (popt, perr) or None if the fit fails.

    popt = best-fit values; perr = their one-standard-deviation uncertainty.
    """
    try:
        popt, pcov = curve_fit(response, t, y, p0=START,
                               bounds=(LOWER, UPPER), maxfev=5000)
    except (RuntimeError, ValueError):
        return None
    perr = np.sqrt(np.diag(pcov))
    return popt, perr


def rms_residual(t, y, popt):
    """Root-mean-square gap between data and fit. A good fit is near sigma."""
    return float(np.sqrt(np.mean((y - response(t, *popt)) ** 2)))


# ----------------------------------------------------------------------
# 4. The noise test
# ----------------------------------------------------------------------
def noise_test(t, true_params, sigmas, n_repeats, rng):
    """Repeat the fit n_repeats times at each noise level.

    Returns a dict: sigma -> array of fitted parameters (one row per good fit)
    plus the number of failed fits.
    """
    results = {}
    for sigma in sigmas:
        fits = []
        failures = 0
        for _ in range(n_repeats):
            y = simulate(t, true_params, sigma, rng)
            out = fit_once(t, y)
            if out is None:
                failures += 1
            else:
                fits.append(out[0])
        results[sigma] = (np.array(fits), failures)
    return results


def print_noise_table(results, true_params):
    names = ("gain", "delay", "tau")
    print("\nNoise test: spread of fitted values over repeated fits")
    print("true values:", dict(zip(names, true_params)))
    print(f"{'sigma':>6} {'fits':>5} | "
          f"{'gain mean±std':>16} {'delay mean±std':>16} {'tau mean±std':>16} | "
          f"relative spread (std/true)")
    for sigma, (fits, failures) in results.items():
        mean = fits.mean(axis=0)
        std = fits.std(axis=0)
        rel = std / np.array(true_params)
        cells = " ".join(f"{m:7.2f}±{s:<7.2f}" for m, s in zip(mean, std))
        rels = "  ".join(f"{n}={r:5.0%}" for n, r in zip(names, rel))
        print(f"{sigma:6.2f} {len(fits):5d} | {cells} | {rels}"
              + (f"   ({failures} failed)" if failures else ""))


# ----------------------------------------------------------------------
# 5. Plots
# ----------------------------------------------------------------------
def plot_examples(t, true_params, sigmas, rng, path):
    """One fitted example per noise level: data dots, fit line, true curve."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(sigmas), figsize=(4 * len(sigmas), 3.4),
                             sharey=True)
    for ax, sigma in zip(np.atleast_1d(axes), sigmas):
        y = simulate(t, true_params, sigma, rng)
        out = fit_once(t, y)
        ax.plot(t, y, ".", ms=3, alpha=0.6, label="noisy data")
        ax.plot(t, response(t, *true_params), "k--", lw=1, label="true curve")
        if out is not None:
            popt, perr = out
            ax.plot(t, response(t, *popt), lw=2, label="fit")
            ax.set_title(f"noise {sigma}\n"
                         f"gain {popt[0]:.2f}±{perr[0]:.2f}  "
                         f"delay {popt[1]:.2f}±{perr[1]:.2f}\n"
                         f"tau {popt[2]:.2f}±{perr[2]:.2f}", fontsize=8)
        ax.set_xlabel("time (s)")
    np.atleast_1d(axes)[0].set_ylabel("response")
    np.atleast_1d(axes)[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return fig


def plot_spread(results, true_params, path):
    """Relative spread of each parameter against noise level."""
    import matplotlib.pyplot as plt

    names = ("gain", "delay", "tau")
    sigmas = list(results.keys())
    fig, ax = plt.subplots(figsize=(5, 3.6))
    for i, name in enumerate(names):
        rel = [100 * results[s][0][:, i].std() / true_params[i] for s in sigmas]
        ax.plot(sigmas, rel, "o-", label=name)
    ax.set_xlabel("noise level (sigma)")
    ax.set_ylabel("spread of fitted value (% of true value)")
    ax.set_title("Which parameter stops being reliable first?", fontsize=9)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return fig


# ----------------------------------------------------------------------
# 6. Main
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--show", action="store_true",
                        help="open the figures on screen")
    parser.add_argument("--repeats", type=int, default=100,
                        help="fits per noise level in the noise test")
    args = parser.parse_args()

    if not args.show:
        import matplotlib
        matplotlib.use("Agg")           # draw to files only, no window

    rng = np.random.default_rng(0)      # fixed seed: same numbers every run
    t = np.linspace(0, 20, 400)         # 400 time points from 0 to 20 s
    true_params = (2.0, 3.0, 4.0)       # gain, delay, tau
    sigmas = (0.1, 0.5, 1.0, 2.0)       # noise levels to test

    # Step A: one clean fit, to see the method work.
    y = simulate(t, true_params, sigma=0.1, rng=rng)
    popt, perr = fit_once(t, y)
    print("One fit at noise 0.1")
    print("  true  :", true_params)
    print("  fitted:", np.round(popt, 2), "  uncertainty:", np.round(perr, 2))
    print("  residual rms:", round(rms_residual(t, y, popt), 3),
          "(should be close to the noise level, 0.1)")

    # Step B: the noise test.
    results = noise_test(t, true_params, sigmas, args.repeats, rng)
    print_noise_table(results, true_params)

    # Step C: figures.
    fig1 = plot_examples(t, true_params, sigmas, rng, "fit_examples.png")
    fig2 = plot_spread(results, true_params, "noise_spread.png")
    print("\nSaved: fit_examples.png, noise_spread.png")
    if args.show:
        import matplotlib.pyplot as plt
        plt.show()


if __name__ == "__main__":
    main()
