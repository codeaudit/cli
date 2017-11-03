import datetime
import unittest
from riseml.client import models
from .status import _get_status_headers, _get_experiment_rows, show_experiments


class TestStatus(unittest.TestCase):

    def test_get_status_headers(self):
        tests = [
            {
                "user": True,
                "collapsed": True,
            },
            {
                "user": True,
                "collapsed": False,
            },
            {
                "user": False,
                "collapsed": False,
            },
            {
                "user": False,
                "collapsed": True,
            },
        ]
        for test in tests:
            h, w = _get_status_headers(users=test["user"], collapsed=test["collapsed"])
            self.assertEqual(test["user"], 'USER' in h)
            self.assertEqual(not test["collapsed"], 'PARAMS' in h)
            self.assertEqual(not test["collapsed"], 'RESULT' in h)
            self.assertEqual(len(h), len(w))

    def test_get_experiment_rows(self):
        tests = [
            {
                "all": True,
                "user": False,
                "rows-len": 2,
            },
            {
                "all": False,
                "user": True,
                "rows-len": 1,
            },
        ]
        for test in tests:
            exps = self.generate_experiments()
            rows = _get_experiment_rows(exps, all=test["all"], users=test["user"])
            show_experiments(exps, all=test["all"], users=test["user"], collapsed=False)
            self.assertEqual(test["rows-len"], len(rows))
            for row in rows:
                if test["user"]:
                    self.assertEqual(row[1], "admin")

    def generate_experiments(self):
        return [
            models.experiment.Experiment(
                short_id="1",
                state="KILLED",
                user=models.user.User(username="admin"),
                project=models.project.Project(name="test 1")
            ),
            models.experiment.Experiment(
                short_id="2",
                state="PENDING",
                user=models.user.User(username="admin"),
                project=models.project.Project(name="test 2"),
                children=[
                    models.experiment.Experiment(
                        short_id="1",
                        state="KILLED",
                        user=models.user.User(username="admin"),
                        project=models.project.Project(name="test 2 child"),
                        params="{}",
                    ),
                ],
            )
        ]        
