#!/bin/bash

echo "🔧 SOC Copilot Frontend 修复脚本"
echo "=================================="
echo ""

cd /Users/levent/Desktop/sec/frontend

echo "📋 问题诊断..."
echo "Node.js 版本: $(node --version 2>&1 || echo '未安装')"
echo "npm 版本: $(npm --version 2>&1 || echo '未安装')"
echo ""

echo "🗑️  清理旧文件..."
rm -rf node_modules package-lock.json .next 2>/dev/null
echo "✅ 清理完成"
echo ""

echo "📦 安装依赖（这可能需要几分钟）..."
echo "提示：如果遇到权限错误，请运行："
echo "  sudo chown -R \$(whoami) ~/.npm"
echo ""

npm install 2>&1 | tee install.log

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ 依赖安装成功！"
  echo ""
  echo "🚀 启动开发服务器..."
  npm run dev
else
  echo ""
  echo "❌ 依赖安装失败"
  echo "请查看 install.log 文件获取详细错误信息"
  echo ""
  echo "💡 建议："
  echo "1. 确保网络连接正常"
  echo "2. 尝试修复 npm 缓存权限:"
  echo "   sudo chown -R \$(whoami) ~/.npm"
  echo "   npm cache clean --force"
  echo "3. 或者尝试使用 yarn:"
  echo "   yarn install"
  echo "   yarn dev"
fi
