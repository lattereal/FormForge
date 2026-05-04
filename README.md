# FormForge v2.3

**Advanced Google Form Automation Engine actually maintained, actually working.**

> This is open source. Don't resell it, don't claim it's yours.

---

## Why this one is different

Most Google Form spammers you'll find are broken, outdated, or straight-up don't work anymore. FormForge is built differently:

- **Parses forms directly from `FB_PUBLIC_LOAD_DATA_`**  Google's internal form data blob, not fragile CSS selectors. This means it keeps working even when Google tweaks the UI.
- **Full multi-page form support**  Automatically detects how many pages a form has and builds the correct `pageHistory` token so multi-page submissions actually go through instead of silently failing.
- **Real multithreading**  Uses Python threads to fire off submissions in parallel. Set 25 threads and it sends 25 requests at once.
- **Not a script, it's a full tool**  26 options, proxy support, session logging, batch queue, answer saving/loading, system info, and more.

---

## What it can't do

- **Sign-in required forms**  If the form redirects you to `accounts.google.com`, FormForge will detect this and tell you clearly. There is no way around this without a real Google account login, and that's out of scope. These forms cannot be parsed or submitted.
- **File upload questions**  Not supported.
- **Image/video questions**  Not supported.
- **Forms with reCAPTCHA**  You get 20 seconds during parsing to solve it manually. Submission CAPTCHAs are not bypassable.

---

## Install

Clone the repo and install dependencies:

```bash
git clone https://github.com/lattereal/FormForge
cd FormForge/FormForge-v2.3
pip install -r requirements.txt
```

Or install requirements directly:

```bash
pip install requests beautifulsoup4 selenium webdriver-manager lxml
```

**You also need Google Chrome installed.** webdriver-manager handles the ChromeDriver automatically  you don't need to download it separately.

---

## Run

```bash
python main.py
```

Windows users can double-click `scripts\run.bat`.

**Requirements:** Python 3.9+, Google Chrome.

---

## Usage

### Basic flow

1. **Option 1  Start New Form**  
   Paste a Google Form URL. Selenium opens Chrome in the background, waits up to 20 seconds (press Enter to skip early), then parses all questions automatically.

2. **Option 6  Enter Answers**  
   Type your answer for each question. Checkbox questions accept comma-separated values.

3. **Option 2  Quick Spam**  
   Enter how many submissions to send. Threads fire in parallel.

### Supported question types

| Type | Works |
|------|-------|
| Short Answer | ✅ |
| Paragraph | ✅ |
| Multiple Choice | ✅ |
| Checkbox (multi-select) | ✅ |
| Dropdown | ✅ |
| Linear Scale | ✅ |
| Date / Time | ✅ |
| Grid | ✅ |
| File Upload | ❌ |

### All 26 options

| # | Option | What it does |
|---|--------|-------------|
| 1 | Start New Form | Parse URL → enter answers → spam |
| 2 | Quick Spam | Spam with answers already in session |
| 3 | Single Test | Send exactly one submission to verify it works |
| 4 | Form Inspector | Parse and display all questions without submitting |
| 5 | Batch Queue | Parse multiple forms one by one, collect all answers, spam them all at the end |
| 6 | Enter Answers | Re-enter answers for the current loaded form |
| 7 | Save Answers | Save session answers to `data/answers.json` |
| 8 | Load Answers | Load answers from `data/answers.json` |
| 9 | View Answers | Preview what answers are currently in memory |
| 10 | Clear Answers | Wipe session answers |
| 11 | Proxy Manager | Toggle proxy mode on/off, reload proxies |
| 12 | Load Proxies | Reload from `data/proxies.txt` |
| 13 | Test Proxies | Check which proxies are alive |
| 14 | IP Check | Show your public IP and geolocation |
| 15 | Ping Test | Check connectivity to Google |
| 16 | Speed Test | Rough download speed benchmark |
| 17 | Settings | Adjust threads, delay, timeout, user-agent |
| 18 | Save Settings | Write settings to `config/config.json` |
| 19 | Load Settings | Reload settings from `config/config.json` |
| 20 | View Logs | List session log files |
| 21 | Clear Logs | Delete all log files |
| 22 | Export Report | Save a summary TXT to `logs/` |
| 23 | System Info | OS, Python version, active config |
| 24 | Stress Test | Benchmark how fast your machine spawns threads |
| 25 | Legal | Disclaimer |
| 26 | Credits | About |

---

## Batch Queue (Option 5)

This is one of the more useful features. You enter multiple form URLs, FormForge parses each one individually, you answer the questions for each form, then it spams all of them back to back. Good for when you have multiple forms to hit in one session.

---

## Multi-page forms

FormForge handles multi-page forms automatically. When parsing, it counts page break blocks in the form data and stores the page count internally. When submitting, it builds the correct `pageHistory` field (e.g. `0,1,2` for a 3-page form) that Google expects in the POST body. Without this, submissions to multi-page forms return 200 but never actually register  most other tools get this wrong.

---

## Proxy support

Add proxies to `data/proxies.txt`, one per line:

```
http://host:port
http://user:password@host:port
socks5://host:port
```

Enable proxy mode from Option 11  Proxy Manager. FormForge rotates through the list in order across threads.

---

## Configuration

`config/config.json` is created automatically when you save settings:

```json
{
  "threads": 25,
  "delay": 0.35,
  "timeout": 20,
  "use_proxies": false,
  "user_agent": "random"
}
```

- **threads**  How many parallel threads to use per spam run
- **delay**  Seconds to wait between each request per thread
- **timeout**  HTTP request timeout in seconds
- **user_agent**  `random` rotates through a list of common browser UA strings; `fixed` always uses the first one

---

## Project structure

```
FormForge-v2.3/
├── main.py                  # Entry point  run this
├── requirements.txt
│
├── utils/
│   ├── parser.py            # Selenium form parser (FB_PUBLIC_LOAD_DATA_)
│   ├── helpers.py           # Request engine, threading, proxy support
│   └── logger.py            # Colored console output, session log files
│
├── scripts/
│   ├── run.bat              # Windows double-click launcher
│   ├── install.bat          # Auto pip install
│   └── clear_logs.bat       # Wipes the logs folder
│
├── data/
│   ├── proxies.txt          # One proxy per line
│   └── answers.json         # Saved answer sets
│
├── logs/                    # Auto-generated session logs
└── config/
    └── config.json          # Persistent settings
```

---

## FAQ

**Do I need a Google account?**  
No, for public forms. Forms that redirect to a Google sign-in page cannot be used  FormForge will detect this and tell you.

**Does this work on Windows?**  
Yes, Windows is the main target. Use `scripts\run.bat` if you want a launcher.

**Why does Chrome open first?**  
Selenium loads the form page so the parser can read the full question data from the page source. It only opens briefly during parsing  submissions use plain HTTP requests, no browser needed.

**Press Enter to skip the wait  what does that do?**  
FormForge waits 20 seconds by default so you can solve any CAPTCHA that appears. If the page loaded fine, just press Enter to skip the countdown and continue immediately.

**The form has multiple pages  will it work?**  
Yes. FormForge detects the number of pages and sends the correct `pageHistory` value automatically.

**Where are saved answers stored?**  
`data/answers.json`

**Where are logs stored?**  
`logs/`  one file per session.

---

## Troubleshooting

**Missing Python dependency**  
Run `pip install -r requirements.txt` again.

**Selenium or Chrome failed to start**  
Make sure Google Chrome is installed and up to date. webdriver-manager downloads the matching ChromeDriver automatically.

**Parser returned nothing**  
The form URL might be wrong, or the form requires sign-in. Try Option 4  Form Inspector and check whether Chrome loads the form or redirects to a login page.

**HTTP 400 during submission**  
Usually means the form was updated or the token expired. Re-parse the form and re-enter your answers.

**Submissions return 200 but nothing shows up**  
If the form has multiple pages and you're using a different tool, it's probably missing the `pageHistory` field. FormForge handles this correctly.

**Proxy setup failed**  
Check your proxy format in `data/proxies.txt` and use Option 13  Test Proxies before enabling proxy mode.

---

## Disclaimer

For educational purposes and testing forms you own or have explicit permission to test. Submitting Google Forms without the form owner's consent may violate Google's Terms of Service and applicable laws depending on your jurisdiction. The author accepts no liability for misuse.

This is fully open source. The code is all here, nothing is hidden, no telemetry, no callbacks home. Read it yourself.

---

## License

MIT  see [LICENSE](LICENSE)
