@echo off
chcp 65001 >nul
title تفعيل إضافة FlexDown لمتصفح Edge

echo ======================================================================
echo           FlexDown - تفعيل إضافة المتصفح (Edge / Chrome)
echo ======================================================================
echo.
echo [1] جاري نسخ مسار الإضافة إلى الحافظة (Presse-papiers)...
powershell -NoProfile -Command "Set-Clipboard -Value '%~dp0browser_extension'"

echo [2] جاري فتح صفحة إضافات Edge (edge://extensions)...
start msedge.exe edge://extensions

echo [3] جاري فتح المجلد لتحديده...
start explorer.exe /select,"%~dp0browser_extension"

echo.
echo ----------------------------------------------------------------------
echo                     الخطوات البسيطة المتبقية:
echo ----------------------------------------------------------------------
echo.
echo  بالفرنسية (Si votre Edge est en Français) :
echo  1. Activez le bouton "Mode développeur" (dans le menu à gauche).
echo  2. Glissez-Déposez le dossier "browser_extension" sélectionné
echo     directement dans la fenêtre de Edge !
echo     (Ou cliquez sur "Charger les extensions décompressées" et collez le chemin).
echo.
echo  بالعربية :
echo  1. فعّل خيار "وضع المطور" (Mode développeur) في القائمة الجانبية.
echo  2. اسحب مجلد "browser_extension" المحدد بالفأرة وأفلته داخل Edge !
echo.
echo ======================================================================
echo بعد التفعيل، سيظهر شعار FlexDown فوق أي فيديو في YouTube و TikTok وغيرها!
echo ======================================================================
echo.
pause
