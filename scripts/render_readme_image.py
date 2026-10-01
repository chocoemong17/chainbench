"""Render the README preview from a full CLI deblurring record, without a new run."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path

from smoke_deblurring import validate_deblurring

from chainbench.deblur_views import image_uri


def render(record):
    validate_deblurring(record)
    if record["parameters"]["steps"] != 10000:
        raise ValueError("The README preview requires the full 10,000-update protocol")
    problem, runs = record["problem"], record["runs"]
    provenance = {
        "kind": "chainbench.readme-preview",
        "source": record["source"],
        "parameters": record["parameters"],
        "input_hashes": {k: v for k, v in problem.items() if k.endswith("sha256")},
        "environment": record["environment"],
        "final_observations": {k: v["rows"][-1] for k, v in runs.items()},
        "final_image_hashes": {k: v["snapshots"][-1]["sha256"] for k, v in runs.items()},
        "display": "Shared [0,1] grayscale, round-to-nearest byte; display-only clipping",
    }
    tiles = [
        ("Clean input", "Public procedural image", problem["clean_image"]),
        ("Blurred observation", "Start for both methods", problem["observed_image"]),
        ("ISTA · 10,000 updates", "Same fixed step and budget", runs["ista"]["snapshots"][-1]["image"]),
        ("FISTA · 10,000 updates", "Same fixed step and budget", runs["fista"]["snapshots"][-1]["image"]),
    ]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 646" role="img" '
        'aria-labelledby="title description">',
        '<title id="title">A computed noiseless image experiment</title>',
        '<desc id="description">Clean and blurred 64 by 64 images, then actual ISTA and '
        'FISTA reconstructions after 10,000 updates. Beck–Teboulle Figure 5 protocol '
        'subset, lambda zero, Gaussian blur sigma four, L two. One synthetic experiment '
        'with declared source differences, not a universal ranking.</desc>',
        '<metadata id="chainbench-preview">' + escape(json.dumps(provenance)) + '</metadata>',
        '<rect width="680" height="646" rx="18" fill="#f3f7fa"/>',
    ]
    for i, (title, subtitle, values) in enumerate(tiles):
        x, y = 24 + (i % 2) * 328, 18 + (i // 2) * 316
        svg.extend([
            f'<g transform="translate({x} {y})" font-family="sans-serif" fill="#173148">',
            f'<text x="0" y="24" font-size="22" font-weight="600">{escape(title)}</text>',
            f'<text x="0" y="48" font-size="17">{escape(subtitle)}</text>',
            f'<image x="36" y="65" width="232" height="232" '
            f'style="image-rendering:pixelated" href="{image_uri(values)}"/>',
            '</g>',
        ])
    svg.append('</svg>\n')
    return "".join(svg)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(render(json.loads(args.record.read_text(encoding="utf-8"))), encoding="utf-8")


if __name__ == "__main__":
    main()
