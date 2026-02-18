# Pending_Approval — 待你审批后发送的邮件草稿

- Agent 将待发邮件草稿写入本目录，例如 `Pending_Approval/Carr_Properties.md`。
- **审批方式（二选一）**：
  1. 在文件名末尾加 `-OK`（如 `Carr_Properties-OK.md`），或  
  2. 在文件正文末尾新增一行：`APPROVED`
- 若项目同步到 Google Drive，可在手机端修改文件名或添加 `APPROVED`，Agent 检测到后再执行发送。
- 发送前 Agent 必须提示：请先审阅 `drafts/xxx.md` 或 `Pending_Approval/xxx.md`，确认后输入 `Y` 或说「Proceed with sending」再实际发送。
