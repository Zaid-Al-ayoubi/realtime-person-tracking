"""
Simple IoU-based tracker — dependency-free reference implementation.

Works well enough for Phase 1 smoke tests and for low-density scenes.
Phase 2 swaps this out for ByteTrack (via ultralytics track) without
any caller changes, thanks to the `Tracker` interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.vision.detection.base import Detection
from app.vision.tracking.base import Track, Tracker


@dataclass
class _LiveTrack:
    track_id: int
    last_bbox: tuple[float, float, float, float]
    missed: int = 0


class IoUTracker(Tracker):
    def __init__(self, iou_threshold: float = 0.3, max_missed: int = 10) -> None:
        self._iou_threshold = iou_threshold
        self._max_missed = max_missed
        self._live: list[_LiveTrack] = []
        self._next_id = 1

    def update(self, detections: Sequence[Detection]) -> Sequence[Track]:
        matched: list[Track] = []
        used_dets: set[int] = set()
        used_tracks: set[int] = set()

        # Greedy matching — good enough for a reference impl.
        pairs = []
        for ti, trk in enumerate(self._live):
            for di, det in enumerate(detections):
                iou = _iou(trk.last_bbox, (det.x, det.y, det.w, det.h))
                if iou >= self._iou_threshold:
                    pairs.append((iou, ti, di))
        pairs.sort(reverse=True)

        for iou, ti, di in pairs:
            if ti in used_tracks or di in used_dets:
                continue
            trk = self._live[ti]
            det = detections[di]
            trk.last_bbox = (det.x, det.y, det.w, det.h)
            trk.missed = 0
            matched.append(Track(track_id=trk.track_id, detection=det))
            used_tracks.add(ti)
            used_dets.add(di)

        # New tracks for unmatched detections
        for di, det in enumerate(detections):
            if di in used_dets:
                continue
            new = _LiveTrack(
                track_id=self._next_id,
                last_bbox=(det.x, det.y, det.w, det.h),
            )
            self._next_id += 1
            self._live.append(new)
            matched.append(Track(track_id=new.track_id, detection=det))

        # Age out unmatched tracks
        survivors: list[_LiveTrack] = []
        for ti, trk in enumerate(self._live):
            if ti in used_tracks:
                survivors.append(trk)
                continue
            trk.missed += 1
            if trk.missed <= self._max_missed:
                survivors.append(trk)
        self._live = survivors

        return matched

    def reset(self) -> None:
        self._live.clear()
        self._next_id = 1


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter = inter_w * inter_h
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0
