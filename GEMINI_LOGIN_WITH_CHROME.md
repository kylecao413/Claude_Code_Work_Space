# 用本机 Chrome 完成 Gemini 登录（避免「此浏览器可能不安全」）

Google 会拦截 Playwright 自带的 Chromium，提示「This browser or app may not be secure」。改用**你已安装的 Chrome** 并通过「远程调试」让脚本连接，即可正常登录并保存 Cookie。

---

## Cookie 失效 / 登录失败？做一次 100% 重新登录

如果 `gemini_web_automation.py` 仍被重定向到 Google 登录页，或提示 Cookie 失效：

1. **关闭所有 Chrome 窗口**（任务管理器里结束所有「Google Chrome」进程更保险）。
2. **（可选）删掉旧 Cookie**：删除项目目录下的 `.google_cookies.json`，避免混用旧状态。
3. **只开一个“干净”的 Chrome**：双击运行 `start_chrome_for_gemini_login.bat`（会以 `--remote-debugging-port=9222` 启动一个新窗口）。
4. **在这个窗口里** 打开 https://gemini.google.com ，用你的 Google 账号**完整登录**（验证码、2FA 等都做完），直到看到 Gemini 对话界面。
5. **不要关这个 Chrome 窗口**，在项目目录运行：  
   `python google_gemini_login_chrome.py`  
   看到「登录成功，Cookie 已保存」即可。
6. 之后再运行 `gemini_web_automation.py` 或 Master Proposal Pipeline Phase 3 会使用这份新 Cookie。

**重要**：每次“重新登录”都建议从步骤 1 开始（100% 新鲜 Chrome + 重新登录一次），这样保存的 Cookie 才稳定。

---

## 步骤一：用「远程调试」方式启动 Chrome

1. **先关闭所有已打开的 Chrome 窗口**（否则可能无法绑定 9222 端口；脚本会提示你关闭后再按键）。
2. 双击运行：
   ```text
   start_chrome_for_gemini_login.bat
   ```
   脚本会使用你**当前默认的 Chrome 用户资料**（`Default`）启动，所以打开的窗口通常已是你的 Gmail 登录状态。**不要在打开后点击切换成别的 Chrome 用户**——那样会关掉当前窗口、新开的窗口不再带 9222，保存 Cookie 会失败。

3. **若你常用的是另一个 Chrome 用户（例如「Profile 1」）**：先关掉所有 Chrome，在资源管理器打开 `%LOCALAPPDATA%\Google\Chrome\User Data`，看你要用的资料夹名称（如 `Default`、`Profile 1`、`Profile 2`）。在运行 bat 之前，在 CMD 里设环境变量再运行，例如：
   ```text
   set GEMINI_CHROME_PROFILE=Profile 1
   start_chrome_for_gemini_login.bat
   ```
   这样启动的就是该用户，无需在窗口里再点切换用户。

4. 此时弹出的 Chrome 窗口就是带 9222 的「你的 Chrome」，Google 不会报不安全。

---

## 步骤二：在 Chrome 里登录 Gemini

1. 在这个 Chrome 窗口里打开：**https://gemini.google.com**
2. 若跳转到 Google 登录，**照常输入账号密码、完成验证**，并停留在 Gemini 页面（不要关窗口）。

---

## 步骤三：运行登录脚本保存 Cookie

在项目目录下执行：

```text
python google_gemini_login_chrome.py
```

脚本会：

- 连接本机 `localhost:9222` 的 Chrome
- 若当前页不是 Gemini，会自动打开 Gemini 页面
- 检测到你已在 Gemini 页面后，把登录状态保存到 **`.google_cookies.json`**

看到「登录成功，Cookie 已保存」后即可关闭该 Chrome 或继续使用；之后运行 `gemini_web_automation.py` 会使用这份 Cookie，无需再登录。

---

## 若 9222 被占用

若提示 9222 连接失败，可能是上次的 Chrome 还没关干净。可：

- 在任务管理器中结束所有「Google Chrome」进程后，重新运行 `start_chrome_for_gemini_login.bat`；或  
- 换一个端口，例如 `--remote-debugging-port=9223`，并把脚本里的 `CDP_URL` 改为 `http://localhost:9223`。
