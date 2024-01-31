# Cohort map computation backend for Raidionics related publications

[![License](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg)](https://opensource.org/licenses/BSD-2-Clause)
[![](https://img.shields.io/badge/python-3.8|3.9|3.10|3.11|3.12-blue.svg)](https://www.python.org/downloads/)
[![Paper](https://zenodo.org/badge/DOI/10.3389/fneur.2022.932219.svg)](https://www.frontiersin.org/articles/10.3389/fneur.2022.932219/full)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/gist/dbouget/7560fe410db03e384a45ddc77bbe9a57/01_heatmap_generation_example.ipynb)

The code corresponds to the Raidionics backend for creating population-based maps from cohorts.
The module can either be used as a Python library, as CLI, or as Docker container.

## [Installation](https://github.com/dbouget/raidionics_maps#installation)

```
pip install git+https://github.com/dbouget/raidionics_maps.git
```

## [Continuous integration](https://github.com/dbouget/raidionics_maps#continuous-integration)

<div style="display: flex;">
  <div style="flex: 1; margin-right: 20px;">

| Operating System | Status                                                                                                                                                                                                                       |
|------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Windows**      | [![Build macOS](https://github.com/dbouget/raidionics_maps/actions/workflows/build_windows.yml/badge.svg)](https://github.com/dbouget/raidionics_maps/actions/workflows/build_windows.yml)                    |
| **Ubuntu**       | [![Build macOS](https://github.com/dbouget/raidionics_maps/actions/workflows/build_ubuntu.yml/badge.svg)](https://github.com/dbouget/raidionics_maps/actions/workflows/build_ubuntu.yml)       |
| **macOS**        | [![Build macOS](https://github.com/dbouget/raidionics_maps/actions/workflows/build_macos.yml/badge.svg)](https://github.com/dbouget/raidionics_maps/actions/workflows/build_macos.yml)         |
| **macOS ARM**    | [![Build macOS](https://github.com/dbouget/raidionics_maps/actions/workflows/build_macos_arm.yml/badge.svg)](https://github.com/dbouget/raidionics_maps/actions/workflows/build_macos_arm.yml) |
  </div>
</div>

## [Getting started](https://github.com/dbouget/raidionics_maps#getting-started)

### [Notebooks](https://github.com/dbouget/raidionics_maps#notebooks)

Below are Jupyter Notebooks including simple examples on how to get started.

<div style="display: flex;">
  <div style="flex: 1; margin-right: 20px;">

| Notebook             | Colab                                                                                                                                                                                                                                     | GitHub                                                                                                                                                                                      |
|----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Location heatmap** | <a href="" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a> | [![View on GitHub](https://img.shields.io/badge/View%20on%20GitHub-blue?logo=github)](https://github.com/dbouget/raidionics_maps/blob/master/notebooks/01_heatmap_generation_example.ipynb) |

  </div>
</div>

### [Usage](https://github.com/dbouget/raidionics_maps#usage)

In the following, a description of how the data should be organized on disk is provided, and a test dataset can
be downloaded [here](https://github.com/raidionics/Raidionics-models/releases/download/1.2.0/Samples-RaidionicsMaps_UnitTest1.zip).

<details>
<summary>

#### [Folder and data structures and naming conventions](https://github.com/dbouget/raidionics_maps#folder-and-data-structures-and-naming-conventions)
</summary>

#### [1.1 Original data folder structure](https://github.com/dbouget/raidionics_maps#11-original-data-folder-structure)
The main data directory containing the original 3D volumes and corresponding annotations for the class of
interest is expected to resemble the following structure:

    └── path/to/data/cohort/
        └── Pat001/
            ├── Pat001_MRI.nii.gz
            ├── Pat001_MRI_label_tumor.nii.gz
        └── Pat002/
            ├── Pat002_MRI.nii.gz
            ├── Pat002_MRI_label_tumor.nii.gz
        [...]
        └── PatXXX/
            ├── PatXXX_MRI.nii.gz
            └── PatXXX_MRI_label_tumor.nii.gz

#### [1.2 Results folder structure](https://github.com/dbouget/raidionics_maps#12-inference-results-folder-structure)
Results will be stored inside a sub-folder for each patient, following the same pattern as the input folder structure.
A registration folder is kept inside each patient sub-folder, for easy re-use and cohort inclusion, to update the
location heatmaps.

    └── path/to/cohort-results/
        └── Pat001/
            ├── Transforms/
            │   ├── Pat-to-MNI/
            │   │   ├── forward_***0GenericAffine.mat
            │   │   ├── forward_***1Warp.nii.gz
            │   │   ├── inverse_***0GenericAffine.mat
            │   │   └── inverse_***1InverseWarp.nii.gz  
            │   ├── input_reg_mni.nii.gz
            │   ├── input_reg_mni_label_tumor.nii.gz 
        [...]
        └── PatXXX/
            ├── Transforms/
            │   ├── Pat-to-MNI/
            │   │   ├── forward_***0GenericAffine.mat
            │   │   ├── forward_***1Warp.nii.gz
            │   │   ├── inverse_***0GenericAffine.mat
            │   │   └── inverse_***1InverseWarp.nii.gz  
            │   ├── input_reg_mni.nii.gz
            │   └── input_reg_mni_label_tumor.nii.gz

</details>

<details>
<summary>

### [Installation](https://github.com/dbouget/raidionics_maps#installation)
</summary>
Create a virtual environment using at least Python 3.8, and install all dependencies from
the requirements.txt file.

```
  cd /path/to/raidionics_maps  
  virtualenv -p python3 venv  
  source venv/bin/activate  
  TMPDIR=$PWD/venv pip install --cache-dir=$PWD/venv -r requirements.txt (--no-deps)
```

Then the final step is to do the following in a terminal.
```
  cd /path/to/raidionics_maps  
  cp blank_main_config.ini main_config.ini 
```

You can now edit your __main\_config.ini__ file for running the different processes.  
An additional explanation of all parameters specified in the configuration file can be
found in _/Utils/resources.py_. 

</details>

<details>
<summary>

### [Process](https://github.com/dbouget/raidionics_maps#process)
</summary>
To run, you need to supply the configuration file as parameter.

```
  python main.py -c main_config.ini (-v debug)
```

</details>

## [How to cite](https://github.com/dbouget/raidionics_maps#how-to-cite)

If you are using Raidionics in your research, please cite the following references.

For segmentation validation and metrics computation:
```
@article{bouget2022preoptumorseg,
    title={Preoperative Brain Tumor Imaging: Models and Software for Segmentation and Standardized Reporting},
    author={Bouget, David and Pedersen, André and Jakola, Asgeir S. and Kavouridis, Vasileios and Emblem, Kyrre E. and Eijgelaar, Roelant S. and Kommers, Ivar and Ardon, Hilko and Barkhof, Frederik and Bello, Lorenzo and Berger, Mitchel S. and Conti Nibali, Marco and Furtner, Julia and Hervey-Jumper, Shawn and Idema, Albert J. S. and Kiesel, Barbara and Kloet, Alfred and Mandonnet, Emmanuel and Müller, Domenique M. J. and Robe, Pierre A. and Rossi, Marco and Sciortino, Tommaso and Van den Brink, Wimar A. and Wagemakers, Michiel and Widhalm, Georg and Witte, Marnix G. and Zwinderman, Aeilko H. and De Witt Hamer, Philip C. and Solheim, Ole and Reinertsen, Ingerid},
    journal={Frontiers in Neurology},
    volume={13},
    year={2022},
    url={https://www.frontiersin.org/articles/10.3389/fneur.2022.932219},
    doi={10.3389/fneur.2022.932219},
    issn={1664-2295}
}
```

The final software including updated performance metrics for preoperative tumors and introducing postoperative tumor segmentation:
```
@article{bouget2023raidionics,
    author = {Bouget, David and Alsinan, Demah and Gaitan, Valeria and Holden Helland, Ragnhild and Pedersen, André and Solheim, Ole and Reinertsen, Ingerid},
    year = {2023},
    month = {09},
    pages = {},
    title = {Raidionics: an open software for pre-and postoperative central nervous system tumor segmentation and standardized reporting},
    volume = {13},
    journal = {Scientific Reports},
    doi = {10.1038/s41598-023-42048-7},
}
```
