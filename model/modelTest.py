import cv2
import numpy as np
import time
import os
import csv
import json
from model.line import draw_line_from_center

frame_size = 608

weightsFilePath = r"model\files\yolov4-custom_last.weights"
cfgFilePath = r"model\files\yolov4-custom.cfg"
namesFilePath = r"model\files\coco.names"
columns = ('Score', 'Distance', 'Accuracy')
data = {}


def execute(videoPath):
    # Load Yolo
    net = cv2.dnn.readNet(weightsFilePath, cfgFilePath)
    classes = []
    with open(namesFilePath) as f:
        classes = [line.strip() for line in f.readlines()]
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i[0] - 1]
                     for i in net.getUnconnectedOutLayers()]
    colors = np.random.uniform(0, 255, size=(len(classes), 3))
    cap = cv2.VideoCapture(videoPath)
    font = cv2.FONT_HERSHEY_PLAIN
    starting_time = time.time()
    frame_id = 0
    while True:
        ret, frame = cap.read()
        if ret:
            frame = cv2.resize(frame, (frame_size, frame_size))
            frame_id += 1

            height, width, channels = frame.shape

            # Detecting objects
            blob = cv2.dnn.blobFromImage(
                frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)

            net.setInput(blob)
            outs = net.forward(output_layers)

            # Showing informations on the screen
            class_ids = []
            confidences = []
            boxes = []
            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    if confidence > 0.8:
                        # Object detected
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)

                        # Rectangle coordinates
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)

                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)

            indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.8, 0.3)

            for i in range(len(boxes)):
                if i in indexes:
                    x, y, w, h = boxes[i]
                    # label = str(classes[class_ids[i]])
                    confidence = confidences[i]
                    color = colors[class_ids[i]]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    frame, score, distance = draw_line_from_center(
                        frame, (x+int(w/2)), y+int(h/2))

                    cv2.putText(frame, '  '+str(score),
                                (x, y + 30), font, 2, color, 3)

                    data[i] = {columns[0]: score,
                               columns[1]: str(round(distance, 2)),
                               columns[2]: str(round(confidence*100, 2))}

            if frame_id % 10 == 0:
                with open('data.json', 'w') as fp:
                    json.dump(data, fp,  indent=4)
                cv2.imwrite('static/results/result.jpg', frame)

            elapsed_time = time.time() - starting_time
            fps = frame_id / elapsed_time

            # msg = 'Processing Frame# ' + \
            #     str(frame_id)+', Processing Speed: ' + \
            #     str(round(fps, 1))+' Frames per Second.<br>'

            print(frame_id)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            break
