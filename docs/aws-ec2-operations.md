# AWS 操作筆記（白話版）

這份記錄整理我剛才幫你在 AWS 上所做的事情，並說明相關的憑證放在哪裡、怎麼保管，以及後續要連線或節省費用時可以怎麼做。

## 我做了哪些事

- 用 `aws-cli` 查詢你帳號（IAM 使用者 `claude-temp-deploy`）的身分確認我有權限操作。
- 確認預設區域是大阪（`ap-northeast-3`），看到目前只有一台 EC2（`i-06dc8b0e59e1a523f`）。
- 啟動這台停著的機器，等它變成 `running`，再讀取詳細資訊：Public IP `16.209.24.162`、Public DNS `ec2-16-209-24-162.ap-northeast-3.compute.amazonaws.com`、使用的 key pair 叫 `badminton-forum-osaka-key`。
- 重新分配新的 Elastic IP（`16.209.24.162`）並綁定這台機器，再釋放舊的 `15.168.229.18` 以免閒置計費。
- 檢查安全群組 `badminton-forum-sg`，確認 22/80/443 等常見埠都有對外開啟。
- 在你主機的 `~/.ssh` 看到同名的私鑰 `badminton-forum-osaka-key.pem`，權限正確（600），推定就是這台 EC2 用的鑰匙。
- 試著用 `ec2-user` SSH 上去，收到 `Permission denied` 後改用 `ubuntu`，成功連上並輸出 `ok`。
- 嘗試透過 AWS Pricing 與 Cost Explorer API 查費用，但因為 IAM 權限沒有開放 `pricing:GetProducts`、`ce:GetCostAndUsage`，所以只能提供公開價與概略估算。

## 目前這台機器的狀態與費用

- 機器狀態：`running`，型號 `c5.large`。
- 只要開機，每小時大約 0.12 美元（大阪區按需價）。
- 附掛了一顆 30 GiB 的 `gp3` 磁碟，就算機器關機仍會計費，約 3.6 美元一個月。
- 如果暫時不用，記得執行 `aws ec2 stop-instances --instance-ids i-06dc8b0e59e1a523f` 把它關掉。

## 私鑰、公鑰與其他憑證在哪

- AWS Access Key（CLI 用的）放在 `~/.aws/credentials`，區域等設定在 `~/.aws/config`。我沒有顯示內容，只是讓 CLI 自動讀取。
- EC2 的私鑰在 `~/.ssh/badminton-forum-osaka-key.pem`，權限是 600，只有你這台機器看得到。
- 如果你需要公鑰，在需要時再自己導出：
  ```bash
  ssh-keygen -y -f ~/.ssh/badminton-forum-osaka-key.pem > ~/.ssh/badminton-forum-osaka-key.pub
  chmod 600 ~/.ssh/badminton-forum-osaka-key.pub
  ```
  AWS 端已經保存了這把公鑰，所以不急著生成檔案也沒關係。

## 這台電腦上的其他憑證與設定檔

- `~/.ssh/id_rsa`、`~/.ssh/id_rsa.pub`：可能是你或 Git 服務的 SSH 登入用鑰匙；同樣 600 權限保護。
- `~/.ssh/my-ec2-key.pem`：另一把 EC2 私鑰，推測對應不同 key pair；建議確認是否仍需要。
- `~/.ssh/config`：SSH 主機設定檔，可能自動指定主機別名或使用的私鑰。
- `~/.ssh/known_hosts`、`known_hosts.old`：SSH 指紋記錄，不是憑證，但代表你曾連過的遠端主機。
- `~/.gitconfig`：Git 全域設定（包含 user.name、user.email 以及 credential.helper=store）。
- `~/.git-credentials`：存放 Git HTTPS 登入資訊（通常是 GitHub Personal Access Token）；因為 helper=store，內容是純文字，必要時請改用更安全的憑證管理方式。
- `/home/one123/projects/badminton-forum/.env`：環境變數檔，通常包含 API Key、資料庫密碼等敏感資訊。

## 連線方式（以 Ubuntu 映像為例）

```bash
ssh -i ~/.ssh/badminton-forum-osaka-key.pem \
    ubuntu@ec2-16-209-24-162.ap-northeast-3.compute.amazonaws.com
```

第一次連線如果詢問指紋，加入 `-o StrictHostKeyChecking=accept-new` 可以自動接受。

## 憑證與安全的保管建議

1. 只在可信任的主機保存 `~/.aws` 和 `~/.ssh`，並保持 600 權限。
2. 不要把 Access Key、Secret Key 或私鑰放到版本控制、聊天或公開文件裡；必要時用密碼管理工具或 AWS Secrets Manager。
3. 定期輪換 Access Key，開啟 MFA，移除不需要的 IAM 使用者或權限。
4. 私鑰請備份在安全位置（加密硬碟、密碼管理器）。遺失時就要在 AWS 重新建立 key pair，再把新的公鑰掛到 EC2。
5. 想查精確費用需要額外 IAM 權限（`pricing:GetProducts`、`ce:GetCostAndUsage`）；若要開啟，請在 IAM 調整或讓擁有權限的人執行。

## 換到新電腦時怎麼重新申請或轉移

- **AWS CLI Access Key**  
  1. 在 AWS IAM 重新產生 Access Key（舊的如果不再使用記得停用）。  
  2. 在新電腦安裝 AWS CLI 後執行 `aws configure`（官方文件也建議這樣做），輸入 Access Key、Secret Key、預設區域與輸出格式；或照官方做法使用環境變數/自訂檔案路徑。  
  3. 若有多個 profile，也要將 `~/.aws/config` 中的設定一併複製或重新寫入。

- **EC2 Key Pair (`badminton-forum-osaka-key.pem`、`my-ec2-key.pem`)**  
  - AWS 只在建立 key pair 當下提供私鑰下載，無法再次下載；所以要從舊電腦複製 `.pem` 到新電腦（保持 600 權限）。  
  - 如果遺失，就得回 AWS 建立新的 key pair，並在 EC2 上更新 authorized_keys（可透過 Systems Manager、開機 ISO 或 AMI 重建等方式）。  
  - 搬到新電腦後，記得測試 `ssh -i <pem> ubuntu@...` 確認連線無誤。

- **個人 SSH 金鑰 (`id_rsa`)**  
  - 若這把鑰匙綁定 GitHub/GitLab 等服務，可直接複製到新電腦，或照 OpenSSH 的流程重新產生：  
    ```bash
    ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
    ```  
  - 把新產生的公鑰貼回 Git 平台的 SSH Keys 設定，舊的不用時記得移除。

- **Git HTTPS 登入（`~/.git-credentials`）**  
  - 因為採用 credential store，裡面通常是 `https://<token>@github.com` 這種純文字，換電腦時建議直接在 GitHub 重新建立 Personal Access Token，再 `git config --global credential.helper store` + `git credential-store --file ~/.git-credentials store` 寫入。  
  - 如果想要更安全，可改用 Git Credential Manager 或 GitHub CLI（`gh auth login`）來管理憑證。

- **專案 `.env`**  
  - `.env` 裡的內容 AWS 並不會替你重建；需要自己保存或在新環境手動輸入。  
  - 若 `.env` 來自 Secrets Manager、Parameter Store 等服務，可在新電腦重新下載；否則請另外備份。

## 後續如果要關機

```bash
aws ec2 stop-instances --instance-ids i-06dc8b0e59e1a523f
```

這會停止計算資源，僅保留磁碟費用。若長時間不用，也可以考慮釋放 EBS 或將 AMI/快照備份後刪除磁碟以節省成本。
