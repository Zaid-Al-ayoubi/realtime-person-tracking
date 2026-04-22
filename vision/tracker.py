"""
ByteTrack wrapper — maintains person IDs across frames.

Refactored from YOLOv80 0.3 (Vedio).py and Face.py.
track_id is TEMPORARY and only valid within one processing session.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from vision.detector import Detection

logger = get_logger(__name__)


@dataclass
class TrackedPerson:
    track_id: int
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    face_bbox: tuple[int, int, int, int] | None
    face_confidence: float
    face_stable: bool = False   # True once face is confirmed N consecutive frames


class PersonTracker:
    """
    Wraps ultralytics ByteTrack. Adds a face-stability filter:
    a face is only considered verified after it appears in N consecutive
    frames for the same track_id (avoids false positives from side views).
    """

    def __init__(self, stability_frames: int | None = None) -> None:
        from app.config import settings
        self.stability_frames = stability_frames or settings.FACE_STABILITY_FRAMES
        # Per track_id consecutive face detection counter
        self._face_counters: dict[int, int] = {}
        self._stable_ids: set[int] = set()

    def update(
        self, detections: list["Detection"], frame: np.ndarray
    ) -> list[TrackedPerson]:
        """
        Run ByteTrack on the current frame detections.
        Returns a list of TrackedPerson with stable face flags.
        """
        if not detections:
            return []

        try:
            from ultralytics import YOLO
            # We use the tracker built into ultralytics — it is already applied
            # when calling model.track(). Here we receive pre-detected boxes
            # and assign track IDs using a lightweight association.
            # For direct ByteTrack integration (without re-running YOLO), we
            # use the supervision or boxmot library if available, else fall back.
            return self._track_with_boxmot(detections, frame)
        except ImportError:
            return self._simple_passthrough(detections)

    def _track_with_boxmot(
        self, detections: list["Detection"], frame: np.ndarray
    ) -> list[TrackedPerson]:
        """Use boxmot's ByteTrack directly on pre-computed boxes."""
        try:
            import boxmot
            if not hasattr(self, "_tracker"):
                from boxmot import ByteTrack
                self._tracker = ByteTrack()

            # boxmot expects (x1,y1,x2,y2,conf,cls) array
            dets_arr = np.array(
                [[*d.bbox, d.confidence, 0] for d in detections], dtype=np.float32
            )
            tracks = self._tracker.update(dets_arr, frame)  # returns (x1,y1,x2,y2,id,conf,cls,idx)

            tracked = []
            for t in tracks:
                x1, y1, x2, y2 = int(t[0]), int(t[1]), int(t[2]), int(t[3])
                tid = int(t[4])
                conf = float(t[5])

                # Find matching detection by highest IoU
                best_det = self._match_detection(detections, (x1, y1, x2, y2))
                face_bbox = best_det.face_bbox if best_det else None
                face_conf = best_det.face_confidence if best_det else 0.0

                stable = self._update_face_stability(tid, face_bbox is not None)

                tracked.append(
                    TrackedPerson(
                        track_id=tid,
                        bbox=(x1, y1, x2, y2),
                        confidence=conf,
                        face_bbox=face_bbox,
                        face_confidence=face_conf,
                        face_stable=stable,
                    )
                )
            return tracked
        except Exception as exc:
            logger.warning("tracker.boxmot_failed", error=str(exc))
            return self._simple_passthrough(detections)

    def _simple_passthrough(
        self, detections: list["Detection"]
    ) -> list[TrackedPerson]:
        """
        Fallback when ByteTrack is unavailable.
        Assigns sequential IDs — no cross-frame consistency.
        Sufficient for batch processing where frame sequences are short.
        """
        tracked = []
        for i, det in enumerate(detections):
            tracked.append(
                TrackedPerson(
                    track_id=i,
                    bbox=det.bbox,
                    confidence=det.confidence,
                    face_bbox=det.face_bbox,
                    face_confidence=det.face_confidence,
                    face_stable=det.face_bbox is not None,
                )
            )
        return tracked

    def _update_face_stability(self, track_id: int, face_detected: bool) -> bool:
        if face_detected:
            self._face_counters[track_id] = self._face_counters.get(track_id, 0) + 1
        else:
            # Decay
            self._face_counters[track_id] = max(
                0, self._face_counters.get(track_id, 0) - 1
            )
        is_stable = self._face_counters[track_id] >= self.stability_frames
        if is_stable:
            self._stable_ids.add(track_id)
        return track_id in self._stable_ids

    @staticmethod
    def _match_detection(
        detections: list["Detection"],
        bbox: tuple[int, int, int, int],
    ) -> "Detection | None":
        best, best_iou = None, 0.0
        for det in detections:
            iou = _iou(det.bbox, bbox)
            if iou > best_iou:
                best_iou = iou
                best = det
        return best if best_iou > 0.3 else None


def _iou(a: tuple, b: tuple) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)
