# 下一次對話重要線索

## 專案現況摘要
- 引擎：Django 5.2，虛擬環境在 `.venv/`，主要命令 `./.venv/bin/python manage.py <cmd>`。
- 資料庫目前使用 SQLite（`db.sqlite3`），設定集中在 `hospital/settings/`。
- 已完成病患端需求 A1–A13（註冊、登入、查詢班表、預約/取消、家屬管理、看診進度、個資與密碼修改）。
- 櫃檯（B14–B20）、醫師（C21–C24）、管理員前端（D25–D30）、系統自動化（E31–E34）尚待開發。
- `PROGRESS.md` 已完整列出 34 個事件的觸發器/活動/回應與完成狀態，可快速對照進度。

## 待處理優先事項（建議）
1. **櫃檯端**：現場掛號、病歷建立、報到與門診狀態查詢（B14–B20）。
2. **醫師端**：叫號、看診進度控制、門診狀態（C21–C24）。
3. **管理員前端**：醫師/班表/科別維護、公告與統計報表（D25–D30）。
4. **系統作業**：提醒通知、開放掛號、每日報表、資料備份（E31–E34）。

## 重要路徑／檔案
- 病患相關：`patients/views.py`、`patients/forms.py`、`patients/urls.py`、`templates/patients/*.html`
- 帳號管理：`accounts/forms.py`、`accounts/views.py`、`accounts/urls.py`
- 掛號模型與表單：`registrations/models.py`、`registrations/forms.py`
- 進度文件：`PROGRESS.md`
- 下一步檔案（本文件）：`NEXT_STEPS.md`

## 其他小提醒
- 在終端機內跑指令前記得 `source .venv/bin/activate` 或直接使用 `./.venv/bin/python`。
- 開發伺服器指令：`./manage.py runserver 0.0.0.0:8000`
- 若需遷移：`./manage.py makemigrations`、`./manage.py migrate`

此文件可在下次對話時引用，確保上下文對齊。
