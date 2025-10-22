# Docker 部署指南（使用 SQLite）

專案已包含容器化所需的檔案，並維持原本的 SQLite。此指南說明如何準備環境、啟動服務與保存資料。相關做法參考 Docker 官方文件（`/docker/docs`）。

## 快速開始（給第一次玩的你）

1. 建立環境檔：  
   ```bash
   cp .env.docker.example .env.docker
   ```  
   打開 `.env.docker`，把 `DJANGO_SECRET_KEY=replace-me` 換成隨機密碼（可以亂打一串長字串）。

2. 建資料夾（存 SQLite 與上傳檔案）：  
   ```bash
   mkdir -p .docker-data/sqlite media staticfiles
   ```  
   有舊的 `db.sqlite3` 要沿用就複製到 `.docker-data/sqlite/db.sqlite3`。

3. 第一次建置並啟動：  
   ```bash
   docker compose build
   docker compose up -d
   ```  
   會自動跑 migrate 和 collectstatic。

4. 檢查：  
   ```bash
   docker compose logs -f
   ```  
   無錯誤的話瀏覽器開 `http://localhost/`。

5. 要建管理者：  
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

6. 常用指令：  
   - 停：`docker compose stop`  
   - 啟：`docker compose start`  
   - 完全關：`docker compose down`  
   - 看 log：`docker compose logs -f`

## 1. 專案提供的檔案總覽

- `Dockerfile`：以 `python:3.12-slim` 建立虛擬環境、安裝 `requirements.txt`，並使用 Gunicorn 啟動 Django。
- `entrypoint.sh`：在容器啟動時自動執行 `migrate` 與 `collectstatic`，並確保 SQLite 目錄存在。
- `docker-compose.yml`：啟動單一 `web` 服務，將 SQLite、靜態與媒體檔掛載至主機。
- `.env.docker.example`：範例環境變數，包含 `DJANGO_DB_SQLITE_PATH=/app/data/db.sqlite3` 等設定。
- `.dockerignore`：排除 `.git`、臨時檔、資料輸出等，縮小建置內容。

## 2. 事前準備

1. 複製環境檔並填入值：
   ```bash
   cp .env.docker.example .env.docker
   ```
  - `DJANGO_SETTINGS_MODULE` 預設為 `hospital.settings.prod`（啟用強制 HTTPS 與安全設定）。範例檔同時預先加入 `DJANGO_SECURE_SSL_REDIRECT=0`、`DJANGO_SECURE_HSTS_SECONDS=0` 方便短期以 HTTP 測試；上線前請刪除或改回預設（`1` 與 `31536000`），或改用 `DJANGO_SETTINGS_MODULE=hospital.settings.prod` 搭配前置代理提供 HTTPS。
   - `DJANGO_SECRET_KEY` 請自行替換。
   - 預設 `DJANGO_ALLOWED_HOSTS=*`，方便 demo；若要鎖定來源請改成逗號分隔的網域或 IP。
   - `DJANGO_DB_SQLITE_PATH` 亦可改為其他路徑。

2. 建立資料夾並放入 SQLite 假資料（若已有本機 `db.sqlite3` 可直接複製）：
   ```bash
   mkdir -p .docker-data/sqlite
   cp /path/to/your/db.sqlite3 .docker-data/sqlite/db.sqlite3  # 無檔案則略過
   mkdir -p media staticfiles
   ```
   SQLite 位置會透過環境變數掛載到 `/app/data/db.sqlite3`，並由 `entrypoint.sh` 自動建立資料庫。

3. 確認 `requirements.txt` 與 `hospital/settings/base.py` 已包含 Whitenoise，靜態檔可由 Gunicorn 直接服務。

## 3. 建置與啟動

```bash
docker compose build
docker compose up -d
```

首次啟動步驟：
- `entrypoint.sh` 會在 `/app/data` 建立資料夾（若不存在），然後執行 `python manage.py migrate --noinput`。
- 接著執行 `python manage.py collectstatic --noinput`，輸出至主機的 `./staticfiles`。
- 最後以 `gunicorn hospital.wsgi:application --bind 0.0.0.0:8000` 啟動服務。

瀏覽器開啟 `http://localhost/` 即可看到系統畫面。若需要改回其它埠號，可調整 `docker-compose.yml` 的 `ports` 對應（例如 `8000:8000`）。

## 4. 常用指令

```bash
# 即時查看 log
docker compose logs -f

# 進入容器執行管理指令
docker compose exec web python manage.py createsuperuser

# 停止 / 啟動 / 移除容器
docker compose stop
docker compose start
docker compose down              # 保留資料
docker compose down -v           # 連資料夾一起刪除
```

若要重新建置 image（例如更新程式碼或套件）：

```bash
docker compose build --no-cache
docker compose up -d
```

## 5. 資料與靜態檔持久化

- `.docker-data/sqlite`：掛載到容器 `/app/data`，保存 `db.sqlite3`。如需自動帶入假資料，啟動前將檔案置於此資料夾即可。
- `media/`：掛載到 `/app/media`，保存使用者上傳內容。
- `staticfiles/`：`collectstatic` 輸出目錄，可上傳至 CDN 或反向代理服務靜態檔。

備份方式：
```bash
tar czf backup-sqlite.tgz -C .docker-data/sqlite db.sqlite3
tar czf backup-media.tgz media
```

## 6. 其他注意事項

- 若在純 HTTP 或局域網測試，可使用範例檔預設的 `DJANGO_SECURE_SSL_REDIRECT=0` 與 `DJANGO_SECURE_HSTS_SECONDS=0`。要改回正式環境時，請刪除這兩行（或分別設為 `1`、`31536000`）並重新啟動服務，確保流量強制走 HTTPS 和 HSTS。
- 若要載入 fixtures，可於啟動後執行：
  ```bash
  docker compose exec web python manage.py loaddata fixtures/seed.json
  ```
- 若 `collectstatic` 失敗，請確認 `static/` 中有資源，或刪除舊的 `staticfiles/` 後重試。

依照上述流程即可在 Docker 中維持 SQLite 的同時部署 Hospital 專案，並保留既有假資料與媒體檔。

## 7. 常見問題

- **容器找不到 db.sqlite3**：確保 Volume 已掛載，或先 `docker compose run --rm web python manage.py migrate` 生成 DB，再 `docker compose up`。
- **收不到靜態檔**：請執行 `collectstatic`，並確認 WhiteNoise 已啟用；若使用瀏覽器快取，可 `docker compose exec web python manage.py collectstatic --noinput` 後重啟容器。
- **檔案上傳失敗**：確認 `/app/media` 具寫入權限（Volume 預設可寫），並於 Compose 使用具備 persistent storage 的 Volume。
- **權限問題**：若在非 root 主機以 bind mount 寫入，需要在 Dockerfile 建立非 root user（可另行新增 `RUN useradd -m appuser && chown -R appuser:appuser /app` + `USER appuser`）。

依此指南即可在保留 SQLite 的前提下容器化 Hospital 專案，快速於任何支援 Docker 的環境（EC2、VM、Bare-metal）部署並維持資料持久性。若日後想改用 Postgres，只需在 Compose 增加資料庫服務、調整設定即可。
