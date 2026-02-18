# 在 Google Drive「我的云端硬盘」里看到 Pending_Approval

当前 **Pending_Approval** 在项目本地目录，所以你在手机 Google Drive App 的「我的云端硬盘」里看不到。

## 做法：把审批目录放到 Google Drive

1. **在电脑上确认 Google Drive 同步文件夹路径**  
   使用「Google 云端硬盘」桌面版时，通常会同步一个本地文件夹到「我的云端硬盘」，例如：
   - `C:\Users\你的用户名\Google Drive\My Drive`
   - 或 `C:\Users\你的用户名\My Drive`
   - 或在安装时你自选的路径

2. **在该路径下建一个子文件夹**  
   例如在「我的云端硬盘」里新建文件夹：**Pending_Approval**。  
   对应到本机可能是：  
   `C:\Users\Kyle Cao\Google Drive\My Drive\Pending_Approval`

3. **在项目 .env 里指定这个路径**  
   打开项目根目录的 `.env`，找到并**取消注释**、改成你的实际路径：
   ```env
   PENDING_APPROVAL_DIR=C:\Users\Kyle Cao\Google Drive\My Drive\Pending_Approval
   ```
   路径不要用引号，且必须是**已经和「我的云端硬盘」同步**的那个本地路径。

4. **保存 .env 后**  
   - 之后 `batch_run_research.py`、`gemini_web_automation.py` 会把草稿写到该目录；  
   - `approval_monitor.py` 会扫描该目录里的 `*-OK.md` 并发送、移到 **Sent**。  
   手机打开 Google Drive → 我的云端硬盘 → **Pending_Approval**，就能看到草稿；把要发的改成 `XXX-OK.md` 即可触发发送（电脑上的 approval_monitor 需在运行）。

## 若没有安装 Google Drive 桌面版

先在电脑上安装并登录 [Google 云端硬盘](https://www.google.com/drive/download/)，把「我的云端硬盘」同步到一个本地文件夹，再按上面步骤把 `PENDING_APPROVAL_DIR` 指到该文件夹下的 `Pending_Approval`。
