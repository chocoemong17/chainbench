"""Image-generation subset ported from Hansen's Regularization Tools blur.m.

Source: Netlib na4-matlab7.tgz, REGU/blur.m, v4.1 (March 2008).
Original function attribution: Per Christian Hansen, IMM, 11/11/97.
Only the procedural image is ported; its original blur operator is not used.
Copyright (c) 1993 and 1998 by Per Christian Hansen and IMM.

  ***************************************************************************
  * All the software  contained in this library  is protected by copyright. *
  * Permission  to use, copy, modify, and  distribute this software for any *
  * purpose without fee is hereby granted, provided that this entire notice *
  * is included  in all copies  of any software which is or includes a copy *
  * or modification  of this software  and in all copies  of the supporting *
  * documentation for such software.                                        *
  ***************************************************************************
  * THIS SOFTWARE IS BEING PROVIDED "AS IS", WITHOUT ANY EXPRESS OR IMPLIED *
  * WARRANTY. IN NO EVENT, NEITHER  THE AUTHORS, NOR THE PUBLISHER, NOR ANY *
  * MEMBER  OF THE EDITORIAL BOARD OF  THE JOURNAL  "NUMERICAL ALGORITHMS", *
  * NOR ITS EDITOR-IN-CHIEF, BE  LIABLE FOR ANY ERROR  IN THE SOFTWARE, ANY *
  * MISUSE  OF IT  OR ANY DAMAGE ARISING OUT OF ITS USE. THE ENTIRE RISK OF *
  * USING THE SOFTWARE LIES WITH THE PARTY DOING SO.                        *
  ***************************************************************************
  * ANY USE  OF THE SOFTWARE  CONSTITUTES  ACCEPTANCE  OF THE TERMS  OF THE *
  * ABOVE STATEMENT.                                                        *
  ***************************************************************************
"""

from __future__ import annotations

import numpy as np


def simple_image(n: int = 64) -> np.ndarray:
    """Return the source's ellipse/triangle/cross image, divided by its maximum 4."""
    if type(n) is not int or n not in (64, 256):
        raise ValueError("source image size must be 64 or 256")
    # MATLAB round for positive arguments (not Python ties-to-even).
    half, third, sixth, twelfth = (int(np.floor(n / d + 0.5)) for d in (2, 3, 6, 12))
    image = np.zeros((n, n))
    i, j = np.arange(1, sixth + 1)[:, None], np.arange(1, third + 1)[None, :]
    radius = (i / sixth) ** 2 + (j / third) ** 2

    def ellipse(threshold):
        quarter = (radius < threshold).astype(float)
        top = np.concatenate((quarter[:, ::-1], quarter), axis=1)
        return np.concatenate((top[::-1], top), axis=0)

    image[2 : 2 + 2 * sixth, third - 1 : third - 1 + 2 * third] = ellipse(1.0)
    image[sixth : 3 * sixth, third - 1 : third - 1 + 2 * third] += 2 * ellipse(0.6)
    image[image == 3] = 2
    image[third + twelfth : 2 * third + twelfth, 1 : 1 + third] = 3 * np.triu(
        np.ones((third, third))
    )
    cross = np.zeros((2 * sixth + 1, 2 * sixth + 1))
    cross[sixth, :] = 1
    cross[:, sixth] = 1
    image[half + twelfth : half + twelfth + cross.shape[0], half : half + cross.shape[1]] = (
        4 * cross
    )
    return image / 4
