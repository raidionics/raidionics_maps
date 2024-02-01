import os
import numpy as np
from typing import List, Dict, Any, Union
import traceback
import pandas as pd
from .PatientStructure import Patient
from ..Utils.resources import SharedResources


class Cohort:
    """
    Structure for holding all information about a patient cohort.
    """
    _unique_id = ""  # Internal unique identifier for the cohort
    _input_folderpath = None  # Path containing the input data
    _output_folderpath = None  # Path where the computed results will be stored
    _patients = {}  # Dictionary holding all patients belonging to the cohort, as PatientStructure objects
    _extra_patients_parameters = None  #

    def __init__(self, id: str, input_folder: str, output_folder: str) -> None:
        """

        """
        self.__reset()
        self._unique_id = id
        self._input_folderpath = input_folder
        self._output_folderpath = output_folder

        if not input_folder or not os.path.exists(input_folder):
            # Error case
            raise ValueError("The provided path does not exist on disk with value: {}".format(input_folder))

        self.__init_from_disk()

    def __reset(self) -> None:
        """
        All objects share class or static variables.
        An instance or non-static variables are different for different objects (every object has a copy).
        """
        self._unique_id = ""
        self._input_folderpath = None
        self._output_folderpath = None
        self._patients = {}
        self._extra_patients_parameters = None

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def input_folderpath(self) -> str:
        return self._input_folderpath

    @property
    def extra_patients_parameters(self) -> Union[None, pd.DataFrame]:
        return self._extra_patients_parameters

    @extra_patients_parameters.setter
    def extra_patients_parameters(self, df: pd.DataFrame) -> None:
        self._extra_patients_parameters = df

    @property
    def patients(self) -> Dict[str, Patient]:
        return self._patients

    def __init_from_disk(self) -> None:
        """
        Parses the input folder to identify all patients belonging to the cohort.
        An internal PatientStructure instance is created for each patient.
        :return: None
        """
        patient_dirs = []
        for _, dirs, _ in os.walk(self.input_folderpath):
            for d in dirs:
                patient_dirs.append(d)
            break

        # Parsing the content of the provided patient folders
        for p in patient_dirs:
            try:
                non_available_uid = True
                clean_name = p.strip().lower().replace(' ', '_')
                data_uid = "-1"
                while non_available_uid:
                    data_uid = 'P' + str(np.random.randint(0, 10000)) + '_' + clean_name
                    if data_uid not in list(self.patients.keys()):
                        non_available_uid = False
                patient = Patient(id=data_uid, patient_id=clean_name, input_folder=os.path.join(self.input_folderpath, p))
                self.patients[data_uid] = patient
            except Exception as e:
                print('Patient parsing from disk failed for folder: {}. Collected: \n'.format(p))
                print('{}'.format(traceback.format_exc()))

        if SharedResources.getInstance().maps_extra_parameters_filename is not None and os.path.exists(SharedResources.getInstance().maps_extra_parameters_filename):
            self.extra_patients_parameters = pd.read_csv(SharedResources.getInstance().maps_extra_parameters_filename)
            # Casting the Patient identifiers column as string type
            self.extra_patients_parameters['Patient'] = self.extra_patients_parameters['Patient'].astype(str)
