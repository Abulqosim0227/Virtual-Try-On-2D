import numpy as np
from PIL import Image, ImageStat

from vto.pipeline.context import TryOnContext


def postprocess(context: TryOnContext) -> TryOnContext:
    if context.result_image is None:
        return context

    context.result_image = _match_brightness(context.result_image, context.person_image)
    return context


def _match_brightness(result: Image.Image, reference: Image.Image) -> Image.Image:
    ref_stat = ImageStat.Stat(reference)
    res_stat = ImageStat.Stat(result)

    result_arr = np.array(result, dtype=np.float32)

    for ch in range(3):
        ref_mean = ref_stat.mean[ch]
        res_mean = res_stat.mean[ch]
        if res_mean == 0:
            continue
        scale = ref_mean / res_mean
        scale = max(0.8, min(1.2, scale))
        result_arr[:, :, ch] *= scale

    result_arr = np.clip(result_arr, 0, 255).astype(np.uint8)
    return Image.fromarray(result_arr)
