# 雨课堂接口抓包与对接指南

采集层是**配置驱动**的：抓到接口后，把地址、请求头、字段映射填进 Web UI 的「鉴权与接口」区即可，无需改代码。

## 一、准备工具

- 一台电脑 + 一部安卓手机（同一 WiFi），或 PC 版微信
- **mitmproxy**（免费开源，跨平台）：`pip install mitmproxy`
- 手机安装 CA 证书（mitmproxy 启动后访问 `http://mitm.it` 下载）

> iOS 需在「设置 → 通用 → 关于本机 → 证书信任设置」里手动信任描述文件。

## 二、抓包步骤

1. 电脑启动代理：`mitmweb --listen-port 8080`，浏览器打开 `http://127.0.0.1:8081` 看实时请求。
2. 手机 WiFi 代理设为 `电脑IP:8080`，装好并信任 CA 证书。
3. 手机打开微信 → 雨课堂小程序 → 进入某个课程。
4. 在 mitmweb 里过滤 `yuketang` 或 `icourse` 等关键字，逐个点击请求查看。
5. 分别操作「作业列表 / 习题列表 / 讨论列表」，记录三类请求的：
   - **完整 URL**（含路径，域名即 base_url）
   - **HTTP 方法**（GET / POST）
   - **请求头**（重点：Cookie、Authorization、token、X-Requested-With）
   - **POST Body**（若有，注意动态参数）
   - **响应 JSON 结构**（内容列表在哪个字段下，每条的 id/title/course 等字段名）

## 三、定位登录态

- 常见形式：`Authorization: Bearer xxx`、请求头 `token`、Cookie 里的 `sessionid`。
- 观察 token 是否出现在 URL 参数或 body 中。
- 在 UI 的「Token」框里填入；请求头模板里用 `{{token}}` 占位符引用它（程序会自动替换）。

## 四、填入配置

1. 打开 Web UI → 「鉴权与接口」。
2. **采集模式**选 `HTTP（抓包后填）`。
3. **Base URL** 填域名部分，如 `https://api.yuketang.example`。
4. **请求头 JSON** 填抓到的头，例如：
   ```json
   {"Cookie": "sessionid={{token}}", "User-Agent": "Mozilla/5.0"}
   ```
5. **接口路径 JSON**，例如：
   ```json
   {"homework": "/api/homework/list", "exercise": "/api/exercise/list", "discussion": "/api/discussion/list"}
   ```
6. **列表路径**填内容数组在响应里的位置，如 `data.list`（表示 `response.data.list`）。
7. **字段映射 JSON** 把平台字段映射到统一模型：
   ```json
   {"id": "id", "title": "title", "course": "courseName", "publisher": "teacher", "published_at": "createTime", "url": "detailUrl", "preview": "content"}
   ```
   左边是程序字段名（不要改），右边是平台实际字段名（照抓包结果填），支持 `a.b` 点号取值。
8. 点「保存并生效」，先观察「运行日志」是否有报错，再等一条新内容验证通知。

## 五、常见问题

- **拉取为空**：检查列表路径与字段映射；先看原始响应 JSON 确认结构。
- **401/403**：token 过期或请求头不对，重新抓一次登录态。
- **频率过快被限流**：把频率调到 30s 以上，或启用指数退避（默认开）。
- **接口变了**：小程序更新后重新抓包，只改配置里的路径/字段映射即可。

## 六、合规提示

本项目仅用于个人学习与技术验证。请自行评估目标平台的使用条款与数据获取方式，控制请求频率，避免对服务造成负担。
