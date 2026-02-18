# Outbound — 待发开发信草稿

- `batch_run_research.py` 与 `gemini_web_automation.py` 将开发信草稿写入此目录。
- 将需发送的文件改名为 `XXX-OK.md` 后，由 `approval_monitor.py` 或 `mobile_sync_manager.py` 自动发送并移至 Sent/。
