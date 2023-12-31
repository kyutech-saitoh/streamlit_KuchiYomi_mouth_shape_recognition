import numpy as np
import math
import cv2
from PIL import Image
import mediapipe as mp
import torch
from torchvision import transforms

# left eye contour
landmark_left_eye_points = [133, 173, 157, 158, 159, 160, 161, 246, 33, 7, 163, 144, 145, 153, 154, 155]
# right eye contour
landmark_right_eye_points = [362, 398, 384, 385, 386, 387, 388, 466, 263, 249, 390, 373, 374, 380, 381, 382]

size_LFROI = 160 # [pixel]
size_graph_width = 200 # [pixel]
size_graph_height = 140 # [pixel]

# data transform
transform = transforms.Compose([
    #transforms.Resize((160, 160)),
    transforms.ToTensor(),
])

# training model path
model_path = "model/model_P00.pth"
# load model
model = torch.load(model_path)

def set_model(target_person_id):
    model_file_name = "model/model_" + target_person_id + ".pth"
    model = torch.load(model_file_name)

# load device : cpu
device = torch.device("cpu")
model.to(device)

# モデルを評価モードにする
model.eval()

magrin = 5

str_message1 = ""
str_message2 = ""


def pil2cv(image):
    ''' PIL型 --> OpenCV型 '''
    new_image = np.array(image, dtype=np.uint8)
    if new_image.ndim == 2:
        # モノクロ
        pass
    elif new_image.shape[2] == 3:
        # カラー
        new_image = new_image[:, :, ::-1]
    elif new_image.shape[2] == 4:
        # 透過
        new_image = new_image[:, :, [2, 1, 0, 3]]
        
    return new_image


def cv2pil(image):
    ''' OpenCV型 --> PIL型 '''
    new_image = image.copy()
    if new_image.ndim == 2:
        # モノクロ
        pass
    elif new_image.shape[2] == 3:
        # カラー
        new_image = new_image[:, :, ::-1]
    elif new_image.shape[2] == 4:
        # 透過
        new_image = new_image[:, :, [2, 1, 0, 3]]

    new_image = Image.fromarray(new_image)

    return new_image


def func(value1, value2):
    return int(value1 * value2)


def LFROI_extraction_sub(image, face_points0):
    global str_message1
    global str_message2

    image_height, image_width, channels = image.shape[:3]

    image_cx = image_width / 2
    image_cy = image_height / 2

    left_eye_x = face_points0[33][0]
    left_eye_y = face_points0[33][1]

    right_eye_x = face_points0[263][0]
    right_eye_y = face_points0[263][1]

    nose_x = face_points0[2][0]
    nose_y = face_points0[2][1]

    eye_distance2 = (left_eye_x - right_eye_x) * (left_eye_x - right_eye_x) + (left_eye_y - right_eye_y) * (left_eye_y - right_eye_y)
    eye_distance = math.sqrt(eye_distance2)

    value = float(left_eye_y - right_eye_y) / float(left_eye_x - right_eye_x)
    if left_eye_x != right_eye_x:
        eye_angle = math.atan(float(left_eye_y - right_eye_y) / float(left_eye_x - right_eye_x))
    else:
        eye_angle = 0

    eye_angle = math.degrees(eye_angle)

    target_eye_distance = 160
    scale = target_eye_distance / eye_distance
    cx = nose_x
    cy = nose_y

    mat_rot = cv2.getRotationMatrix2D((int(cx), int(cy)), eye_angle, scale)
    tx = image_cx - cx
    ty = image_cy - cy
    mat_tra = np.float32([[1, 0, tx], [0, 1, ty]])

    normalized_image1 = cv2.warpAffine(image, mat_rot, (int(image_width), int(image_height)))
    normalized_image2 = cv2.warpAffine(normalized_image1, mat_tra, (int(image_width), int(image_height)))

    face_points1 = np.array([face_points0])
    face_points2 = cv2.transform(face_points1, mat_rot)
    face_points3 = cv2.transform(face_points2, mat_tra)
    face_points3 = np.squeeze(face_points3)
    
    #for p in face_points3:
    #    x = p[0]
    #    y = p[1]
    #    cv2.circle(normalized_image2, center=(x, y), radius=1, color=(255, 255, 255), thickness=-1)

    lip_x = (face_points3[61][0] + face_points3[291][0]) / 2
    lip_y = (face_points3[61][1] + face_points3[291][1]) / 2
    left = int(lip_x - target_eye_distance / 2)
    top = int(lip_y - target_eye_distance / 3)
    right = left + target_eye_distance
    bottom = top + target_eye_distance

    str_message1 = "eye distance = %.0f pixel" % eye_distance
    str_message2 = "angle = %.2f deg" % eye_angle
    
    return (left, top, right, bottom), normalized_image2, face_points3


def LFROI_extraction(image):
    global str_message1
    global str_message2

    out_image = image.copy()

    black_image = np.zeros((size_LFROI, size_LFROI, 3), np.uint8)
    white_image = black_image + 200
    is_detected_face = False

    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5
    ) as face_mesh:

        results = face_mesh.process(image)
        (image_height, image_width) = image.shape[:2]

        if results.multi_face_landmarks:
            for face in results.multi_face_landmarks:
                points = []
                for index, landmark in enumerate(face.landmark):
                    x = func(landmark.x, image_width)
                    y = func(landmark.y, image_height)
                    if index in [33, 263, 2, 61, 291]:
                        cv2.circle(out_image, center=(x, y), radius=3, color=(0, 255, 0), thickness=-1)
                        cv2.circle(out_image, center=(x, y), radius=1, color=(255, 255, 255), thickness=-1)
                    else:
                        cv2.circle(out_image, center=(x, y), radius=1, color=(0, 0, 255), thickness=-1)
                        #cv2.circle(out_image, center=(x, y), radius=1, color=(255, 255, 255), thickness=-1)
                    points.append((x, y))


                rect_LFROI, normalized_image, new_points_LFROI = LFROI_extraction_sub(image, points)
                LFROI = normalized_image[rect_LFROI[1]:rect_LFROI[3], rect_LFROI[0]:rect_LFROI[2]]

            is_detected_face = True
            #st.image(normalized_image)

            return out_image, LFROI, is_detected_face

    str_message1 = "no face detected"
    str_message2 = ""
    
    return out_image, white_image, is_detected_face


def preprocess(image, transform):   
    image = transform(image)  # PIL
    C, H, W = image.shape
    image = image.reshape(1, C, H, W)
    
    return image


def make_graph_image(values):
    graph_image = np.zeros((size_graph_height, size_graph_width, 3), np.uint8)

    fontface = cv2.FONT_HERSHEY_PLAIN
    label = ["a", "i", "u", "e", "o", "N"]
    fontscale = 1.0
    thickness = 1

    max_idx = np.argmax(values)

    x0 = 90
    for idx, v in enumerate(values):
        x1 = x0 + int(v * 100)
        y0 = 10 + idx * 20
        y1 = 10 + (idx + 1) * 20
        if idx == max_idx:
            cv2.rectangle(graph_image, (x0, y0), (x1, y1), (0, 0, 255), -1)
            #cv2.rectangle(graph_image, (x0+1, y0+1), (x1-1, y1-1), (200, 200, 255), -1)
        else:
            cv2.rectangle(graph_image, (x0, y0), (x1, y1), (0, 255, 0), -1)
            cv2.rectangle(graph_image, (x0+1, y0+1), (x1-1, y1-1), (200, 255, 200), -1)

        (w, h), baseline = cv2.getTextSize(label[idx], fontface, fontscale, thickness)
        x = int((20 - w) / 2)
        cv2.putText(graph_image, label[idx], (x, y1-3), fontface, fontscale, (255, 255, 255), thickness)

        str_value = "(%0.3f)" % v
        cv2.putText(graph_image, str_value, (25, y1-3), fontface, fontscale, (255, 255, 255), thickness)
        
    return graph_image


def prediction(model, crop_image):
    with torch.no_grad():
        # 予測
        outputs = model(crop_image)
        probabilities = torch.nn.functional.softmax(outputs[0], dim=0)

        graph_image = make_graph_image(probabilities)
        
        # 予測結果をクラス番号に変換
        _, predicted = torch.max(outputs, 1)

    return predicted, graph_image


def lip_reading(image_cv, is_mirroring):
    image_height, image_width, channels = image_cv.shape[:3]

    # LFROI extraction
    # 五つのmissing ScriptRunContext
    image_cv, LFROI_cv, is_detected_face = LFROI_extraction(image_cv)

    if is_mirroring == True:
        out_image_cv = cv2.flip(image_cv, 1)
    else:
        out_image_cv = image_cv.copy()
    #out_image_cv = image_cv.copy()

    if is_detected_face == True:
        out_image_cv[magrin:size_LFROI+magrin, magrin:size_LFROI+magrin] = LFROI_cv

        LFROI_array = cv2pil(LFROI_cv)
        #crop_image_pil = preprocess(LFROI_array, transform)
        crop_image_pil = preprocess(LFROI_cv, transform)

        # predict
        predict, graph_image_cv = prediction(model, crop_image_pil)
        out_image_cv[magrin:magrin+size_graph_height, image_width-1-magrin-size_graph_width:image_width-1-magrin] = graph_image_cv
    
    cv2.putText(out_image_cv, str_message1, (20, image_height-60), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 255, 255), 1)
    cv2.putText(out_image_cv, str_message2, (20, image_height-40), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 255, 255), 1)

    return out_image_cv
