---
name: opencv-recognition
description: OpenCV template matching patterns for screen state detection in DQW AutoBattle
---

# OpenCV Template Matching Patterns

## Basic Template Match
```python
import cv2
import numpy as np

def find_template(screen: np.ndarray, template: np.ndarray, threshold: float = 0.8) -> tuple | None:
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        h, w = template.shape[:2]
        center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
        return center, max_val
    return None
