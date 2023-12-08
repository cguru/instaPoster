from dotenv import load_dotenv
from IPython.display import display, Image, Audio

import cv2  # We're using OpenCV to read video
import base64
import time
import io
import openai
import os
import requests

import streamlit as st
import tempfile
import numpy as np


load_dotenv()



def main():
    print(os.environ['OPENAI_API_KEY'])


if __name__ == "__main__":
    main()
