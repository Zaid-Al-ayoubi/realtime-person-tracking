"""
Unit tests for VideoRingBuffer — no camera or CV models needed.
"""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from vision.video_buffer import VideoRingBuffer


def make_frame(h=480, w=640) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_buffer_push_and_limit():
    buf = VideoRingBuffer(fps=1.0, max_seconds=5)
    for _ in range(10):
        buf.push(make_frame())
    # maxlen = fps * max_seconds = 5
    assert len(buf._buffer) == 5


def test_buffer_flush_creates_file(tmp_path):
    buf = VideoRingBuffer(fps=25.0, max_seconds=2)
    for _ in range(50):
        buf.push(make_frame())

    out = str(tmp_path / "test_clip.mp4")
    with patch("cv2.VideoWriter") as mock_writer_cls:
        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer
        buf.flush_to_file(out)
        assert mock_writer.write.call_count == 50
        mock_writer.release.assert_called_once()


def test_empty_buffer_flush_does_not_raise(tmp_path):
    buf = VideoRingBuffer(fps=25.0, max_seconds=10)
    out = str(tmp_path / "empty.mp4")
    result = buf.flush_to_file(out)
    assert result == out
