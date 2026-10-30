"""Command line: python -m evaluation [DATASET_DIR] [--markdown OUT.md]

Generates the synthetic dataset if it is missing, runs the evaluation with the
default settings and prints the results (US-12 AC1).
"""
import argparse
import json
from pathlib import Path

from dataset.generator import generate
from engine.settings import DEFAULT_SETTINGS

from .evaluate import run_evaluation, to_markdown


def main():
    parser = argparse.ArgumentParser(description="Measure VeriDoc accuracy on the synthetic dataset.")
    parser.add_argument("dataset", nargs="?", default="data/dataset")
    parser.add_argument("--markdown", help="also write the report as Markdown to this file")
    parser.add_argument("--json", help="also write the full report as JSON to this file")
    args = parser.parse_args()
    dataset = Path(args.dataset)
    if not (dataset / "ground_truth.json").exists():
        print(f"Generating the synthetic dataset in {dataset} …")
        generate(dataset)
    report = run_evaluation(dataset, DEFAULT_SETTINGS)
    text = to_markdown(report)
    print(text)
    if args.markdown:
        Path(args.markdown).write_text(text)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
