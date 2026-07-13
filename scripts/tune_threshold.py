"""
Threshold Tuner for SFace face recognition.

Usage:
    python scripts/tune_threshold.py --known-dir ./known_faces --impostor-dir ./impostor_faces

Output:
    - Console report of FAR/FRR/EER at various thresholds
    - Suggested optimal recognition_threshold and unknown_threshold
    - CSV file with full pairwise similarity matrix
"""
import os
import sys
import json
import csv
import argparse
import itertools
import re
from pathlib import Path

CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

import cv2
import numpy as np
from face_pipeline import FacePipeline


def load_images_from_dir(dir_path: str, label: str) -> list[dict]:
    images = []
    supported = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
    for fpath in sorted(Path(dir_path).rglob("*")):
        if fpath.suffix.lower() not in supported:
            continue
        person_name = re.sub(r"_\d+$", "", fpath.stem)
        img = cv2.imread(str(fpath))
        if img is None:
            print(f"  [SKIP] Cannot read {fpath}")
            continue
        images.append({"path": str(fpath), "person": person_name, "label": label, "image": img})
    return images


def extract_embeddings(pipeline: FacePipeline, images: list[dict]) -> list[dict]:
    for item in images:
        faces = pipeline.detect_faces(item["image"], score_threshold=0.5)
        if not faces:
            item["embedding"] = None
            print(f"  [NO FACE] {item['path']}")
            continue
        faces.sort(key=lambda f: f["score"], reverse=True)
        face = faces[0]
        emb = pipeline.extract_embedding(item["image"], face["raw_face"])
        item["embedding"] = np.array(emb, dtype=np.float32)
        print(f"  [OK] {item['person']:20s} | {item['path']}")
    return images


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a <= 1e-6 or norm_b <= 1e-6:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def compute_pairwise_scores(known: list[dict], impostors: list[dict]) -> list[dict]:
    scores = []
    # Genuine pairs: same person
    for person_name, group in itertools.groupby(
        sorted(known, key=lambda x: x["person"]), key=lambda x: x["person"]
    ):
        items = list(group)
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i]["embedding"] is None or items[j]["embedding"] is None:
                    continue
                sim = cosine_similarity(items[i]["embedding"], items[j]["embedding"])
                scores.append({
                    "type": "genuine",
                    "person_a": person_name,
                    "person_b": person_name,
                    "sim": sim,
                    "file_a": items[i]["path"],
                    "file_b": items[j]["path"],
                })

    # Impostor pairs: different known persons
    all_known = [x for x in known if x["embedding"] is not None]
    for i in range(len(all_known)):
        for j in range(i + 1, len(all_known)):
            if all_known[i]["person"] == all_known[j]["person"]:
                continue
            sim = cosine_similarity(all_known[i]["embedding"], all_known[j]["embedding"])
            scores.append({
                "type": "impostor_known",
                "person_a": all_known[i]["person"],
                "person_b": all_known[j]["person"],
                "sim": sim,
                "file_a": all_known[i]["path"],
                "file_b": all_known[j]["path"],
            })

    # Impostor pairs: known vs impostor set
    valid_impostors = [x for x in impostors if x["embedding"] is not None]
    for k, imp in itertools.product(all_known, valid_impostors):
        sim = cosine_similarity(k["embedding"], imp["embedding"])
        scores.append({
            "type": "impostor_unknown",
            "person_a": k["person"],
            "person_b": imp["person"],
            "sim": sim,
            "file_a": k["path"],
            "file_b": imp["path"],
        })

    return scores


def evaluate_thresholds(scores: list[dict], output_csv: str):
    genuine = np.array([s["sim"] for s in scores if s["type"] == "genuine"])
    impostor = np.array([s["sim"] for s in scores if s["type"] != "genuine"])

    print("\n" + "=" * 70)
    print("THRESHOLD EVALUATION REPORT")
    print("=" * 70)
    print(f"  Genuine pairs (same person):  {len(genuine)}")
    print(f"  Impostor pairs (different):   {len(impostor)}")
    print(f"  Total pairs:                  {len(scores)}")

    if len(genuine) == 0 or len(impostor) == 0:
        print("\n  ERROR: Need both genuine and impostor pairs to evaluate.")
        return

    print(f"\n  Genuine similarity:  mean={genuine.mean():.4f}  std={genuine.std():.4f}")
    print(f"  Impostor similarity: mean={impostor.mean():.4f}  std={impostor.std():.4f}")
    print(f"  Separation gap:      {genuine.mean() - impostor.mean():.4f}")

    print("\n" + "-" * 70)
    print(f"{'Threshold':>10} | {'FAR':>8} | {'FRR':>8} | {'EER_metric':>10} | {'TPR':>8} | {'Precision':>10} | {'F1':>8}")
    print("-" * 70)

    rows = []
    best_eer = float("inf")
    best_thresh = 0.5

    for t in np.arange(0.10, 0.99, 0.01):
        t = round(t, 2)
        far = float((impostor >= t).sum() / len(impostor)) if len(impostor) > 0 else 0.0
        frr = float((genuine < t).sum() / len(genuine)) if len(genuine) > 0 else 0.0
        eer_metric = abs(far - frr)
        tp = int((genuine >= t).sum())
        fp = int((impostor >= t).sum())
        fn = int((genuine < t).sum())
        tn = int((impostor < t).sum())
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = 2 * (precision * tpr) / (precision + tpr) if (precision + tpr) > 0 else 0.0

        rows.append({
            "threshold": t,
            "far": far,
            "frr": frr,
            "eer_metric": eer_metric,
            "tpr": tpr,
            "precision": precision,
            "f1": f1,
        })

        marker = " <<< EER" if eer_metric < best_eer and t > 0.3 else ""
        if eer_metric < best_eer:
            best_eer = eer_metric
            best_thresh = t

        print(f"{t:>10.2f} | {far:>8.4f} | {frr:>8.4f} | {eer_metric:>10.4f} | {tpr:>8.4f} | {precision:>10.4f} | {f1:>8.4f}{marker}")

    print("-" * 70)

    # Find EER point (where FAR == FRR closest)
    print(f"\n  >> Optimal threshold (EER point): {best_thresh:.2f} (FAR={rows[0]['far']:.4f}, FRR={rows[0]['frr']:.4f})")

    # Find threshold that maximizes F1
    best_f1_row = max(rows, key=lambda r: r["f1"])
    print(f"  >> Threshold @ max F1 ({best_f1_row['f1']:.4f}): {best_f1_row['threshold']:.2f} (FAR={best_f1_row['far']:.4f}, TPR={best_f1_row['tpr']:.4f})")

    # Find threshold with low FAR (<1%) while maximizing TPR
    low_far_candidates = [r for r in rows if r["far"] <= 0.01]
    if low_far_candidates:
        best_low_far = max(low_far_candidates, key=lambda r: r["tpr"])
        print(f"  >> Recommended KNOWN threshold (FAR≤1%, max TPR): {best_low_far['threshold']:.2f}")
        print(f"     (FAR={best_low_far['far']:.4f}, FRR={best_low_far['frr']:.4f}, TPR={best_low_far['tpr']:.4f})")

    # Find threshold for unknown re-ID (more lenient, e.g. FAR <= 5%)
    med_far_candidates = [r for r in rows if 0.01 < r["far"] <= 0.10]
    if med_far_candidates:
        best_med_far = max(med_far_candidates, key=lambda r: r["tpr"])
        print(f"  >> Recommended UNKNOWN threshold (FAR≤10%, max TPR): {best_med_far['threshold']:.2f}")
        print(f"     (FAR={best_med_far['far']:.4f}, FRR={best_med_far['frr']:.4f}, TPR={best_med_far['tpr']:.4f})")

    # Current defaults
    print(f"\n  Current defaults in code:")
    print(f"     recognition_threshold = 0.60   (KNOWN match)")
    print(f"     unknown_threshold     = 0.55   (UNKNOWN re-ID)")

    print("\n  To apply: update CameraConfig via DB or API:")
    rec_opt = f"{best_f1_row['threshold']:.2f}"
    if low_far_candidates:
        rec_opt += f"  # or {best_low_far['threshold']:.2f} for stricter"
    print(f"     recognition_threshold = {rec_opt}")
    if med_far_candidates:
        print(f"     unknown_threshold     = {best_med_far['threshold']:.2f}")
    print()
    print("=" * 70)

    # Write CSV
    if output_csv:
        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "threshold", "far", "frr", "eer_metric", "tpr", "precision", "f1"
            ])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n  CSV written to: {output_csv}")

    # Write pairwise similarity matrix
    pairwise_csv = output_csv.replace(".csv", "_pairs.csv") if output_csv else "threshold_pairs.csv"
    with open(pairwise_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "type", "person_a", "person_b", "similarity", "file_a", "file_b"
        ])
        writer.writeheader()
        for s in scores:
            writer.writerow({
                "type": s["type"],
                "person_a": s["person_a"],
                "person_b": s["person_b"],
                "similarity": f"{s['sim']:.6f}",
                "file_a": s["file_a"],
                "file_b": s["file_b"],
            })
    print(f"  Pairwise similarity matrix: {pairwise_csv}")

    return best_thresh


def main():
    parser = argparse.ArgumentParser(
        description="Tune SFace face recognition threshold using real images."
    )
    parser.add_argument(
        "--known-dir", required=True,
        help="Directory with known/enrolled person images. Filename (without ext) = person name."
    )
    parser.add_argument(
        "--impostor-dir", default=None,
        help="Directory with impostor/unknown person images (not enrolled)."
    )
    parser.add_argument(
        "--output", default="threshold_report.csv",
        help="Output CSV file for threshold evaluation."
    )
    args = parser.parse_args()

    print("Initializing FacePipeline...")
    pipeline = FacePipeline()
    print("FacePipeline ready.\n")

    print("Loading known faces...")
    known = load_images_from_dir(args.known_dir, "known")

    impostors = []
    if args.impostor_dir and os.path.isdir(args.impostor_dir):
        print("\nLoading impostor faces...")
        impostors = load_images_from_dir(args.impostor_dir, "impostor")

    if not known:
        print("ERROR: No valid face images found in --known-dir.")
        sys.exit(1)

    print(f"\nExtracting embeddings ({len(known) + len(impostors)} images)...")
    known = extract_embeddings(pipeline, known)
    if impostors:
        impostors = extract_embeddings(pipeline, impostors)

    valid_known = [x for x in known if x["embedding"] is not None]
    print(f"\nSuccessfully extracted: {len(valid_known)}/{len(known)} known, "
          f"{len([x for x in impostors if x['embedding'] is not None])}/{len(impostors)} impostor")

    if len(valid_known) < 2:
        print("ERROR: Need at least 2 valid known faces (with 2+ images each) to compute scores.")
        sys.exit(1)

    print("\nComputing pairwise similarities...")
    scores = compute_pairwise_scores(known, impostors)

    evaluate_thresholds(scores, args.output)


if __name__ == "__main__":
    main()
