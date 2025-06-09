# -*- coding: utf-8 -*-
from flask import Flask, jsonify, render_template, request, redirect, url_for
import json
import os
from datetime import datetime
import random
import logging
import traceback
import threading
import google.generativeai as genai

# ==============================================================================
# 1. 통합 설정 및 초기화
# ==============================================================================

# --- Flask 앱 인스턴스 생성 ---
app = Flask(__name__)

# --- 로깅 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 설문조사 앱 설정 ---
json_folder = 'json'  # 설문조사 json 파일이 있는 폴더
if not os.path.exists('post'):
    os.makedirs('post')  # 설문조사 결과 저장 폴더 생성

# --- Google Generative AI 설정 ---
API_KEY_PROVIDED = "YOUR_API_KEY_HERE"  # 여기에 실제 API 키를 입력하세요.
MODEL_NAME = "gemini-1.5-flash"

try:
    api_key = os.environ.get("GEMINI_API_KEY", API_KEY_PROVIDED)
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        raise ValueError("API 키가 제공되지 않았습니다. 환경 변수(GEMINI_API_KEY) 또는 코드 내(API_KEY_PROVIDED)에 키를 설정해주세요.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=MODEL_NAME)
    logger.info(f"Google Generative AI 모델 '{MODEL_NAME}'이(가) 성공적으로 초기화되었습니다.")

except Exception as e:
    logger.error(f"Google Generative AI 초기화 중 심각한 오류 발생: {e}")
    logger.error(traceback.format_exc())
    model = None

# --- 피드백 저장 설정 ---
feedback_lock = threading.Lock()

# Yes/No 피드백 파일
FEEDBACK_FILE = 'feedback_counts.json'


def _initialize_feedback_file():
    with feedback_lock:
        if not os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, 'w') as f:
                json.dump({"yes": 0, "no": 0}, f, indent=2)
            logger.info(f"'{FEEDBACK_FILE}' 파일이 생성되었습니다.")


# 별점 피드백 파일
STAR_FEEDBACK_FILE = 'star_feedback.json'


def _initialize_star_feedback_file():
    with feedback_lock:
        if not os.path.exists(STAR_FEEDBACK_FILE):
            # 초기 구조: 각 별점에 대한 카운트
            initial_data = {str(i): 0 for i in range(1, 6)}  # {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
            with open(STAR_FEEDBACK_FILE, 'w') as f:
                json.dump(initial_data, f, indent=2)
            logger.info(f"'{STAR_FEEDBACK_FILE}' 파일이 생성되었습니다.")


# 앱 시작 시 각 피드백 파일 초기화
_initialize_feedback_file()
_initialize_star_feedback_file()

# --- AI 프롬프트 템플릿 ---
SUMMARY_PROMPT_TEMPLATE = (
    "사용자 의도와 목적: 규칙 1. 이 요약기는 사용자가 긴 글에서 가장 중요한 정보를 빠르고 정확하게 파악할 수 있도록 돕는 것을 목적으로 한다. 요약문은 원문의 의미를 오해 없이 전달하되, 복잡한 정보는 재구성하여 직관적으로 이해할 수 있게 표현된다. "
    "도메인 특이성: 규칙 2. 이 시스템은 다양한 도메인(철학적 서술, 경제 분석, 기술 개요, 미디어 이론 등)의 글을 인식하고, 각 도메인 특성에 맞게 요약 전략을 조절한다. 예를 들어, 철학적 글에서는 논증 구조를 중심으로 요약하고, 경제적 글에서는 원인-결과 및 개념 정의를 요약 중심에 둔다. 기술 글은 단계적 설명의 흐름을 유지하며, 미디어 글은 주요 이론을 중심으로 맥락을 간결하게 정리한다."
    "<지문 1>"
    "책상 위에 빨간 사과가 놓여 있는 상황에 대한 사유 과정은 사과의 형태나 색깔이 감각 기관을 통해 들어오고, 이를 사과라고 인식하는 것이다. 우리는 일반적으로 이 사과가 현실에 실재하는 대상이라는 것을 의심하지 않는다. 그러나 근대 철학자들 중에는 감각되지 않은 물리적 대상이 독립적으로 존재한다는 것을 증명할 수 없다는 이유로 이러한 대상의 실재함은 사유에 의존하는 것은 아닌지 의심하는 사람이 있었다. 이러한 의심을 바탕으로 한 여러 철학적 논변이 나타나면서 하나의 공통된 입장이 형성되었다. 그것은 인간의 사유와 독립한 존재가 실재하지 않으며, 사유와 대상이 따로 분리되어서는 어떤 것도 접근이나 이해가 불가능하다는 입장이다."
    "현대 철학자 메야수는 이러한 입장을 상관주의라고 명명하며, 사유 의존적인 대상뿐만 아니라 인간의 사유와 독립한 존재가 실재한다고 주장한다. 그의 주장은, 상관주의가 유럽 대륙 철학의 주요 입장 중 하나가 되면서 인간의 사유를 대상과 사유의 관계로 제한했다는 문제 의식에서 비롯되었다. 메야수는 인간이라는 종의 출현에 선행하는 존재 전부를 ’선조적인 것‘이라고 하면서 인간의 사유와 독립한 존재가 실재함을 과학의 발견들이 드러낸다고 주장한다. 가령 방사성 동위 원소의 측정으로 '46억 년 전에 최초의 지구가 존재했다.'라는 것이 입증되었다. 메야수에 따르면, 이는 인간의 사유와 독립한 존재가 실재한다는 증거이다. 그리고 이를 부정하면 선조적인 것을 전제해야만 설명할 수 있는 것들과 충돌을 일으킨다고 보았다."
    "이렇게 인간의 사유와 독립한 존재가 실재한다고 주장한 메야수는 이러한 존재가 가능성을 가진 우연성이라는 특성을 가지고 있다고 보았다. 예를 들어 공전하는 달은 일식의 가능성을 가지는 것일 뿐, 달의 공전이 일식과의 인과적인 필연성이 있는 것은 아니다. 태양의 변화로 일식이 나타나지 않을 수도 있기 때문이다. 이렇게 우연성을 가진 존재에 대한 그의 주장은 우리 인간이 이러한 존재가 가지는 다양한 가능성들에 대해 사유해야 한다는 것을 내포하고 있다."
    "메야수는 상관주의에서 부정하는, 인간의 사유와 독립한 존재가 실재하며 이에 대해 사유할 수 있음을 논증했다. 또한 인간의 사유와 독립한 존재가 실재한다고 보는 그의 철학은 인간 중심적인 사유의 세계에서 벗어나 우리의 사유와 세계의 확장을 시도하는 것으로 볼 수 있다."
    "<요약문1> 근대 철학자들은 감각되지 않은 대상의 실재성을 의심하며, 사유와 대상이 분리될 수 없다고 주장했다. 반면 메야수는 인간의 사유와 독립한 존재가 실재한다며, 상관주의를 반박했다. 그는 인간 출현 이전의 세계가 이를 입증하며, 이 세계의 여러 우연적 현상을 사유해야한다고 본다."
    "<지문2>... (다른 프롬프트 예시들도 여기에 포함) ...<요약문2>"
    "명확성 및 구체성: 규칙 3. 요약문은 단순히 글의 길이를 줄이는 것이 아니라, 본문의 중심 논지를 유지하면서 가장 핵심적인 정보가 누락되지 않도록 구성된다. 독자가 글을 읽지 않고도 주요 내용을 파악할 수 있어야 한다. 중요 키워드, 중심 주장, 주요 사례 또는 정의는 반드시 포함되어야 한다."
    "제약 조건: 규칙 4. 글을 요약할 때는 원문을 그대로 복사하기보다는 정보의 논리적 흐름을 재구성하여, 원문보다 더 명료하게 전달되도록 한다. 필요 시 중복 표현, 장황한 수식어, 부차적 예시는 생략한다. 원문과 논리적으로 충돌하는 문장은 요약문에서 제거한다."
    "출력 형식 : 규칙 5. 전체 글의 구조를 간결하게 압축하되, 요약문의 비율은 글 길이에 따라 자동 조정된다. 입력 글이 20문장 이하일 경우, 최대 40% 분량으로 요약하며, 20문장을 초과할 경우 최대 30% 분량으로 요약한다. 요약문은 문단 단위가 아닌 하나의 통합된 문장 흐름으로 출력하며, 필요 시 명확성을 위한 문장 분리는 허용된다. 또한 어조는 문어체, 평서문, 중립적 어조를 유지한다."
    "\n\n--- 원본 글 ---:\n{text_to_summarize}"
    "\n\n--- 요약문 ---:"
)

CORE_SUMMARY_PROMPT_TEMPLATE = (
    "당신은 텍스트의 핵심 논증과 결론만을 추출하는 전문가입니다. "
    "모든 부가 설명, 예시, 배경 정보는 제거하고, 오직 글의 뼈대가 되는 주장과 그에 대한 최종적인 결론만을 간결하게 한두 문장으로 요약해주세요. "
    "반드시 가장 중요한 키워드를 포함해야 합니다."
    "\n\n--- 원본 글 ---:\n{text_to_summarize}"
    "\n\n--- 핵심 요약문 ---:"
)

SAMPLE_TEXT_GENERATION_PROMPT = (
    "흥미로운 주제에 대한 한국어 비문학 지문을 생성해주세요. "
    "이 지문은 최소 4개의 문단으로 구성되어야 하며, 각 문단은 명확한 내용을 담고 있어야 합니다. "
    "독자들이 새로운 정보를 얻거나 생각해볼 만한 내용을 포함해주세요. "
    "지문 내용만 응답으로 생성하고, 다른 부가적인 설명은 포함하지 마세요."
)


# ==============================================================================
# 2. 헬퍼 함수
# ==============================================================================

def get_random_json(page):
    """설문조사 json 폴더에서 랜덤한 JSON 파일 선택"""
    files = [f for f in os.listdir(json_folder) if f.endswith('.json')]
    if not files:
        return None
    random.shuffle(files)
    for i in files:
        file_path = os.path.join(json_folder, i)
        try:
            with open(file_path, 'r', encoding='UTF-8') as json_file:
                data = json.load(json_file)
                # id와 page가 문자열이고 2진수 형태라고 가정
                if (int(data['id'], 2) & int(page, 2) != 0):
                    continue
                return data
        except (IOError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"파일 '{file_path}' 처리 중 오류 발생: {e}")
            continue
    return None


def _generate_text_from_model(prompt_template, text_input, context_log=""):
    """AI 모델을 호출하고 결과를 반환하는 범용 함수"""
    if model is None:
        logger.error(f"AI 모델이 초기화되지 않아 {context_log} 요청을 처리할 수 없습니다.")
        return jsonify({'error': 'AI 모델을 초기화하는 데 실패했습니다. 서버 로그를 확인해주세요.'}), 500

    try:
        full_prompt = prompt_template.format(text_to_summarize=text_input)
        logger.info(f"AI 모델에 {context_log} 요청 전송 중...")
        response = model.generate_content(full_prompt)
        logger.info(f"AI 모델로부터 {context_log} 응답 수신 완료.")

        result_text = response.text
        if not result_text.strip():
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                error_message = f"콘텐츠 생성 중 API에 의해 차단되었습니다. 이유: {response.prompt_feedback.block_reason}"
                logger.error(error_message)
                return jsonify({'error': error_message}), 400
            else:
                logger.warning(f"AI 모델이 빈 {context_log} 결과를 반환했습니다.")
                return jsonify({'error': f'AI 모델이 {context_log} 결과를 생성하지 못했습니다.'}), 500

        return jsonify({'result': result_text.strip()}), 200

    except Exception as e:
        logger.error(f"'{context_log}' 처리 중 예상치 못한 오류 발생: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'서버 내부 오류가 발생했습니다: {str(e)}'}), 500


# ==============================================================================
# 3. 라우트(Routes) 정의
# ==============================================================================

# --- 설문조사 앱 라우트 ---

@app.route('/survey')
def start():
    """설문조사 시작 페이지"""
    return render_template('start.html')


@app.route('/page', methods=['GET'])
def survey_page():
    """설문조사 질문 페이지"""
    ip_address = request.remote_addr
    logger.info(f"설문조사 페이지 접근 - IP: {ip_address}")

    page = request.args.get('page', '00000000')
    if (page == '11111111'):
        return render_template('39.html')  # 설문 완료 페이지

    data = get_random_json(page)
    if data is None:
        return render_template('39.html')

    return render_template('index.html', text=str(data["text"]).replace("\n", "<br>"),
                           Q1_1=str(data["q1_1"]), Q1_2=str(data["q1_2"]),
                           Q1_3=str(data["q1_3"]), Q1_4=str(data["q1_4"]),
                           Q1_5=str(data["q1_5"]), Q2=str(data['q2']),
                           Q3=str(data['q3']), Q4=str(data['q4']),
                           Q5=str(data['q5']), id=str(data['id']))


@app.route('/post', methods=['POST'])
def save_survey_post():
    """설문조사 결과 저장 API"""
    ip_address = request.remote_addr
    logger.info(f"설문조사 제출 요청 - IP: {ip_address}")

    data = request.form.to_dict()
    data['ip'] = ip_address
    data['timestamp_utc'] = datetime.utcnow().isoformat()

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f'post/{timestamp}_{ip_address.replace(":", "_")}.json'

    with open(filename, 'w', encoding='UTF-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)

    logger.info(f"설문조사 데이터 저장 완료: {filename}")

    next_page_val = int(data.get('page', '0'), 2) + int(data.get('id', '0'), 2)
    redirect_page_str = bin(next_page_val)[2:].zfill(8)

    redirect_url = url_for('survey_page', page=redirect_page_str)
    return jsonify({"redirect_url": redirect_url})


# --- AI 요약 앱 라우트 ---

@app.route('/')
def summarizer_home():
    """AI 요약기 메인 페이지"""
    return render_template('summarizer.html')


# [수정됨]
@app.route('/api/summarize', methods=['POST'])
def generate_standard_summary():
    """[기존] 일반적인 텍스트 요약 API"""
    if not request.is_json:
        return jsonify({'error': '요청은 JSON 형식이어야 합니다.'}), 400

    request_data = request.get_json()
    # 'data' 키를 먼저 확인하고, 그 안에서 'text'를 찾도록 수정
    data_payload = request_data.get('data', {})
    text_to_summarize = data_payload.get('text')

    if not text_to_summarize or not isinstance(text_to_summarize, str) or not text_to_summarize.strip():
        return jsonify({'error': '요약할 텍스트(text)는 비어있지 않은 문자열이어야 합니다.'}), 400

    return _generate_text_from_model(SUMMARY_PROMPT_TEMPLATE, text_to_summarize, context_log="일반 요약")


# [수정됨]
@app.route('/api/core-summary', methods=['POST'])
def generate_core_summary():
    """[신규] 핵심 논증을 요약하는 API"""
    if not request.is_json:
        return jsonify({'error': '요청은 JSON 형식이어야 합니다.'}), 400

    request_data = request.get_json()
    # 'data' 키를 먼저 확인하고, 그 안에서 'text'를 찾도록 수정
    data_payload = request_data.get('data', {})
    text_to_summarize = data_payload.get('text')

    if not text_to_summarize or not isinstance(text_to_summarize, str) or not text_to_summarize.strip():
        return jsonify({'error': '요약할 텍스트(text)는 비어있지 않은 문자열이어야 합니다.'}), 400

    return _generate_text_from_model(CORE_SUMMARY_PROMPT_TEMPLATE, text_to_summarize, context_log="핵심 요약")

# --- 기타 API 라우트 ---

@app.route('/api/sample-text', methods=['GET'])
def get_sample_text():
    """샘플 텍스트를 생성하는 API 엔드포인트"""
    if model is None:
        logger.error("AI 모델이 초기화되지 않아 샘플 텍스트 요청을 처리할 수 없습니다.")
        return jsonify({'error': 'AI 모델을 초기화하는 데 실패했습니다.'}), 500

    try:
        logger.info(f"AI 모델에 샘플 텍스트 생성 요청 전송 중...")
        response = model.generate_content(SAMPLE_TEXT_GENERATION_PROMPT)
        logger.info("AI 모델로부터 샘플 텍스트 응답 수신 완료.")
        return jsonify({'text': response.text.strip()})
    except Exception as e:
        logger.error(f"'/api/sample-text' 처리 중 오류 발생: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'서버 내부 오류가 발생했습니다: {str(e)}'}), 500


@app.route('/api/feedback', methods=['POST'])
def handle_feedback():
    """Yes/No 피드백을 기록하는 API 엔드포인트"""
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    data = request.get_json()
    feedback_value = data.get('feedback')

    if feedback_value not in ['yes', 'no']:
        return jsonify({'error': 'Invalid feedback value. Must be "yes" or "no".'}), 400

    try:
        with feedback_lock:
            try:
                with open(FEEDBACK_FILE, 'r') as f:
                    current_counts = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                current_counts = {"yes": 0, "no": 0}

            current_counts[feedback_value] += 1

            with open(FEEDBACK_FILE, 'w') as f:
                json.dump(current_counts, f, indent=2)

        logger.info(f"Yes/No 피드백 수신: '{feedback_value}'. 현재 카운트: {current_counts}")
        return jsonify({'message': 'Feedback received successfully'}), 200
    except Exception as e:
        logger.error(f"Yes/No 피드백 처리 오류: {e}")
        return jsonify({'error': 'Server error while processing feedback'}), 500


@app.route('/api/star-feedback', methods=['POST'])
def handle_star_feedback():
    """별점 피드백을 기록하는 API 엔드포인트"""
    if not request.is_json:
        return jsonify({'error': '요청은 JSON 형식이어야 합니다.'}), 400

    data = request.get_json()
    rating = data.get('rating')

    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({'error': '잘못된 별점 값입니다. 1에서 5 사이의 정수여야 합니다.'}), 400

    rating_key = str(rating)

    try:
        with feedback_lock:
            try:
                with open(STAR_FEEDBACK_FILE, 'r') as f:
                    current_counts = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                current_counts = {str(i): 0 for i in range(1, 6)}

            if rating_key in current_counts:
                current_counts[rating_key] += 1
            else:
                current_counts[rating_key] = 1

            with open(STAR_FEEDBACK_FILE, 'w') as f:
                json.dump(current_counts, f, indent=2)

        logger.info(f"별점 피드백 수신: {rating}점. 현재 누적: {current_counts}")
        return jsonify({'message': '별점이 성공적으로 기록되었습니다.'}), 200

    except Exception as e:
        logger.error(f"별점 피드백 처리 중 오류 발생: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': '서버에서 별점을 처리하는 중 오류가 발생했습니다.'}), 500


# ==============================================================================
# 4. 앱 실행
# ==============================================================================

if __name__ == '__main__':
    # debug=True는 개발 중에만 사용하고, 실제 배포 시에는 False로 변경하세요.
    # host='0.0.0.0'은 로컬 네트워크의 다른 장치에서 접근할 수 있게 합니다.
    app.run(debug=False, host='0.0.0.0', port=5000)