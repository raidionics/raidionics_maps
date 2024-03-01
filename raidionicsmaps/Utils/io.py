import os
import nibabel as nib
import pandas as pd
import numpy as np
from pathlib import PurePath
from nibabel import four_to_three
import logging
import traceback
import zipfile
import requests
import shutil
import hashlib


def load_nifti_volume(volume_path):
    nib_volume = nib.load(volume_path)
    if len(nib_volume.shape) > 3:
        if len(nib_volume.shape) == 4:  # Common problem
            nib_volume = four_to_three(nib_volume)[0]
        else:  # DWI volumes
            nib_volume = nib.Nifti1Image(nib_volume.get_fdata()[:, :, :, 0, 0], affine=nib_volume.affine)

    return nib_volume


def get_available_cloud_models_list():
    cloud_models_list = []
    cloud_models_list_url = 'https://github.com/raidionics/Raidionics-models/releases/download/1.2.0/raidionics_cloud_models_list_github.csv'
    cloud_models_list_filename = os.path.join(os.path.expanduser("~"), '.raidionics', 'resources', 'models',
                                              'cloud_models_list.csv')
    if os.name == 'nt':
        script_path_parts = list(PurePath(os.path.expanduser("~")).parts[:] + ('.raidionics', 'resources', 'models',
                                                                       'cloud_models_list.csv'))
        cloud_models_list_filename = PurePath()
        for x in script_path_parts:
            cloud_models_list_filename = cloud_models_list_filename.joinpath(x)

    try:
        os.makedirs(os.path.dirname(cloud_models_list_filename), exist_ok=True)
        headers = {}
        response = requests.get(cloud_models_list_url, headers=headers, stream=True)
        response.raise_for_status()

        if response.status_code == requests.codes.ok:
            with open(cloud_models_list_filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=1048576):
                    f.write(chunk)
    except Exception as e:
        print('Impossible to access the cloud models list on Github.\n')
        print('{}'.format(traceback.format_exc()))
        logging.warning('Impossible to access the cloud models list on Github with: \n {}'.format(traceback.format_exc()))

    if not os.path.exists(cloud_models_list_filename):
        logging.error('The cloud models list does not exist on disk at: {}'.format(cloud_models_list_filename))
    cloud_models_list = pd.read_csv(cloud_models_list_filename)
    return cloud_models_list


def download_model(model_name: str):
    """
    Utilitarian method for downloading a model, hosted on Github, if no local version can be found or if the local version
    is outdated compared to the remote version.

    Parameters
    ----------
    model_name: str
        Unique name for the model to download, as specified inside the cloud models list file (.csv).
    """
    download_state = False
    extract_state = False
    try:
        cloud_models_list = get_available_cloud_models_list()
        if model_name in list(cloud_models_list['Model'].values):
            model_params = cloud_models_list.loc[cloud_models_list['Model'] == model_name]
            url = model_params['link'].values[0]
            md5 = model_params['sum'].values[0]
            tmp_dep = model_params['dependencies'].values[0]
            dep = list(tmp_dep.strip().split(';')) if tmp_dep == tmp_dep else []
            models_path = os.path.join(os.path.expanduser('~'), '.raidionics', 'resources', 'models')
            os.makedirs(models_path, exist_ok=True)
            models_archive_path = os.path.join(os.path.expanduser('~'), '.raidionics', 'resources', 'models',
                                               '.cache', model_name + '.zip')
            os.makedirs(os.path.dirname(models_archive_path), exist_ok=True)

            if (not os.path.exists(models_archive_path) or
                    hashlib.md5(open(models_archive_path, 'rb').read()).hexdigest() != md5):
                download_state = True

            if download_state:
                if os.path.exists(models_archive_path):
                    # Just in case, deleting the old cached archive, if a new one is to be downloaded
                    os.remove(models_archive_path)
                headers = {}

                response = requests.get(url, headers=headers, stream=True)
                response.raise_for_status()

                if response.status_code == requests.codes.ok:
                    with open(models_archive_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=1048576):
                            f.write(chunk)
                    extract_state = True
            else:
                zip_content = zipfile.ZipFile(models_archive_path).namelist()
                for f in zip_content:
                    if not os.path.exists(os.path.join(models_path, f)):
                        extract_state = True

            if extract_state:
                # Perform a force deletion of the model folder, if already existing, and before extraction
                # to avoid mixing files.
                if os.path.exists(os.path.join(models_path, model_name)):
                    shutil.rmtree(os.path.join(models_path, model_name))
                with zipfile.ZipFile(models_archive_path, 'r') as zip_ref:
                    zip_ref.extractall(models_path)

            for d in dep:
                if d == d:
                    download_model(d)
        else:
            print("No model exists with the provided name: {}.\n".format(model_name))
            logging.error("No model exists with the provided name: {}.\n".format(model_name))
    except Exception as e:
        print('Issue trying to collect the latest {} model.\n'.format(model_name))
        print('{}'.format(traceback.format_exc()))
        logging.error('Issue trying to collect the latest {} model with: \n {}'.format(model_name,
                                                                                       traceback.format_exc()))
