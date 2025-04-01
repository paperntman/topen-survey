# -*- coding: utf-8 -*-
from flask import Flask, jsonify, render_template, request
import json
import os
from datetime import datetime
import random
import logging

# json 폴더의 경로
json_folder = 'json'  # json 폴더가 현재 작업 디렉터리에 있다고 가정

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

global count
count = 0

# json 폴더에서 랜덤한 JSON 파일 선택
def get_random_json():
    global count
    files = [f for f in os.listdir(json_folder) if f.endswith('.json')]  # JSON 파일 목록
    if not files:
        return None  # JSON 파일이 없으면 None 반환
    random_file = random.choice(files)  # 랜덤으로 파일 선택
    file_path = os.path.join(json_folder, random_file)  # 파일 경로 생성

    # 선택한 JSON 파일 읽기
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)  # JSON 데이터 로드
    return data  # 데이터 반환

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    ip_address = request.remote_addr  # 클라이언트의 IP 주소 가져오기
    logger.info(f"Home page accessed from IP: {ip_address}")
    
    data = get_random_json()
    if data is None:
        return jsonify({"error": "No data available"}), 404
    return render_template('index.html', text=str(data["text"]).replace("\n", "<br>"), 
                           Q1_1=str(data["q1_1"]), Q1_2=str(data["q1_2"]), 
                           Q1_3=str(data["q1_3"]), Q1_4=str(data["q1_4"]), 
                           Q1_5=str(data["q1_5"]), Q2=str(data['q2']), 
                           Q3=str(data['q3']), Q4=str(data['q4']), 
                           Q5=str(data['q5']), id=str(data['id']))

@app.route('/post', methods=['POST'])
def post():
    ip_address = request.remote_addr  # 클라이언트의 IP 주소 가져오기
    logger.info(f"Post request received from IP: {ip_address}")

    # POST 요청으로 받은 데이터
    data = request.form.to_dict()  # 폼 데이터를 사전 형태로 변환
    data['ip'] = ip_address

    # 현재 시각을 파일명으로 변환 (예: 2023-03-31_13-45-30.json)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f'post/{timestamp}.json'

    # JSON 형식으로 파일 저장
    with open(filename, 'w', encoding='UTF-8') as json_file:
        json.dump(data, json_file)
    
    logger.info(f"Data saved: {filename}")
    return jsonify({"message": "Data saved successfully", "filename": filename})

if __name__ == '__main__':
    app.run(debug=False, port=80)
