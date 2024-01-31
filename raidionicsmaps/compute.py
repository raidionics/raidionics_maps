import traceback
import logging
from .Computation.registration_step import RegistrationStep
from .Computation.heatmap_computation_processor import HeatmapComputationProcessor
from .Structures.CohortStructure import Cohort
from .Utils.resources import SharedResources


def compute(config_filename: str, logging_filename: str = None) -> None:
    """

    :param config_filename: Filepath to the *.ini with the user-specific runtime parameters
    :param logging_filename: Filepath to an external file used for logging events (e.g., the Raidionics .log)
    :return: None
    """
    try:
        SharedResources.getInstance().set_environment(config_filename=config_filename)
        if logging_filename:
            logger = logging.getLogger()
            handler = logging.FileHandler(filename=logging_filename, mode='a', encoding='utf-8')
            handler.setFormatter(logging.Formatter(fmt="%(asctime)s ; %(name)s ; %(levelname)s ; %(message)s",
                                                   datefmt='%d/%m/%Y %H.%M'))
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
    except Exception as e:
        print('Compute could not proceed. Issue arose during environment setup. Collected: \n')
        print('{}'.format(traceback.format_exc()))

    task = SharedResources.getInstance().task
    cohort = None
    try:
        cohort = Cohort(id="0", input_folder=SharedResources.getInstance().maps_input_folder,
                        output_folder=SharedResources.getInstance().maps_output_folder)
    except Exception as e:
        print('Parsing of the cohort folder could not proceed.  Collected: \n'.format(task))
        print('{}'.format(traceback.format_exc()))

    if not SharedResources.getInstance().maps_use_registered_data:
        # Perform the step of co-registration for the whole cohort beforehand
        for p in list(cohort.patients.keys()):
            pat = cohort.patients[p]
            processor = RegistrationStep()
            processor.setup(pat)
            pat = processor.execute()
            cohort.patients[p] = pat

    try:
        if task == 'heatmap':
            processor = HeatmapComputationProcessor()
            processor.setup(cohort)
            processor.run()
        else:
            logging.warning("The requested task, with value {}, has not been implemented.\n"
                            "Please make sure to select a valid task!".format(task))
    except Exception as e:
        print('Compute could not proceed. Issue arose during task {}. Collected: \n'.format(task))
        print('{}'.format(traceback.format_exc()))
