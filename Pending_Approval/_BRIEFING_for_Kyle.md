# BCC Outreach 全量审计 — 给 Kyle 的简报

**审计时间**:2026-04-27 (周一上午)
**数据源**:IMAP 拉 admin@ + ycao@ 自 2026-02-01 至今全部 INBOX + Sent
**总数据**:308 封 outbound 已发,244 封 inbound,自动检出 39 封 reply。

---

## 你之前的判断对了一半

我之前看 `work_log.json` + `sent_log.csv` 说"都没发",**错了**。
真相:**确实发出去了不少** —— 只是 `send_proposals.py` 没把 status 翻成 `email_sent`,导致本地追踪文件没更新。原始邮件能在 admin@ 的 Sent + ycao@ 的 INBOX (CC 副本)里找到。我已经把全部 308 封 outbound 拉出来了。

---

## 📌 立即行动 (Bucket A — 客户回复了,你没跟进)

| # | 客户 | 项目 | 最后回复 | 内容 | 建议动作 |
|---|---|---|---|---|---|
| 1 | **michael.cecchini@whiting-turner.com** | Diner Bar JW Marriott (1331 Penn Ave NW) | 2-23 | "Yes, we received your bid... hoping to have feedback from owner this week" | 隔了 2 个月没动静,**followup 问 owner decision** |
| 2 | **matt@builtwithbenchmark.com** | Insomnia Cookies & Joe & The Juice Union Station | 3-19 | "Apologize for delay, extremely busy, will get back to you" | 5 周没动静,**followup 客气提醒** |
| 3 | **seydou.tounkara@whiting-turner.com** | JW Marriott Restaurant Rebid | 2-19 | "Confirming receipt, ended up in spam" | 2 个月没动静,**followup 问 outcome** |
| 4 | **nerdelyi@pwccompanies.com** | GPO NARA 4th Floor (PWC) | 4-9 | "Received - thanks!" | 2.5 周,**followup 问进度** |
| 5 | **eric@aandeconstructionllc.com** | 3109 Oak Hill (DYRS Modular) | 4-3 | "Follow up with the proposal per our conversation. Please advise." | **欠 Eric 一个回复** —— 这个不是 cold,是 active project,Eric 在等你 |

---

## 🆕 新线索 (referral,需要 fresh outreach)

| # | 新联系人 | 来源 | 项目 |
|---|---|---|---|
| 6 | **senit.t.hailemariam@gunet.georgetown.edu** | shenelle.j.scott + basani.j.ruffin 都把我们指向她 | MedStar Georgetown Cyberknife Equipment Addition |

→ 不是 followup,是给 Senit 发**新的**冷开拓邮件,提到是 Shenelle/Basani 推荐过来的。

---

## ⏸️ 太近了暂时不动 (sent <7 天,等回复)

| 客户 | 项目 | 发送日 |
|---|---|---|
| natasha.solis@desbuild.com | US GPO QCIM Room Renovation + JBAB B94 | 4-22, 4-23 |
| sandrar@horizonretail.com | LaserAway 1427 P St | 4-22 |
| travis.boren@guardiangc.net | NHM Sanitary & Storm | 4-22 |
| jlopatin@sachse.net | Neko Health Anthem Row | 4-22 |
| jwhiting@pkwycon.com | Panda Express 1247 1st St SE | 4-23 |
| epalma@capitaltradesva.com | GPO NARA Turnkey | 4-23 |
| cmcbride@g3-contracting.com | Room Renovation 732 N Capitol | 4-23 |
| amiles@tcco.com | AIA Headquarters Renewal (Turner) | 4-23 |
| reduxllcdesigns@gmail.com | 427 Ridge St NW | 4-21 |
| ibarry@jandjconst.net | 1724 F St NW + Interior Multi-Floor | 4-14, 4-23 |

→ **建议**:5-1 之后再统一 followup 这批没回复的(给 1 周 grace period)。

---

## 📞 已发已死 (Bucket B — 客户拒了,跳过)

| 客户 | 项目 | 回复 |
|---|---|---|
| lcaudle@hickokcole.com | Former Fox 5 | "Sorry this is no longer our project" |
| pwhite@infinitybuildinginc.com | House Bar 300 Morse St | "We lost that one" |
| raymond@nixdevco.com | Deanwood Metro | "Hold contact info as we go through procurement" (软挂) |
| daryl.thomas@dc.gov | Reservation 13/Hill East Hotel | "Reach out to DOB" (政府推走) |
| john.falcicchio@dc.gov | St Elizabeths East | Auto: "no longer monitored" |
| artur.k.sivaslian@medstar.net | MedStar Urgent Care | Out of Office (2-20,陈旧) |
| shenelle.j.scott + basani.j.ruffin | MedStar Cyberknife | 都不是合适联系人 → 见上面 #6 Senit |

---

## ⏳ 已发久未回 — BC Proposal followup-eligible (Bucket E,精选 9 条)

CW cold outreach 那 113 个收件人本周已经发过 touch-2 了 (4-23 那批 "Following Up..." email),不再手动 followup。
下面只列**单次发了 BC proposal 但 ≥1 周无回复**的:

| 客户 | 项目 | 首发 | 距今 |
|---|---|---|---|
| bmiller@sachse.net | Rivian Flagship 1100 NY Ave NW | 2-20 | 9.5 周 |
| cbell@terryadamsinc.com | Rivian Flagship (同上,不同 GC?) | 2-2 | 12 周 |
| tplum@winmarconstruction.com | 3050 K St NW Floors 3 & 4 | 2-20 | 9.5 周 |
| jlauer@hbwconstruction.com | Kolmac Expansion 1025 Vermont | 2-20 | 9.5 周 |
| tliang@doyleconco.com | 2001 K St NW (EagleBank) | 3-16 | 6 周 |
| labvictor33@gmail.com + melissae@rmtax.services | 4900 Georgia Ave NW | 2-25 | 9 周 |
| agrossjr@aol.com | 1154 4th St NE + 6024 8th St NW | 3-2 | 8 周 |
| jwilliams@hbwconstruction.com | Washington Endometriosis | 3-4 | 8 周 |
| service@seiwork.com | 1425 Rhode Island Ave NW | 3-23 | 5 周 |

→ **建议**:写一批简短 followup,不重发 PDF,只问"还有 active 的 plan/project 我们可以参与吗?"

---

## 🚫 真正从来没发过的 BC Proposal 草稿 (Bucket F,**12 个**)

这些是 `Pending_Approval/Outbound/` 里的草稿,审计后**确认**没发:

| # | Draft 文件 | 草稿里写的收件人 | 草稿日期 |
|---|---|---|---|
| 1 | 1999 K St Whitebox | jjames@hbwconstruction.com | 2-20 |
| 2 | 1st and M Lobby Renovations | nerdelyi@pwccompanies.com | 2-20 |
| 3 | 5407 Georgia Ave NW Electrical Meter Separation | adeyemi05@gmail.com | 4-19 |
| 4 | 800 Connecticut Ave Lobby Renovation | jmadary@hbwconstruction.com | 2-20 |
| 5 | DuFour Center Locker Room Renovation | acolon@hbwconstruction.com | 2-20 |
| 6 | GPO Bldg B Garage Roof & Skylight Replacement | jtaylor@imecgroupllc.com | 2-20 |
| 7 | GPO FM Modernization | nerdelyi@pwccompanies.com | 2-20 |
| 8 | Garage - Washington DC | zachw@elderjones.com | 2-20 |
| 9 | HVAC Replacement 1704 19th St NW | (草稿没写收件人 — 需查 BC) | 4-8 |
| 10 | Union Station Parking Garage Generator Room Upgrade | jmadary@hbwconstruction.com | 2-20 |
| 11 | Ward 8 Senior Center | mhannon@paradigmcos.com | 2-20 |
| 12 | Washington Improv Theater | nerdelyi@pwccompanies.com | 4-9 |

⚠️ 这里有 **2 个 nerdelyi@pwccompanies.com 的旧草稿** (1st and M Lobby + GPO FM Modernization) —— 但她最近一次回复是 "Received - thanks!" 给 NARA 项目 (4-9)。她已经收到过 PWC 的 NARA proposal,如果你现在再发 1st and M Lobby + GPO FM,她会一次收到 3 个 PWC proposal 显得很乱。**建议**:把 1st and M Lobby + GPO FM 合并到一封"PWC additional opportunities"邮件里,不要分开发。

⚠️ HBW 的 4 个 (1999 K St / 800 Conn / DuFour / Union Station) 收件人分散在 jjames / jmadary / acolon —— 同一家公司不同 estimator,**每人一封**单独发(不合并,因为 estimator 之间不一定共享)。

---

## 📊 数字一览

- 308 outbound (其中 **17 BC formal proposal**,112 CW cold intro,115 followup,42 其它,22 reply/forward)
- 244 inbound
- 39 自动检出的 reply,人工分类后:
  - 5 active 需立即 followup (Bucket A)
  - 1 referral 新线索 (Senit)
  - 6 已死 (Bucket B)
  - ~10 是你 existing 项目的内部往来 (不是冷开拓回复)
  - 其它 ~17 是 receipt-only ack
- **140 个 sent + no-reply** 收件人(其中 113 是 CW cold outreach 已经在 3-touch 序列里,不需要手动 followup)
- **12 个** BC proposal 草稿确认从未发出

---

## 🛑 我现在停下来等你确认

这报告结论性比较强但**任何 send 都需要你 Y**(per CLAUDE.md 商业规则)。

请你按下面挑要我做的:

**A. 立即 followup Bucket A 的 5 个 active 客户?** (我会写 5 个简短 followup draft,你批 Y 后发)
**B. 给 senit.t.hailemariam 发 fresh intro?** (referral 来源是 Shenelle/Basani)
**C. 发 12 个从未发过的 BC proposal?** (其中 nerdelyi 那 2 个建议合并;HBW 4 个分开)
**D. 给 BC proposal 9 周以上没回复的 9 个客户写 short followup?** (不重发 PDF,只问 active 项目)
**E. 暂停 / 我先看你的 audit 文件再决定** — 全部数据在:
  - `Pending_Approval/_BRIEFING_for_Kyle.md` (本文件)
  - `Pending_Approval/_audit_report.md` (5 个 bucket 完整 308 行)
  - `Pending_Approval/_audit_data.json` (机器可读)

我建议顺序:**A → B → D → C**(先把热的 followup 发出去,新草稿压最后)。等你的指令。
