import os
import re
import numpy as np
from typing import List
import logging

from ..Utils.resources import SharedResources
from .RegistrationStructure import Registration


class Patient:
    """

    """
    _unique_id = ""  # Internal unique identifier for the patient
    _patient_id = ""  # Identifier for the patient based off the folder name
    _input_folderpath = None  # Folder containing the raw patient data
    _output_folderpath = None  # Folder containing the generated patient data
    _volume_filepath = None  # Filepath to the input radiological volume
    _label_filepath = None  # Filepath to the input annotation mask
    _registered_volume_filepath = None  # Filepath for the generated atlas-registered radiological volume
    _registered_label_filepath = None  # Filepath for the generated atlas-registered annotation mask
    _class_names = []  # Not used for now
    _registrations = {}  # Dictionary containing a RegistrationStructure with the transformation info for each registration, if multiple atlases are used over time

    def __init__(self, id: str, patient_id: str, input_folder: str) -> None:
        """

        """
        self.__reset()
        self._unique_id = id
        self.patient_id = patient_id
        self.input_folderpath = input_folder
        self.output_folderpath = os.path.join(SharedResources.getInstance().maps_output_folder, patient_id)

        if not input_folder or not os.path.exists(input_folder):
            # Error case
            raise ValueError("The provided path does not exist on disk with value: {}".format(input_folder))

        if not os.path.exists(self.output_folderpath):
            os.makedirs(self.output_folderpath)

        self.__init_from_disk()

    def __reset(self) -> None:
        """
        All objects share class or static variables.
        An instance or non-static variables are different for different objects (every object has a copy).
        """
        self._unique_id = ""
        self._patient_id = ""
        self._input_folderpath = None
        self._output_folderpath = None
        self._volume_filepath = None
        self._label_filepath = None
        self._registered_volume_filepath = None
        self._registered_label_filepath = None
        self._class_names = None
        self._registrations = {}

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def patient_id(self) -> str:
        return self._patient_id

    @patient_id.setter
    def patient_id(self, patient_id: str) -> None:
        self._patient_id = patient_id

    @property
    def input_folderpath(self) -> str:
        return self._input_folderpath

    @input_folderpath.setter
    def input_folderpath(self, input_folderpath: str) -> None:
        self._input_folderpath = input_folderpath

    @property
    def volume_filepaths(self) -> str:
        return self._volume_filepath

    @volume_filepaths.setter
    def volume_filepaths(self, volume_filepaths: str) -> None:
        self._volume_filepath = volume_filepaths

    @property
    def label_filepaths(self) -> str:
        return self._label_filepath

    @label_filepaths.setter
    def label_filepaths(self, label_filepaths: str) -> None:
        self._label_filepath = label_filepaths

    @property
    def registered_volume_filepaths(self) -> str:
        return self._registered_volume_filepath

    @registered_volume_filepaths.setter
    def registered_volume_filepaths(self, filepath: str) -> None:
        self._registered_volume_filepath = filepath

    @property
    def registered_label_filepaths(self) -> str:
        return self._registered_label_filepath

    @registered_label_filepaths.setter
    def registered_label_filepaths(self, filepath: str) -> None:
        self._registered_label_filepath = filepath

    @property
    def class_names(self) -> List[str]:
        return self._class_names

    @property
    def registrations(self) -> dict:
        return self._registrations

    def __init_from_disk(self) -> None:
        """
        Iterating through the patient folder to identify the content.
        """
        volume_files = []
        label_files = []
        for _, _, files in os.walk(self.input_folderpath):
            for f in files:
                if SharedResources.getInstance().maps_gt_files_suffix in f:
                    label_files.append(f)
                else:
                    volume_files.append(f)
            break

        self.volume_filepaths = os.path.join(self.input_folderpath, volume_files[0])
        self.label_filepaths = os.path.join(self.input_folderpath, label_files[0])

        res_patient_folder = os.path.join(SharedResources.getInstance().maps_output_folder, self.patient_id)
        if os.path.exists(res_patient_folder):
            reg_folder = None
            contents = []
            for _, dirs, _ in os.walk(res_patient_folder):
                for d in dirs:
                    contents.append(d)
                break

            if len(contents) != 0:
                reg_folder = os.path.join(res_patient_folder, contents[0])
                reg_folder = os.path.join(reg_folder, 'Pat-to-MNI')
                if not os.path.exists(reg_folder):
                    return

                transform_contents = []
                inverse_transform_contents = []
                for _, _, files in os.walk(reg_folder):
                    for f in files:
                        if 'forward' in f:
                            transform_contents.append(f)
                        elif 'inverse' in f:
                            inverse_transform_contents.append(f)
                    break

                non_available_uid = True
                reg_uid = None
                while non_available_uid:
                    reg_uid = 'R' + str(np.random.randint(0, 10000))
                    if reg_uid not in list(self.registrations.keys()):
                        non_available_uid = False

                registration = Registration(uid=reg_uid, fixed_uid='MNI', moving_uid='Pat',
                                            fwd_paths=transform_contents,
                                            inv_paths=inverse_transform_contents,
                                            output_folder=self.output_folderpath)
                self.include_registration(reg_uid, registration)

            reg_input_fn = os.path.join(self.output_folderpath, 'input_reg_mni.nii.gz')
            reg_labels_fn = os.path.join(self.output_folderpath,
                                         'input_reg_mni_' + SharedResources.getInstance().maps_gt_files_suffix)
            if os.path.exists(reg_input_fn):
                self.registered_volume_filepaths = reg_input_fn
            if os.path.exists(reg_labels_fn):
                self.registered_label_filepaths = reg_labels_fn

        if SharedResources.getInstance().maps_use_registered_data:
            if self.registered_volume_filepaths is None:
                self.registered_volume_filepaths = self.volume_filepaths
            if self.registered_label_filepaths is None:
                self.registered_label_filepaths = self.label_filepaths

    def include_registration(self, reg_uid: str, registration: Registration) -> None:
        self.registrations[reg_uid] = registration
