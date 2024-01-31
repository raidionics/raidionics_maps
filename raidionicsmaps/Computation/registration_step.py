import os
import shutil
import numpy as np
import nibabel as nib
import logging
import configparser
import traceback
from ..Utils.resources import SharedResources
from ..Utils.io import load_nifti_volume
from ..Utils.ants_registration import *
# from ..Processing.brain_processing import *
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

    def __init__(self):
        self.__reset()
        self._registration_runner = ANTsRegistration()

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
            self._moving_volume_filepath = self.patient_parameters.volume_filepaths
            self._fixed_volume_filepath = SharedResources.getInstance().mni_atlas_filepath_T1
        except Exception as e:
            logging.error("[RegistrationStep] Setting up process failed with {}".format(traceback.format_exc()))
            raise ValueError("[RegistrationStep] Setting up process failed.")

    def execute(self):
        try:
            # Flag for performing stripping?
            # fmf, mmf = self.__registration_preprocessing()
            # self.__registration(fmf, mmf)

            # Flag for skipping registration if transform files already exist
            if len(self.patient_parameters.registrations.keys()) == 0:
                self.__registration(self._fixed_volume_filepath, self._moving_volume_filepath)

            # Flag for skipping applying registration to annotation files if they exist already
            if self.patient_parameters.registered_label_filepaths is None:
                self.__apply_registration()

            self._registration_runner.clear_cache()
        except Exception as e:
            logging.error("[RegistrationStep] Execute failed with: {}.".format(traceback.format_exc()))
            self._registration_runner.clear_cache()
            raise ValueError("[RegistrationStep] Execution failed.")

        return self._patient_parameters

    def __registration_preprocessing(self):
        """
        Generating masked version of both the fixed and moving inputs, for occluding irrelevant structures.
        For example the region outside the brain/lungs, or areas exhibiting cancer expressions.
        """
        fixed_masked_filepath = None
        moving_masked_filepath = None
        if ResourcesConfiguration.getInstance().diagnosis_task == 'neuro_diagnosis':
            if self._fixed_volume_uid:
                brain_anno = self._patient_parameters.get_all_annotations_uids_class_radiological_volume(self._fixed_volume_uid, AnnotationClassType.Brain)
                if len(brain_anno) != 0:
                    self._fixed_mask_filepath = self._patient_parameters.get_annotation(annotation_uid=brain_anno[0]).get_usable_input_filepath()
            else:
                self._fixed_mask_filepath = ResourcesConfiguration.getInstance().mni_atlas_brain_mask_filepath

            if self._moving_volume_uid:
                brain_anno = self._patient_parameters.get_all_annotations_uids_class_radiological_volume(self._moving_volume_uid, AnnotationClassType.Brain)
                if len(brain_anno) != 0:
                    self._moving_mask_filepath = self._patient_parameters.get_annotation(annotation_uid=brain_anno[0]).get_usable_input_filepath()
            else:
                self._moving_mask_filepath = ResourcesConfiguration.getInstance().mni_atlas_brain_mask_filepath

            moving_masked_filepath = perform_brain_masking(image_filepath=self._moving_volume_filepath,
                                                           mask_filepath=self._moving_mask_filepath,
                                                           output_folder=self._registration_runner.registration_folder)
            fixed_masked_filepath = perform_brain_masking(image_filepath=self._fixed_volume_filepath,
                                                          mask_filepath=self._fixed_mask_filepath,
                                                          output_folder=self._registration_runner.registration_folder)
            return fixed_masked_filepath, moving_masked_filepath

    def __registration(self, fixed_filepath, moving_filepath):
        try:
            registration_method = 'SyN'
            logging.info("[RegistrationStep] Using {} ANTs backend.".format(SharedResources.getInstance().system_ants_backend))
            if SharedResources.getInstance().system_ants_backend == "cpp":
                logging.info("[RegistrationStep] ANTs root located in {}.".format(SharedResources.getInstance().ants_root))
            self._registration_runner.compute_registration(fixed=fixed_filepath, moving=moving_filepath,
                                                           registration_method=registration_method)
            non_available_uid = True
            reg_uid = None
            while non_available_uid:
                reg_uid = 'R' + str(np.random.randint(0, 10000))
                if reg_uid not in list(self.patient_parameters.registrations.keys()):
                    non_available_uid = False

            self._fixed_volume_uid = 'MNI'
            self._moving_volume_uid = 'Pat'
            registration = Registration(uid=reg_uid, fixed_uid=self._fixed_volume_uid, moving_uid=self._moving_volume_uid,
                                        fwd_paths=self._registration_runner.reg_transform['fwdtransforms'],
                                        inv_paths=self._registration_runner.reg_transform['invtransforms'],
                                        output_folder=self.patient_parameters.output_folderpath)
            self.patient_parameters.include_registration(reg_uid, registration)
        except Exception as e:
            logging.error("[RegistrationStep] Registration failed with: {}.".format(traceback.format_exc()))
            self._registration_runner.clear_cache()
            raise ValueError("[RegistrationStep] Registration failed.")

    def __apply_registration(self):
        try:
            reg_input_fn = self._registration_runner.apply_registration_transform(fixed=self._fixed_volume_filepath,
                                                                                  moving=self._moving_volume_filepath,
                                                                                  interpolation='linear')
            shutil.move(reg_input_fn, os.path.join(self.patient_parameters.output_folderpath, 'input_reg_mni.nii.gz'))
            moving_filepath = self.patient_parameters._label_filepaths
            reg_anno_fn = self._registration_runner.apply_registration_transform(fixed=self._fixed_volume_filepath,
                                                                                 moving=moving_filepath)
            shutil.move(reg_anno_fn, os.path.join(self.patient_parameters.output_folderpath, 'input_reg_mni_' + SharedResources.getInstance().maps_gt_files_suffix))
        except Exception as e:
            logging.error("[RegistrationStep] Apply registration failed with: {}.".format(traceback.format_exc()))
            self._registration_runner.clear_cache()
            raise ValueError("[RegistrationStep] Apply registration failed.")
