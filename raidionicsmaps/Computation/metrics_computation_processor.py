from __future__ import division

import logging
import traceback
from typing import List
import numpy as np
import csv
import sys
import os
from copy import deepcopy

import pandas as pd
from tqdm import tqdm

from ..Computation.location_computation_step import LocationComputationStep
from ..Computation.size_computation_step import SizeComputationStep
from ..Utils.resources import SharedResources
from ..Utils.utils import get_metrics_target_class


class MetricsComputationProcessor:
    """

    """
    _cohort = None  # Placeholder for all loaded patients belonging to the cohort of interest

    def __init__(self):
        self.__reset()

    @property
    def cohort(self):
        return self._cohort

    @cohort.setter
    def cohort(self, input_cohort) -> None:
        self._cohort = input_cohort

    def __reset(self) -> None:
        """
        All objects share class or static variables.
        An instance or non-static variables are different for different objects (every object has a copy).
        """
        self.cohort = None

    def setup(self, cohort) -> None:
        """
        Iterates over all patients belonging to the cohort for asserting the existence of an annotation mask of the
        structure of interest, registered in the atlas-space.
        A warning is raised for each patient were a proper annotation mask cannot be found, for visual inspection.
        :param cohort: Container for all loaded patients.
        :return: None
        """
        self.cohort = cohort

    def run(self) -> None:
        """

        :return:
        """
        logging.info("Computing metrics for the complete cohort!")
        try:
            for p in tqdm(list(self.cohort.patients.keys())):
                pat = self.cohort.patients[p]
                if SharedResources.getInstance().metrics_tumor_size:
                    processor = SizeComputationStep()
                    processor.setup(pat)
                    pat = processor.execute()

                if (SharedResources.getInstance().metrics_brain_location or
                    SharedResources.getInstance().metrics_multifocality or
                        len(SharedResources.getInstance().metrics_cortical_features_location) != 0 or
                        len(SharedResources.getInstance().metrics_subcortical_features_location) != 0):
                    processor = LocationComputationStep()
                    processor.setup(pat)
                    pat = processor.execute()

                self.cohort.patients[p] = pat
        except Exception as e:
            logging.error("Detected problem during metrics computation over the whole cohort.\n {}".format(traceback.format_exc()))

        # Global metrics export for all patients into a single file
        cohort_metrics_filename = os.path.join(SharedResources.getInstance().maps_output_folder,
                                               "all_metrics_" + get_metrics_target_class() + ".csv")
        all_metrics = []
        all_metrics_columns = None
        for p in list(self.cohort.patients.keys()):
            pat = self.cohort.patients[p]
            pat_metrics_fn = os.path.join(pat.output_folderpath,
                                          "computed_metrics_" + get_metrics_target_class() + ".csv")
            pat_metrics_df = pd.read_csv(pat_metrics_fn)
            all_metrics.append([pat.patient_id] + list(pat_metrics_df.values[0]))
            if all_metrics_columns is None:
                all_metrics_columns = ["Patient_ID"] + list(pat_metrics_df.columns)

        all_metrics_df = pd.DataFrame(all_metrics, columns=all_metrics_columns)
        all_metrics_df.to_csv(cohort_metrics_filename, index=False)

        # @TODO. The metrics file could be fused with the extra_parameters file in addition?
