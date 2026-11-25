# yuketang-watcher

监测微信小程序「雨课堂」里的**作业 / 习题 / 讨论**，一有新内容就通过可配置渠道（邮箱 / 钉钉 / Telegram / 自定义 Webhook）通知你。带本地 Web UI，可开关、调频率、设时段、换渠道、看通知历史。

> 本项目为个人学习用途的技术骨架。雨课堂接口非公开，采集层为**配置驱动**：抓包后把接口填进设置页即可工作；未抓包时可用内置 Mock 采集器完整体验功能。

## 特性

- 双进程：Guardian（常驻 Web UI + 进程管理） / Watcher（可开关的业务进程）
- 三类内容全覆盖，SQLite 唯一 ID 去重，不漏不重
- 频率完全自定义（秒），附 10/30/100s 预设
- 可添加**多个自定义时间窗口**（含星期选择）+ 时段预设
- 渠道可增删，预设 + 全自定义配置，每个渠道独立「发送测试」
- 配置草稿 → 保存并生效，**热更新不重启**
- 勿扰总开关、上次送达时间、**通知历史筛选查询**、运行日志
- 异常指数退避 + 随机抖动，降低风控风险

## 快速开始

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e .
cp .env.example .env

# 启动守护进程（含 Web UI）
python -m yuketang_watch.guardian
```

浏览器打开 `http://127.0.0.1:8765`。首次进入在「接口设置」里启用 Mock 采集器，即可看到完整流程；真实使用请先读 [docs/reverse-engineering.md](docs/reverse-engineering.md) 抓包并填入接口。

## 常用命令

```bash
python -m yuketang_watch.guardian            # 启动 Web UI + 守护
python -m yuketang_watch.watcher             # 单独运行业务进程（调试）
python -m yuketang_watch.guardian --status   # 查看守护状态
pytest -q                                    # 跑测试（Mock，不需真实账号）
```

## 安全

- `.env`、`*.db`、token、授权码均已 `.gitignore`，**不会进仓库**
- README 与示例只含占位符
- 服务默认只监听 `127.0.0.1`；如需局域网访问，改 `HOST=0.0.0.0` 并自行做好网络安全

## 文档

- [DESIGN.md](DESIGN.md) — 完整设计稿
- [docs/reverse-engineering.md](docs/reverse-engineering.md) — 抓包与接口对接指南
