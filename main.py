from dotenv import load_dotenv
from IPython.display import display, Image, Audio

import cv2  # We're using OpenCV to read video
import base64
import time
import io
from openai import OpenAI
import os
import requests

import streamlit as st
import tempfile
import numpy as np
from PIL import Image
import datetime
import mysql.connector
from mysql.connector import Error
import bcrypt
from string import Template


load_dotenv()


def main():
    st.set_page_config(page_title="instaPoster", page_icon=":dog:")

    connect_db()

    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Go to", ("Login", "instaPoster", "Sign Up"))

    if choice == "Login":
        st.title("Login to Your Account")
        login_form()
    elif choice == "instaPoster":
        st.title("인스타 글작성")
        insta_form()
    elif choice == "Sign Up":
        st.title("Create New Account")
        signup_form()

# 데이터베이스 연결 함수
def connect_db():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='insta_poster',
            user=os.environ["MYSQL_ID"],
            password=os.environ["MYSQL_PASSWORD"]
        )
        return connection
    except Error as e:
        print("Error while connecting to MySQL", e)
        return None


# 사용자 정보를 데이터베이스에 저장하는 함수
def register_user(username, hashed_pw, email):
    conn = connect_db()
    if conn is not None:
        cursor = conn.cursor()
        query = "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)"
        values = (username, hashed_pw, email)
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    return False


# 회원가입 폼
def signup_form():
    with st.form("signup_form", clear_on_submit=True):
        username = st.text_input("Username", max_chars=50)
        password = st.text_input("Password", type="password", max_chars=50)
        email = st.text_input("Email", max_chars=50)
        submit_button = st.form_submit_button("Sign Up")

        if submit_button:
            if username and password and email:
                hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                success = register_user(username, hashed_pw, email)
                if success:
                    st.success("Successfully registered!")
                else:
                    st.error("Registration failed. Please try again.")
            else:
                st.error("Please fill out all fields.")


# 로그인 폼
def login_form():
    with st.form("login_form"):
        email = st.text_input("Email", max_chars=50)
        password = st.text_input("Password", type="password", max_chars=50)
        login_button = st.form_submit_button("Login")
        if login_button:
            user = check_user(email, password)
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                st.session_state['user.username'] = user['username']
                st.session_state['user.uid'] = user['uid']
                st.success("Logged in successfully!")
                st.session_state['prompt.prompt'] = get_my_prompt()
            else:
                st.error("Invalid email or password")

def check_user(email, password):
    conn = None
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        cursor.close()

        # 사용자가 존재하고 비밀번호가 일치하는지 확인
        if user :
            return user
        else:
            return None
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if conn:
            conn.close()
    return None

def get_my_prompt():
    conn = None
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT prompt FROM insta_poster.prompts WHERE users_uid = %s"
        cursor.execute(query, (st.session_state['user.uid'],))
        prompt = cursor.fetchone()
        cursor.close()
        if prompt :
            return prompt['prompt']
        else:
            return "주어진 사진에 따라 인스타그램에 적합한 글을 써주세요."

    except Error as e:
        print("Error... while connecting to MySQL", e)
    finally:
        if conn:
            conn.close()
    return None

# 글작성 폼
def insta_form():
    st.header("instaPoster :dog:")

    uploaded_file = st.file_uploader("Choose a file", key="insta_poster_uploader")
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image)
        
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    current_season = get_season(datetime.datetime.now())

    contents_count = 10

    print(st.session_state['prompt.prompt'])
    if 'prompt.prompt' not in st.session_state or not st.session_state['prompt.prompt']:
        current_prompt = '기본 템플릿을 여기에 쓰시고 save prompt 버튼을 누르세요.'
    else:
        current_prompt = st.session_state['prompt.prompt']

    prompt = st.text_area("prompt", value=current_prompt, height=200)

    col1, col2 = st.columns([3, 1])

    with col1:
        generate_button = st.button('Generate')
    with col2:
        save_button = st.button('Save Prompt')
    
    if generate_button and uploaded_file is not None:
        # Template 객체 생성
        t = Template(prompt)

        # 필요한 변수들을 딕셔너리 형태로 제공
        prompt_values = {
            'current_date': current_date,
            'current_season': current_season,
            'contents_count': contents_count
        }

        # 변수를 포함한 최종 텍스트 생성
        converted_prompt = t.safe_substitute(prompt_values)
        print(converted_prompt)
        buffer = io.BytesIO()
        image = Image.open(uploaded_file)
        resized_image = resize_image(image)
        resized_image.save(buffer, format="JPEG")
        byte_data = buffer.getvalue()
        b64image = base64.b64encode(byte_data).decode('utf-8')
        st.text_input("base64", value=b64image)

        print(converted_prompt)

        response = image_to_story(b64image, converted_prompt)
        st.text_area("포스팅 내용", value=response, height=400)

    if save_button:
        if save_prompt(prompt):
            st.success("저장되었습니다.")
        else:
            st.error("오류가 발생하였습니다.")

def save_prompt(prompt):
    if 'user.uid' not in st.session_state or not st.session_state['user.uid']:
        st.warning("로그인을 먼저 하세요.")
    else:
        conn = connect_db()
        if conn is not None:
            try:
                cursor = conn.cursor()
                check_query = "SELECT * FROM prompts WHERE users_uid = %s"
                cursor.execute(check_query, (st.session_state['user.uid'],))
                result = cursor.fetchone()

                if result:
                    update_query = "UPDATE prompts SET prompt = %s WHERE users_uid = %s"
                    cursor.execute(update_query, (prompt, st.session_state['user.uid']))
                else:
                    insert_query = "INSERT INTO prompts (users_uid, prompt) VALUES (%s, %s)"
                    cursor.execute(insert_query, (st.session_state['user.uid'], prompt))

                conn.commit()
                return True
            except Error as e:
                print("Error in database operation", e)
                return False
            finally:
                cursor.close()
                conn.close()
    return False
    

def image_to_story(base64Image, prompt):
    PROMPT_MESSAGES = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64, {base64Image}"
                    }
                }
            ],
        },
    ]

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    result = client.chat.completions.create(
        messages=PROMPT_MESSAGES,
        model="gpt-4-vision-preview",
        max_tokens=2000,
        temperature=0.7,  # 예시 값
        frequency_penalty=0.5  # 예시 값
    )
#    print(result)
#    st.text_area("REQUEST MESSAGE", value=PROMPT_MESSAGES, height=400)

    return result.choices[0].message.content

def resize_image(image, base_width=1080):
    w_percent = (base_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    resized_image = image.resize((base_width, h_size), Image.Resampling.LANCZOS)
    return resized_image


def get_season(date):
    month = date.month
    day = date.day

    if (month == 3 and day >= 20) or (month == 4) or (month == 5) or (month == 6 and day < 21):
        return "봄"
    elif (month == 6 and day >= 21) or (month == 7) or (month == 8) or (month == 9 and day < 23):
        return "여름"
    elif (month == 9 and day >= 23) or (month == 10) or (month == 11) or (month == 12 and day < 21):
        return "가을"
    else:
        return "겨울"


if __name__ == "__main__":
    main()
