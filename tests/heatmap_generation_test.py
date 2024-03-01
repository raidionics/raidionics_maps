import os
import shutil
import configparser
import logging
import sys
import subprocess
import traceback
import zipfile

try:
    import requests
except:
    subprocess.check_call([sys.executable, "-m", "pip", "install", 'requests'])
    import requests


def heatmap_generation_test():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    logging.info("Running heatmap generation unit test.\n")
    logging.info("Downloading unit test resources.\n")
    test_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'unit_tests_results_dir')
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)

    try:
        resources_url = 'https://github.com/raidionics/Raidionics-models/releases/download/1.2.0/Samples-RaidionicsMaps-UnitTest1.zip'

        archive_dl_dest = os.path.join(test_dir, 'resources.zip')
        headers = {}
        response = requests.get(resources_url, headers=headers, stream=True)
        response.raise_for_status()
        if response.status_code == requests.codes.ok:
            with open(archive_dl_dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=1048576):
                    f.write(chunk)
        with zipfile.ZipFile(archive_dl_dest, 'r') as zip_ref:
            zip_ref.extractall(test_dir)

        if not os.path.exists(os.path.join(test_dir, 'Cohort_UnitTest1')):
            raise ValueError('Resources download or extraction failed, content not available on disk.')
    except Exception as e:
        logging.error("Error during resources download with: \n {}.\n".format(traceback.format_exc()))
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        raise ValueError("Error during resources download.\n")

    logging.info("Preparing configuration file.\n")
    try:
        unit_test_config = configparser.ConfigParser()
        unit_test_config.add_section('Default')
        unit_test_config.set('Default', 'task', 'heatmap')
        unit_test_config.set('Default', 'input_folder', os.path.join(test_dir, 'Cohort_UnitTest1'))
        unit_test_config.set('Default', 'output_folder', os.path.join(test_dir, 'Cohort_UnitTest1_Output'))
        unit_test_config.add_section('Maps')
        unit_test_config.set('Maps', 'gt_files_suffix', 'label_tumor.nii.gz')
        unit_test_config.set('Maps', 'sequence_type', 'T1-CE')
        unit_test_config.set('Maps', 'use_registered_data', 'true')
        config_filename = os.path.join(test_dir, 'config.ini')
        with open(config_filename, 'w') as outfile:
            unit_test_config.write(outfile)

        logging.info("Running heatmap generation unit test.\n")
        from raidionicsmaps.compute import compute
        compute(config_filename)

        logging.info("Collecting and comparing results.\n")
        heatmap_filename = os.path.join(test_dir, 'Cohort_UnitTest1_Output', 'Heatmaps', 'Overall', 'heatmap_percentages.nii.gz')
        if not os.path.exists(heatmap_filename):
            logging.error("Heatmap generation unit test failed, no heatmap was generated.\n")
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
            raise ValueError("Heatmap generation unit test failed, no heatmap was generated.\n")

        logging.info("Heatmap generation CLI unit test started.\n")
        try:
            import platform
            if platform.system() == 'Windows':
                subprocess.check_call(['raidionicsmaps',
                                       '{config}'.format(config=config_filename),
                                       '--verbose', 'debug'], shell=True)
            elif platform.system() == 'Darwin' and platform.processor() == 'arm':
                subprocess.check_call(['python3', '-m', 'raidionicsmaps',
                                       '{config}'.format(config=config_filename),
                                       '--verbose', 'debug'])
            else:
                subprocess.check_call(['raidionicsmaps',
                                       '{config}'.format(config=config_filename),
                                       '--verbose', 'debug'])
        except Exception as e:
            logging.error("Error during heatmap generation CLI unit test with: \n {}.\n".format(traceback.format_exc()))
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
            raise ValueError("Error during heatmap generation CLI unit test.\n")

        logging.info("Collecting and comparing results.\n")
        heatmap_filename = os.path.join(test_dir, 'Cohort_UnitTest1_Output', 'Heatmaps', 'Overall', 'heatmap_percentages.nii.gz')
        if not os.path.exists(heatmap_filename):
            logging.error("Heatmap generation unit test failed, no heatmap was generated.\n")
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
            raise ValueError("Heatmap generation unit test failed, no heatmap was generated.\n")
        logging.info("Heatmap generation CLI unit test succeeded.\n")
    except Exception as e:
        logging.error("Error during heatmap generation unit test with: \n {}.\n".format(traceback.format_exc()))
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        raise ValueError("Error during heatmap generation unit test with.\n")

    logging.info("Heatmap generation unit test succeeded.\n")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


heatmap_generation_test()
