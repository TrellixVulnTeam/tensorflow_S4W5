#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append('./utility')
import optuna
import tensorflow as tf
from utils import Utils
from functools import partial

class Optuna():
    def __init__(self, db_name=None):
        self.name = db_name if db_name is not None else 'example'

    def search(self, obj, para, trials):
        assert trials > 0, "trial is bigger than 0"
        util = Utils(prefix='optuna')
        util.conf_log()
        study = optuna.create_study(study_name=self.name, storage='sqlite:///{}/hypara_search.db'.format(util.res_dir))
        f = partial(obj, para)
        study.optimize(f, n_trials=trials)
        return

    def confirm(self, directory):
        self.study = optuna.Study(study_name=self.name, storage='sqlite:///{}/hypara_search.db'.format(directory))
        self.df = self.study.trials_dataframe()
        """
        self.study.best_params  # Get best parameters for the objective function.
        self.study.best_value  # Get best objective value.
        self.study.best_trial  # Get best trial's information.
        self.study.trials  # Get all trials' information.
        """
        
if __name__ == '__main__':
    op = Optuna('example-study')
    op.confirm('results')
    print(op.study.best_params)
    print(op.study.best_value)