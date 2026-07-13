import os
import numpy as np
from unittest.mock import patch, MagicMock, mock_open


@patch("face_pipeline.os.path.exists")
@patch("face_pipeline.os.path.abspath")
@patch("face_pipeline.cv2")
def test_face_pipeline_init(mock_cv2, mock_abspath, mock_exists):
    mock_abspath.return_value = "C:\\app\\face_pipeline.py"
    mock_exists.return_value = True

    from face_pipeline import FacePipeline
    fp = FacePipeline()
    assert fp.detector_path.endswith("face_detection_yunet_2023mar.onnx")
    assert fp.recognizer_path.endswith("face_recognition_sface_2021dec.onnx")


@patch("face_pipeline.os.path.exists")
@patch("face_pipeline.os.path.abspath")
@patch("face_pipeline.cv2")
def test_face_pipeline_init_missing_detector(mock_cv2, mock_abspath, mock_exists):
    mock_abspath.return_value = "C:\\app\\face_pipeline.py"
    mock_exists.side_effect = lambda p: "recognizer" in p

    from face_pipeline import FacePipeline
    try:
        FacePipeline()
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


@patch("face_pipeline.os.path.exists")
@patch("face_pipeline.os.path.abspath")
@patch("face_pipeline.cv2")
def test_face_pipeline_init_missing_recognizer(mock_cv2, mock_abspath, mock_exists):
    mock_abspath.return_value = "C:\\app\\face_pipeline.py"
    mock_exists.side_effect = lambda p: "detector" in p

    from face_pipeline import FacePipeline
    try:
        FacePipeline()
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


@patch("face_pipeline.os.path.exists")
@patch("face_pipeline.os.path.abspath")
@patch("face_pipeline.cv2")
def test_detect_faces_no_faces(mock_cv2, mock_abspath, mock_exists):
    mock_abspath.return_value = "C:\\app\\face_pipeline.py"
    mock_exists.return_value = True

    mock_recognizer = MagicMock()
    mock_cv2.FaceRecognizerSF.create.return_value = mock_recognizer
    mock_detector = MagicMock()
    mock_cv2.FaceDetectorYN.create.return_value = mock_detector
    mock_detector.detect.return_value = (False, None)

    from face_pipeline import FacePipeline
    fp = FacePipeline()
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = fp.detect_faces(img)
    assert faces == []


@patch("face_pipeline.os.path.exists")
@patch("face_pipeline.os.path.abspath")
@patch("face_pipeline.cv2")
def test_detect_faces_with_results(mock_cv2, mock_abspath, mock_exists):
    mock_abspath.return_value = "C:\\app\\face_pipeline.py"
    mock_exists.return_value = True

    mock_recognizer = MagicMock()
    mock_cv2.FaceRecognizerSF.create.return_value = mock_recognizer
    mock_detector = MagicMock()
    mock_cv2.FaceDetectorYN.create.return_value = mock_detector

    face_data = np.array([[10, 20, 50, 60, 30, 31, 32, 33, 34, 40, 41, 42, 43, 44, 0.95]], dtype=np.float64)
    mock_detector.detect.return_value = (True, face_data)

    from face_pipeline import FacePipeline
    fp = FacePipeline()
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = fp.detect_faces(img)
    assert len(faces) == 1
    assert faces[0]["score"] == 0.95
    assert len(faces[0]["bbox"]) == 4
    assert len(faces[0]["landmarks"]) == 5
    assert "raw_face" in faces[0]


@patch("face_pipeline.os.path.exists")
@patch("face_pipeline.os.path.abspath")
@patch("face_pipeline.cv2")
def test_detect_faces_multiple(mock_cv2, mock_abspath, mock_exists):
    mock_abspath.return_value = "C:\\app\\face_pipeline.py"
    mock_exists.return_value = True

    mock_recognizer = MagicMock()
    mock_cv2.FaceRecognizerSF.create.return_value = mock_recognizer
    mock_detector = MagicMock()
    mock_cv2.FaceDetectorYN.create.return_value = mock_detector

    face_data = np.array([
        [10, 20, 50, 60, 30, 31, 32, 33, 34, 40, 41, 42, 43, 44, 0.95],
        [100, 200, 30, 40, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 0.85],
    ], dtype=np.float64)
    mock_detector.detect.return_value = (True, face_data)

    from face_pipeline import FacePipeline
    fp = FacePipeline()
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = fp.detect_faces(img)
    assert len(faces) == 2
    assert faces[0]["score"] == 0.95
    assert faces[1]["score"] == 0.85


@patch("face_pipeline.os.path.exists")
@patch("face_pipeline.os.path.abspath")
@patch("face_pipeline.cv2")
def test_detect_faces_score_threshold(mock_cv2, mock_abspath, mock_exists):
    mock_abspath.return_value = "C:\\app\\face_pipeline.py"
    mock_exists.return_value = True

    mock_recognizer = MagicMock()
    mock_cv2.FaceRecognizerSF.create.return_value = mock_recognizer
    mock_detector = MagicMock()
    mock_detector.detect.return_value = (False, None)
    mock_cv2.FaceDetectorYN.create.return_value = mock_detector

    from face_pipeline import FacePipeline
    fp = FacePipeline()
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    fp.detect_faces(img, score_threshold=0.8)
    call_kwargs = mock_cv2.FaceDetectorYN.create.call_args
    assert call_kwargs is not None


@patch("face_pipeline.os.path.exists")
@patch("face_pipeline.os.path.abspath")
@patch("face_pipeline.cv2")
def test_extract_embedding(mock_cv2, mock_abspath, mock_exists):
    mock_abspath.return_value = "C:\\app\\face_pipeline.py"
    mock_exists.return_value = True

    mock_recognizer = MagicMock()
    mock_cv2.FaceRecognizerSF.create.return_value = mock_recognizer
    mock_detector = MagicMock()
    mock_cv2.FaceDetectorYN.create.return_value = mock_detector

    aligned = np.zeros((112, 112, 3), dtype=np.uint8)
    mock_recognizer.alignCrop.return_value = aligned
    mock_recognizer.feature.return_value = np.random.randn(1, 128).astype(np.float32)

    from face_pipeline import FacePipeline
    fp = FacePipeline()
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    raw_face = np.random.randn(15).astype(np.float64)
    embedding = fp.extract_embedding(img, raw_face)
    assert len(embedding) == 128
    assert all(isinstance(v, float) for v in embedding)
    mock_recognizer.alignCrop.assert_called_once_with(img, raw_face)
    mock_recognizer.feature.assert_called_once_with(aligned)


@patch("face_pipeline.os.path.exists")
@patch("face_pipeline.os.path.abspath")
@patch("face_pipeline.cv2")
def test_extract_embedding_normalized(mock_cv2, mock_abspath, mock_exists):
    mock_abspath.return_value = "C:\\app\\face_pipeline.py"
    mock_exists.return_value = True

    mock_recognizer = MagicMock()
    mock_cv2.FaceRecognizerSF.create.return_value = mock_recognizer
    mock_detector = MagicMock()
    mock_cv2.FaceDetectorYN.create.return_value = mock_detector

    aligned = np.zeros((112, 112, 3), dtype=np.uint8)
    mock_recognizer.alignCrop.return_value = aligned
    mock_recognizer.feature.return_value = np.array([[0.5] * 128], dtype=np.float32)

    from face_pipeline import FacePipeline
    fp = FacePipeline()
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    raw_face = np.random.randn(15).astype(np.float64)
    embedding = fp.extract_embedding(img, raw_face)
    assert embedding == [0.5] * 128
