<raw_guide>
나랑 대화를 나누면서 내가 하려고 하는 작업의 spec 을 같이 가다듬어줘.
내가 하려고 하는 작업은 video 로 만들 sequence 에 대한 기획 자료를 기반으로
실제로 이미 있는 영상 파편, llm 으로 생성한 자료 이미지, 자료 영상 / 그리고 css javascript 등으로 구현한 text animation
TTS 등을 이용해서 각 cut 그리고 강조하는 beat 의 파편을 ffmpeg 를 이용해 scene 과 sequence 로 통합해내는 작업을 하려고해.
참고로 이는 숏폼영상이야. layout 은 9:16으로 고정될 예정이고 720p 로 영상을 만들어줘.
<example_sequence_data>
{
"scenario_title": "야식 먹고도 붓기 없는 그 언니의 비밀, 소화제 아니고 '식이섬유'였어?",
"matched_tone": "팩트 폭격하는 관리의 신, 30대 마케팅 팀장 언니의 시원시원하고 솔직한 말투. 공감 100% 현실 고증과 신뢰감 있는 정보 전달.",
"scenes": [
{
"scene_number": 1,
"scene_visual_note": "[인물] 야식을 즐기지만 날씬한 여성의 뒷모습에서 줌아웃. '관리의 신' 자막.",
"script_kr": "맨날 야식 먹고도 배 안나오게 유지하는 그 언니가 먹는거, 소화 효소인 줄 알았는데 그거 아니래요.",
"audio_note": "[비밀을 폭로하듯 은밀하지만 또렷한 목소리]"
},
{
"scene_number": 2,
"scene_visual_note": "[자료화면] 배부른 상태에서 가루 효소를 입에 털어 넣는 일반적인 사람들 모습 빠르게 교차.",
"script_kr": "효소는 소화를 돕는 거잖아요? 식후에 배 빵빵하다고 습관처럼 효소 털어 넣는 분들 지금이라도 멈춰야해요.",
"audio_note": "[답답하다는 듯, 진심으로 말리는 말투]"
},
{
"scene_number": 3,
"scene_visual_note": "[모션그래픽] 위장에서 음식물이 잘게 부서지며 붉은색(지방/당)으로 변해 몸 전체로 퍼지는 그래픽.",
"script_kr": "효소는 먹은 음식을 빠르게 분해해서, 몸에 더 빨리, 더 잘 흡수되라고 열심히 도와주는거예요",
"audio_note": "[팩트를 짚어주며 약간의 냉소 섞인 톤]"
},
{
"scene_number": 4,
"scene_visual_note": "[인물] 카메라를 정면으로 응시하며 고개를 절레절레 흔드는 모습. 자막: '문제는 소화가 아냐!'",
"script_kr": "그러니까 결국, 우리가 살찌는 건 소화가 안 돼서가 아니라, 필요 이상으로 흡수가 너무 잘 돼서 그런 건데,",
"audio_note": "[논리적으로 따지듯, 귀에 쏙 박히는 딕션]"
},
{
"scene_number": 5,
"scene_visual_note": "[인물] 뱃살을 잡으며 한숨 쉬는 모습. 뱃살 쪽에 '흡수 완료' 도장이 쾅 찍히는 효과.",
"script_kr": "거기다 소화 잘 되라고 효소까지 넣어주니까, 먹는 그대로 뱃살로 쌓이는 최악의 상황인 거죠.",
"audio_note": "[안타까움과 경각심을 주는 강조 톤]"
},
{
"scene_number": 6,
"scene_visual_note": "[3D 그래픽] 장 내부에 촘촘한 그물망이 형성되는 모습. 깨끗한 라인의 실루엣 등장.",
"script_kr": "진짜 살 안 찌는 사람들은 소화력이 좋은 게 아니라, 장 속에 흡수를 걸러주는 '거름망'이 아주 촘촘한 거예요.",
"audio_note": "[해답을 제시하는 자신감 있는 목소리]"
},
{
"scene_number": 7,
"scene_visual_note": "[분할화면] 왼쪽: 샐러드 먹는 모습 / 오른쪽: 장에서 영양분이 스펀지처럼 흡수되는 그래픽.",
"script_kr": "아무리 굶고 식단 조절해도, 장에서 영양분 100% 다 빨아들이면 열심히 식단한거 아무 소용없는데",
"audio_note": "[현실을 꼬집는 씁쓸한 말투]"
},
{
"scene_number": 8,
"scene_visual_note": "[제품 시연] 물속의 기름때를 그물망이 싹 걷어내는 실험 영상 클로즈업.",
"script_kr": "이 거름망이 튼튼하면, 기름진 걸 먹어도 몸에 흡수되기 전에 싹 걸러서 밖으로 내보내거든요.",
"audio_note": "[속 시원한 해결책을 제시하듯 경쾌하게]"
},
{
"scene_number": 9,
"scene_visual_note": "[제품] 'STOM' 패키지를 줌인. '흡수 전 처리' 텍스트 강조.",
"script_kr": "먹은 거 죄책감 덜어내려면, 소화제가 아니라 흡수되기 전에 걸러주는 '식이섬유'를 드셔야 돼요.",
"audio_note": "[제품명을 명확하고 강렬하게 전달]"
},
{
"scene_number": 10,
"scene_visual_note": "[3D 그래픽] 끈적한 식이섬유가 붉은 지방 덩어리를 칭칭 감싸서 미끄러지듯 이동하는 모습.",
"script_kr": "단순히 장을 비우는 게 아니라, 끈적한 식이섬유가 음식물을 그물처럼 칭칭 감아서 흡수를 막아버리니까",
"audio_note": "[원리를 설명하며 신뢰감을 주는 톤]"
},
{
"scene_number": 11,
"scene_visual_note": "[비포/애프터] 라면 먹은 다음 날 퉁퉁 부은 얼굴 vs 붓기 없이 날렵한 턱선 비교.",
"script_kr": "밤에 라면 먹고 자도 다음 날 아침에 얼굴 붓기 하나도 없고, 아랫배도 전혀 나오지 않아요. 신기하죠?",
"audio_note": "[결과에 감탄하며 친구에게 자랑하듯]"
},
{
"scene_number": 12,
"scene_visual_note": "[상황] 사무실 탕비실에서 여직원들이 몰래 알약을 나눠 먹는 모습.",
"script_kr": "요즘 관리 좀 한다는 회사 언니들이 밥 먹기 전에 몰래 챙겨 먹는 게 다 이거라더니 이유가 있더라구요.",
"audio_note": "[소문을 확인했다는 듯 끄덕이며]"
},
{
"scene_number": 13,
"scene_visual_note": "[제품 클로즈업] 작고 매끈한 10mm 정제를 손바닥에 올리고 꿀꺽 삼키는 모습.",
"script_kr": "입에 텁텁하게 남는 역한 가루가 아니라서 깔끔하고, 10mm 미니 사이즈 알약이라 목 넘김도 진짜 편해요.",
"audio_note": "[사용감의 편리함을 강조하며 산뜻하게]"
},
{
"scene_number": 14,
"scene_visual_note": "[상황] 사무실 의자에 앉아 편안한 표정으로 업무를 보는 모습. 헐렁해진 허리춤 강조.",
"script_kr": "하루 종일 사무실에 앉아 있어도 아랫배 쪼이는 느낌 없이 속이 너무 편해서 일에 집중도 훨씬 잘되구요.",
"audio_note": "[직장인들의 공감을 유도하는 편안한 톤]"
},
{
"scene_number": 15,
"scene_visual_note": "[인물] 화장실에서 나오며 배를 문지르고 깜짝 놀란 표정. '가벼움' 텍스트 효과.",
"script_kr": "화장실 한번 갔다 오면, 와... 내 뱃속에 이런 게 들어있었나 싶다니까요. 묵은 게 싹 내려가요.",
"audio_note": "[리얼한 후기를 전하듯 감탄사 섞어]"
},
{
"scene_number": 16,
"scene_visual_note": "[자료] 성분표가 스크롤 되며 '식물성 100%' 마크가 크게 확대됨.",
"script_kr": "요즘은 성분이 중요해서 열심히 찾아봤는데, 한국인에 맞는 식물성 식이섬유를 2대1 황금비율로 배합한거라 안심해도 되고,",
"audio_note": "[똑똑하게 따져봤다는 듯 신뢰감 있게]"
},
{
"scene_number": 17,
"scene_visual_note": "[인물] 진지한 표정으로 화면 가까이 다가와 속삭이듯 말함.",
"script_kr": "솔직히 싼 가격은 아니거든요? 근데 헬스장 끊고 안 가는 비용 생각하면 이게 훨씬 남는 장사예요.",
"audio_note": "[현실적인 조언을 하듯 솔직하게]"
},
{
"scene_number": 18,
"scene_visual_note": "[배너] '한정 수량 특가' 배너가 뜨며 구매 버튼 클릭 유도.",
"script_kr": "그러니까 나중에 사려다 후회하지 말고, 지금 물량 풀렸을 때 무조건 쟁여두세요",
"audio_note": "[긴박함을 주며 행동을 촉구하는 강한 어조]"
}
]
}
</example_sequence_data>
주어진 example 의 형태가 더 적절한 형태로 번형이 되도 괜찮아.
DDD 를 좋아하는데, 이를 각 작업의 domain을 잘 나누면서 작업했으면 좋겠어.
python 을 가장 기본이 되는 언어로 활용해줘.
영상과 이미지 생성 API 는 주로 google 의 nano banana pro, veo 3.1 등을 쓰려고 하고
text 에 대한 애니메이션
그리고 이미지를 이동 시키거나, 흔들거나 확대하는 등의 beat 들을 활용할 수 있도록 프로젝트를 구성하려고 해.
이의 가장 main 함수는 어떤 sequence 에 대한 기획 데이터를 넘기면
영상을 최종적으로 생성하도록 해줘.
이 과정에서 생성한 영상 들을 local 에 잘 저장해서 내가 리뷰하면서 다시 다른 것으로 고를 수 있도록 해주고.
기존 촬영 영상의 경우는 gemini 3 flash API 를 이용해서 해당 영상을 파편으로 나누고 description을 각 파편별로 가지도록 해서 적합한 영상을 가져와서 사용할 수 있도록 해줘.
TTS 의 경우는 chirp v3 를 활용할 거야.
그리고 별도의 caption 생성은 안해도 돼.
</raw_guide>

제시해주신 기획은 매우 흥미롭고, 최신 AI 기술(Gemini, Veo, Imagen, Chirp)과 고전적인 영상 처리 기술(FFmpeg, Web Tech)을 결합한 하이브리드 파이프라인이네요. 특히 **DDD(Domain-Driven Design)** 접근 방식을 원하시므로, 복잡한 비즈니스 로직을 명확한 도메인으로 분리하여 설계해 보겠습니다.

우선, **데이터 스펙(Spec)**을 시스템이 처리하기 좋게 가다듬고, 그 다음 **아키텍처**와 **구현 로직**을 제안하겠습니다.

---

### 1. Refined Data Specification (가다듬어진 데이터 스펙)

기존 JSON은 기획자 관점입니다. 이를 시스템이 바로 처리할 수 있도록 **`Asset Type`**, **`Effect Beat`**, **`Duration Constraint`** 등의 엔지니어링 속성을 추가하여 구조화해야 합니다.

```json
{
  "project_id": "stom_diet_video_001",
  "scenario_meta": {
    "title": "야식 먹고도 붓기 없는 비밀",
    "tone_voice": "energetic_professional_female",
    "aspect_ratio": "9:16"
  },
  "scenes": [
    {
      "scene_id": "s01",
      "sequence_order": 1,
      "audio_script": {
        "text": "맨날 야식 먹고도 배 안나오게 유지하는 그 언니가 먹는거, 소화 효소인 줄 알았는데 그거 아니래요.",
        "voice_preset_id": "chirp_v3_korean_female_confident",
        "speed": 1.1
      },
      "visual_layer": {
        "type": "existing_footage",
        "query_tags": ["slim woman", "back view", "night snack", "zoom out"],
        "fallback_gen_prompt": "Cinematic shot, back view of a slim woman eating a snack at night, high quality, 4k"
      },
      "text_overlay": {
        "content": "관리의 신",
        "style_template": "bold_impact_red",
        "animation": "fade_in_up"
      },
      "fx_beat": {
        "camera_movement": "zoom_out_slow",
        "transition_next": "whip_pan_left"
      }
    },
    {
      "scene_id": "s03",
      "sequence_order": 3,
      "audio_script": {
        "text": "효소는 먹은 음식을 빠르게 분해해서, 몸에 더 빨리, 더 잘 흡수되라고 열심히 도와주는거예요",
        "voice_preset_id": "chirp_v3_korean_female_cynical"
      },
      "visual_layer": {
        "type": "motion_graphic_gen",
        "prompt": "3D medical animation, food breaking down in stomach, turning red, spreading to body",
        "model": "google_veo_3.1"
      },
      "fx_beat": {
        "effect": "shake_on_beat",
        "beat_timing": [0.5, 2.1]
      }
    }
  ]
}
```

**변경 포인트:**

- **`visual_layer`**: 영상 소스의 출처를 구분 (`existing_footage` vs `ai_gen` vs `web_render`).
- **`text_overlay`**: CSS/JS로 렌더링할 텍스트 정보와 애니메이션 타입 분리.
- **`fx_beat`**: FFmpeg에서 적용할 효과(줌, 쉐이크 등) 명시.

---

### 2. DDD Architecture Design

전체 시스템을 4개의 핵심 도메인(Context)으로 나눕니다.

#### 1) Planning Context (기획 도메인)

- **역할**: 시나리오 JSON을 파싱하고, 각 Scene의 논리적 흐름과 제약조건(시간, 순서)을 관리합니다.
- **주요 객체**: `Scenario`, `Scene`, `Script`.

#### 2) Library Context (자산 도메인 - Inventory)

- **역할**: 로컬 스토리지와 메타데이터를 관리합니다. 기존 영상 파일들의 인덱싱(Gemini 분석 결과)을 담당합니다.
- **주요 객체**: `AssetRepository`, `VideoClip` (Start/End time 포함), `MediaFile`.
- **핵심 로직**: Gemini를 이용해 원본 영상(`raw_video`)을 `clip` 단위로 쪼개고 Description을 Vector DB(또는 JSON)로 관리.

#### 3) Studio Context (생성 도메인 - Factory)

- **역할**: 없는 리소스를 만들어냅니다. 외부 API(Vertex AI, Chirp) 및 내부 렌더러(Headless Browser)와 통신합니다.
- **주요 객체**: `GeneratorService`, `TTSWorker`, `ImageGenWorker`, `TextAnimator`.

#### 4) Editing Context (편집 도메인 - Assembly)

- **역할**: 확보된 자산들을 타임라인에 배치하고 FFmpeg 명령어를 생성하여 최종 렌더링합니다.
- **주요 객체**: `Timeline`, `Composer`, `FilterGraph`, `Renderer`.

---

### 3. Python Project Structure

```text
project_root/
├── domains/
│   ├── planning/          # 시나리오 파싱 및 관리
│   ├── library/           # 기존 영상 인덱싱, Gemini 분석
│   ├── studio/            # AI 생성 (TTS, Image, Video), Web Rendering
│   └── editing/           # FFmpeg 조합, Beat 효과 적용
├── infrastructure/        # Google API Client, FFmpeg Wrapper, File System
├── assets/
│   ├── raw_footage/       # 사용자가 찍은 원본 영상
│   ├── library_index/     # 원본 영상 분석 메타데이터 (JSON/DB)
│   ├── generated/         # AI 생성물 및 TTS 캐시
│   └── review_output/     # 최종 결과물
├── templates/             # Text Animation용 HTML/CSS/JS 템플릿
└── main.py
```

---

### 4. Implementation Details & Code Snippets

각 도메인별 핵심 로직 구현 방향입니다.

#### A. Library Context: 기존 영상 분석 (Gemini 2.0 Flash)

Gemini 2.0 Flash는 긴 비디오 컨텍스트 처리에 강력합니다. 원본 영상을 통째로 넘기고 타임스탬프별 설명을 요청합니다.

```python
# domains/library/analyzer.py
import google.generativeai as genai

class VideoContentAnalyzer:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")

    def analyze_footage(self, video_path):
        """영상을 업로드하고 씬 별 묘사와 타임스탬프를 추출"""
        video_file = genai.upload_file(path=video_path)

        # 영상 처리가 완료될 때까지 대기하는 로직 필요

        prompt = """
        Analyze this video frame by frame.
        Break down the video into distinct clips based on visual changes or actions.
        For each clip, provide:
        1. Start Time (MM:SS)
        2. End Time (MM:SS)
        3. Visual Description (detailed for semantic search)
        4. Camera Angle/Movement
        Output as JSON.
        """

        response = self.model.generate_content([prompt, video_file])
        return self._parse_json(response.text)
```

#### B. Studio Context: Text Animation (Web Tech + Playwright)

CSS/JS 애니메이션을 영상으로 굽기 위해 Playwright를 사용합니다. 투명 배경(Alpha Channel)이 있는 WebM으로 렌더링하거나, Green Screen으로 녹화 후 FFmpeg에서 크로마키를 뺍니다.

```python
# domains/studio/text_renderer.py
from playwright.sync_api import sync_playwright

class TextAnimationRenderer:
    def render_overlay(self, text_data, output_path, duration):
        """
        HTML 템플릿에 텍스트를 주입하고 화면을 녹화하여 비디오로 저장
        """
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1080, 'height': 1920})

            # 로컬 HTML 템플릿 로드 및 데이터 주입 (JS 실행)
            page.goto(f"file://{TEMPLATE_PATH}/index.html")
            page.evaluate(f"window.startAnimation('{text_data['content']}', '{text_data['style']}')")

            # 화면 녹화 로직 (Playwright의 screencast 기능 또는 프레임 캡처)
            # 실제로는 여기에서 ffmpeg으로 파이프를 연결하여 스트림을 저장하는 방식이 고화질에 유리함.
            # 간편하게는 배경을 #00FF00(Green)으로 하고 스크린샷 시퀀스를 저장.

            browser.close()
```

#### C. Studio Context: Audio & Beat (TTS)

TTS 생성 길이에 맞춰 영상의 길이를 조절하는 것이 핵심입니다.

```python
# domains/studio/tts_generator.py
class TTSGenerator:
    def generate(self, text, preset_id):
        # Google Chirp API 호출
        audio_content = google_cloud_tts_call(text, preset_id)
        duration = get_audio_duration(audio_content)
        return AudioAsset(content=audio_content, duration=duration)
```

#### D. Editing Context: FFmpeg Composition (The Main Function)

가장 중요한 통합 부분입니다. `ffmpeg-python` 라이브러리를 사용하거나 직접 서브프로세스를 호출합니다.

```python
# domains/editing/composer.py
import ffmpeg

class SequenceComposer:
    def compose(self, sequence_plan, output_path):
        """
        1. Base Video (Existing or AI Gen)
        2. Audio (TTS)
        3. Overlay (Text Animation)
        4. Effects (Beats)
        """
        inputs = []

        for scene in sequence_plan.scenes:
            # 1. Video Stream 준비
            if scene.visual_type == 'image':
                # 이미지는 오디오 길이만큼 Loop
                vid = ffmpeg.input(scene.visual_path, loop=1, t=scene.duration)
                # 효과 적용 (예: 줌인)
                if scene.beat == 'zoom_in':
                    vid = vid.filter('zoompan', z='min(zoom+0.0015,1.5)', d=700)
            else:
                # 동영상은 길이 맞추기 (trim or loop)
                vid = ffmpeg.input(scene.visual_path).trim(duration=scene.duration)

            # 2. Audio Stream 준비
            aud = ffmpeg.input(scene.audio_path)

            # 3. Text Overlay 합성
            if scene.has_text:
                overlay = ffmpeg.input(scene.text_video_path, color_mode='yuva420p')
                vid = ffmpeg.overlay(vid, overlay)

            # Scene 세트 저장
            inputs.append({'v': vid, 'a': aud})

        # 모든 Scene 연결 (Concat)
        joined = ffmpeg.concat(*[s['v'] for s in inputs] + *[s['a'] for s in inputs], v=1, a=1).node

        # 최종 렌더링
        out = ffmpeg.output(joined[0], joined[1], output_path)
        out.run()
```

---

### 5. Workflow Summary (Main Process)

이 `main.py`가 당신이 원하는 **"기획 데이터를 넘기면 최종 영상을 생성"**하는 메인 함수가 됩니다.

```python
# main.py (Pseudo-code)

def create_video_from_sequence(json_data):
    # 1. Parsing
    scenario = PlanningDomain.parse(json_data)

    # 2. Asset Preparation
    timeline_assets = []

    for scene in scenario.scenes:
        # A. Audio 생성 (가장 먼저 길이를 확정해야 함)
        audio_asset = StudioDomain.generate_tts(scene.script, scene.voice_tone)
        scene_duration = audio_asset.duration

        # B. Visual 확보
        if scene.visual_source == 'library':
            # 기존 영상 라이브러리에서 의미론적 검색
            video_asset = LibraryDomain.find_best_match(scene.visual_query, duration=scene_duration)
        elif scene.visual_source == 'gen_ai':
            # AI 영상/이미지 생성
            video_asset = StudioDomain.generate_visual(scene.visual_prompt, model='veo')

        # C. Text Animation 생성
        text_asset = StudioDomain.render_text(scene.text_content, duration=scene_duration)

        timeline_assets.append({
            'video': video_asset,
            'audio': audio_asset,
            'text': text_asset,
            'effects': scene.effects
        })

    # 3. Assembly & Rendering
    output_filename = f"output/{scenario.title}_{timestamp}.mp4"
    EditingDomain.render_timeline(timeline_assets, output_filename)

    print(f"Video saved to {output_filename}")

if __name__ == "__main__":
    # Load JSON
    data = load_json("example_sequence_data.json")
    create_video_from_sequence(data)
```

### 요약 및 제안

1.  **DDD 구조**: Planning(기획), Library(자재창고), Studio(제작소), Editing(편집실)로 나누어 코드를 관리하세요.
2.  **Gemini 활용**: 촬영 원본 영상들을 폴더에 넣어두면, 시스템이 알아서 "야식 먹는 뒷모습", "배 잡고 있는 모습" 등으로 태깅해두고, 기획서의 지문에 맞춰 꺼내 쓰도록 만듭니다.
3.  **FFmpeg Filter**: 확대, 흔들림 등의 Beat는 파이썬에서 FFmpeg 필터 체인(`zoompan`, `vignette`, `shake` 등)을 문자열로 조립하여 적용하는 것이 가장 효율적입니다.
