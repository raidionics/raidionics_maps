import os
import shutil
import numpy as np
import nibabel as nib
import logging
import traceback
import pandas as pd
from scipy.ndimage import measurements
from skimage.measure import regionprops

from ..Utils.resources import SharedResources
from ..Utils.utils import *
from ..Structures.MetricsStructure import Metrics


class SizeComputationStep():
    _patient_parameters = None  # Placeholder for all patient related data
    _step_input_folder = None
    _step_output_folder = None
    _registered_volume_filepath = None

    def __init__(self):
        self.__reset()
        self._step_input_folder = os.path.join(os.path.join(SharedResources.getInstance().maps_output_folder,
                                                            'pipeline_input'))
        os.makedirs(self._step_input_folder)
        self._step_output_folder = os.path.join(os.path.join(SharedResources.getInstance().maps_output_folder,
                                                             'pipeline_output'))
        os.makedirs(self._step_output_folder)

    def __reset(self):
        self._patient_parameters = None
        self._step_input_folder = None
        self._step_output_folder = None
        self._registered_volume_filepath = None

    @property
    def patient_parameters(self) -> str:
        return self._patient_parameters

    @patient_parameters.setter
    def patient_parameters(self, pat_params) -> None:
        self._patient_parameters = pat_params

    @property
    def registered_volume_filepath(self) -> str:
        return self._registered_volume_filepath

    @registered_volume_filepath.setter
    def registered_volume_filepath(self, fp: str) -> None:
        self._registered_volume_filepath = fp

    def setup(self, patient_parameters):
        """

        """
        self.patient_parameters = patient_parameters
        try:
            self.registered_volume_filepath = os.path.join(SharedResources.getInstance().maps_output_folder,
                                                           self.patient_parameters.patient_id,
                                                           "input_reg_mni_" + SharedResources.getInstance().maps_gt_files_suffix)
            if not os.path.exists(self.registered_volume_filepath):
                raise ValueError("No registered volume in MNI space can be found for computing size-related metrics.")
        except Exception as e:
            logging.error("[MetricsComputationStep] Setting up process failed with {}".format(traceback.format_exc()))
            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
            raise ValueError("[MetricsComputationStep] Setting up process failed.")

    def execute(self):
        try:
            # Flag for skipping computation if metrics already existing
            if (not self.patient_parameters.is_metrics_for_class(get_metrics_target_class())
                    or not self.patient_parameters.metrics[get_metrics_target_class()].size_metrics_exist()):
                self.__compute_size()

            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
        except Exception as e:
            logging.error("[SizeComputationStep] Execute failed with: {}.".format(traceback.format_exc()))
            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
            raise ValueError("[SizeComputationStep] Execution failed.")

        return self._patient_parameters

    def __compute_size(self):
        try:
            size_metrics = []
            labels_ni = nib.load(self.registered_volume_filepath)
            labels = labels_ni.get_fdata().astype('uint8')
            voxel_size = np.prod(labels_ni.header.get_zooms()[0:3])
            volume_pixels = np.count_nonzero(labels != 0)  # Might be more than one label, but not considering it yet
            volume_mmcube = voxel_size * volume_pixels
            volume_ml = volume_mmcube * 1e-3

            # Computing some other parameters for the main tumor component, not for other foci
            if len(labels.shape) == 4:  # Still some cases with a fourth dimension...
                labels = labels[..., 0]
            tumor_clusters = measurements.label(labels)[0]
            tumor_clusters_labels = regionprops(tumor_clusters)
            # Sorting by cluster size to get the parameters of the main component.
            tumor_clusters_labels = sorted(tumor_clusters_labels, key=lambda r: r.area, reverse=True)

            long_axis_mm = -1
            short_axis_mm = -1
            diameter_x = -1
            diameter_y = -1
            diameter_z = -1

            if volume_pixels > 0:
                long_axis_mm = tumor_clusters_labels[0].major_axis_length
                short_axis_mm = tumor_clusters_labels[0].minor_axis_length
                diameter_x = (tumor_clusters_labels[0].bbox[3] - tumor_clusters_labels[0].bbox[0]) * voxel_size
                diameter_y = (tumor_clusters_labels[0].bbox[4] - tumor_clusters_labels[0].bbox[1]) * voxel_size
                diameter_z = (tumor_clusters_labels[0].bbox[5] - tumor_clusters_labels[0].bbox[2]) * voxel_size
            size_metrics = [volume_ml, long_axis_mm, short_axis_mm, diameter_x, diameter_y, diameter_z]
        except Exception:
            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
            raise ValueError("Size metrics computation failed on patient.")

        try:
            target_class = get_metrics_target_class()
            if self.patient_parameters.is_metrics_for_class(target_class):
                metrics = self.patient_parameters.get_metrics_for_class(target_class)
            else:
                non_available_uid = True
                metrics_uid = None
                while non_available_uid:
                    metrics_uid = 'M' + str(np.random.randint(0, 10000))
                    if metrics_uid not in list(self.patient_parameters.metrics.keys()):
                        non_available_uid = False
                metrics = Metrics(uid=metrics_uid, input_folder=self.patient_parameters.output_folderpath)

            computation_df = pd.DataFrame(np.asarray(size_metrics).reshape((1, 6)),
                                          columns=["Volume (ml)", "Long-axis diameter (mm)",
                                                   "Short-axis diameter (mm)", "Diameter X (mm)",
                                                   "Diameter Y (mm)", "Diameter Z (mm)"])
            metrics.fill_size_metrics_from_report(computation_df)
            self.patient_parameters.include_metrics(target_class, metrics)
            metrics.dump_metrics_file_on_disk()
        except Exception:
            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
            raise ValueError("Size metrics computation failed on patient during results parsing.")
