import os
import cv2
import numpy as np

class FacePipeline:
    def __init__(self):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Paths to models
        self.detector_path = os.path.join(app_dir, "face_detection_yunet_2023mar.onnx")
        self.recognizer_path = os.path.join(app_dir, "face_recognition_sface_2021dec.onnx")
        
        # Verify files exist
        if not os.path.exists(self.detector_path):
            raise FileNotFoundError(f"YuNet model not found at {self.detector_path}")
        if not os.path.exists(self.recognizer_path):
            raise FileNotFoundError(f"SFace model not found at {self.recognizer_path}")
            
        # Create FaceRecognizerSF
        self.recognizer = cv2.FaceRecognizerSF.create(self.recognizer_path, "")
        
        # We cache detector instances for different image shapes
        self.detectors = {}

    def _get_detector(self, width: int, height: int, score_threshold: float = 0.65, nms_threshold: float = 0.3):
        key = (width, height, score_threshold, nms_threshold)
        if key not in self.detectors:
            self.detectors[key] = cv2.FaceDetectorYN.create(
                self.detector_path,
                "",
                (width, height),
                score_threshold,
                nms_threshold
            )
        else:
            # Set input size dynamically just in case
            self.detectors[key].setInputSize((width, height))
        return self.detectors[key]

    def detect_faces(self, img, score_threshold: float = 0.65):
        """
        Detect faces in image.
        Returns:
            list of dicts, each with:
                'bbox': [x, y, w, h]
                'landmarks': list of 5 coordinates [[x,y], ...]
                'score': float confidence score
                'raw_face': numpy array of shape (15,) containing raw detector output
        """
        h, w = img.shape[:2]
        detector = self._get_detector(w, h, score_threshold=score_threshold)
        
        retval, faces = detector.detect(img)
        if not retval or faces is None:
            return []
            
        results = []
        for face in faces:
            bbox = face[0:4].astype(int).tolist()
            landmarks = face[4:14].reshape(5, 2).astype(int).tolist()
            score = float(face[14])
            
            results.append({
                "bbox": bbox,
                "landmarks": landmarks,
                "score": score,
                "raw_face": face
            })
        return results

    def extract_embedding(self, img, raw_face):
        """
        Aligns, crops face and extracts 128-dimensional embedding.
        """
        # Align & Crop the face
        aligned_face = self.recognizer.alignCrop(img, raw_face)
        # Extract features
        embedding = self.recognizer.feature(aligned_face)
        # Normalize and convert to list of floats
        embedding = embedding[0].tolist()
        return embedding
