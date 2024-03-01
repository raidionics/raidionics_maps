from ..Utils.resources import SharedResources


def get_metrics_target_class() -> str:
    target_class = SharedResources.getInstance().maps_gt_files_suffix.split('.')[0].split('label_')[-1]
    return target_class
