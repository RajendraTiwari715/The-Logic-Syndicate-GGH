from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = BACKEND_DIR / "yolov8n.pt"
VEHICLE_LABELS = {"car", "motorcycle", "bus", "truck"}

# Recognized Indian State & UT Codes
INDIAN_STATES = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
    "MZ", "NL", "OD", "OR", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK",
    "UA", "UP", "WB", "BH"
}


@dataclass(slots=True)
class OCRResult:
    raw_text: str
    normalized: str
    confidence: float
    bbox: tuple[Any, ...] | None = None
    sharpness: float = 0.0
    state_code: str | None = None


@dataclass(slots=True)
class PlateCandidate:
    image: np.ndarray
    bbox_xyxy: tuple[int, int, int, int]
    score: float
    angle: float = 0.0


@dataclass(slots=True)
class VehicleDetection:
    vehicle_type: str
    confidence: float
    bbox_xyxy: tuple[int, int, int, int]


@dataclass(slots=True)
class ANPRCapture:
    raw_text: str
    plate_number: str
    plate_confidence: float
    vehicle_type: str
    vehicle_confidence: float
    vehicle_bbox_xyxy: tuple[int, int, int, int]
    plate_bbox_xyxy: tuple[int, int, int, int] | None
    sharpness: float = 0.0
    state_code: str | None = None


class ANPRService:
    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or str(DEFAULT_MODEL_PATH if DEFAULT_MODEL_PATH.exists() else "yolov8n.pt")
        self._ocr_reader: Any | None = None
        self._ocr_backend: str | None = None
        self._ocr_error: str | None = None
        self._yolo_model: Any | None = None
        self._yolo_class_ids: list[int] | None = None
        self._yolo_error: str | None = None
        self._clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

    @property
    def ocr_backend(self) -> str | None:
        self._ensure_ocr()
        return self._ocr_backend

    @property
    def ocr_error(self) -> str | None:
        self._ensure_ocr()
        return self._ocr_error

    def _ensure_ocr(self) -> None:
        if self._ocr_backend is not None or self._ocr_error is not None:
            return

        try:
            import easyocr

            self._ocr_reader = easyocr.Reader(["en"], gpu=False)
            self._ocr_backend = "easyocr"
            return
        except Exception as exc:
            easyocr_error = str(exc)

        try:
            import pytesseract

            self._ocr_reader = pytesseract
            self._ocr_backend = "tesseract"
            return
        except Exception as exc:
            self._ocr_error = f"No OCR backend available. easyocr: {easyocr_error}; pytesseract: {exc}"

    def _ensure_yolo(self) -> None:
        if self._yolo_model is not None or self._yolo_error is not None:
            return

        try:
            from ultralytics import YOLO

            self._yolo_model = YOLO(self.model_path)
            names = getattr(self._yolo_model, "names", {})
            self._yolo_class_ids = [class_id for class_id, label in names.items() if label in VEHICLE_LABELS]
        except Exception as exc:
            self._yolo_error = str(exc)

    @staticmethod
    def calculate_sharpness(image: np.ndarray) -> float:
        """Calculates Laplacian variance to measure image sharpness/focus."""
        if image.size == 0:
            return 0.0
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    @staticmethod
    def normalize_plate(text: str) -> str:
        """High-precision Indian license plate normalization with positional character disambiguation."""
        raw = re.sub(r"[^A-Z0-9]", "", text.upper())
        
        # Strip leading IND badge if present (HSRP blue badge)
        if raw.startswith("IND") and len(raw) >= 7:
            cand = raw[3:]
            if cand[:2] in INDIAN_STATES or any(cand.startswith(st) for st in INDIAN_STATES) or len(cand) >= 6:
                raw = cand

        if len(raw) < 4:
            return raw

        chars = list(raw)
        digit_to_letter = {"0": "O", "1": "I", "2": "Z", "4": "A", "5": "S", "6": "G", "8": "B"}
        letter_to_digit = {"O": "0", "D": "0", "I": "1", "Z": "2", "A": "4", "S": "5", "G": "6", "B": "8"}

        # Check for Bharat Series: e.g. 22BH1234AA
        bh_match = re.match(r"^(\d{2})BH(\d{4})([A-Z]{1,2})$", raw)
        if bh_match:
            return raw

        # State code at start: first two chars must be letters
        if len(chars) >= 2:
            if chars[0] in digit_to_letter:
                chars[0] = digit_to_letter[chars[0]]
            if chars[1] in digit_to_letter:
                chars[1] = digit_to_letter[chars[1]]

        # Only perform letter-to-digit disambiguation if the text actually has some digits
        if any(c.isdigit() for c in raw):
            # Position 2 & 3 should be RTO digits if preceded by 2 letters
            if len(chars) >= 4 and chars[0].isalpha() and chars[1].isalpha():
                if chars[2] in letter_to_digit:
                    chars[2] = letter_to_digit[chars[2]]
                if chars[3] in letter_to_digit:
                    chars[3] = letter_to_digit[chars[3]]

            # Final 3 to 4 characters should be registration digits
            for i in range(max(len(chars) - 4, 4), len(chars)):
                if chars[i] in letter_to_digit:
                    chars[i] = letter_to_digit[chars[i]]

        return "".join(chars)

    @staticmethod
    def format_plate(text: str) -> str:
        normalized = ANPRService.normalize_plate(text)
        
        # Bharat Series format
        bh_match = re.match(r"^(\d{2})(BH)(\d{4})([A-Z]{1,2})$", normalized)
        if bh_match:
            return " ".join(bh_match.groups())

        # Standard Indian Format
        indian_match = re.match(r"^([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{3,4})$", normalized)
        if indian_match:
            return " ".join(indian_match.groups())
            
        return normalized

    @staticmethod
    def validate_plate(text: str) -> bool:
        clean = re.sub(r"[^A-Z0-9]", "", text.upper())
        if clean.startswith("IND") and len(clean) >= 7:
            clean = clean[3:]
        if len(clean) < 4 or len(clean) > 13:
            return False
        # Must have at least one digit and at least one letter originally
        if not any(char.isdigit() for char in clean):
            return False
        if not any(char.isalpha() for char in clean):
            return False
        return True

    @staticmethod
    def get_state_code(normalized_plate: str) -> str | None:
        clean = normalized_plate
        if clean.startswith("IND") and len(clean) >= 7:
            clean = clean[3:]
        if len(clean) >= 2:
            prefix = clean[:2]
            if prefix in INDIAN_STATES:
                return prefix
            # Check BH series
            if len(clean) >= 4 and clean[2:4] == "BH":
                return "BH"
        return None

    @staticmethod
    def _clamp_bbox(
        bbox_xyxy: tuple[float, float, float, float],
        width: int,
        height: int,
        padding: int = 0,
    ) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = bbox_xyxy
        return (
            max(0, int(x1) - padding),
            max(0, int(y1) - padding),
            min(width, int(x2) + padding),
            min(height, int(y2) + padding),
        )

    def _preprocess_for_ocr(self, image: np.ndarray, method: str = "clahe") -> np.ndarray:
        """High-precision multi-pass preprocessing for license plate crops."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
        
        # Scaling up small plates to optimum OCR font size (~70-90px height)
        height, width = gray.shape[:2]
        if height < 64 or width < 240:
            scale = max(70 / max(height, 1), 260 / max(width, 1))
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        if method == "clahe":
            # Contrast Limited Adaptive Histogram Equalization
            enhanced = self._clahe.apply(gray)
            return cv2.bilateralFilter(enhanced, 7, 50, 50)
        elif method == "otsu":
            # Adaptive / Otsu Thresholding
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return thresh
        else:
            return cv2.bilateralFilter(gray, 9, 75, 75)

    def _read_text(self, image: np.ndarray) -> list[OCRResult]:
        self._ensure_ocr()
        if self._ocr_backend is None or self._ocr_reader is None:
            return []

        sharpness = self.calculate_sharpness(image)
        results: list[OCRResult] = []

        if self._ocr_backend == "easyocr":
            # Scale up small crops for optimal CRAFT detection
            height, width = image.shape[:2]
            orig_scaled = image
            if height < 64 or width < 240:
                scale = max(70 / max(height, 1), 260 / max(width, 1))
                orig_scaled = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            clahe_img = self._preprocess_for_ocr(orig_scaled, method="clahe")
            variants = [orig_scaled, clahe_img]

            def get_bbox_center_y(bbox: Any) -> float:
                try:
                    return sum(float(p[1]) for p in bbox) / len(bbox)
                except Exception:
                    return 0.0

            def get_bbox_min_x(bbox: Any) -> float:
                try:
                    return min(float(p[0]) for p in bbox)
                except Exception:
                    return 0.0

            for var_img in variants:
                try:
                    detections = self._ocr_reader.readtext(var_img)
                except Exception:
                    continue

                if not detections:
                    continue

                # Filter out single IND badges from detections list if accompanied by other text
                meaningful_dets = []
                for bbox, text, prob in detections:
                    clean = re.sub(r"[^A-Z0-9]", "", text.upper())
                    if clean == "IND" and len(detections) > 1:
                        continue
                    meaningful_dets.append((bbox, text, float(prob)))

                if not meaningful_dets:
                    meaningful_dets = [(d[0], d[1], float(d[2])) for d in detections]

                # Sort top-to-bottom, left-to-right
                sorted_dets = sorted(
                    meaningful_dets,
                    key=lambda d: (get_bbox_center_y(d[0]) // 30, get_bbox_min_x(d[0]))
                )

                # 1. Evaluate individual detections
                for bbox, text, prob in sorted_dets:
                    normalized = self.normalize_plate(text)
                    if self.validate_plate(normalized):
                        state_code = self.get_state_code(normalized)
                        results.append(OCRResult(text, normalized, prob, tuple(bbox), sharpness, state_code))

                # 2. Evaluate full combination across all detected boxes (crucial for multi-line & spaced plates)
                if len(sorted_dets) > 1:
                    combined_text = " ".join(d[1] for d in sorted_dets)
                    combined_norm = self.normalize_plate(combined_text)
                    if self.validate_plate(combined_norm):
                        avg_prob = sum(d[2] for d in sorted_dets) / len(sorted_dets)
                        state_code = self.get_state_code(combined_norm)
                        results.append(OCRResult(combined_text, combined_norm, avg_prob, tuple(sorted_dets[0][0]), sharpness, state_code))

                # If high-confidence valid plate found, stop further passes
                if results and max((r.confidence for r in results), default=0) >= 0.70:
                    break

            # If still no results or low confidence, try Otsu thresholding pass
            if not results or max((r.confidence for r in results), default=0) < 0.45:
                try:
                    otsu_img = self._preprocess_for_ocr(orig_scaled, method="otsu")
                    detections = self._ocr_reader.readtext(otsu_img)
                    if detections:
                        sorted_dets = sorted(
                            detections,
                            key=lambda d: (get_bbox_center_y(d[0]) // 30, get_bbox_min_x(d[0]))
                        )
                        for bbox, text, prob in sorted_dets:
                            normalized = self.normalize_plate(text)
                            if self.validate_plate(normalized):
                                state_code = self.get_state_code(normalized)
                                results.append(OCRResult(text, normalized, float(prob), tuple(bbox), sharpness, state_code))

                        if len(sorted_dets) > 1:
                            combined_text = " ".join(d[1] for d in sorted_dets)
                            combined_norm = self.normalize_plate(combined_text)
                            if self.validate_plate(combined_norm):
                                avg_prob = sum(float(d[2]) for d in sorted_dets) / len(sorted_dets)
                                state_code = self.get_state_code(combined_norm)
                                results.append(OCRResult(combined_text, combined_norm, avg_prob, tuple(sorted_dets[0][0]), sharpness, state_code))
                except Exception:
                    pass

            return results


        try:
            data = self._ocr_reader.image_to_data(
                enhanced,
                config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                output_type=self._ocr_reader.Output.DICT,
            )
            for index, text in enumerate(data.get("text", [])):
                normalized = self.normalize_plate(text)
                if not self.validate_plate(normalized):
                    continue
                try:
                    confidence = max(0.0, float(data["conf"][index])) / 100.0
                    bbox = (
                        int(data["left"][index]),
                        int(data["top"][index]),
                        int(data["left"][index]) + int(data["width"][index]),
                        int(data["top"][index]) + int(data["height"][index]),
                    )
                except Exception:
                    confidence = 0.0
                    bbox = None
                state_code = self.get_state_code(normalized)
                results.append(OCRResult(text, normalized, confidence, bbox, sharpness, state_code))
        except Exception:
            return []

        return results

    def _deskew_crop(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotates slightly skewed license plates horizontally for higher OCR accuracy."""
        if abs(angle) < 1.0 or abs(angle) > 40.0:
            return image
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, rot_mat, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    def _candidate_from_rect(
        self,
        image: np.ndarray,
        x: int,
        y: int,
        width: int,
        height: int,
        score: float,
        angle: float = 0.0,
    ) -> PlateCandidate | None:
        frame_height, frame_width = image.shape[:2]
        x1, y1, x2, y2 = self._clamp_bbox((x, y, x + width, y + height), frame_width, frame_height, padding=4)
        if x2 <= x1 or y2 <= y1:
            return None
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            return None
            
        if abs(angle) > 1.5:
            crop = self._deskew_crop(crop, angle)
            
        return PlateCandidate(crop, (x1, y1, x2, y2), score, angle)

    def find_plate_candidates(self, vehicle_crop: np.ndarray) -> list[PlateCandidate]:
        """Multi-pass candidate localization: Edge, Blackhat/Tophat morphology, and HSV color filtering."""
        height, width = vehicle_crop.shape[:2]
        if height < 20 or width < 20:
            return []

        aspect = width / max(height, 1)
        full_score = 0.85 if 1.8 <= aspect <= 7.0 else 0.15
        candidates: list[PlateCandidate] = [
            PlateCandidate(vehicle_crop, (0, 0, width, height), full_score),
            PlateCandidate(vehicle_crop[int(height * 0.45) : height, 0:width], (0, int(height * 0.45), width, height), 0.35),
        ]


        gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)

        # 1. Edge + Rectangular Morphology Close
        edges = cv2.Canny(gray, 60, 180)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = max(120.0, width * height * 0.002)
        for contour in contours:
            x, y, rect_w, rect_h = cv2.boundingRect(contour)
            if rect_h <= 0:
                continue
            aspect_ratio = rect_w / rect_h
            area = rect_w * rect_h
            if 1.8 <= aspect_ratio <= 7.0 and area >= min_area and rect_w >= 35 and rect_h >= 10:
                lower_bonus = y / max(height, 1) * 0.30
                shape_score = max(0.0, 1.0 - abs(aspect_ratio - 4.2) / 4.2)
                
                # Check orientation angle
                min_rect = cv2.minAreaRect(contour)
                angle = min_rect[-1]
                if angle < -45:
                    angle = 90 + angle
                elif angle > 45:
                    angle = angle - 90
                    
                candidate = self._candidate_from_rect(vehicle_crop, x, y, rect_w, rect_h, 0.45 + shape_score + lower_bonus, angle=angle)
                if candidate:
                    candidates.append(candidate)

        # 2. Black-hat Morphology (High sensitivity for dark text on white/yellow plates)
        blackhat_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, blackhat_kernel)
        _, bh_thresh = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        bh_close = cv2.morphologyEx(bh_thresh, cv2.MORPH_CLOSE, kernel)
        bh_contours, _ = cv2.findContours(bh_close, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in bh_contours:
            x, y, rect_w, rect_h = cv2.boundingRect(contour)
            if rect_h <= 0:
                continue
            aspect_ratio = rect_w / rect_h
            area = rect_w * rect_h
            if 2.0 <= aspect_ratio <= 7.0 and area >= min_area and rect_w >= 35 and rect_h >= 10:
                candidate = self._candidate_from_rect(vehicle_crop, x, y, rect_w, rect_h, 0.70 + y / max(height, 1) * 0.25)
                if candidate:
                    candidates.append(candidate)

        # 3. HSV Color Masking (Yellow commercial & White private plates)
        hsv = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2HSV)
        yellow_mask = cv2.inRange(hsv, (15, 50, 80), (40, 255, 255))
        white_mask = cv2.inRange(hsv, (0, 0, 135), (180, 80, 255))
        color_mask = cv2.morphologyEx(cv2.bitwise_or(yellow_mask, white_mask), cv2.MORPH_CLOSE, kernel)
        color_contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in color_contours:
            x, y, rect_w, rect_h = cv2.boundingRect(contour)
            if rect_h <= 0:
                continue
            aspect_ratio = rect_w / rect_h
            area = rect_w * rect_h
            if 1.8 <= aspect_ratio <= 7.5 and area >= min_area and rect_w >= 35 and rect_h >= 10:
                candidate = self._candidate_from_rect(vehicle_crop, x, y, rect_w, rect_h, 0.80 + y / max(height, 1) * 0.25)
                if candidate:
                    candidates.append(candidate)

        unique: dict[tuple[int, int, int, int], PlateCandidate] = {}
        for candidate in sorted(candidates, key=lambda item: item.score, reverse=True):
            unique.setdefault(candidate.bbox_xyxy, candidate)
        return list(unique.values())[:15]

    def process_plate_crop(self, image: np.ndarray) -> OCRResult | None:
        best_result: OCRResult | None = None
        best_score = 0.0

        for result in self._read_text(image):
            # Prioritize plates matching valid Indian pattern
            norm = result.normalized
            is_indian = bool(re.match(r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}$", norm) or re.match(r"^\d{2}BH\d{4}[A-Z]{1,2}$", norm))
            pattern_bonus = 0.20 if is_indian else 0.0
            length_bonus = min(len(norm), 10) / 10.0 * 0.05
            score = result.confidence + pattern_bonus + length_bonus
            if score > best_score:
                best_score = score
                best_result = result

        return best_result

    def detect_vehicles(self, frame: np.ndarray, confidence_threshold: float = 0.35) -> list[VehicleDetection]:
        frame_height, frame_width = frame.shape[:2]
        self._ensure_yolo()
        if self._yolo_model is None or not self._yolo_class_ids:
            return [VehicleDetection("vehicle", 0.0, (0, 0, frame_width, frame_height))]

        try:
            results = self._yolo_model(
                frame,
                classes=self._yolo_class_ids,
                conf=confidence_threshold,
                verbose=False,
            )
        except Exception:
            return [VehicleDetection("vehicle", 0.0, (0, 0, frame_width, frame_height))]

        detections: list[VehicleDetection] = []
        if not results or results[0].boxes is None:
            return detections

        boxes = results[0].boxes
        xyxy = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy() if boxes.conf is not None else np.zeros(len(xyxy))
        class_ids = boxes.cls.cpu().numpy().astype(int) if boxes.cls is not None else np.zeros(len(xyxy), dtype=int)

        for index, box in enumerate(xyxy):
            x1, y1, x2, y2 = self._clamp_bbox(tuple(box), frame_width, frame_height, padding=8)
            if x2 <= x1 or y2 <= y1:
                continue
            label = str(self._yolo_model.names[int(class_ids[index])])
            detections.append(
                VehicleDetection(
                    vehicle_type=label,
                    confidence=float(confidences[index]),
                    bbox_xyxy=(x1, y1, x2, y2),
                )
            )

        return sorted(detections, key=lambda item: item.confidence, reverse=True)

    def analyze_frame(self, frame: np.ndarray) -> list[ANPRCapture]:
        """Main analysis pipeline for photos or individual video frames."""
        frame_height, frame_width = frame.shape[:2]
        vehicles = self.detect_vehicles(frame)
        if not vehicles:
            vehicles = [VehicleDetection("vehicle", 0.0, (0, 0, frame_width, frame_height))]

        captures: list[ANPRCapture] = []
        seen_plates: set[str] = set()

        for vehicle in vehicles:
            x1, y1, x2, y2 = vehicle.bbox_xyxy
            vehicle_crop = frame[y1:y2, x1:x2]
            if vehicle_crop.size == 0:
                continue

            best_result: OCRResult | None = None
            best_candidate: PlateCandidate | None = None
            best_score = 0.0
            for candidate in self.find_plate_candidates(vehicle_crop):
                result = self.process_plate_crop(candidate.image)
                if result is None:
                    continue
                score = result.confidence + candidate.score * 0.08
                if score > best_score:
                    best_score = score
                    best_result = result
                    best_candidate = candidate

            if best_result is None or best_candidate is None:
                continue

            plate_number = self.normalize_plate(best_result.normalized)
            if plate_number in seen_plates:
                continue
            seen_plates.add(plate_number)

            px1, py1, px2, py2 = best_candidate.bbox_xyxy
            captures.append(
                ANPRCapture(
                    raw_text=best_result.raw_text,
                    plate_number=plate_number,
                    plate_confidence=max(0.0, min(1.0, best_result.confidence)),
                    vehicle_type=vehicle.vehicle_type,
                    vehicle_confidence=max(0.0, min(1.0, vehicle.confidence)),
                    vehicle_bbox_xyxy=vehicle.bbox_xyxy,
                    plate_bbox_xyxy=(x1 + px1, y1 + py1, x1 + px2, y1 + py2),
                    sharpness=best_result.sharpness,
                    state_code=self.get_state_code(plate_number),
                )
            )

        # Fallback: Check full frame directly if vehicles missed the plate
        if not captures:
            direct_result = self.process_plate_crop(frame)
            if direct_result:
                plate_number = self.normalize_plate(direct_result.normalized)
                captures.append(
                    ANPRCapture(
                        raw_text=direct_result.raw_text,
                        plate_number=plate_number,
                        plate_confidence=max(0.0, min(1.0, direct_result.confidence)),
                        vehicle_type="Vehicle",
                        vehicle_confidence=0.8,
                        vehicle_bbox_xyxy=(0, 0, frame_width, frame_height),
                        plate_bbox_xyxy=(0, 0, frame_width, frame_height),
                        sharpness=direct_result.sharpness,
                        state_code=self.get_state_code(plate_number),
                    )
                )

        return captures

    def draw_annotations(
        self,
        frame: np.ndarray,
        captures: list[ANPRCapture],
        camera_id: str = "CAM-LIVE",
        timestamp_str: str = "",
        watchlist_plates: set[str] | None = None,
    ) -> np.ndarray:
        """Renders precision HUD bounding boxes, detection badges, and border surveillance watermark."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        for cap in captures:
            norm_plate = self.normalize_plate(cap.plate_number)
            is_watchlist = bool(watchlist_plates and norm_plate in watchlist_plates)
            box_color = (0, 0, 240) if is_watchlist else (0, 220, 100) # Red or Green
            
            # 1. Vehicle Bbox
            vx1, vy1, vx2, vy2 = cap.vehicle_bbox_xyxy
            if (vx2 - vx1) < w or (vy2 - vy1) < h:
                cv2.rectangle(annotated, (vx1, vy1), (vx2, vy2), box_color, 2)
            
            # 2. Plate Bbox
            if cap.plate_bbox_xyxy:
                px1, py1, px2, py2 = cap.plate_bbox_xyxy
                cv2.rectangle(annotated, (px1, py1), (px2, py2), (30, 200, 255), 2)

            # 3. Floating Detection Badge
            display_plate = self.format_plate(cap.plate_number)
            conf_pct = int(round(cap.plate_confidence * 100))
            label = f"{display_plate} [{cap.vehicle_type.upper()}] {conf_pct}%"
            if is_watchlist:
                label = f"! WATCHLIST ! {label}"
                
            label_y = max(vy1 - 10, 24)
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(annotated, (vx1, label_y - lh - 6), (vx1 + lw + 12, label_y + 4), box_color, -1)
            text_color = (255, 255, 255) if is_watchlist else (0, 0, 0)
            cv2.putText(annotated, label, (vx1 + 6, label_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.55, text_color, 2, cv2.LINE_AA)

        # 4. Top/Bottom HUD Watermark
        cv2.rectangle(annotated, (0, 0), (w, 24), (20, 20, 20), -1)
        hud_text = f"IBVAP ANPR ENGINE | {camera_id} | {timestamp_str} | CAPTURES: {len(captures)}"
        cv2.putText(annotated, hud_text, (10, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 230), 1, cv2.LINE_AA)
        
        return annotated


anpr_service = ANPRService()
