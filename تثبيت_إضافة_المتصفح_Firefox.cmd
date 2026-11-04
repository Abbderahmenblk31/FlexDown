@echo off
chcp 65001 >nul
title تفعيل إضافة FlexDown لمتصفح Firefox

echo ======================================================================
echo           FlexDown - تفعيل إضافة المتصفح لـ Mozilla Firefox
echo ======================================================================
echo.
echo [1] جاري نسخ مسار ملف manifest.json إلى الحافظة (Presse-papiers)...
powershell -NoProfile -Command "Set-Clipboard -Value '%~dp0browser_extension\manifest.json'"

echo [2] جاري فتح صفحة إعداد الملحقات في Firefox...
start "" "C:\Program Files\Mozilla Firefox\firefox.exe" "about:debugging#/runtime/this-firefox"

echo [3] جاري فتح المجلد وتحديد ملف manifest.json...
start explorer.exe /select,"%~dp0browser_extension\manifest.json"

echo.
echo ----------------------------------------------------------------------
echo                     الخطوات البسيطة المتبقية:
echo ----------------------------------------------------------------------
echo.
echo  بالفرنسية (Dans Firefox en Français) :
echo  1. Dans la page ouverte, cliquez sur le bouton :
echo     "Charger un module temporaire..."
echo  2. Sélectionnez le fichier "manifest.json" (déjà sélectionné dans la fenêtre)
echo     ou collez directement le chemin (Ctrl+V) puis Valider !
echo.
echo  بالعربية :
echo  1. في الصفحة المفتوحة في فايرفوكس، اضغط على زر:
echo     "Charger un module temporaire..." (تحميل ملحق مؤقت...)
echo  2. اختر ملف "manifest.json" المظلل أمامك (أو الصق المسار مباشرة عبر Ctrl+V) !
echo.
echo ======================================================================
echo بعد التفعيل، سيظهر شعار FlexDown فوق أي مقطع في YouTube و TikTok وغيرها!
echo ======================================================================
echo.
pause
