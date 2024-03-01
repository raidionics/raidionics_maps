import os
import shutil
import numpy as np
import nibabel as nib
import logging
import configparser
import json
import traceback

import pandas as pd

from ..Utils.utils import *
from ..Utils.resources import SharedResources
from ..Utils.ants_registration import *
from ..Structures.MetricsStructure import Metrics


class LocationComputationStep():
    _patient_parameters = None  # Placeholder for all patient related data
    _step_input_folder = None
    _step_output_folder = None

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

    @property
    def patient_parameters(self) -> str:
        return self._patient_parameters

    @patient_parameters.setter
    def patient_parameters(self, pat_params) -> None:
        self._patient_parameters = pat_params

    def setup(self, patient_parameters):
        """

        """
        self.patient_parameters = patient_parameters
        try:
            reg_input_filepath = os.path.join(SharedResources.getInstance().maps_output_folder,
                                              self.patient_parameters.patient_id, "input_reg_mni.nii.gz")
            mask_reg_input_filepath = os.path.join(SharedResources.getInstance().maps_output_folder,
                                                   self.patient_parameters.patient_id,
                                                   "input_reg_mni_" + SharedResources.getInstance().maps_gt_files_suffix)
            ts_path = os.path.join(self._step_input_folder, "T0")
            os.makedirs(ts_path)

            dest_base_reg_fn = SharedResources.getInstance().maps_sequence_type + '_' + os.path.basename(reg_input_filepath)
            if SharedResources.getInstance().maps_sequence_type == "T1-CE":
                dest_base_reg_fn = 't1gd_' + os.path.basename(reg_input_filepath)

            dest_base_mask_reg_fn = SharedResources.getInstance().maps_sequence_type + '_' + os.path.basename(mask_reg_input_filepath)
            if SharedResources.getInstance().maps_sequence_type == "T1-CE":
                dest_base_mask_reg_fn = 't1gd_' + os.path.basename(mask_reg_input_filepath)

            shutil.copyfile(src=reg_input_filepath,
                            dst=os.path.join(ts_path, dest_base_reg_fn))
            shutil.copyfile(src=mask_reg_input_filepath,
                            dst=os.path.join(ts_path, dest_base_mask_reg_fn))
        except Exception as e:
            logging.error("[LocationComputationStep] Setting up process failed with {}".format(traceback.format_exc()))
            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
            raise ValueError("[LocationComputationStep] Setting up process failed.")

    def execute(self):
        try:
            # Flag for skipping location computation already existing
            if (not self.patient_parameters.is_metrics_for_class(get_metrics_target_class())
                    or not self.patient_parameters.metrics[get_metrics_target_class()].location_metrics_exist()):
                self.__compute_location()

            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
        except Exception as e:
            logging.error("[LocationComputationStep] Execute failed with: {}.".format(traceback.format_exc()))
            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
            raise ValueError("[LocationComputationStep] Execution failed.")

        return self._patient_parameters

    def __compute_location(self):
        rads_config = configparser.ConfigParser()
        rads_config.add_section('Default')
        rads_config.set('Default', 'task', 'neuro_diagnosis')
        rads_config.set('Default', 'caller', '')
        rads_config.add_section('System')
        rads_config.set('System', 'gpu_id', "-1")  # Always running on CPU
        rads_config.set('System', 'input_folder', self._step_input_folder)
        rads_config.set('System', 'output_folder', self._step_output_folder)
        rads_config.set('System', 'model_folder', SharedResources.getInstance().system_models_folder)

        pipeline_filename = os.path.join(self._step_input_folder, 'rads_pipeline.json')
        pipeline = self.__generate_registration_pipeline()
        with open(pipeline_filename, 'w', newline='\n') as outfile:
            json.dump(pipeline, outfile, indent=4)
        rads_config.set('System', 'pipeline_filename', pipeline_filename)
        rads_config.add_section('Neuro')
        if not self.patient_parameters.metrics[get_metrics_target_class()].cortical_structures_location_metrics_exist():
            rads_config.set('Neuro', 'cortical_features', ','.join(SharedResources.getInstance().metrics_cortical_features_location))
        if not self.patient_parameters.metrics[get_metrics_target_class()].subcortical_structures_location_metrics_exist():
            rads_config.set('Neuro', 'subcortical_features', ','.join(SharedResources.getInstance().metrics_subcortical_features_location))
        rads_config_filename = os.path.join(self._step_input_folder, 'rads_config.ini')
        with open(rads_config_filename, 'w') as outfile:
            rads_config.write(outfile)

        try:
            from raidionicsrads.compute import run_rads
            run_rads(rads_config_filename)
        except Exception:
            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
            raise ValueError("Location computation failed on patient.")

        location_results_filename = os.path.join(self._step_output_folder, "neuro_clinical_report.json")
        if not os.path.exists(location_results_filename):
            logging.error("No location computation file found on disk.\n")
            raise ValueError("No location computation file found on disk.\n")

        try:
            non_available_uid = True
            metrics_uid = None
            while non_available_uid:
                metrics_uid = 'M' + str(np.random.randint(0, 10000))
                if metrics_uid not in list(self.patient_parameters.metrics.keys()):
                    non_available_uid = False

            computation_df = pd.read_json(location_results_filename)
            target_class = SharedResources.getInstance().maps_gt_files_suffix.split('.')[0].split('label_')[-1]
            if self.patient_parameters.is_metrics_for_class(target_class):
                metrics = self.patient_parameters.get_metrics_for_class(target_class)
            else:
                metrics = Metrics(uid=metrics_uid, input_folder=self.patient_parameters.output_folderpath)

            if SharedResources.getInstance().metrics_brain_location:
                metrics.fill_brain_location_from_report(computation_df)
            if SharedResources.getInstance().metrics_multifocality:
                metrics.fill_multifocality_metrics_from_report(computation_df)
            metrics.fill_cortical_location_from_report(computation_df)
            metrics.fill_subcortical_location_from_report(computation_df)

            self.patient_parameters.include_metrics(target_class, metrics)
            metrics.dump_metrics_file_on_disk()

        except Exception:
            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
            raise ValueError("Location computation failed on patient during results parsing.")

    def __generate_registration_pipeline(self):
        timestamp_order = 0
        im_seq = SharedResources.getInstance().maps_sequence_type
        pip = {}
        pip_num_int = 0

        pip_num_int = pip_num_int + 1
        pip_num = str(pip_num_int)
        pip[pip_num] = {}
        pip[pip_num]["task"] = 'Features computation'
        pip[pip_num]["input"] = {}
        pip[pip_num]["input"]["timestamp"] = timestamp_order
        pip[pip_num]["input"]["sequence"] = im_seq
        pip[pip_num]["target"] = "Tumor"
        pip[pip_num]["space"] = "Patient"
        pip[pip_num]["description"] = "Tumor features computation in MNI space"

        return pip

    def __apply_registration(self):
        try:
            reg_input_fn = self._registration_runner.apply_registration_transform(fixed=self._fixed_volume_filepath,
                                                                                  moving=self._moving_volume_filepath,
                                                                                  interpolation='linear')
            shutil.move(reg_input_fn, os.path.join(self.patient_parameters.output_folderpath, 'input_reg_mni.nii.gz'))
            self.patient_parameters.registered_volume_filepaths = os.path.join(self.patient_parameters.output_folderpath,
                                                                               'input_reg_mni.nii.gz')
            moving_filepath = self.patient_parameters.label_filepath
            reg_anno_fn = self._registration_runner.apply_registration_transform(fixed=self._fixed_volume_filepath,
                                                                                 moving=moving_filepath)
            reg_base_name = 'input_reg_mni_' + SharedResources.getInstance().maps_gt_files_suffix
            shutil.move(reg_anno_fn, os.path.join(self.patient_parameters.output_folderpath, reg_base_name))
            self.patient_parameters.registered_label_filepath = os.path.join(self.patient_parameters.output_folderpath,
                                                                              reg_base_name)
        except Exception as e:
            logging.error("[RegistrationStep] Apply registration failed with: {}.".format(traceback.format_exc()))
            self._registration_runner.clear_cache()
            raise ValueError("[RegistrationStep] Apply registration failed.")
