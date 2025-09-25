# Pydantic AI & LangGraph 기반 Text-to-SQL 에이전트

## 🚀 Windows 환경을 위한 Quick Start

이 가이드는 Windows 환경에서 프로젝트를 클론한 후 바로 실행할 수 있도록 필수적인 설정 단계를 안내합니다.

### 사전 준비
- **Docker Desktop for Windows**: [Docker Desktop](https://www.docker.com/products/docker-desktop/)이 설치되어 있어야 합니다.
- **Python 3.12 이상**: Python이 설치되어 있고, Path에 추가되어 있어야 합니다.

---

### 1. Docker로 PostgreSQL 실행하기

프로젝트는 `docker-compose.yml` 파일을 사용하여 PostgreSQL 데이터베이스를 실행합니다.

1.  **PowerShell 또는 명령 프롬프트(CMD)를 엽니다.**
2.  프로젝트의 루트 디렉토리에서 다음 명령어를 실행하여 Docker 컨테이너를 백그라운드에서 시작합니다.

    ```bash
    docker-compose up -d
    ```
    이 명령어는 `text-to-sql-db`라는 이름의 PostgreSQL 데이터베이스를 생성하고 실행합니다.

---

### 2. 환경 변수 및 의존성 설치

Python 가상 환경을 설정하고 `uv`를 사용하여 필요한 라이브러리를 설치합니다.

1.  **`.env` 파일 생성**
    프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 아래 내용을 추가합니다. 이 파일은 데이터베이스 연결 정보와 OpenAI API 키를 관리합니다.

    ```env
    # .env
    DATABASE_URL="postgresql+asyncpg://myuser:mypassword@localhost:5432/text2sql"
    OPENAI_API_KEY="sk-..."
    ```
    *`sk-...` 부분에 자신의 OpenAI API 키를 입력하세요.*

2.  **`uv`로 라이브러리 설치**
    `uv`는 빠른 Python 패키지 설치 도구입니다.

    ```bash
    # 1. uv 설치 (아직 설치하지 않은 경우)
    pip install uv

    # 2. 가상 환경 생성
    uv venv

    # 3. 가상 환경 활성화
    .venv\Scripts\activate

    # 4. pyproject.toml에 명시된 라이브러리 설치
    uv sync
    ```

---

### 3. FastAPI 서버 실행 및 테스트

이제 FastAPI 개발 서버를 실행하고 Swagger UI를 통해 에이전트를 테스트합니다.

1.  **FastAPI 서버 실행**
    가상 환경이 활성화된 터미널에서 다음 명령어를 실행합니다.

    ```bash
    fastapi dev
    ```
    서버가 `http://127.0.0.1:8000`에서 실행됩니다.

2.  **Swagger UI로 테스트하기**
    웹 브라우저를 열고 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)로 이동합니다.

    **a. 데이터베이스 초기화**
    - `/admin/setup-db` 엔드포인트를 찾습니다.
    - `Try it out` 버튼을 클릭합니다.
    - `Execute` 버튼을 눌러 데이터베이스 테이블과 초기 데이터를 생성합니다.
    - "Database setup complete." 메시지를 확인합니다.

    **b. 에이전트 테스트**
    - `/agent/invoke` 엔드포인트를 찾습니다.
    - `Try it out` 버튼을 클릭합니다.
    - **Request body**에 테스트할 질문을 JSON 형식으로 입력합니다.
      ```json
      {
        "question": "마케팅 부서 매니저는 누구인가요?"
      }
      ```
    - `Execute` 버튼을 눌러 에이전트를 실행합니다.
    - **Response body**에서 에이전트의 답변을 확인합니다.
