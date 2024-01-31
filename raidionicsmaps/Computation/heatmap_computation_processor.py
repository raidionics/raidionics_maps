from __future__ import division

import logging
import traceback
from typing import List
import numpy as np
import csv
import sys
import os
import scipy.ndimage.morphology as smo
import scipy.ndimage.measurements as smeas
from scipy.ndimage import binary_opening, measurements, binary_closing, binary_erosion, binary_dilation, \
    generate_binary_structure
from skimage.measure import regionprops
from tqdm import tqdm
import nibabel as nib

from ..Utils.resources import SharedResources


class HeatmapComputationProcessor:
    """

    """
    _cohort = None
    _mask_filenames = []
    _suffix = ""
    _output_folder = None

    def __init__(self, suffix=""):
        self.__reset()
        self._suffix = suffix
        self.output_folder = os.path.join(SharedResources.getInstance().maps_output_folder, 'Heatmaps')
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
    def suffix(self):
        return self._suffix

    @suffix.setter
    def suffix(self, s) -> None:
        self._suffix = s

    @property
    def output_folder(self):
        return self._output_folder

    @output_folder.setter
    def output_folder(self, s) -> None:
        self._output_folder = s

    def __reset(self):
        """
        All objects share class or static variables.
        An instance or non-static variables are different for different objects (every object has a copy).
        """
        self.cohort = None
        self._mask_filenames = []
        self._suffix = ""
        self._output_folder = None

    def setup(self, cohort):
        self.cohort = cohort

        for p in list(self.cohort.patients.keys()):
            mask_fn = self.cohort.patients[p].registered_label_filepaths
            if mask_fn is None or not os.path.exists(mask_fn):
                logging.warning("Registered annotation mask missing for {}".format(self.cohort.patients[p].patient_id))
            else:
                self.mask_filenames.append(mask_fn)

    def run(self):
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
            fl = patient.registered_label_filepaths
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
