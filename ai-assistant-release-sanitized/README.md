# ai-assistant-release: ai-assistant-widget + ai-assistant-demo-app

这是一个本地打包的发行包，包含一个独立的 ai-assistant-widget 组件库和一个演示应用 ai-assistant-demo-app，便于直接复制给其他人使用和集成。

目录结构概览
- ai-assistant-release/
  - ai-assistant-widget/
    - package.json
    - tsconfig.json
    - src/
      - index.ts
      - AiAssistantWidget.tsx
      - api.ts
      - types.ts
  - ai-assistant-demo-app/
    - package.json
    - index.html
    - src/
      - main.jsx
  - build_and_run.sh  # 本地打包与启动脚本
  - README.md         # 当前文档
  - ai-assistant-demo-app/README.md
  - ai-assistant-widget/README.md

一、目标与使用场景
- 将 ai-assistant 页面打包成一个可复用的 React 组件库 ai-assistant-widget，方便嵌入到任意现有应用中。
- 提供一个简单的演示应用 ai-assistant-demo-app，帮助新同事快速接入和验证。
- 保留后端接口不变，组件通过后端 API 进行交互。

二、准备条件
- 本地环境：Node.js（推荐 16+）、npm/yarn/pnpm
- 需要将 release 包复制到目标机器即可本地运行和演示

三、快速使用指南
1) 复制 release 包到目标机器，如：/opt/ai-assistant-release
2) 运行打包与演示（确保可执行权限）
   
   bash ai-assistant-release/build_and_run.sh
   说明：该脚本依次构建 widget、安装 demo-app 依赖并启动演示服务。
3) 产物与端口
   - Widget 构建产物：ai-assistant-widget/dist/
   - 演示服务：默认 http://localhost:5173（若端口被占用，请修改演示应用配置）
4) 集成到宿主应用
   - 在宿主应用中通过 npm 或本地路径引入 ai-assistant-widget，传入 apiBaseUrl 等必要 props
   - 参考 ai-assistant-widget/src/types.ts 定义的 Prop 接口

四、Patch/发行内容（变更点回顾）
- 新增 ai-assistant-widget：组件库骨架、核心组件、API 封装、类型定义、打包脚本
- 新增 ai-assistant-demo-app：最小演示应用，演示接入方式
- 新增 build_and_run.sh：本地打包与演示启动脚本
- 新增/更新 README 文档，包含使用步骤、结构说明、兼容性与注意事项

五、常见问题与排查
- 构建失败时，先确保 Node 版本与依赖版本兼容；可以清理 node_modules 重新安装
- 如果演示端口被占用，修改演示应用的端口或释放端口
- 若需要将 widget 发布成 npm 包，可以进一步接入 npm publish 流程

六、后续计划
- 将演示应用升级为真实的 npm 依赖引入形式，方便在任意项目中直接安装使用
- 增加 CI/CD 流水线，自动打包并发布到私有 npm 仓库
- 增加更多示例场景（跨框架嵌入、Next.js App 的嵌入示例等）

如果你愿意，我也可以把上述 README 同步到具体各子包的 README.md 中，形成统一的使用文档集。需要我继续吗？

八、离线打包与脱敏分发
- 提供一个本地脱敏打包工具：`ai-assistant-release/sanitize_release.sh`，用于将 Release 打包为脱敏的离线 ZIP。
- 使用占位符替换密钥，确保不会暴露密钥信息，同时保留演示用的最小配置。
- 运行示例:
  - bash ai-assistant-release/sanitize_release.sh
- 产出: `ai-assistant-release-sanitized.zip`，可直接分发给同事。
- 脱敏占位符策略（示例）:
  - NVIDIA_API_KEY=REPLACE_WITH_YOUR_NVIDIA_API_KEY
  - ZHIPU_API_KEY=REPLACE_WITH_YOUR_ZHIPU_API_KEY
  - MOONSHOT_API_KEY=REPLACE_WITH_YOUR_MOONSHOT_API_KEY
  - OPENROUTER_API_KEY=REPLACE_WITH_YOUR_OPENROUTER_API_KEY
  - ANTHROPIC_API_KEY=REPLACE_WITH_YOUR_ANTHROPIC_API_KEY
  - OPENAI_API_KEY=REPLACE_WITH_YOUR_OPENAI_API_KEY
  - JWT_SECRET=REPLACE_WITH_YOUR_JWT_SECRET
  - SECRET_ENCRYPTION_KEY=REPLACE_WITH_YOUR_SECRET_ENC_KEY
  - OTX_API_KEY=REPLACE_WITH_YOUR_OTX_API_KEY
  - 其它密钥以 KEY 名称命名的占位符同理。
