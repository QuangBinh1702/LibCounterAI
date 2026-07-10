import os
import cv2
import numpy as np
import onnxruntime as ort

class YOLOv8Detector:
    def __init__(self, model_path=None, conf_threshold=0.4, nms_threshold=0.4):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), "yolov8n.onnx")
        
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        available_providers = ort.get_available_providers()
        preferred_providers = [
            provider
            for provider in ("CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider")
            if provider in available_providers
        ]
        if not preferred_providers:
            preferred_providers = ["CPUExecutionProvider"]

        self.session = ort.InferenceSession(
            model_path,
            sess_options=session_options,
            providers=preferred_providers,
        )
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape # [1, 3, 640, 640]
        self.input_width = self.input_shape[2]
        self.input_height = self.input_shape[3]

    def preprocess(self, img):
        # img: BGR OpenCV image
        h, w, c = img.shape
        # Resize to 640x640
        resized = cv2.resize(img, (self.input_width, self.input_height))
        # BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        # Normalize to [0.0, 1.0]
        normalized = rgb.astype(np.float32) / 255.0
        # HWC to CHW
        chw = np.transpose(normalized, (2, 0, 1))
        # Add batch dimension: [1, 3, 640, 640]
        batch = np.expand_dims(chw, axis=0)
        return batch, w, h

    def detect(self, img):
        # 1. Preprocess
        batch, orig_w, orig_h = self.preprocess(img)
        
        # 2. Run inference
        outputs = self.session.run(None, {self.input_name: batch})
        output = outputs[0] # Shape is [1, 84, 8400]
        
        # 3. Postprocess
        # In YOLOv8, output is [1, 84, 8400] where 84 = 4 box coordinates + 80 class confidences
        # If output shape is [1, 8400, 84], transpose it to [1, 84, 8400]
        if output.shape[2] == 84:
            output = np.transpose(output, (0, 2, 1))
            
        predictions = output[0] # [84, 8400]
        
        boxes = []
        confidences = []
        
        # YOLOv8 class 0 is person
        class_ids = [0]
        
        # Extract boxes and confidences for class 0 (person)
        # Bbox parameters are: x_center, y_center, width, height (scaled to 640x640)
        # Class score is at index 4 (since boxes are 0, 1, 2, 3)
        scores = predictions[4, :]
        indices = np.where(scores >= self.conf_threshold)[0]
        
        for idx in indices:
            xc = predictions[0, idx]
            yc = predictions[1, idx]
            w  = predictions[2, idx]
            h  = predictions[3, idx]
            
            # Convert to [x1, y1, x2, y2] relative to 640x640
            x1 = xc - w / 2
            y1 = yc - h / 2
            x2 = xc + w / 2
            y2 = yc + h / 2
            
            # Rescale to original image size
            x1 = float(x1 * orig_w / self.input_width)
            y1 = float(y1 * orig_h / self.input_height)
            x2 = float(x2 * orig_w / self.input_width)
            y2 = float(y2 * orig_h / self.input_height)
            
            width = x2 - x1
            height = y2 - y1
            
            boxes.append([x1, y1, width, height])
            confidences.append(float(scores[idx]))
            
        # 4. NMS (Non-Maximum Suppression)
        indices_nms = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.nms_threshold)
        
        final_detections = []
        if len(indices_nms) > 0:
            for idx in indices_nms.flatten():
                box = boxes[idx]
                x1 = box[0]
                y1 = box[1]
                x2 = x1 + box[2]
                y2 = y1 + box[3]
                conf = confidences[idx]
                final_detections.append([x1, y1, x2, y2, conf])
                
        return final_detections
