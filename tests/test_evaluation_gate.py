import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import train


class FakeMlflowClient:
    def __init__(self, production_runs=None):
        self.production_runs = production_runs or []
        self.set_tags = []
        self.deleted_tags = []

    def get_experiment_by_name(self, _name):
        return SimpleNamespace(experiment_id="experiment-1")

    def search_runs(self, experiment_ids, filter_string=None, order_by=None, max_results=None):
        if filter_string == "tags.stage = 'Production'" and max_results == 1:
            return self.production_runs[:1]
        if filter_string == "tags.stage = 'Production'":
            return self.production_runs
        return []

    def set_tag(self, run_id, key, value):
        self.set_tags.append((run_id, key, value))

    def delete_tag(self, run_id, key):
        self.deleted_tags.append((run_id, key))


def fake_run(run_id, metrics):
    return SimpleNamespace(
        info=SimpleNamespace(run_id=run_id),
        data=SimpleNamespace(metrics=metrics),
    )


class EvaluationGateTests(unittest.TestCase):
    def test_promotes_when_no_production_model_exists(self):
        client = FakeMlflowClient()

        promoted = train.evaluation_gate(
            client,
            "new-run",
            {"test_f1": 0.80, "test_auc": 0.90},
        )

        self.assertTrue(promoted)
        self.assertEqual(client.set_tags, [("new-run", "stage", "Production")])
        self.assertEqual(client.deleted_tags, [])

    def test_rejects_worse_model(self):
        client = FakeMlflowClient([
            fake_run("prod-run", {"test_f1": 0.91, "test_auc": 0.97})
        ])

        promoted = train.evaluation_gate(
            client,
            "new-run",
            {"test_f1": 0.75, "test_auc": 0.98},
        )

        self.assertFalse(promoted)
        self.assertEqual(client.set_tags, [])
        self.assertEqual(client.deleted_tags, [])

    def test_promotes_better_f1_model_and_removes_old_production_tag(self):
        client = FakeMlflowClient([
            fake_run("prod-run", {"test_f1": 0.88, "test_auc": 0.97})
        ])

        promoted = train.evaluation_gate(
            client,
            "new-run",
            {"test_f1": 0.89, "test_auc": 0.95},
        )

        self.assertTrue(promoted)
        self.assertEqual(client.deleted_tags, [("prod-run", "stage")])
        self.assertEqual(client.set_tags, [("new-run", "stage", "Production")])

    def test_promotes_equal_f1_model_only_when_auc_is_better(self):
        client = FakeMlflowClient([
            fake_run("prod-run", {"test_f1": 0.88, "test_auc": 0.91})
        ])

        promoted = train.evaluation_gate(
            client,
            "new-run",
            {"test_f1": 0.88, "test_auc": 0.92},
        )

        self.assertTrue(promoted)
        self.assertEqual(client.deleted_tags, [("prod-run", "stage")])
        self.assertEqual(client.set_tags, [("new-run", "stage", "Production")])

    def test_rejects_equal_f1_model_when_auc_is_not_better(self):
        client = FakeMlflowClient([
            fake_run("prod-run", {"test_f1": 0.88, "test_auc": 0.91})
        ])

        promoted = train.evaluation_gate(
            client,
            "new-run",
            {"test_f1": 0.88, "test_auc": 0.90},
        )

        self.assertFalse(promoted)
        self.assertEqual(client.set_tags, [])
        self.assertEqual(client.deleted_tags, [])


class TrainingDataResolutionTests(unittest.TestCase):
    def test_downloads_gcs_uri_to_tmp_file(self):
        fake_blob = SimpleNamespace(download_to_filename=lambda path: None)
        fake_bucket = SimpleNamespace(blob=lambda object_name: fake_blob)
        fake_client = SimpleNamespace(bucket=lambda bucket_name: fake_bucket)

        with patch("train.get_storage_client", return_value=fake_client):
            local_path = train.resolve_training_data("gs://training-bucket/path/latest.csv")

        self.assertEqual(Path(local_path).name, "latest.csv")

    def test_rejects_invalid_gcs_uri(self):
        with self.assertRaises(ValueError):
            train.resolve_training_data("gs://training-bucket")


if __name__ == "__main__":
    unittest.main()
