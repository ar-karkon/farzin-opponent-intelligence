from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import chess
import chess.pgn

from foi_pipeline.dataset import Source, ingest
from foi_pipeline.evaluation import evaluate


def synthetic_game(day: date, event: str = "Fixture") -> str:
    game = chess.pgn.Game()
    game.headers.update(
        {
            "Event": event,
            "Site": "Fixture",
            "Date": day.strftime("%Y.%m.%d"),
            "Round": "1",
            "White": "Fixture Player A",
            "Black": "Fixture Player B",
            "WhiteFideId": "9000001",
            "BlackFideId": "9000002",
            "Result": "1/2-1/2",
            "TimeControl": "5400+30",
        }
    )
    board = game.board()
    node = game
    for san in ("e4", "e5", "Nf3", "Nc6", "Bb5", "a6"):
        move = board.parse_san(san)
        node = node.add_variation(move)
        board.push(move)
    return game.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False))


class DatasetPipelineTests(unittest.TestCase):
    def test_local_validation_command_writes_private_dataset_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pgn = root / "fixture.pgn"
            pgn.write_text(synthetic_game(date(2020, 1, 1)), encoding="utf-8")
            players = root / "players.yaml"
            players.write_text(
                "players:\n  - fide_id: '9000001'\n    display_name: Fixture Player A\n    verification_source: synthetic fixture only\n"
                "identity_map:\n  - fide_id: '9000002'\n    canonical_name: Fixture Player B\n    verification_source: synthetic fixture only\n",
                encoding="utf-8",
            )
            ratings = root / "ratings.csv"
            ratings.write_text(
                "fide_id,month,standard_elo,source_url\n"
                "9000001,2020-01,2500,https://example.invalid/rating-a\n"
                "9000002,2020-01,2450,https://example.invalid/rating-b\n",
                encoding="utf-8",
            )
            manifest = root / "sources.csv"
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["pgn_path", "source_type", "source_url", "source_license"])
                writer.writeheader()
                writer.writerow(
                    {
                        "pgn_path": str(pgn),
                        "source_type": "manual",
                        "source_url": "https://example.invalid/fixture",
                        "source_license": "synthetic fixture only",
                    }
                )
            reviews = root / "reviews.csv"
            with reviews.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "source_file",
                        "game_index",
                        "time_control_classical_verified",
                        "classification_source",
                        "venue_otb_verified",
                        "venue_source",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "source_file": str(pgn.resolve()),
                        "game_index": 0,
                        "time_control_classical_verified": "true",
                        "classification_source": "synthetic fixture only",
                        "venue_otb_verified": "true",
                        "venue_source": "synthetic fixture only",
                    }
                )
            output = root / "validated"
            repo = Path(__file__).resolve().parents[1]
            completed = subprocess.run(
                [
                    sys.executable,
                    str(repo / "scripts/validate_dataset.py"),
                    "--players",
                    str(players),
                    "--ratings",
                    str(ratings),
                    "--reviews",
                    str(reviews),
                    "--source-manifest",
                    str(manifest),
                    "--output-dir",
                    str(output),
                ],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            summary = json.loads((output / "validation.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["eligible_games"], 1)
            self.assertEqual(summary["target_positions"], 3)
            self.assertEqual(len((output / "positions.jsonl").read_text(encoding="utf-8").splitlines()), 3)

    def test_dedup_legal_history_target_only_and_chronological_splits(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pgn = root / "fixture.pgn"
            dates = [date(2020, 1, 1) + timedelta(days=i * 40) for i in range(5)]
            pgn.write_text("\n\n".join(synthetic_game(day) for day in dates) + "\n", encoding="utf-8")
            duplicate = root / "duplicate.pgn"
            duplicate.write_text(synthetic_game(dates[0], "Other source copy") + "\n", encoding="utf-8")
            rating_csv = root / "ratings.csv"
            rating_csv.write_text(
                "fide_id,month,standard_elo,source_url\n"
                "9000001,2020-01,2500,https://ratings.example/2020-01\n"
                "9000002,2020-01,2450,https://ratings.example/2020-01\n",
                encoding="utf-8",
            )
            reviews = []
            for path, count in ((pgn, 5), (duplicate, 1)):
                reviews.extend(
                    {
                        "source_file": str(path.resolve()),
                        "game_index": str(index),
                        "time_control_classical_verified": "true",
                        "classification_source": "fixture-only official event metadata",
                        "venue_otb_verified": "true",
                        "venue_source": "fixture-only organizer event page",
                        "event_id": "synthetic-fixture",
                        "source_issue": "synthetic test data",
                    }
                    for index in range(count)
                )
            players = {
                "players": [
                    {
                        "fide_id": "9000001",
                        "display_name": "Fixture Player A",
                        "verification_source": "synthetic test fixture only",
                    }
                ],
                "identity_map": [
                    {
                        "fide_id": "9000002",
                        "canonical_name": "Fixture Player B",
                        "verification_source": "synthetic test fixture only",
                    }
                ],
            }
            sources = [
                Source(pgn, "manual", "https://example.invalid/fixture.pgn", "fixture-only"),
                Source(duplicate, "twic", "https://example.invalid/twic-copy.pgn", "fixture-only"),
            ]
            # Inject review rows without writing a persistent real-player configuration.
            import csv

            review_csv = root / "reviews.csv"
            with review_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(reviews[0]))
                writer.writeheader()
                writer.writerows(reviews)
            games, _quarantine, outputs = ingest(sources, players, rating_csv, review_csv)
            summary = outputs["summary"]
            self.assertEqual(summary["eligible_games"], 5)
            self.assertEqual(summary["exclusions"]["duplicate_game"], 1)
            self.assertEqual(summary["target_positions"], 15)
            self.assertEqual(len(games), 5)
            self.assertEqual(len({position["target_fide_id"] for position in outputs["positions"]}), 1)
            self.assertTrue(all(len(row["prior_positions_fen"]) <= 7 for row in outputs["positions"]))
            self.assertEqual(
                next(row for row in outputs["positions"] if row["ply_index"] == 0)["prior_positions_fen"], []
            )
            self.assertTrue(all(row["actual_move_uci"] in row["legal_moves_uci"] for row in outputs["positions"]))
            split_dates = {}
            for game in games:
                split_dates.setdefault(game["split"], []).append(game["date"])
            ordered_splits = ["train", "validation", "historical_test"]
            nonempty = [(name, split_dates[name]) for name in ordered_splits if name in split_dates]
            for (_left_name, left), (_right_name, right) in zip(nonempty, nonempty[1:]):
                self.assertLess(max(left), min(right))
            for row in outputs["positions"]:
                board = chess.Board()
                for move_uci in row["prior_moves_uci"]:
                    move = chess.Move.from_uci(move_uci)
                    self.assertIn(move, board.legal_moves)
                    board.push(move)
                self.assertEqual(board.fen(), row["fen_before"])

    def test_no_targets_or_missing_evidence_are_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pgn = root / "fixture.pgn"
            pgn.write_text(synthetic_game(date(2020, 1, 1)), encoding="utf-8")
            games, _quarantine, outputs = ingest(
                [Source(pgn, "manual", "", "")],
                {"players": [], "identity_map": []},
                None,
                None,
            )
            self.assertEqual(games, [])
            self.assertEqual(outputs["summary"]["status"], "no_eligible_games")
            self.assertGreater(outputs["summary"]["quarantined_games"], 0)


class EvaluationTests(unittest.TestCase):
    def test_full_policy_scoring_and_deterministic_rank(self):
        rows = []
        for game_id, actual in (("g1", "e2e4"), ("g2", "d2d4")):
            policy = {"e2e4": 0.5, "d2d4": 0.3, "g1f3": 0.2}
            if actual == "d2d4":
                policy = {"d2d4": 0.5, "e2e4": 0.3, "g1f3": 0.2}
            rows.append(
                {
                    "sample_id": game_id + "-p1",
                    "game_id": game_id,
                    "target_fide_id": "9000001",
                    "target_color": "white",
                    "phase": "opening",
                    "opening_key": "e2e4",
                    "split": "historical_test",
                    "actual_move_uci": actual,
                    "legal_moves_uci": sorted(policy),
                    "models": {"dsc-150m": {"probabilities": policy}, "maia3-79m": {"probabilities": policy}},
                }
            )
        metrics = evaluate(rows, bootstrap_draws=10, seed=4)
        self.assertEqual(metrics["status"], "evaluated")
        self.assertEqual(metrics["models"]["dsc-150m"]["top1"], 1.0)
        self.assertEqual(metrics["models"]["maia3-79m"]["top5"], 1.0)
        self.assertIn("target_fide_id", metrics["models"]["dsc-150m"]["by"])

    def test_rejects_top_five_or_malformed_policy(self):
        row = {
            "sample_id": "s1",
            "game_id": "g1",
            "actual_move_uci": "e2e4",
            "legal_moves_uci": ["e2e4", "d2d4"],
            "models": {"dsc-150m": {"probabilities": {"e2e4": 1.0}}, "maia3-79m": {"probabilities": {"e2e4": 1.0}}},
        }
        with self.assertRaises(ValueError):
            evaluate([row], bootstrap_draws=1)


if __name__ == "__main__":
    unittest.main()
