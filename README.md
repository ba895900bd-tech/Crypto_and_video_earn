# Telegram Video Earn & Crypto Rewards Bot — Starter

বাংলা Telegram bot starter: ভিডিও টাস্ক, অ্যাডমিন অনুমোদন, ডেমো ব্যালেন্স, রেফারেল লিংক ও উইথড্র রিকোয়েস্ট।

## গুরুত্বপূর্ণ
- এটি প্রকৃত crypto mining করে না।
- Binance Pay-এ স্বয়ংক্রিয় পেমেন্ট সংযুক্ত নয়। অ্যাডমিনকে Binance-এ পেমেন্ট আলাদাভাবে পাঠিয়ে যাচাই করতে হবে।
- ভিডিও সত্যিই দেখা হয়েছে কি না স্বয়ংক্রিয়ভাবে প্রমাণ করা যায় না; এই সংস্করণে অ্যাডমিন টাস্ক অনুমোদন করেন।
- রিওয়ার্ড/ব্যালেন্স ডেমো লেজার, নিশ্চিত আয় নয়।
- ব্যবহারকারীর Binance password, 2FA code, seed phrase বা API secret কখনো সংগ্রহ করবেন না।
- বাস্তব পেমেন্ট চালুর আগে স্থানীয় আইন, Binance-এর শর্ত, গোপনীয়তা, fraud prevention এবং হিসাব মিলিয়ে নেওয়ার ব্যবস্থা যাচাই করুন।

## সেটআপ
1. Python 3.10+ ইনস্টল করুন।
2. `pip install -r requirements.txt`
3. Telegram-এ @BotFather থেকে bot token নিন। token গোপন রাখুন।
4. `BOT_TOKEN` এবং আপনার numeric Telegram user ID-কে `ADMIN_ID` environment variable হিসেবে সেট করুন।
5. `python main.py`

Linux/macOS:
```bash
export BOT_TOKEN="YOUR_BOT_TOKEN"
export ADMIN_ID="YOUR_NUMERIC_TELEGRAM_ID"
export MIN_WITHDRAW="5"
python main.py
```
Windows PowerShell:
```powershell
$env:BOT_TOKEN="YOUR_BOT_TOKEN"
$env:ADMIN_ID="YOUR_NUMERIC_TELEGRAM_ID"
$env:MIN_WITHDRAW="5"
python main.py
```

## কমান্ড
- `/start` — বট চালু
- `/withdraw 5.00 BinancePayID` — উইথড্র রিকোয়েস্ট
- অ্যাডমিন: `/addtask শিরোনাম | https://example.com/video | 0.10`

ডেটা `bot.sqlite3`-এ থাকবে। ২৪/৭ চালাতে hosting/server প্রয়োজন। এই starter-এ automated Binance payout, ad-network integration, production-grade anti-fraud বা identity verification নেই।
