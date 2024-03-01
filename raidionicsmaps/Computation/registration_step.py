import os
import shutil
import numpy as np
import nibabel as nib
import logging
import configparser
import json
import traceback
from ..Utils.resources import SharedResources
from ..Utils.io import load_nifti_volume
from ..Utils.ants_registration import *
from ..Structures.RegistrationStructure import Registration


class RegistrationStep():
    _patient_parameters = None  # Placeholder for all patient related data
    _moving_volume_uid = None  # Internal unique identifier for the radiological volume to register
    _fixed_volume_uid = None  # Internal unique identifier for the radiological volume to use as registration target
    _registration_method = None  # Unused for now, might be more than just SyN in the future?
    _moving_volume_filepath = None
    _fixed_volume_filepath = None
    _moving_mask_filepath = None
    _fixed_mask_filepath = None
    _registration_runner = None
    _step_input_folder = None
    _step_output_folder = None

    def __init__(self):
        self.__reset()
        self._registration_runner = ANTsRegistration()
        self._step_input_folder = os.path.join(os.path.join(SharedResources.getInstance().maps_output_folder,
                                                             'pipeline_input'))
        os.makedirs(self._step_input_folder)
        self._step_output_folder = os.path.join(os.path.join(SharedResources.getInstance().maps_output_folder,
                                                        'pipeline_output'))
        os.makedirs(self._step_output_folder)

    def __reset(self):
        self._patient_parameters = None
        self._moving_volume_uid = None
        self._fixed_volume_uid = None
        self._registration_method = None
        self._moving_volume_filepath = None
        self._fixed_volume_filepath = None
        self._registration_runner = None
        self._moving_mask_filepath = None
        self._fixed_mask_filepath = None
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
            self._moving_volume_filepath = self.patient_parameters.volume_filepath
            self._fixed_volume_filepath = SharedResources.getInstance().mni_atlas_filepath_T1

            ts_path = os.path.join(self._step_input_folder, "T0")
            os.makedirs(ts_path)

            dest_basename = SharedResources.getInstance().maps_sequence_type + '_' + os.path.basename(self._moving_volume_filepath)
            if SharedResources.getInstance().maps_sequence_type == "T1-CE":
                dest_basename = "T1gd" + '_' + os.path.basename(self._moving_volume_filepath)
            shutil.copyfile(src=self._moving_volume_filepath,
                            dst=os.path.join(ts_path, dest_basename))
            if self.patient_parameters.mask_filepath is not None:
                shutil.copyfile(src=self.patient_parameters.mask_filepath,
                                dst=os.path.join(ts_path, dest_basename))

        except Exception as e:
            logging.error("[RegistrationStep] Setting up process failed with {}".format(traceback.format_exc()))
            raise ValueError("[RegistrationStep] Setting up process failed.")

    def execute(self):
        try:
            # Flag for skipping registration if transform files already exist
            if len(self.patient_parameters.registrations.keys()) == 0:
                self.__registration()

            # Flag for skipping applying registration to annotation files if they exist already
            if self.patient_parameters.registered_label_filepath is None:
                self.__apply_registration()

            self._registration_runner.clear_cache()

            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
        except Exception as e:
            logging.error("[RegistrationStep] Execute failed for patient {}, with: \n{}.".format(self.patient_parameters.patient_id, traceback.format_exc()))
            self._registration_runner.clear_cache()
            if os.path.exists(self._step_input_folder):
                shutil.rmtree(self._step_input_folder)
            if os.path.exists(self._step_output_folder):
                shutil.rmtree(self._step_output_folder)
            raise ValueError("[RegistrationStep] Execution failed.")

        return self._patient_parameters

    def __registration(self):
        # Setting up the runtime configuration file, mandatory for the raidionics_rads_lib to run.
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
        # Option2. Hard-coding for the different use cases.
        # Actually mandatory in the case of MRI_Brain where the pipeline must be adjusted on the fly to run on multiple sequences...
        pipeline = self.__generate_registration_pipeline()
        with open(pipeline_filename, 'w', newline='\n') as outfile:
            json.dump(pipeline, outfile, indent=4)
        rads_config.set('System', 'pipeline_filename', pipeline_filename)
        rads_config.add_section('Runtime')
        rads_config.set('Runtime', 'reconstruction_method', 'thresholding')
        rads_config.set('Runtime', 'reconstruction_order', 'resample_first')
        rads_config.add_section('Neuro')
        rads_config.set('Neuro', 'cortical_features', 'MNI, Schaefer7')
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
            raise ValueError("Registration failed on patient.")

        reg_transform_forward = []
        reg_transform_inverse = []
        transform_folder = []
        for _, dirs, _ in os.walk(os.path.join(self._step_output_folder, "Transforms")):
            for d in dirs:
                # @TODO. Should retrieve based on input image name
                transform_folder.append(os.path.join(self._step_output_folder, "Transforms", d))
            break

        for _, _, files in os.walk(transform_folder[0]):
            for f in files:
                if 'forward' in f:
                    reg_transform_forward.append(os.path.join(transform_folder[0], f))
                elif 'inverse' in f:
                    reg_transform_inverse.append(os.path.join(transform_folder[0], f))
            break
        non_available_uid = True
        reg_uid = None
        while non_available_uid:
            reg_uid = 'R' + str(np.random.randint(0, 10000))
            if reg_uid not in list(self.patient_parameters.registrations.keys()):
                non_available_uid = False

        self._fixed_volume_uid = 'MNI'
        self._moving_volume_uid = 'Pat'
        registration = Registration(uid=reg_uid, fixed_uid=self._fixed_volume_uid, moving_uid=self._moving_volume_uid,
                                    fwd_paths=reg_transform_forward,
                                    inv_paths=reg_transform_inverse,
                                    output_folder=self.patient_parameters.output_folderpath)
        self.patient_parameters.include_registration(reg_uid, registration)
        self._registration_runner.transform_names = reg_transform_forward
        self._registration_runner.inverse_transform_names = reg_transform_inverse[::-1]
        self._registration_runner.reg_transform['fwdtransforms'] = reg_transform_forward
        self._registration_runner.reg_transform['invtransforms'] = reg_transform_inverse[::-1]

        #@TODO. Should include the brain mask also if computed during this step, or we don't care?
        if self.patient_parameters.mask_filepath is None:
            brain_mask_filename = None
            for _, _, files in os.walk(os.path.join(self._step_output_folder, "T0")):
                for f in files:
                    brain_mask_filename = (os.path.join(self._step_output_folder, "T0", f))
                break

    def __generate_registration_pipeline(self):
        timestamp_order = 0
        im_seq = SharedResources.getInstance().maps_sequence_type
        pip = {}
        pip_num_int = 0

        # pip_num_int = pip_num_int + 1
        # pip_num = str(pip_num_int)
        # pip[pip_num] = {}
        # pip[pip_num]["task"] = "Classification"
        # pip[pip_num]["inputs"] = {}  # Empty input means running it on all existing data for the patient
        # pip[pip_num]["model"] = "MRI_Sequence_Classifier"
        # pip[pip_num]["description"] = "Classification of the MRI sequence type for all input scans."

        pip_num_int = pip_num_int + 1
        pip_num = str(pip_num_int)
        pip[pip_num] = {}
        pip[pip_num]["task"] = 'Segmentation'
        pip[pip_num]["inputs"] = {}
        pip[pip_num]["inputs"]["0"] = {}
        pip[pip_num]["inputs"]["0"]["timestamp"] = timestamp_order
        pip[pip_num]["inputs"]["0"]["sequence"] = im_seq
        pip[pip_num]["inputs"]["0"]["labels"] = None
        pip[pip_num]["inputs"]["0"]["space"] = {}
        pip[pip_num]["inputs"]["0"]["space"]["timestamp"] = timestamp_order
        pip[pip_num]["inputs"]["0"]["space"]["sequence"] = im_seq
        pip[pip_num]["target"] = ['Brain']
        pip[pip_num]["model"] = "MRI_Brain"
        pip[pip_num]["description"] = "Brain segmentation in " + im_seq + " (T" + str(timestamp_order) + ")"

        pip_num_int = pip_num_int + 1
        pip_num = str(pip_num_int)
        pip[pip_num] = {}
        pip[pip_num]["task"] = "Registration"
        pip[pip_num]["moving"] = {}
        pip[pip_num]["moving"]["timestamp"] = timestamp_order
        pip[pip_num]["moving"]["sequence"] = im_seq
        pip[pip_num]["fixed"] = {}
        pip[pip_num]["fixed"]["timestamp"] = -1
        pip[pip_num]["fixed"]["sequence"] = "MNI"
        pip[pip_num]["description"] = "Registration " + im_seq + " (T" + str(timestamp_order) + ") to MNI."

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
