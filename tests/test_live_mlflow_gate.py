import os
import time
import unittest

import mlflow
from mlflow.tracking import MlflowClient

import train


class LiveMlflowGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tracking_uri = os.getenv(
            "MLFLOW_TRACKING_URI",
            "https://momo-mlflow-7e2lu7f7ta-uc.a.run.app",
        )
        cls.experiment_name = os.getenv(
            "MLFLOW_GATE_TEST_EXPERIMENT",
            f"momo-fraud-gate-test-{int(time.time())}",
        )
        mlflow.set_tracking_uri(cls.tracking_uri)
        mlflow.set_experiment(cls.experiment_name)
        cls.client = MlflowClient(tracking_uri=cls.tracking_uri)

    def _create_run(self, name, metrics):
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_metrics(metrics)
            return run.info.run_id

    def test_live_gate_rejects_worse_and_promotes_better_model(self):
        original_experiment = train.MLFLOW_EXPERIMENT
        train.MLFLOW_EXPERIMENT = self.experiment_name
        try:
            production_run = self._create_run(
                "production-baseline",
                {"test_f1": 0.80, "test_auc": 0.90},
            )
            self.client.set_tag(production_run, "stage", "Production")

            worse_run = self._create_run(
                "worse-candidate",
                {"test_f1": 0.70, "test_auc": 0.95},
            )
            worse_promoted = train.evaluation_gate(
                self.client,
                worse_run,
                {"test_f1": 0.70, "test_auc": 0.95},
            )

            better_run = self._create_run(
                "better-candidate",
                {"test_f1": 0.81, "test_auc": 0.91},
            )
            better_promoted = train.evaluation_gate(
                self.client,
                better_run,
                {"test_f1": 0.81, "test_auc": 0.91},
            )

            self.assertFalse(worse_promoted)
            self.assertTrue(better_promoted)

            production_metrics = train.get_production_metrics(self.client)
            self.assertEqual(production_metrics["test_f1"], 0.81)
            self.assertEqual(production_metrics["test_auc"], 0.91)

            prod_run = self.client.get_run(production_run)
            better_prod_run = self.client.get_run(better_run)
            self.assertNotIn("stage", prod_run.data.tags)
            self.assertEqual(better_prod_run.data.tags["stage"], "Production")
        finally:
            train.MLFLOW_EXPERIMENT = original_experiment


if __name__ == "__main__":
    unittest.main()
