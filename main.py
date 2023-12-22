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

load_dotenv()

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
    print(result)
    return result.choices[0].message.content

def main():
    # print(os.environ['OPENAI_API_KEY'])
    st.set_page_config(page_title="instaPoster", page_icon=":bird:")
    default_prompt = "인스타그램용 포스팅을 쓰려고 하는데 첨부된 사진을 기반으로 글과 해시태그를 감상적으로 100자 정도로 emoji를 포함하여 3개의 글을 작성해주세요. 강아지의 이름은 '노아' 이고 저의 반려견입니다."
    prompt = st.text_input("prompt", value=default_prompt)
    st.header("instaPoster :bird:")
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        new_image = image.resize((image.width // 8, image.height // 8))
        st.image(new_image)

    if st.button('Generate', type="primary") and uploaded_file is not None:
        buffer = io.BytesIO()
        image = Image.open(uploaded_file)
        new_image = image.resize((image.width // 8, image.height // 8))
        new_image.save(buffer, format="JPEG")
        byte_data = buffer.getvalue()
        b64image = base64.b64encode(byte_data).decode('utf-8')

        # base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        st.text_input("base64", value=b64image)
        response = image_to_story(b64image, prompt)
        st.text_area("포스팅 내용", value=response, height=200)

if __name__ == "__main__":
    main()
