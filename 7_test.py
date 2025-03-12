from ultralytics import YOLO

# Load a model
model = YOLO(r"runs\detect\train\weights\best.pt")  # pretrained YOLO11n model

# Run batched inference on a list of images
results = model([
    r"dataset\images\test\image (1).jpg",
    r"dataset\images\test\image (2).jpg",
    r"dataset\images\test\image (3).jpg",
    r"dataset\images\test\image (4).jpg",
    r"dataset\images\test\image (5).jpg",
    r"dataset\images\test\image (6).jpg",
    r"dataset\images\test\image (7).jpg",
    r"dataset\images\test\image (8).jpg",
    ])  # return a list of Results objects

for result in results:
    boxes = result.boxes  # Boxes object for bounding box outputs
    masks = result.masks  # Masks object for segmentation masks outputs
    keypoints = result.keypoints  # Keypoints object for pose outputs
    probs = result.probs  # Probs object for classification outputs
    obb = result.obb  # Oriented boxes object for OBB outputs
    result.show()  # display to screen