import os
import sys
import logging
import configparser
from pathlib import PurePath

logger = logging.getLogger(__name__)


class SharedResources:
    """
    Singleton class to have access from anywhere in the code at the resources/parameters.
    """
    __instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if SharedResources.__instance == None:
            SharedResources()
        return SharedResources.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if SharedResources.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            SharedResources.__instance = self
            self.__setup()

    def __setup(self):
        """
        Definition of all attributes accessible through this singleton.
        """
        self.config_filename = None
        self.config = None
        self.home_path = ''

        self.task = None
        self.system_ants_backend = 'python'
        self.ants_root = None
        self.ants_reg_dir = None
        self.ants_apply_dir = None

        self.maps_input_folder = ''
        self.maps_output_folder = ''
        self.maps_gt_files_suffix = ''
        self.maps_extra_parameters_filename = ''
        self.maps_use_registered_data = False
        self.maps_distribution_dense_parameters = []
        self.maps_distribution_categorical_parameters = []

    def set_environment(self, config_filename):
        self.config = configparser.ConfigParser()
        if not os.path.exists(config_filename):
            pass

        self.config_filename = config_filename
        self.config.read(self.config_filename)

        if os.name == 'posix':  # Linux system
            self.home_path = os.path.expanduser("~")

        self.__parse_default_parameters()
        self.__parse_maps_parameters()
        self.__set_neuro_atlases_parameters()
        self.__set_ants_parameters()

    def __parse_default_parameters(self):
        """
        Parse the user-selected configuration parameters linked to the overall behaviour.
        :param: task: (str) identifier for the task to perform, for now validation or study
        :param: number_processes: (int) number of parallel processes to use to perform the different task
        :return:
        """
        if self.config.has_option('Default', 'task'):
            if self.config['Default']['task'].split('#')[0].strip() != '':
                self.task = self.config['Default']['task'].split('#')[0].strip()

        if self.config.has_option('Default', 'input_folder'):
            if self.config['Default']['input_folder'].split('#')[0].strip() != '':
                self.maps_input_folder = self.config['Default']['input_folder'].split('#')[0].strip()

        if self.config.has_option('Default', 'output_folder'):
            if self.config['Default']['output_folder'].split('#')[0].strip() != '':
                self.maps_output_folder = self.config['Default']['output_folder'].split('#')[0].strip()

    def __parse_maps_parameters(self) -> None:
        """
        Parse the user-selected configuration parameters linked to the location maps creation process.
        :param: gt_files_suffix
        :param: maps_extra_parameters_filename: resources file containing patient-specific information, for example
        the tumor volume, data origin, etc... for in-depth analysis.
        :param: use_registered_data
        :param: distribution_dense_parameters
        :param: distribution_categorical_parameters
        :return: None
        """
        if self.config.has_option('Maps', 'gt_files_suffix'):
            if self.config['Maps']['gt_files_suffix'].split('#')[0].strip() != '':
                self.maps_gt_files_suffix = self.config['Maps']['gt_files_suffix'].split('#')[0].strip()

        if self.config.has_option('Maps', 'extra_parameters_filename'):
            if self.config['Maps']['extra_parameters_filename'].split('#')[0].strip() != '':
                self.maps_extra_parameters_filename = self.config['Maps']['extra_parameters_filename'].split('#')[0].strip()

        if self.config.has_option('Maps', 'use_registered_data'):
            if self.config['Maps']['use_registered_data'].split('#')[0].strip() != '':
                self.maps_use_registered_data = True if self.config['Maps']['use_registered_data'].split('#')[0].strip().lower() == 'true' else False

        if self.config.has_option('Maps', 'distribution_dense_parameters'):
            if self.config['Maps']['distribution_dense_parameters'].split('#')[0].strip() != '':
                self.maps_distribution_dense_parameters = self.config['Maps']['distribution_dense_parameters'].split('#')[0].strip().split('\\')

        if self.config.has_option('Maps', 'distribution_categorical_parameters'):
            if self.config['Maps']['distribution_categorical_parameters'].split('#')[0].strip() != '':
                self.maps_distribution_categorical_parameters = self.config['Maps']['distribution_categorical_parameters'].split('#')[0].strip().split('\\')

    def __set_neuro_atlases_parameters(self):
        self.mni_atlas_filepath_T1 = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                                  'Atlases/mni_icbm152_nlin_sym_09a/mni_icbm152_t1_tal_nlin_sym_09a.nii')
        self.mni_atlas_filepath_T2 = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                                  'Atlases/mni_icbm152_nlin_sym_09a/mni_icbm152_t2_tal_nlin_sym_09a.nii')
        self.mni_atlas_brain_mask_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                                          'Atlases/mni_icbm152_nlin_sym_09a/mni_icbm152_t1_tal_nlin_sym_09a_mask.nii')
        if os.name == 'nt':
            script_path_parts = list(PurePath(os.path.realpath(__file__)).parts[:-2] + ('Atlases', 'mni_icbm152_nlin_sym_09a', 'mni_icbm152_t1_tal_nlin_sym_09a.nii'))
            script_path = PurePath()
            for x in script_path_parts:
                script_path = script_path.joinpath(x)
            self.mni_atlas_filepath_T1 = str(script_path)

            script_path_parts = list(PurePath(os.path.realpath(__file__)).parts[:-2] + ('Atlases', 'mni_icbm152_nlin_sym_09a', 'mni_icbm152_t2_relx_tal_nlin_sym_09a.nii'))
            script_path = PurePath()
            for x in script_path_parts:
                script_path = script_path.joinpath(x)
            self.mni_atlas_filepath_T2 = str(script_path)

            script_path_parts = list(PurePath(os.path.realpath(__file__)).parts[:-2] + ('Atlases', 'mni_icbm152_nlin_sym_09a', 'mni_icbm152_t1_tal_nlin_sym_09a_mask.nii'))
            script_path = PurePath()
            for x in script_path_parts:
                script_path = script_path.joinpath(x)
            self.mni_atlas_brain_mask_filepath = str(script_path)

    def __set_ants_parameters(self):
        self.ants_root = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../', 'ANTs')

        if self.config.has_option('Default', 'ants_root'):
            if self.config['Default']['ants_root'].split('#')[0].strip() != '' and \
                    os.path.isdir(self.config['Default']['ants_root'].split('#')[0].strip()):
                self.ants_root = self.config['Default']['ants_root'].split('#')[0].strip()

        if os.path.exists(self.ants_root) and os.path.exists(os.path.join(self.ants_root, "bin")):
            os.environ["ANTSPATH"] = os.path.join(self.ants_root, "bin")
            self.ants_reg_dir = os.path.join(self.ants_root, 'Scripts')
            self.ants_apply_dir = os.path.join(self.ants_root, 'bin')
            self.system_ants_backend = 'cpp'
