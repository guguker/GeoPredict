import unittest

from geopredict_ml.jobs import InMemoryAnalysisJobStore


class AnalysisJobStoreTest(unittest.TestCase):
    def test_inline_job_finishes_with_result(self):
        store = InMemoryAnalysisJobStore()

        job = store.submit({"x": 1}, lambda payload: {"ok": payload["x"]}, run_inline=True)

        self.assertEqual(job["status"], "done")
        self.assertEqual(job["result"], {"ok": 1})

    def test_inline_job_records_failure(self):
        store = InMemoryAnalysisJobStore()

        def fail(_payload):
            raise RuntimeError("boom")

        job = store.submit({}, fail, run_inline=True)

        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["error"], "boom")


if __name__ == "__main__":
    unittest.main()
