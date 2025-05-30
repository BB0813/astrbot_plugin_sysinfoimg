#!/bin/bash
# Linux中文字体安装脚本
# 用于解决AstrBot系统信息插件在Linux环境下中文显示问题

echo "=== AstrBot 系统信息插件 - Linux中文字体安装脚本 ==="
echo "此脚本将帮助您安装中文字体以解决图片中文字符显示问题"
echo ""

# 检测Linux发行版
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
elif type lsb_release >/dev/null 2>&1; then
    OS=$(lsb_release -si)
    VER=$(lsb_release -sr)
elif [ -f /etc/lsb-release ]; then
    . /etc/lsb-release
    OS=$DISTRIB_ID
    VER=$DISTRIB_RELEASE
elif [ -f /etc/debian_version ]; then
    OS=Debian
    VER=$(cat /etc/debian_version)
elif [ -f /etc/SuSe-release ]; then
    OS=openSUSE
    VER=$(cat /etc/SuSe-release | grep VERSION | cut -d'=' -f2)
elif [ -f /etc/redhat-release ]; then
    OS=$(cat /etc/redhat-release | cut -d' ' -f1)
    VER=$(cat /etc/redhat-release | cut -d' ' -f3)
else
    OS=$(uname -s)
    VER=$(uname -r)
fi

echo "检测到系统: $OS $VER"
echo ""

# 根据不同发行版安装字体
case "$OS" in
    *Ubuntu*|*Debian*)
        echo "正在为 Ubuntu/Debian 系统安装中文字体..."
        sudo apt-get update
        echo "安装文泉驿字体..."
        sudo apt-get install -y fonts-wqy-microhei fonts-wqy-zenhei
        echo "安装Noto CJK字体..."
        sudo apt-get install -y fonts-noto-cjk fonts-noto-cjk-extra
        echo "安装思源字体..."
        sudo apt-get install -y fonts-source-han-sans-cn fonts-source-han-serif-cn
        ;;
    *CentOS*|*Red*Hat*|*RHEL*|*Fedora*)
        echo "正在为 CentOS/RHEL/Fedora 系统安装中文字体..."
        if command -v dnf &> /dev/null; then
            echo "使用 dnf 包管理器..."
            sudo dnf install -y wqy-microhei-fonts wqy-zenhei-fonts
            sudo dnf install -y google-noto-cjk-fonts
            sudo dnf install -y adobe-source-han-sans-cn-fonts adobe-source-han-serif-cn-fonts
        else
            echo "使用 yum 包管理器..."
            sudo yum install -y wqy-microhei-fonts wqy-zenhei-fonts
            sudo yum install -y google-noto-cjk-fonts
            sudo yum install -y adobe-source-han-sans-cn-fonts adobe-source-han-serif-cn-fonts
        fi
        ;;
    *SUSE*|*openSUSE*)
        echo "正在为 openSUSE 系统安装中文字体..."
        sudo zypper install -y wqy-microhei-fonts wqy-zenhei-fonts
        sudo zypper install -y noto-sans-cjk-fonts noto-serif-cjk-fonts
        ;;
    *Arch*|*Manjaro*)
        echo "正在为 Arch Linux 系统安装中文字体..."
        sudo pacman -S --noconfirm wqy-microhei wqy-zenhei
        sudo pacman -S --noconfirm noto-fonts-cjk
        sudo pacman -S --noconfirm adobe-source-han-sans-cn-fonts adobe-source-han-serif-cn-fonts
        ;;
    *)
        echo "未识别的Linux发行版: $OS"
        echo "请手动安装以下字体包之一:"
        echo "- 文泉驿字体 (wqy-microhei, wqy-zenhei)"
        echo "- Google Noto CJK 字体"
        echo "- Adobe 思源字体"
        echo ""
        echo "或者从以下网址下载字体文件并放置到 ~/.fonts/ 目录:"
        echo "- https://github.com/googlefonts/noto-cjk"
        echo "- https://github.com/adobe-fonts/source-han-sans"
        exit 1
        ;;
esac

echo ""
echo "正在刷新字体缓存..."
fc-cache -fv

echo ""
echo "=== 字体安装完成 ==="
echo "已安装的中文字体:"
fc-list :lang=zh | head -10

echo ""
echo "安装完成！现在重启 AstrBot 服务，中文字符应该能正常显示了。"
echo "如果问题仍然存在，请检查 AstrBot 日志中的字体加载信息。"