#!/bin/bash

echo "=================================================="
echo "🚀 北北桃台語活動行事曆 - GitHub Pages 上線助手"
echo "=================================================="
echo ""

# 檢查 git 是否初始化
if [ ! -d ".git" ]; then
  echo "📦 正在初始化 Git 儲存庫..."
  git init -b main
else
  echo "✅ Git 儲存庫已存在。"
fi

echo "📝 正在將所有檔案加入版本控制..."
git add .
git commit -m "🎉 初始發布：北北桃台語活動行事曆與自動化爬蟲系統"

echo ""
echo "--------------------------------------------------"
echo "💡 接下來請依照以下 3 個步驟將專案推送到 GitHub："
echo "--------------------------------------------------"
echo "1. 在 GitHub 上建立一個新的公開儲存庫 (Public Repository)，名稱建議為：taigi_activities"
echo "2. 在終端機執行以下指令（請將 YOUR_USERNAME 替換為您的 GitHub 帳號）："
echo ""
echo "   git remote add origin https://github.com/YOUR_USERNAME/taigi_activities.git"
echo "   git push -u origin main"
echo ""
echo "3. 開啟 GitHub 專案頁面："
echo "   點選 Settings -> Pages"
echo "   在 Build and deployment 的 Source 選擇「GitHub Actions」"
echo ""
echo "✨ 完成後，您的網站將發布於："
echo "   https://YOUR_USERNAME.github.io/taigi_activities/"
echo "   且每天凌晨 04:00 會自動執行爬蟲更新活動資料！"
echo "=================================================="
