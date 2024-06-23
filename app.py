from flask import Flask, render_template, Response, request, redirect, url_for
from text_speech import text_to_speech
import cv2
from tensorflow.keras.models import model_from_json
from tensorflow.keras.preprocessing import image
import numpy as np
from spellchecker import SpellChecker

app = Flask(__name__)
camera = cv2.VideoCapture(0)

d = {0: ' ', 1: 'A', 2: 'B', 3: 'C',
     4: 'D', 5: 'E', 6: 'F', 7: 'G',
     8: 'H', 9: 'I', 10: 'J', 11: 'K',
     12: 'L', 13: 'M', 14: 'N', 15: 'O',
     16: 'P', 17: 'Q', 18: 'R', 19: 'S',
     20: 'T', 21: 'U', 22: 'V', 23: 'W',
     24: 'X', 25: 'Y', 26: 'Z'}

upper_left = (335, 3)
bottom_right = (635, 303)

json_file = open('model-bw.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
loaded_model.load_weights("model-bw.h5")

def function(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 1)
    th3 = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    ret, res = cv2.threshold(th3, 70, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return res

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            frame = cv2.flip(frame, 1)
            r = cv2.rectangle(frame, upper_left, bottom_right, (0, 0, 0), 5)
            rect_img = frame[upper_left[1]:bottom_right[1], upper_left[0]:bottom_right[0]]
            sketcher_rect = rect_img
            sketcher_rect = function(sketcher_rect)
            sketcher_rect_rgb = cv2.cvtColor(sketcher_rect, cv2.COLOR_GRAY2RGB)
            frame[upper_left[1]:bottom_right[1], upper_left[0]:bottom_right[0]] = sketcher_rect_rgb

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

l = []
str1 = ""
voice_gender = "Male"

@app.route('/set_voice', methods=['POST'])
def set_voice():
    global voice_gender
    voice_gender = request.form['voice']
    return redirect(url_for('index'))

@app.route('/predict', methods=['POST'])
def predictions():
    while True:
        success, frame = camera.read()
        frame = cv2.flip(frame, 1)
        r = cv2.rectangle(frame, upper_left, bottom_right, (0, 0, 0), 5)
        rect_img = frame[upper_left[1]:bottom_right[1], upper_left[0]:bottom_right[0]]
        sketcher_rect = rect_img
        sketcher_rect = function(sketcher_rect)
        sketcher_rect_rgb = cv2.cvtColor(sketcher_rect, cv2.COLOR_GRAY2RGB)
        frame[upper_left[1]:bottom_right[1], upper_left[0]:bottom_right[0]] = sketcher_rect_rgb

        sketcher_rect = cv2.resize(sketcher_rect, (128, 128))
        x = image.img_to_array(sketcher_rect)
        x = np.expand_dims(x, axis=0)
        x = x / 255.0
        pre = loaded_model.predict(x)
        p_test = np.argmax(pre)
        a = d[p_test]
        l.append(a)
        str1 = ""
        print(l)

        for ele in l:
            str1 += ele
        return render_template("index.html", pred=str1, predicted_output=autocorrect_text(str1), voice_gender=voice_gender)

@app.route('/stop', methods=['POST'])
def stopping():
    global voice_gender
    text_to_speech('Predicting the output', voice_gender)
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            frame = cv2.flip(frame, 1)
            r = cv2.rectangle(frame, upper_left, bottom_right, (0, 0, 0), 5)
            rect_img = frame[upper_left[1]:bottom_right[1], upper_left[0]:bottom_right[0]]
            sketcher_rect = rect_img
            sketcher_rect = function(sketcher_rect)
            sketcher_rect_rgb = cv2.cvtColor(sketcher_rect, cv2.COLOR_GRAY2RGB)
            frame[upper_left[1]:bottom_right[1], upper_left[0]:bottom_right[0]] = sketcher_rect_rgb
            str1 = ""
            for ele in l:
                str1 += ele
            text_to_speech(autocorrect_text(str1), voice_gender)
            l.clear()
            return render_template("index.html", pred=str1, voice_gender=voice_gender)

@app.route('/')
def index():
    text_to_speech('Hi there please show the hand gesture in the provided space', gender=voice_gender)
    return render_template('index.html', voice_gender=voice_gender)

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def autocorrect_text(text):
    spell = SpellChecker()
    words = text.split()
    corrected_words = [spell.correction(word) for word in words]
    corrected_text = ' '.join(corrected_words)
    return corrected_text

if __name__ == "__main__":
    app.run(debug=True)
