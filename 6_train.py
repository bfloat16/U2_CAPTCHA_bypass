from ultralytics import YOLO

if __name__ == '__main__':
    model = YOLO("yolo11s.yaml")  # build a new model from YAML
    model = YOLO("yolo11s.pt")  # load a pretrained model (recommended for training)
    model = YOLO("yolo11s.yaml").load("yolo11s.pt")  # build from YAML and transfer weights

    # Train the model
    results = model.train(data="u2.yaml", epochs=5, imgsz=640)