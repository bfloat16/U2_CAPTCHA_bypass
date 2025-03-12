from ultralytics import YOLO

model = model = YOLO("yolo11m.pt")
model = YOLO(r"runs\detect\train3\weights\best.pt")

# Export the model
model.export(format="onnx", dynamic=True)