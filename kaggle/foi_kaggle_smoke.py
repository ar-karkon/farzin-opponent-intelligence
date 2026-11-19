"""FOI v1 Kaggle smoke test for ChessDS DSC and Maia-3, no real player data.

Run as a *private* Kaggle GPU script with Internet enabled. Produces
/kaggle/working/foi_smoke_results.json. Model weights are downloaded at run time.
NOT a training script and NOT a validated player-specific benchmark.
"""

from __future__ import annotations

import gc
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path

# First run: smallest models to verify the end-to-end pipeline.
# After a successful run, Codex may change to "dsc-150m" and "maia3-79m".
DSC_MODEL = "dsc-150m"
MAIA_MODEL = "maia3-79m"
OUT_DIR = Path("/kaggle/working") if Path("/kaggle/working").is_dir() else Path.cwd()
REPORT = OUT_DIR / "foi_smoke_results.json"


def save(payload: dict) -> None:
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"FOI report: {REPORT}", flush=True)


def install_deps() -> None:
    """No Kaggle credentials or other secrets should be required in this script."""
    pkgs = [
        "python-chess>=1.999",
        "safetensors",
        "huggingface_hub",
        "git+https://github.com/ChessDS/chessds-dsc.git@v0.1.0",
        "git+https://github.com/CSSLab/maia3.git",
    ]
    for pkg in pkgs:
        print(f"Installing {pkg} ...", flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])


def sample_position(chess_module):
    """Use a fully reconstructed move stack, not a FEN-only fake history."""
    board = chess_module.Board()
    for san in "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Be3 e5 Nb3 Be6".split():
        board.push_san(san)
    return board


def do_dsc(board, device: str):
    from chessds_dsc import DSC

    model = DSC.load(DSC_MODEL, device=device)
    prediction = model.predict(
        board, white_elo=2700, black_elo=2650, rating_system="fide", time_control="classical", venue="otb"
    )
    probabilities = {str(uci): float(prob) for uci, prob in prediction.moves.items()}
    legal = {m.uci() for m in board.legal_moves}
    if set(probabilities) != legal:
        raise AssertionError(f"DSC legal moves mismatch: have {len(probabilities)} expected {len(legal)}")
    if abs(sum(probabilities.values()) - 1.0) > 1e-3:
        raise AssertionError("DSC probabilities do not sum to 1")
    top = sorted(probabilities.items(), key=lambda pair: (-pair[1], pair[0]))[:5]
    result = {
        "model": DSC_MODEL,
        "device": device,
        "predicted_top5": [{"move_uci": m, "probability": p} for m, p in top],
        "legal_moves": len(legal),
        "probabilities_sum": sum(probabilities.values()),
        "probability_coverage": "full legal move set",
    }
    del prediction, model
    gc.collect()
    return result


def do_maia(board, device: str):
    # Maia-3's published UCI wrapper exposes ranked candidate moves, not
    # full legal-move policy values through standard UCI output. For this
    # smoke test we use its Python UCI implementation's INTERNAL helper,
    # which currently returns exact policy probabilities for the top-N.
    # Codex must stabilize a version-pinned public adapter before NLL testing.
    from maia3.uci import Maia3UCIEngine, parse_args
    from maia3.utils import seed_everything

    seed_everything(42)
    cfg = parse_args(
        [
            "--model",
            MAIA_MODEL,
            "--device",
            device,
            "--use-uci-history",
            "--temperature",
            "0",
            "--multipv",
            "5",
        ]
    )
    engine = Maia3UCIEngine(cfg)
    engine.ensure_model_loaded()
    history = " ".join(move.uci() for move in board.move_stack)
    engine.cmd_position("position startpos moves " + history)
    # UCI self/opponent ratings are relative to the side to move.
    engine.self_elo = 2700 if board.turn else 2650
    engine.oppo_elo = 2650 if board.turn else 2700
    predicted, candidates = engine.score_moves()
    if predicted is None or not candidates:
        raise AssertionError("Maia returned no legal move")
    top = [{"move_uci": entry["move"].uci(), "probability": float(entry["policy"])} for entry in candidates]
    legal = {m.uci() for m in board.legal_moves}
    if any(x["move_uci"] not in legal for x in top):
        raise AssertionError("Maia candidate is not legal")
    result = {
        "model": MAIA_MODEL,
        "device": device,
        "predicted_move_uci": predicted.uci(),
        "predicted_top5": top,
        "legal_moves": len(legal),
        "probability_coverage": "top-5 only; do NOT calculate NLL from this",
        "internal_maia_api_warning": "Uses Maia3UCIEngine.score_moves: version-pin for production",
    }
    del engine
    gc.collect()
    return result


def main():
    started = time.monotonic()
    payload = {
        "status": "started",
        "created_at_unix": time.time(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "purpose": "model and GPU smoke test only",
        "real_fide_games_used": 0,
        "models_requested": {"dsc": DSC_MODEL, "maia": MAIA_MODEL},
    }
    save(payload)
    try:
        import torch

        payload["torch"] = torch.__version__
        payload["cuda_available"] = torch.cuda.is_available()
        if not torch.cuda.is_available():
            raise RuntimeError("Kaggle CUDA unavailable. Confirm GPU is enabled.")
        payload["gpu"] = torch.cuda.get_device_name(0)
        payload["vram_gib"] = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
        print("CUDA ready:", payload["gpu"], payload["vram_gib"], "GiB", flush=True)

        install_deps()
        payload["packages"] = {}
        for name in ("chessds-dsc", "maia3", "python-chess", "safetensors", "huggingface-hub"):
            try:
                dist = importlib.metadata.distribution(name)
                direct = dist.read_text("direct_url.json")
                payload["packages"][name] = {"version": dist.version, "source": json.loads(direct) if direct else None}
            except importlib.metadata.PackageNotFoundError:
                payload["packages"][name] = None
        import chess

        board = sample_position(chess)
        payload["position"] = {
            "fen": board.fen(),
            "past_moves_uci": [move.uci() for move in board.move_stack],
            "white_elo": 2700,
            "black_elo": 2650,
            "rating_system": "fide",
            "time_control": "classical",
            "venue": "otb",
            "sample_is_synthetic": True,
        }
        model_started = time.monotonic()
        payload["dsc"] = do_dsc(board, "cuda")
        payload["dsc"]["elapsed_seconds"] = round(time.monotonic() - model_started, 3)
        save(payload)
        torch.cuda.empty_cache()
        model_started = time.monotonic()
        payload["maia3"] = do_maia(board, "cuda")
        payload["maia3"]["elapsed_seconds"] = round(time.monotonic() - model_started, 3)
        payload["elapsed_seconds"] = round(time.monotonic() - started, 3)
        payload["status"] = "completed"
        save(payload)
        print("FOI_SMOKE_SUCCESS", flush=True)
    except Exception as exc:
        payload["status"] = "error"
        payload["error_type"] = type(exc).__name__
        payload["error"] = str(exc)
        payload["traceback"] = traceback.format_exc(limit=20)
        save(payload)
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
