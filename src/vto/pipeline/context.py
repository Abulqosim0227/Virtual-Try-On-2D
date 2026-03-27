from typing import Literal

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field


class TryOnContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    person_image: Image.Image
    garment_image: Image.Image
    category: Literal["upper", "lower", "full"]
    cache_key: str
    tier: Literal["fast", "hd"]

    pose_keypoints: np.ndarray | None = None
    parsed_mask: np.ndarray | None = None
    garment_mask: Image.Image | None = None

    result_image: Image.Image | None = None

    timings: dict[str, float] = Field(default_factory=dict)
    model_used: str | None = None
