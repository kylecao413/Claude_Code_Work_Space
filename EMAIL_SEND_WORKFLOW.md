# 邮件发送流程（避免误发 + 反垃圾）

## 1. 正式发送（Green Light）

当你检查过草稿（如 `Carr_Outreach_Draft.md` 或 `drafts/email_1.md`）无误后，在 Composer 中对 Agent 说：

**「Proceed with sending. 请使用 admin@buildingcodeconsulting.com 发送，并按规则抄送和记录。」**

- Agent 将使用 admin@ 发送，抄送 ycao@buildingcodeconsulting.com。
- **不再在正文末尾添加签名**（两账号已自动带签名）。

## 2. Agent 发送前必须做的

- 在终端或回复中明确写出：  
  **Email content ready for [Contact Name]. Please review '[path/to/draft].md' and type 'Y' to send.**
- 未经你回复「Proceed with sending」或「Y」，不得调用发送接口/脚本。

## 3. 主题与反垃圾

- 每封邮件**主题尽量不同**，避免成批使用 "Bid Inquiry - [Project Name]" 等雷同主题。
- 正文中**鼓励对方回复**（例如邀请简短通话、索要 bid link），回复能显著降低被判为垃圾邮件的概率。

## 4. 草稿存放位置

- 单封重要邮件：`Carr_Outreach_Draft.md` 等放在项目根目录或 `drafts/`。
- 批量待审：`Pending_Approval/[Project_Name].md`；审批通过（文件名加 `-OK` 或正文加 `APPROVED`）后再发送。
