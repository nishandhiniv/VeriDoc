"""Robustness probe: held-out seed and harsher degradation.

python -m evaluation.stress OUT_DIR

Not part of the D3 headline numbers. It shows where the engine stops reading
with confidence, and checks that the fail-safe still holds when it does.
"""
import io
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

import dataset.generator as gen
from engine.settings import DEFAULT_SETTINGS

from .evaluate import evaluate_marksheets

LEVELS = {
    # name: (max skew °, blur radius range, brightness range, noise sd range, JPEG quality range)
    "standard (as in D3)": None,
    "harsh": (3.5, (1.3, 1.8), (0.5, 0.62), (12, 16), (35, 45)),
    "extreme": (5.0, (1.8, 2.6), (0.38, 0.5), (16, 22), (22, 32)),
}


def make_degrade(skew, blur, light, noise, quality):
    def degrade(img, rng):
        angle = rng.uniform(-skew, skew)
        out = img.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=(235, 233, 225))
        out = out.filter(ImageFilter.GaussianBlur(rng.uniform(*blur)))
        out = ImageEnhance.Brightness(out).enhance(rng.uniform(*light))
        arr = np.asarray(out).astype(np.float32)
        arr += np.random.default_rng(rng.randint(0, 2 ** 31)).normal(0, rng.uniform(*noise), arr.shape)
        buf = io.BytesIO()
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(buf, "JPEG", quality=rng.randint(*quality))
        return Image.open(io.BytesIO(buf.getvalue())), {"angle": round(angle, 2)}
    return degrade


def main(out_dir, seed=7):
    original = gen.degrade
    rows = []
    for name, params in LEVELS.items():
        gen.degrade = original if params is None else make_degrade(*params)
        target = Path(out_dir) / name.split()[0]
        gen.generate(target, seed=seed, photos=False)
        errors = []
        m = evaluate_marksheets(target, DEFAULT_SETTINGS, errors)
        deg = [g for g in m["groups"] if g["variant"] == "degraded"]
        fields = sum(g["fields"] for g in deg)
        rows.append((name, m["clean_accuracy"], round(100 * sum(g["correct"] for g in deg) / fields, 1),
                     sum(g["untrusted"] for g in deg), sum(g["wrong"] for g in deg), m["outcomes"]["false_match"],
                     m["applications"]["planted_to_review_pct"], m["applications"]["clean_to_review_pct"]))
    gen.degrade = original
    print(f"Held-out seed {seed} (the engine was developed on seed {gen.SEED}); 40 sheets per level.\n")
    print("| Degradation | Clean acc. | Degraded acc. | Unsure → review | Wrong but trusted | False matches "
          "| Planted errors → review | Correct apps → review |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r[0]} | {r[1]} % | {r[2]} % | {r[3]} | {r[4]} | {r[5]} | {r[6]} % | {r[7]} % |")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/stress")
