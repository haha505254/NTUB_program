# EC2 快速部署 Docker 版 Hospital 專案（新手模式）

這份筆記一步一步帶你把專案搬到 AWS EC2 上，保持 SQLite 不變。

---

## 0. 事前準備

1. 有 AWS 帳號並建立一把 SSH 私鑰（`.pem`）。
2. 在 AWS Console 建立 EC2：建議 Ubuntu 22.04、t3.small、開放 22 與 80 埠。
3. 取得 EC2 公網 IP 或綁定 Elastic IP。

---

## 1. 連到 EC2

```bash
ssh -i /path/to/your-key.pem ubuntu@<EC2 公網 IP>
```

---

## 2. 安裝 Docker

複製貼上以下指令（每段一起貼）：

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

把自己加入 docker 群組，然後登出再登入一次：

```bash
sudo usermod -aG docker $USER
exit
# 重新 ssh 進來
```

---

## 3. 抓專案

```bash
git clone https://github.com/haha505254/NTUB_program.git hospital-app
cd hospital-app
```

（若是私有倉庫，請改用 SSH URL 或設定權限。）

---

## 4. 設定環境檔

```bash
cp .env.docker.example .env.docker
nano .env.docker
```

在編輯器裡至少做這些事：

- 把 `DJANGO_SECRET_KEY=replace-me` 改成任意長串密碼。
- 預設 `DJANGO_ALLOWED_HOSTS=*`，若想限制來源就改成逗號分隔的 IP / 網域（例如 `DJANGO_ALLOWED_HOSTS=<EC2-IP>,localhost`）。
- 如有自己的網域可一併加入。
- 存檔離開（在 nano 裡是 `Ctrl+O`、`Enter`、`Ctrl+X`）。

---

## 5. 建立持久化資料夾

```bash
mkdir -p .docker-data/sqlite media staticfiles
```

若本地有舊的 `db.sqlite3` 想帶上來：

```bash
scp -i /path/to/your-key.pem /local/path/db.sqlite3 ubuntu@<EC2 公網 IP>:~/hospital-app/.docker-data/sqlite/db.sqlite3
```

沒有也沒關係，容器會自動建立空資料庫。

---

## 6. 啟動 Docker

```bash
docker compose build
docker compose up -d
```

第一次執行會自動跑 database migrate、collectstatic。

---

## 7. 確認運作

- 即時看 log：`docker compose logs -f`
- 瀏覽器打開 `http://<EC2 公網 IP>/`
- 想建立超級使用者：

  ```bash
  docker compose exec web python manage.py createsuperuser
  ```

---

## 8. 常用指令

| 動作             | 指令                               |
| ---------------- | ---------------------------------- |
| 停止服務         | `docker compose stop`              |
| 重新啟動         | `docker compose start`             |
| 重建後啟動       | `docker compose build && docker compose up -d` |
| 完全關掉（保留資料） | `docker compose down`                |
| 完全關掉（刪資料）   | `docker compose down -v`             |

---

## 9. 下一步（想更進階可以再做）

- 設定 Nginx 或 ALB，讓對外網址改成 80/443，避免直接暴露 8000。
- `.env.docker` 預設使用 `hospital.settings.prod`，範例檔預先寫入 `DJANGO_SECURE_SSL_REDIRECT=0`、`DJANGO_SECURE_HSTS_SECONDS=0` 方便測試；要上線前請刪除或改回預設（`1`、`31536000`），或改用前置代理提供 HTTPS。
- 使用 `tar` 備份 `.docker-data/sqlite` 與 `media`。
- 搭配 `systemd` 或 CI/CD 自動部署。

---

照著做就能在 EC2 上跑起 Docker 版的 Hospital 專案，有任何卡關把指令與錯誤訊息帶給我，我會協助排查。祝部署順利！
