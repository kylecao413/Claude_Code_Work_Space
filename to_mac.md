# To Mac Mini — 业务逻辑 / 流程同步

**Bridge commit range**: `17d1ca0..5574669` (6 commits, 2026-04-26 → 2026-05-01)
**先做**: `git pull origin master` —— 然后从下面挑你需要的部分读 SKILL/CLAUDE 文件，不用全读 diff。

---

## 1. Outreach 流程改了：判断"发了没"必须走 IMAP audit

- **新工具**: `core_tools/bcc_inbox_audit.py` —— 直接拉 admin@ + ycao@ IMAP，输出 5-bucket 报告（已回复 / 拒绝 / 不明 / 未回复 / 草稿没发）。
- **为什么**: `send_proposals.py` 不写 work_log status，`work_log --status` 不是真相。2026-04-22 重复发邮件事故就是只信 work_log 导致的。
- **新规则**: 回答"我们给 X 发过吗 / 该 followup 谁了" → 先看 `BCC_Outreach_Tracker.md`（仓库根，single source of truth），有疑问再跑 `bcc_inbox_audit.py`，**不要**为验证而再跑一次 send 脚本。
- **每次 send/followup/reply 后**: 更新 `BCC_Outreach_Tracker.md`。

## 2. 新增 MIC（Master Inspection Contract）+ ATP 双层契约模式

- **生成器**: `generate_mic_master_contract.py`（主合同一次性签）+ `generate_atp.py`（每个项目一张 ATP，挂到已签 MIC 下）。
- **模板位置**: `Master Contract And ATP/`（不是 `Projects/`）。Article 1.1 已经写死 per-project ATP 机制。
- **Kyle 说"master proposal / contract / MIC / agreement"** → 走这套，不要去 `Projects/` 那边的旧 proposal 模板。

## 3. Plan Review 收尾包：one-shot Sheets 触发

- **入口**: `wrapup_from_sheets.py "<Google Sheet URL1>" [URL2 ...]`（preview, halt for `Y`）→ 加 `--send` 真发。
- **触发条件**: Kyle 贴 Google Sheet URL + 说 "wrap up" → 调 Drive MCP `download_file_content` → 存 JSON 到 `_drive_cache/<file_id>.json` → 跑 `wrapup_from_sheets.py`。
- 17 步 / 5 文档完整流程在 `Wrap up/CLAUDE.md` Quick Start。
- **新硬规则**（2026-04-28 1522 RIA NE 空 PDF 事故）: 任何生成的 PDF/docx 在宣布"完成"前**必须打开实物核实内容**，不能只看 stdout。

## 4. Fairfax / KCY 业务线（不在 BCC 名下）—— 重要：分清 entity

- **BCC = DC only**。**KCY Engineering Code Consulting LLC = VA/Fairfax 全部 + 其他州**。目前是 LLC，PLLC 改名 pending。
- **Fairfax peer review 输出规则**（利益冲突）: 两层产物 ——
  - 内部笔记: PRR section + 修改方案
  - 客户交付物: **只列 observation + code 引用**，**不能给 suggested correction 文字**
- **Checklists**: `Fairfax_Meeting_Prep/KCY_Peer_Review_Checklists/` —— 7 个 trade × 3 tier (a/b/c) + 县级 detail / Other Agency Coordination + 复用 deficiency-log 模板。
- **Inspection report 流程**（参考 `fill_3303_lockheed_reinspection.py` / `fill_1005_union_church_footing.py`）: fill AcroForm → chunk comments → ASCII-safe → fitz 在 "Signature:" 行盖 `E-Sig.jpg` → flatten 250 DPI → `fairfax_3pi_submit.py` 提交。
- **每个 Fairfax 项目首动作**: dump owner/permit/inspector 元数据到该项目文件夹的 `project_info.md`，不要靠脑子记、不要反复问 Kyle。

## 5. PE Multistate Expansion 结构搭好了

- **入口**: `PE_State_Applications/Multi_State_AHJ_Tracker.md`（跨州 AHJ pipeline view）。
- **目录结构**: `PE_State_Applications/{FL,NC,SC,TX}/AHJs/<jurisdiction>/{README.md, forms/, templates/}`。
- **批量下载工具**: `core_tools/download_ahj_pdfs.py`。
- 当前 blockers 仍记在 MEMORY 的 `pe_state_applications_progress.md`（Xuebin/Yu Tan/Yi Tian 地址、考试城市、DMY supervisor）。

## 6. Cold Outreach 已发批次（避免再发）

- 2026-04-27: bucket A/B + bucket D（`send_bucket_a_b_20260427.py` / `send_bucket_d_20260427.py`）
- 2026-04-28: 13 个 fresh CW 草稿全发完（`send_cw_batch_20260428.py`）
- **Touch-2 窗口**: 这 13 个是 2026-05-09；103 个 legacy Feb rows 是 2026-05-05。
- `Pending_Approval/Outbound/_archived_stale_*` + `_obsolete_already_sent_*` 三个子目录是已经处理过的 stale，**不要**回去补发或 followup。

## 7. Partners 目录（合作方，不是 cold leads）

- `Partners/` 根目录 —— 一个公司一个 markdown。架师/GC/设计师 partner contacts。
- Kyle 给新合作方时：append row 或新建文件，**不要**把 Partner 写进 cold-outreach pipeline。

## 8. Residential SFR 定价表

- `Residential_SFR/generate_residential_pricing_sheet.py` —— 住宅 SFR 报价表生成器。和商业项目走不同 fee 表，不要混。

## 9. CLAUDE.md 主要更新

- **Sender script families 表** —— 4 类 sender（cold outreach / formal proposal / followup / daily orchestrator）+ 哪些有 PDF 附件。`send_to_telegram_review.py` 名字误导，**实际是 cold outreach** 不是 review 工具。
- **Self-Review Checklist** 不再强制 ask_senior，按需判断。
- **Phase 2 dispatch 是 LIVE 状态** —— Mac 上跑业务脚本走 `core_tools/bcc-remote.sh <script.py>`，SSH 进 Windows 执行。Mac 不直接碰 cookies / sent_log / Pending_Approval 状态。

---

## 你需要做什么

1. `git pull origin master`
2. 重读 `CLAUDE.md` 和 `MEMORY.md` 索引（已更新）
3. 按需读上面引用到的 SKILL.md / CLAUDE.md 子文件
4. **Phase 2 提醒**: Mac 是 thin dispatch client，不要在 Mac 本地直接跑 `send_*.py` / scrapers / `fairfax_3pi_submit.py` —— 全部走 `bcc-remote.sh` 转发到 Windows。

---

## ⭐ 本地找不到具体项目文档时 → 去 Google Drive 看

这个仓库 (`C:\Users\Kyle Cao\DC Business\Building Code Consulting\Business Automation\`)
通过 **Google Drive for Desktop** 同步到：

```
My Drive > Computers > My Laptop > DC Business > Building Code Consulting > Business Automation
```

**Mac 上的访问方式**：
- 打开 Google Drive web (drive.google.com) 或 Drive for Desktop
- 进入 **Computers > My Laptop**（不是 My Drive 主目录）
- 浏览到上面那个路径

**什么时候用 Drive 而不是 git**：
- ✅ **具体项目相关的文件** —— `Projects/` 下的 wrap-up 包、proposal docx/PDF、scraped drawings、
  client deliverables、Fairfax 项目的 `project_info.md`、wrap-up package、签过的 MIC/ATP、
  Pending_Approval 里的具体 draft 内容等等。这些文件 **gitignore 里被排除了**（`*.docx`、
  `*.pdf`、`Projects/` 大部分内容、`Research_*.md` 等），git pull 拿不到，去 Drive 看。
- ✅ **Windows 端临时生成、还没 commit 的文件**（比如刚跑完一个 wrapup 还没整理）
- ✅ **图纸 / 截图 / 大文件**

**什么时候用 git pull 而不是 Drive**：
- ✅ **业务逻辑代码 + 流程文档** —— `*.py` 脚本、`CLAUDE.md`、`*_RULES.md`、tracker
  markdown、SKILL 定义、模板生成器。这些是 source of truth，git 是版本控制权威。
- ✅ **跨机器需要保证版本一致的东西**

**默认顺序**：
1. 先 `git pull` 拿最新代码 + 流程文档
2. 涉及具体项目文件时（"我要看 1522 RIA NE 的 wrap-up package 长啥样"），直接去
   `Drive > Computers > My Laptop > DC Business > ... > Projects/<client>/<project>/`
3. 仍然找不到的，问 Kyle 或者通过 `bcc-remote.sh` SSH 进 Windows 直接 ls

**注意**：Drive Computers 那栏对 Mac 是**只读浏览**（不会自动挂载成本地可写目录）。
要写入 Windows 端的文件，走 `bcc-remote.sh` SSH，**不要**试图通过 Drive 双向同步。

---

*生成时间: 2026-05-01 by Windows Claude. 删此文件 = 已读。*
