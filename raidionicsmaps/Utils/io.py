import os
import nibabel as nib
import pandas as pd
import numpy as np
from nibabel import four_to_three


def load_nifti_volume(volume_path):
    nib_volume = nib.load(volume_path)
    if len(nib_volume.shape) > 3:
        if len(nib_volume.shape) == 4:  # Common problem
            nib_volume = four_to_three(nib_volume)[0]
        else:  # DWI volumes
            nib_volume = nib.Nifti1Image(nib_volume.get_fdata()[:, :, :, 0, 0], affine=nib_volume.affine)

    return nib_volume
