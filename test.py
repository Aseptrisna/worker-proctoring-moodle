import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import mysql.connector
import os
from datetime import datetime
import time
import PIL
import numpy as np
import face_recognition
from PIL import Image, ImageDraw, UnidentifiedImageError, ImageFont
import pymongo
import schedule

def DbConnection():
    db = "mongodb://engagement:ZWlbWVudA5nYWd!@database2.pptik.id/?authMechanism=DEFAULT&authSource=engagement"
    myclient = pymongo.MongoClient(db)
    db = myclient["engagement"]
    collection_log = db["log"]
    collection_report = db["resultproctorings"]
    return collection_report, collection_log

def setup_session(retry_count=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]):
    session = requests.Session()
    retries = Retry(total=retry_count, backoff_factor=backoff_factor, status_forcelist=status_forcelist)
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def download_image(image_url, save_path, filename):
    response = requests.get(image_url, stream=True)
    if response.status_code == 200:
        full_path = os.path.join(save_path, f"{filename}.jpg")
        with open(full_path, 'wb') as out_file:
            out_file.write(response.content)
        return full_path
    else:
        print(f"Failed to download the image. HTTP Status Code: {response.status_code}")
        return None

def detect_faces_in_image(image_url, save_path, username, user_id, firstname, lastname, timestamp, date_time, id_courses, course_name, create_at):
    image_directory = "D:/worker/Worker_2022/worker-proctoring-moodle/picture"
    known_face_encodings = []
    known_face_names = []
    for filename in os.listdir(image_directory):
        if filename.endswith((".jpg", ".jpeg", ".png")):
            filepath = os.path.join(image_directory, filename)
            image = face_recognition.load_image_file(filepath)
            face_encodings = face_recognition.face_encodings(image)
            if face_encodings:
                known_face_encodings.append(face_encodings[0])
                known_face_names.append(os.path.splitext(filename)[0])

    try:
        full_path = download_image(image_url, save_path, username)
        unknown_image = face_recognition.load_image_file(full_path)
        face_locations = face_recognition.face_locations(unknown_image)
        face_encodings = face_recognition.face_encodings(unknown_image, face_locations)
        pil_image = Image.fromarray(unknown_image)
        draw = ImageDraw.Draw(pil_image)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
                current_time = time.time()
                dt = datetime.fromtimestamp(current_time)
                fdt2 = dt.strftime("%d-%m-%Y %H:%M:%S")
                str_fdt2 = dt.strftime("%Y%m%d%H%M%S")
                print("Face detected:", user_id, firstname, lastname, "time:", fdt2)
            else:
                print("No face detected")
            warning = False
            if name == username:
                warning = False
            else:
                warning = True
            
            draw.rectangle(((left, top), (right, bottom)), outline=(0, 0, 255))
            caption = fdt2 + "|" + name 
            font = ImageFont.load_default()
            text_width = draw.textlength(caption)
            draw.text((left + 6, bottom - 5), caption, fill=(255, 255, 255))
            pil_image.show()
            output_filename = username + "_" + timestamp
            data_to_save = {
                     "userID": user_id,
                     "filename": f"{output_filename}.jpg",
                     "firstname": firstname,
                     "lastname": lastname,
                     "username": username,
                     "image_url": image_url,
                     "warning": warning,
                     "timestamp": timestamp,
                     "datetime": date_time,
                     "idCourses": id_courses,
                     "courseName": course_name,
                     "createAt": create_at
            }
            report.insert_one(data_to_save)
            print("Data saved to MongoDB")

        del draw

        output_filename = username + "_" + timestamp
        output_path = os.path.join("V:/proctoring", f"{output_filename}.jpg")
        pil_image.save(output_path)
        print("Identified image saved:", output_path, "time", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))

    except PIL.UnidentifiedImageError:
        print(f"Cannot identify image file {image_url}")

def delete_image(image_path):
    if os.path.exists(image_path):
        os.remove(image_path)
        print(f"Image {image_path} has been deleted.")
    else:
        print("The file does not exist.")

def job():
    url = "https://engagement.pptik.id/api/v1/proctoring/row/image"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        username = data.get('username', 'No username provided')
        user_id = data.get('userID', 'No userID provided')
        image_url = data.get('imageURL', 'No image URL provided')
        firstname = data.get('firstname', 'No firstname provided')
        lastname = data.get('lastname', 'No lastname provided')
        timestamp = data.get('timestamp', 'No timestamp provided')
        date_time = data.get('datetime', 'No dateTime provided')
        id_courses = data.get('idCourses', 'No id_courses provided')
        course_name = data.get('courseName', 'No course_name provided')
        create_at = data.get('createdAt', 'No createdAt provided')
        print("Username:", username, "userID:", user_id, "imageURL:", image_url, "firstname:", firstname, "lastname:", lastname, "timestamp:", timestamp, "datetime:", date_time, "idCourses:", id_courses, "courseName:", course_name, "createdAt:", create_at)
        save_path = "D:/worker/Worker_2022/worker-proctoring-moodle/process_image"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        detect_faces_in_image(image_url, save_path, username, user_id, firstname, lastname, timestamp, date_time, id_courses, course_name, create_at)

schedule.every(30).seconds.do(job)

while True:
