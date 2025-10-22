# Repository Guidelines

## 專案結構與模組分工
- `hospital/` 包含 Django 設定與核心 URL/WSGI 入口，`settings/prod.py` 會依 `.env` 指定的變數載入生產參數。
- 功能依領域拆分至根目錄各 app（`patients/`、`registrations/`、`clinics/`、`administration/`、`accounts/`、`system/`）。新增功能請就近放入既有 app，或在根目錄建立新 app 後記得更新 `INSTALLED_APPS`。
- 模板集中在 `templates/`，以 app 名稱區分子資料夾；表單與 UI 調整請維持此結構。靜態資源在 `static/`，`staticfiles/` 為 `collectstatic` 輸出；上傳檔案存放於 `media/`。
- 部署腳本與環境檔住在根目錄（`Dockerfile`、`docker-compose.yml`、`.env.docker*`、`entrypoint.sh`）。`docs/` 提供操作說明，`PROGRESS.md` 與 `NEXT_STEPS.md` 記錄需求與待辦，請同步更新。

## 建置、測試與開發指令
- `python3 -m venv .venv && source .venv/bin/activate` 建立並啟用虛擬環境。
- `pip install -r requirements.txt` 安裝 Django 與執行期依賴。
- `python manage.py migrate` 套用資料庫異動；每次調整模型或設定後都需執行。
- `python manage.py runserver` 啟動開發伺服器（預設網址 `http://127.0.0.1:8000/`）。
- `docker compose build`、`docker compose up -d` 於專案根目錄建置並啟動類生產環境容器。
- 需要管理帳號或測試登入時，可使用 `python manage.py createsuperuser` 或參考 `docs/test_accounts.md` 內的測試帳號。

## 程式風格與命名慣例
- 依 PEP 8 採四格縮排；函式與變數使用 snake_case，類別採用 CamelCase。
- 較複雜的業務邏輯請封裝於 class-based views 或 `services.py` 之類的協助模組，避免堆疊在 view 函式內。
- 所有環境設定皆透過 `.env` 搭配 `os.environ` 讀取，禁止在程式碼中硬編密鑰或主機名稱。
- 模板使用 Django Template Language；共享片段放在 `templates/base.html` 或對應的 `include` 檔案中。

## 測試指引
- 採 Django 內建測試框架：`python manage.py test <app_label>`。
- 目前每個 app 以 `tests.py` 為入口；若需要拆分可建立 `tests/` 套件並在 `__init__.py` 聚合。測試函式與類別請以職責命名，如 `test_patient_flow.py`。
- 若需固定資料，請將 fixtures 放在對應 app 的 `fixtures/` 目錄並記錄於 `docs/`（例如測試帳號、排程樣本）。
- 提交前至少確保與變更相關的測試通過；若新增模組請附上涵蓋正向與邊界情境的測試。

## Commit 與 Pull Request 習慣
- Commit 訊息使用簡短命令句（例：`Tune Gunicorn defaults for 2 vCPU deployment`），必要時加上範疇前綴（如 `docs:`、`settings:`）。
- Pull Request 需概述變更、關聯議題、環境或資料庫影響，若涉及 UI 或部署流程請附上截圖或指令輸出。
- 若調整部署或 `.env` 參數，請於 PR 描述標註需要同步的環境步驟，避免遺漏設定。

## 安全與設定提醒
- Gunicorn 參數由 `GUNICORN_CMD_ARGS` 控制，正式環境請在 `.env.docker` 設定適當 worker 與 timeout。
- 更新 `.env` 前務必檢查敏感資訊，避免進入版控。部署至 EC2 時，先以 `scp` 上傳 `db.sqlite3` 再用 `sudo mv` 替換，可保留正確權限。
- EC2/Container 相關操作請參考 `docs/aws-ec2-operations.md` 與 `docs/docker-sqlite-deployment-guide.md`，確保 IP、Gunicorn worker、資料庫同步流程一致。

## AWS CLI 與 EC2 連線指南
- AWS CLI 事前需在本機設定 `~/.aws/credentials` 與 `~/.aws/config`，確保擁有 `ec2:*` 等必要權限。常用查詢指令示例：
  ```bash
  aws ec2 describe-instances --filters Name=instance-state-name,Values=running
  aws ec2 stop-instances --instance-ids i-06dc8b0e59e1a523f
  aws ec2 start-instances --instance-ids i-06dc8b0e59e1a523f
  ```
- 與 EC2 通訊一律使用私鑰 `~/.ssh/badminton-forum-osaka-key.pem`，並維持檔案權限 `chmod 600`。基本 SSH 指令：
  ```bash
  ssh -i ~/.ssh/badminton-forum-osaka-key.pem ubuntu@16.209.24.162
  ```
  若 IP 變動，請以最新綁定的 Elastic IP 或公有 DNS (`ec2-<ip>.ap-northeast-3.compute.amazonaws.com`) 取代。
- 檔案同步範例：先把本機 SQLite 備份複製到 EC2，再以 `sudo mv` 覆蓋容器掛載路徑。
  ```bash
  scp -i ~/.ssh/badminton-forum-osaka-key.pem db.sqlite3 ubuntu@16.209.24.162:~/db.sqlite3.tmp
  ssh -i ~/.ssh/badminton-forum-osaka-key.pem ubuntu@16.209.24.162 \
      "sudo mv ~/db.sqlite3.tmp /home/ubuntu/hospital-app/.docker-data/sqlite/db.sqlite3"
  ```
  執行敏感操作前後請確認容器狀態（`docker ps`、`docker compose ps`），需要時重新啟動 `docker compose up -d`。
