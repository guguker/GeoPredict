import unittest
from pathlib import Path


class DeploymentPackagingTest(unittest.TestCase):
    def test_docker_context_includes_model_artifacts(self):
        dockerignore = Path(".dockerignore").read_text(encoding="utf-8").splitlines()
        dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

        self.assertNotIn("models", dockerignore)
        self.assertNotIn("*.pkl", dockerignore)
        self.assertIn("COPY models ./models", dockerfile)


if __name__ == "__main__":
    unittest.main()
