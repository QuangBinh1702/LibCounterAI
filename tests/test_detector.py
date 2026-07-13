import pytest
import numpy as np
from unittest.mock import patch, MagicMock, PropertyMock


@patch("detector.ort")
def test_detector_init(mock_ort):
    mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
    mock_session = MagicMock()
    mock_ort.InferenceSession.return_value = mock_session
    mock_input = MagicMock()
    mock_input.name = "images"
    type(mock_input).shape = PropertyMock(return_value=[1, 3, 640, 640])
    mock_session.get_inputs.return_value = [mock_input]

    from detector import YOLOv8Detector
    det = YOLOv8Detector(model_path="/fake/path.onnx")
    assert det.conf_threshold == 0.4
    assert det.nms_threshold == 0.4
    assert det.input_width == 640
    assert det.input_height == 640


@patch("detector.ort")
def test_detector_init_custom_thresholds(mock_ort):
    mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
    mock_session = MagicMock()
    mock_ort.InferenceSession.return_value = mock_session
    mock_input = MagicMock()
    mock_input.name = "images"
    type(mock_input).shape = PropertyMock(return_value=[1, 3, 640, 640])
    mock_session.get_inputs.return_value = [mock_input]

    from detector import YOLOv8Detector
    det = YOLOv8Detector(model_path="/fake/path.onnx", conf_threshold=0.5, nms_threshold=0.6)
    assert det.conf_threshold == 0.5
    assert det.nms_threshold == 0.6


@patch("detector.ort")
def test_preprocess_output_shape(mock_ort):
    mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
    mock_session = MagicMock()
    mock_ort.InferenceSession.return_value = mock_session
    mock_input = MagicMock()
    mock_input.name = "images"
    type(mock_input).shape = PropertyMock(return_value=[1, 3, 640, 640])
    mock_session.get_inputs.return_value = [mock_input]

    from detector import YOLOv8Detector
    det = YOLOv8Detector(model_path="/fake/path.onnx")
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    batch, orig_w, orig_h = det.preprocess(img)
    assert batch.shape == (1, 3, 640, 640)
    assert orig_w == 640
    assert orig_h == 480
    assert batch.dtype == np.float32


@patch("detector.ort")
def test_preprocess_normalization(mock_ort):
    mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
    mock_session = MagicMock()
    mock_ort.InferenceSession.return_value = mock_session
    mock_input = MagicMock()
    mock_input.name = "images"
    type(mock_input).shape = PropertyMock(return_value=[1, 3, 640, 640])
    mock_session.get_inputs.return_value = [mock_input]

    from detector import YOLOv8Detector
    det = YOLOv8Detector(model_path="/fake/path.onnx")
    img = np.full((480, 640, 3), 255, dtype=np.uint8)
    batch, _, _ = det.preprocess(img)
    assert np.allclose(batch[0, 0, 0, 0], 1.0)
    assert np.allclose(batch[0, 0, 5, 5], 1.0)


@patch("detector.ort")
def test_preprocess_non_square_input(mock_ort):
    mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
    mock_session = MagicMock()
    mock_ort.InferenceSession.return_value = mock_session
    mock_input = MagicMock()
    mock_input.name = "images"
    type(mock_input).shape = PropertyMock(return_value=[1, 3, 320, 320])
    mock_session.get_inputs.return_value = [mock_input]

    from detector import YOLOv8Detector
    det = YOLOv8Detector(model_path="/fake/path.onnx")
    img = np.zeros((200, 400, 3), dtype=np.uint8)
    batch, orig_w, orig_h = det.preprocess(img)
    assert batch.shape == (1, 3, 320, 320)
    assert orig_w == 400
    assert orig_h == 200


@patch("detector.ort")
@patch("detector.cv2")
def test_postprocess_no_detections(mock_cv2, mock_ort):
    mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
    mock_session = MagicMock()
    mock_ort.InferenceSession.return_value = mock_session
    mock_input = MagicMock()
    mock_input.name = "images"
    type(mock_input).shape = PropertyMock(return_value=[1, 3, 640, 640])
    mock_session.get_inputs.return_value = [mock_input]

    mock_session.run.return_value = [np.zeros((1, 84, 8400), dtype=np.float32)]
    mock_cv2.dnn.NMSBoxes.return_value = np.array([], dtype=np.int32)

    from detector import YOLOv8Detector
    det = YOLOv8Detector(model_path="/fake/path.onnx")
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    result = det.detect(img)
    assert result == []


@patch("detector.ort")
@patch("detector.cv2")
def test_postprocess_with_detections(mock_cv2, mock_ort):
    mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
    mock_session = MagicMock()
    mock_ort.InferenceSession.return_value = mock_session
    mock_input = MagicMock()
    mock_input.name = "images"
    type(mock_input).shape = PropertyMock(return_value=[1, 3, 640, 640])
    mock_session.get_inputs.return_value = [mock_input]

    output = np.zeros((1, 84, 8400), dtype=np.float32)
    output[0, 0, 0] = 320
    output[0, 1, 0] = 320
    output[0, 2, 0] = 40
    output[0, 3, 0] = 80
    output[0, 4, 0] = 0.9
    mock_session.run.return_value = [output]
    mock_cv2.dnn.NMSBoxes.return_value = np.array([[0]], dtype=np.int32)

    from detector import YOLOv8Detector
    det = YOLOv8Detector(model_path="/fake/path.onnx")
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    result = det.detect(img)
    assert len(result) == 1
    assert len(result[0]) == 5
    assert result[0][4] == pytest.approx(0.9, abs=1e-6)
    assert isinstance(result[0][0], float)
