import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import mysql.connector
import os

def setup_session(retry_count=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]):
    session = requests.Session()
    retries = Retry(total=retry_count, backoff_factor=backoff_factor,
                    status_forcelist=status_forcelist)
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def mdldb_connection():
    return mysql.connector.connect(
        host="lms.pptik.id",
        database="moodle",
        user="adminmoodle",
        password="Pptik2023!"
    )

def new_buffered_cursor(conn):
    return conn.cursor(buffered=True)



def main(conn):
    cursor = new_buffered_cursor(conn)
    query = "SELECT id FROM mdl_user ;"
    cursor.execute(query)

    for (user_id,) in cursor:
        print(user_id)
        # Get user profile picture
        profile_picture_url = get_profile_picture_url(user_id)
        print(profile_picture_url)
        # Insert profile picture URL into mdl_user table
        #insert_profile_picture_url(conn, user_id, profile_picture_url)
    cursor.close()

def get_profile_picture_url(user_id):
    moodle_session = setup_session()
    # LMS PPTIK API
    rest_url = "https://lms.pptik.id/webservice/rest/server.php"
    service_token = "6c5b3c6a8d87906050f61b8dbd476a4f"
    function_name = 'core_user_get_users_by_field'
    field = 'id'

    params = {
        'wstoken': service_token,
        'wsfunction': function_name,
        'moodlewsrestformat': 'json',
        'field': field,
        'values[0]': str(user_id),  # Convert user_id to string and place in list
    }

    # Make the request
    response = moodle_session.get(rest_url, params=params)  # Use the session you set up for retries
    users = response.json()
    #print(users)

    # Assuming a single user ID is queried, extract the profile picture URL directly
    if users and isinstance(users, list) and len(users) > 0:
        profile_image_url = users[0].get('profileimageurl')
        username = users[0].get('username')
        firstname = users[0].get('firstname')

        # Call save_to_path with the corrected arguments
        filepath = save_to_path(profile_image_url, save_path="D:/mdl_work/picture", filename=username)
        
        return profile_image_url, username, firstname
    else:
        print("No user found or error in response.")
        return None

def get_filename(profile_image_url):
    return profile_image_url.split('/')[-3]


def save_to_path(profile_image_url, save_path, filename):
    """
    Download an image from a URL and save it as a JPG file.

    :param image_url: The URL of the image to download.
    :param save_path: The directory where the image will be saved.
    :param filename: The name of the file without extension.
    """
    # Ensure the save directory exists
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # Complete file path
    file_path = os.path.join(save_path, f"{filename}.jpg")

    # Download the image
    response = requests.get(profile_image_url, stream=True)

    # Check if the request was successful
    if response.status_code == 200:
        with open(file_path, 'wb') as out_file:
            # Write the image's content into the file
            out_file.write(response.content)
        print(f"Image successfully saved to {file_path}")
    else:
        print(f"Error downloading the image. Status code: {response.status_code}")

    return file_path

if __name__ == "__main__":
    conn = mdldb_connection()
    print(f"Connection established: {conn.is_connected()}")
    #get_coursename(filename)
    main(conn)
    conn.close()