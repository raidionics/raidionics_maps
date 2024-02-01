from __future__ import division

import logging
import traceback
from typing import List
import numpy as np
import csv
import sys
import os
from copy import deepcopy
import scipy.ndimage.measurements as smeas
from scipy.ndimage import measurements
from skimage.measure import regionprops
from tqdm import tqdm
import nibabel as nib

from ..Utils.resources import SharedResources


class HeatmapComputationProcessor:
    """

    """
    _cohort = None  # Placeholder for all loaded patients belonging to the cohort of interest
    _mask_filenames = []  # List of strings indicating the filepaths for all annotation masks to use to generate the location heatmap
    _suffix = ""  # Specific name to append to the generated heatmap files
    _output_directory = None  # Overall directory designating the location where all the computed results are to be stored
    _output_folder = None

    def __init__(self, suffix=""):
        self.__reset()
        self._suffix = suffix
        self.output_directory = os.path.join(SharedResources.getInstance().maps_output_folder, 'Heatmaps')
        os.makedirs(self.output_directory, exist_ok=True)
        self.output_folder = os.path.join(self.output_directory, 'Overall')
        os.makedirs(self.output_folder, exist_ok=True)

    @property
    def cohort(self):
        return self._cohort

    @cohort.setter
    def cohort(self, input_cohort) -> None:
        self._cohort = input_cohort

    @property
    def mask_filenames(self) -> List[str]:
        return self._mask_filenames

    @mask_filenames.setter
    def mask_filenames(self, filenames: List[str]) -> None:
        self._mask_filenames = filenames

    @property
    def suffix(self) -> str:
        return self._suffix

    @suffix.setter
    def suffix(self, s: str) -> None:
        self._suffix = s

    @property
    def output_directory(self) -> str:
        return self._output_directory

    @output_directory.setter
    def output_directory(self, s: str) -> None:
        self._output_directory = s

    @property
    def output_folder(self) -> str:
        return self._output_folder

    @output_folder.setter
    def output_folder(self, s: str) -> None:
        self._output_folder = s

    def __reset(self) -> None:
        """
        All objects share class or static variables.
        An instance or non-static variables are different for different objects (every object has a copy).
        """
        self.cohort = None
        self._mask_filenames = []
        self._suffix = ""
        self._output_directory = None
        self._output_folder = None

    def setup(self, cohort) -> None:
        """
        Iterates over all patients belonging to the cohort for asserting the existence of an annotation mask of the
        structure of interest, registered in the atlas-space.
        A warning is raised for each patient were a proper annotation mask cannot be found, for visual inspection.
        :param cohort: Container for all loaded patients.
        :return: None
        """
        self.cohort = cohort

        for p in list(self.cohort.patients.keys()):
            mask_fn = self.cohort.patients[p].registered_label_filepath
            if mask_fn is None or not os.path.exists(mask_fn):
                logging.warning("Registered annotation mask missing for {}".format(self.cohort.patients[p].patient_id))
            else:
                self.mask_filenames.append(mask_fn)

    def run(self) -> None:
        """

        :return:
        """
        logging.info("Computing location heatmap for the complete cohort!")
        self.__run()
        for d in SharedResources.getInstance().maps_distribution_dense_parameters:
            params = d.split(',')
            thresholds = [float(x) for x in params[1].split('-')]
            limits = [None, thresholds[0]]
            rparams = [params[0], limits]
            self._suffix = '_' + params[0] + '<' + str(thresholds[0])
            self.output_folder = os.path.join(self.output_directory, 'Population' + self._suffix)
            os.makedirs(self.output_folder, exist_ok=True)
            logging.info("Computing location heatmap for patients with {} under {}".format(params[0], str(thresholds[0])))
            self.__run(dense_parameters=rparams)
            for i, thr in enumerate(thresholds[1:-1]):
                limits = [thresholds[i-1], thr]
                rparams = [params[0], limits]
                self._suffix = '_' + params[0] + '_Range' + str(rparams[0]) + '_' + str(rparams[1])
                self.output_folder = os.path.join(self.output_directory, 'Population' + self._suffix)
                os.makedirs(self.output_folder, exist_ok=True)
                logging.info(
                    "Computing location heatmap for patients with {} in the range [{}, {}]".format(params[0], str(rparams[0]), str(rparams[1])))
                self.__run(dense_parameters=rparams)
            limits = [thresholds[-1], None]
            rparams = [params[0], limits]
            self._suffix = '_' + params[0] + '>=' + str(thresholds[-1])
            self.output_folder = os.path.join(self.output_directory, 'Population' + self._suffix)
            os.makedirs(self.output_folder, exist_ok=True)
            logging.info("Computing location heatmap for patients with {} over {}".format(params[0], str(thresholds[-1])))
            self.__run(dense_parameters=rparams)
        for c in SharedResources.getInstance().maps_distribution_categorical_parameters:
            params = c.split(',')
            if params[1].strip() == '':
                cat = list(np.unique(self.cohort.extra_patients_parameters[params[0]].values))
            else:
                cat = [params[1]]
            for cc in cat:
                rparams = [params[0], cc]
                self._suffix = '_' + params[0] + '-' + cc
                self.output_folder = os.path.join(self.output_directory, 'Population' + self._suffix)
                os.makedirs(self.output_folder, exist_ok=True)
                logging.info("Computing location heatmap for patients with {} as {}".format(params[0], cc))
                self.__run(cat_parameters=rparams)

    def __run(self, dense_parameters=None, cat_parameters=None) -> None:
        """
        Generates the location heatmap for the cohort of interest, whereby six elements are created:
            * heatmap_cumulative.nii.gz: for each voxel, the likelihood is expressed as the total number of patients featuring the object of interest in that location
            * heatmap_percentages.nii.gz: for each voxel, the likelihood is expressed as the percentages of patients featuring the object of interest in that location over the total number of patients in the cohort
            * heatmap_centroids_cumulative.nii.gz: same as the first file, except that only a 3x3x3 pixels centroid is used to represent each object of interest
            * heatmap_centroids_percentages.nii.gz: same as the second file, except that only a 3x3x3 pixels centroid is used to represent each object of interest
            * heatmap_patient_ids.nii.gz: (debug file) where the centroid of each object of interest is marked with the patient id, for an easier identification and correction of outliers
            * patients_ids_lut.csv: (debug file) a look-up-table is provided for mapping each patient internal id with the corresponding patient folder name.
        In the case of centroids generation with multifocal objects of interest, a centroid is created for each foci.
        :param: dense_parameters
        :param: cat_parameters
        :return: Nothing, the appropriate files are saved on disk directly
        """
        atlas_ni = nib.load(SharedResources.getInstance().mni_atlas_filepath_T1)
        atlas = atlas_ni.get_data()
        heatmap = np.zeros(atlas.shape)
        heatmap_centroids = np.zeros(atlas.shape)

        # The pids are a simply ascending counter. Should a look-up-table between counter and patient_id be saved on disk?
        heatmap_pids = np.zeros(atlas.shape).astype(np.uint16)

        count = 0
        logging.info('Collecting data in memory...')
        for i, p in enumerate(tqdm(self.cohort.patients)):
            patient = self.cohort.patients[p]
            pid = patient.patient_id
            if dense_parameters is not None or cat_parameters is not None:
                if dense_parameters is not None and cat_parameters is None:
                    param_value = self.cohort.extra_patients_parameters.loc[self.cohort.extra_patients_parameters['Patient'] == pid][dense_parameters[0]].values[0]
                    param_limits = dense_parameters[1]
                    if param_limits[0] is None and param_value > param_limits[1]:
                        continue
                    elif param_limits[1] is None and param_value <= param_limits[0]:
                        continue
                    elif ((param_limits[0] is not None and param_value < param_limits[0]) and
                          (param_limits[1] is not None and param_value > param_limits[1])):
                        continue
                elif dense_parameters is None and cat_parameters is not None:
                    param_value = self.cohort.extra_patients_parameters.loc[self.cohort.extra_patients_parameters['Patient'] == pid][cat_parameters[0]].values[0]
                    if param_value != cat_parameters[1]:
                        continue
            fl = patient.registered_label_filepath
            labels = None
            try:
                labels_ni = nib.load(fl)
                labels = labels_ni.get_fdata()[:].astype('uint8')
            except Exception as e:
                print('Issue loading {}.\n Skipping...'.format(fl))
                continue

            if labels is not None and labels.shape == heatmap.shape and np.count_nonzero(labels) != 0:
                # heatmap[labels == 1] += 1
                heatmap[labels != 0] += 1

                try:
                    # If multifocal, computing the center of mass for each foci rather than overall, excluding object smaller than 0.1ml
                    tumor_clusters = measurements.label(labels)[0]
                    tumor_clusters_labels = regionprops(tumor_clusters)
                    # Sorting by cluster size to get the parameters of the main component.
                    tumor_clusters_labels = sorted(tumor_clusters_labels, key=lambda r: r.area, reverse=True)

                    for clus in tumor_clusters_labels:
                        clus_volume = clus.area * np.prod(labels_ni.header.get_zooms())
                        clus_volume_ml = clus_volume * 1e-3
                        if clus_volume_ml >= 0.1:
                            clus_lab = np.zeros(labels.shape)
                            clus_lab[tumor_clusters == clus.label] = 1
                            com = smeas.center_of_mass(clus_lab)
                            heatmap_centroids[int(com[0]) - 3:int(com[0]) + 3, int(com[1]) - 3:int(com[1]) + 3,
                            int(com[2]) - 3:int(com[2]) + 3] += 1
                            heatmap_pids[int(com[0]) - 3:int(com[0]) + 3, int(com[1]) - 3:int(com[1]) + 3,
                            int(com[2]) - 3:int(com[2]) + 3] = (count + 1)
                    count += 1
                except Exception as e:
                    print('Could not compute center of mass for {}.'.format(fl))
                    print('Collected: {}'.format(traceback.format_exc()))

        heatmap_perc = np.zeros(atlas.shape)
        heatmap_perc = heatmap / count
        heatmap_centroids_perc = heatmap_centroids / count

        logging.info('Writing heatmaps to disk')
        dtype = np.uint16
        output_filename_heatmap = os.path.join(self.output_folder,
                                               'heatmap_cumulative' + self.suffix + '.nii.gz')
        heatmap_ni = nib.Nifti1Image(heatmap.astype(dtype), atlas_ni.affine, atlas_ni.header)
        heatmap_ni.set_data_dtype(dtype)
        nib.save(heatmap_ni, filename=output_filename_heatmap)

        dtype = np.float32
        output_filename_heatmap_perc = os.path.join(self.output_folder,
                                                    'heatmap_percentages' + self.suffix + '.nii.gz')
        heatmap_perc_ni = nib.Nifti1Image(heatmap_perc.astype(dtype), atlas_ni.affine, atlas_ni.header)
        heatmap_ni.set_data_dtype(dtype)
        nib.save(heatmap_perc_ni, filename=output_filename_heatmap_perc)

        dtype = np.uint16
        output_filename_heatmap_centroids = os.path.join(self.output_folder,
                                                         'heatmap_centroids_cumulative' + self.suffix + '.nii.gz')
        heatmap_com_ni = nib.Nifti1Image(heatmap_centroids.astype(dtype), atlas_ni.affine, atlas_ni.header)
        heatmap_ni.set_data_dtype(dtype)
        nib.save(heatmap_com_ni, filename=output_filename_heatmap_centroids)

        dtype = np.float32
        output_filename_heatmap_com_perc = os.path.join(self.output_folder,
                                                        'heatmap_centroids_percentages' + self.suffix + '.nii.gz')
        heatmap_com_perc_ni = nib.Nifti1Image(heatmap_centroids_perc.astype(dtype), atlas_ni.affine, atlas_ni.header)
        heatmap_ni.set_data_dtype(dtype)
        nib.save(heatmap_com_perc_ni, filename=output_filename_heatmap_com_perc)

        dtype = np.uint16
        output_filename_heatmap_pids = os.path.join(self.output_folder,
                                                    'heatmap_patient_ids' + self.suffix + '.nii.gz')
        heatmap_pids_ni = nib.Nifti1Image(heatmap_pids.astype(dtype), atlas_ni.affine, atlas_ni.header)
        heatmap_ni.set_data_dtype(dtype)
        nib.save(heatmap_pids_ni, filename=output_filename_heatmap_pids)

        logging.info('Computed heatmap location with {} samples.'.format(count))
