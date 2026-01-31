from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

from kinect_forge.config import KinectIntrinsics


def _collect_calibration_points(
    image_paths: List[Path],
    pattern_size: Tuple[int, int],
    square_size: float,
) -> Tuple[List[np.ndarray], List[np.ndarray], Tuple[int, int]]:
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0 : pattern_size[0], 0 : pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size

    objpoints: List[np.ndarray] = []
    imgpoints: List[np.ndarray] = []
    image_size = None

    for path in image_paths:
        image = cv2.imread(str(path))
        if image is None:
            continue
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCorners(gray, pattern_size, None)
        if not found or corners is None:
            continue
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        objpoints.append(objp)
        imgpoints.append(corners2)
        image_size = (gray.shape[1], gray.shape[0])

    if image_size is None:
        raise RuntimeError("No valid chessboard detections found.")

    return objpoints, imgpoints, image_size


def calibrate_intrinsics(
    image_paths: List[Path],
    pattern_size: Tuple[int, int],
    square_size: float,
) -> KinectIntrinsics:
    objpoints, imgpoints, image_size = _collect_calibration_points(
        image_paths, pattern_size, square_size
    )

    if not objpoints or not imgpoints:
        raise RuntimeError("Not enough calibration images.")

    ret, camera_matrix, _, _, _ = cv2.calibrateCamera(
        objpoints, imgpoints, image_size, None, None
    )
    if not ret:
        raise RuntimeError("Calibration failed.")

    fx = float(camera_matrix[0, 0])
    fy = float(camera_matrix[1, 1])
    cx = float(camera_matrix[0, 2])
    cy = float(camera_matrix[1, 2])

    return KinectIntrinsics(
        width=image_size[0],
        height=image_size[1],
        fx=fx,
        fy=fy,
        cx=cx,
        cy=cy,
    )


def save_intrinsics(path: Path, intrinsics: KinectIntrinsics) -> None:
    path.write_text(json.dumps(asdict(intrinsics), indent=2))
