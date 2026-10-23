import cv2
from app.vision.model_manager import model_manager

def test_yolo():
    person_img = cv2.imread("test_face.jpg")
    car_img = cv2.imread("test_car.png")
    
    dets1 = model_manager.get_primary_detector().infer(person_img)
    print("Person image detections:", [(d.object_type, d.confidence) for d in dets1])
    
    dets2 = model_manager.get_primary_detector().infer(car_img)
    print("Car image detections:", [(d.object_type, d.confidence) for d in dets2])

if __name__ == "__main__":
    test_yolo()
