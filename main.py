import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import time
import socket
import platform
import threading
import requests

from utils.logger import ConsoleColor as C, setup_logger, get_log_dir
from utils.helpers import (
    CONFIG, load_proxies, test_proxies, spam_mode,
    get_successful_requests, proxies, generate_cool_id, do_request
)
from utils.parser import (
    parse_form, display_parsed_questions,
    save_answers_json, load_answers_json
)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH  = os.path.join(BASE_DIR, "config", "config.json")
ANSWERS_PATH = os.path.join(BASE_DIR, "data", "answers.json")
PROXIES_PATH = os.path.join(BASE_DIR, "data", "proxies.txt")

_session_answers = {}
_session_url     = ""

ERROR_CODES = {
    "E1001": "Missing Python dependency. Run: pip install -r requirements.txt",
    "E1002": "Chrome or Selenium failed to start. Make sure Google Chrome is installed.",
    "E1003": "Parser returned no questions. Check that the form URL is valid.",
    "E1004": "HTTP 400 during submission. The form data or tokens may be wrong.",
    "E1005": "Proxy setup failed. Check data/proxies.txt and proxy mode settings.",
}

# ─────────────────────────────────────────────
#  DISPLAY HELPERS
# ─────────────────────────────────────────────

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def divider(char="─", width=62, color=C.OKCYAN):
    print(f"{color}{char*width}{C.ENDC}")

def header_line(text, color=C.BOLD+C.WHITE):
    print(f"  {color}{text}{C.ENDC}")

def pause():
    input(f"\n{C.DIM}  Press Enter to continue...{C.ENDC}")

def banner():
    art = r"""
    ███████╗ ██████╗ ██████╗ ███╗   ███╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗
    ██╔════╝██╔═══██╗██╔══██╗████╗ ████║██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
    █████╗  ██║   ██║██████╔╝██╔████╔██║█████╗  ██║   ██║██████╔╝██║  ███╗█████╗
    ██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝
    ██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║╚██████╔╝███████╗
    ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"""
    print(C.OKCYAN + art + C.ENDC)
    print(f"  {C.DIM}{'─'*68}{C.ENDC}")
    print(f"  {C.WARNING}Advanced Form Automation Engine  v2.3{C.ENDC}   "
          f"{C.DIM}Please do not resell or redistribute this tool.{C.ENDC}")
    print(f"  {C.DIM}{'─'*68}{C.ENDC}\n")

def status_bar():
    px_status = (f"{C.OKGREEN}{len(proxies)} proxies{C.ENDC}" if proxies
                 else f"{C.DIM}no proxies{C.ENDC}")
    px_mode   = (f"{C.OKGREEN}ON{C.ENDC}" if CONFIG['use_proxies']
                 else f"{C.FAIL}OFF{C.ENDC}")
    url_disp  = (_session_url[:38] + "…" if len(_session_url) > 39
                 else (_session_url or f"{C.DIM}none{C.ENDC}"))
    ans_count = len(_session_answers)
    print(f"  {C.DIM}Threads:{C.ENDC} {C.WARNING}{CONFIG['threads']}{C.ENDC}  "
          f"{C.DIM}Delay:{C.ENDC} {C.WARNING}{CONFIG['delay']}s{C.ENDC}  "
          f"{C.DIM}Proxies:{C.ENDC} {px_status} [{px_mode}]  "
          f"{C.DIM}Answers:{C.ENDC} {C.WARNING}{ans_count}{C.ENDC}\n"
          f"  {C.DIM}URL:{C.ENDC} {C.OKCYAN}{url_disp}{C.ENDC}")
    print()

MENU_PAGES = [
    [
        ("FORM OPERATIONS", [
            ("1",  "Start New Form",        "Parse URL → answer → spam"),
            ("2",  "Quick Spam",            "Spam with loaded answers"),
            ("3",  "Single Test",           "Send exactly one submission"),
            ("4",  "Form Inspector",        "Parse & display questions only"),
            ("5",  "Batch Queue",           "Parse each URL, answer, spam all"),
        ]),
        ("ANSWER MANAGEMENT", [
            ("6",  "Enter Answers",         "Type answers for loaded questions"),
            ("7",  "Save Answers",          "Save session answers to JSON"),
            ("8",  "Load Answers",          "Load answers from answers.json"),
            ("9",  "View Answers",          "Preview session answers"),
            ("10", "Clear Answers",         "Wipe answers from memory"),
        ]),
    ],
    [
        ("PROXY & NETWORK", [
            ("11", "Proxy Manager",         "Toggle proxy mode on/off"),
            ("12", "Load Proxies",          "Reload from proxies.txt"),
            ("13", "Test Proxies",          "Check alive/dead proxies"),
            ("14", "IP Check",              "Show public IP + geolocation"),
            ("15", "Ping Test",             "Connectivity check to Google"),
            ("16", "Speed Test",            "Measure download speed"),
        ]),
        ("SETTINGS & SYSTEM", [
            ("17", "Settings",              "Adjust threads / delay / timeout"),
            ("18", "Save Settings",         "Write to config.json"),
            ("19", "Load Settings",         "Load from config.json"),
            ("20", "View Logs",             "List session log files"),
            ("21", "Clear Logs",            "Delete all log files"),
            ("22", "Export Report",         "Save TXT summary to logs/"),
        ]),
    ],
    [
        ("INFO & TOOLS", [
            ("23", "System Info",           "OS, Python version, config"),
            ("24", "Stress Test",           "Benchmark threading speed"),
            ("25", "Legal Disclaimer",      "Usage policy"),
            ("26", "Credits",               "About FormForge"),
        ]),
        ("SESSION", [
            ("0",  "Exit",                  "Quit FormForge"),
        ]),
    ],
]

_menu_page = [0]

def show_menu():
    clear()
    banner()
    status_bar()

    page     = _menu_page[0]
    sections = MENU_PAGES[page]
    total    = len(MENU_PAGES)

    for section_title, items in sections:
        print(f"  {C.HEADER}{C.BOLD}  {section_title}{C.ENDC}")
        divider("·", 62, C.DIM)
        for num, label, desc in items:
            num_fmt  = f"{C.OKCYAN}[{num:>2}]{C.ENDC}"
            lbl_fmt  = f"{C.WHITE}{label:<22}{C.ENDC}"
            desc_fmt = f"{C.DIM}{desc}{C.ENDC}"
            print(f"    {num_fmt}  {lbl_fmt}  {desc_fmt}")
        print()

    divider("═", 62)
    nav_parts = []
    if page > 0:
        nav_parts.append(f"{C.DIM}[P] Prev{C.ENDC}")
    nav_parts.append(f"{C.DIM}Page {page+1}/{total}{C.ENDC}")
    if page < total - 1:
        nav_parts.append(f"{C.DIM}[N] Next{C.ENDC}")
    print("  " + "   ".join(nav_parts))
    divider("─", 62, C.DIM)

    raw = input(f"  {C.BOLD}{C.WARNING}Option / N / P: {C.ENDC}").strip().lower()

    if raw == "n" and page < total - 1:
        _menu_page[0] += 1
        return "__NAV__"
    if raw == "p" and page > 0:
        _menu_page[0] -= 1
        return "__NAV__"
    return raw

# ─────────────────────────────────────────────
#  SHARED ANSWER COLLECTION
# ─────────────────────────────────────────────

def _collect_answers(qdict):
    answers = {}
    divider()
    header_line("ANSWER COLLECTION")
    divider()
    for idx, (qid, q) in enumerate(qdict.items(), 1):
        if qid == "__pages__":
            continue
        req = f"{C.FAIL}*{C.ENDC}" if q["Required"] else " "
        print(f"\n  {req} {C.BOLD}Q{idx}.{C.ENDC} {q['Question']}")
        print(f"     {C.DIM}Type: {q['Type']}{C.ENDC}")
        if q["Options"]:
            for i, opt in enumerate(q["Options"], 1):
                print(f"       {C.DIM}{i}.{C.ENDC} {opt}")
        ans = input(f"  {C.HEADER}  Answer: {C.ENDC}").strip()
        if not ans and not q["Required"]:
            continue
        if q["Type"] == "Checkbox":
            answers[qid] = [x.strip() for x in ans.split(",") if x.strip()]
        else:
            answers[qid] = ans
    if "__pages__" in qdict:
        answers["__pages__"] = qdict["__pages__"]
    print(f"\n  {C.OKGREEN}{len(answers) - (1 if '__pages__' in answers else 0)} answer(s) collected.{C.ENDC}")
    return answers

# ─────────────────────────────────────────────
#  OPTION HANDLERS
# ─────────────────────────────────────────────

def opt_full_mode():
    global _session_url, _session_answers
    url = input(f"\n  {C.HEADER}Google Form URL: {C.ENDC}").strip()
    if not url:
        print(f"  {C.FAIL}No URL entered.{C.ENDC}")
        pause(); return
    _session_url = url
    qdict = parse_form(url)
    if not qdict:
        pause(); return
    display_parsed_questions(qdict)
    _session_answers = _collect_answers(qdict)
    if not _session_answers:
        pause(); return
    if input(f"  {C.HEADER}Start spamming? (y/n): {C.ENDC}").lower() == 'y':
        spam_mode(_session_answers, url)

def opt_quick_spam():
    global _session_url
    if not _session_answers:
        print(f"\n  {C.FAIL}No answers loaded. Use option 8 to load from JSON.{C.ENDC}")
        pause(); return
    url = _session_url or input(f"  {C.HEADER}Google Form URL: {C.ENDC}").strip()
    if not url:
        print(f"  {C.FAIL}No URL set.{C.ENDC}")
        pause(); return
    _session_url = url
    spam_mode(_session_answers, url)

def opt_single_test():
    global _session_url, _session_answers
    url = _session_url or input(f"\n  {C.HEADER}Google Form URL: {C.ENDC}").strip()
    if not url:
        print(f"  {C.FAIL}No URL.{C.ENDC}"); pause(); return
    _session_url = url
    if not _session_answers:
        print(f"  {C.WARNING}No answers in session. Parsing form...{C.ENDC}")
        qdict = parse_form(url)
        if not qdict: pause(); return
        display_parsed_questions(qdict)
        _session_answers = _collect_answers(qdict)
    if not _session_answers:
        pause(); return
    base         = url.split("?")[0].rstrip("/")
    viewform_url = base if base.endswith("/viewform") else base + "/viewform"
    form_url     = base.replace("/viewform", "") + "/formResponse"
    print(f"\n  {C.OKCYAN}Sending single test submission...{C.ENDC}")
    do_request(1, form_url, _session_answers, 0, show_output=True, referer_url=viewform_url)
    pause()

def opt_form_inspector():
    url = input(f"\n  {C.HEADER}Google Form URL to inspect: {C.ENDC}").strip()
    if not url:
        print(f"  {C.FAIL}No URL.{C.ENDC}"); pause(); return
    qdict = parse_form(url)
    if qdict:
        display_parsed_questions(qdict)
    pause()

def opt_batch_queue():
    global _session_url, _session_answers
    print(f"\n  {C.OKCYAN}Batch Queue Mode{C.ENDC}")
    divider()
    print(f"  {C.DIM}Enter one Google Form URL per line. Empty line to finish.{C.ENDC}\n")
    urls = []
    while True:
        u = input(f"  {C.HEADER}URL {len(urls)+1} (blank to stop): {C.ENDC}").strip()
        if not u:
            break
        urls.append(u)
    if not urls:
        print(f"  {C.WARNING}No URLs entered.{C.ENDC}"); pause(); return

    queue = []
    for i, url in enumerate(urls, 1):
        print(f"\n  {C.WARNING}{'━'*50}{C.ENDC}")
        print(f"  {C.BOLD}Form {i}/{len(urls)}{C.ENDC}  {C.DIM}{url[:55]}{'…' if len(url)>55 else ''}{C.ENDC}")
        print(f"  {C.WARNING}{'━'*50}{C.ENDC}")
        qdict = parse_form(url)
        if not qdict:
            print(f"  {C.FAIL}Could not parse — skipping form {i}.{C.ENDC}")
            continue
        display_parsed_questions(qdict)
        ans = _collect_answers(qdict)
        if ans:
            queue.append((url, ans))
            print(f"  {C.OKGREEN}Form {i} queued.{C.ENDC}")
        else:
            print(f"  {C.WARNING}No answers entered — skipping form {i}.{C.ENDC}")

    if not queue:
        print(f"\n  {C.FAIL}No forms ready to spam.{C.ENDC}"); pause(); return

    print(f"\n  {C.OKGREEN}{'━'*50}{C.ENDC}")
    print(f"  {C.BOLD}{C.OKGREEN}{len(queue)} form(s) ready:{C.ENDC}")
    for i, (url, _) in enumerate(queue, 1):
        short = url[:55] + "…" if len(url) > 55 else url
        print(f"    {C.DIM}{i}.{C.ENDC} {short}")
    print(f"  {C.OKGREEN}{'━'*50}{C.ENDC}\n")

    if input(f"  {C.HEADER}Spam all now? (y/n): {C.ENDC}").lower() != 'y':
        pause(); return

    for i, (url, ans) in enumerate(queue, 1):
        print(f"\n  {C.WARNING}{'━'*50}{C.ENDC}")
        print(f"  {C.BOLD}Spamming form {i}/{len(queue)}{C.ENDC}")
        print(f"  {C.DIM}{url[:55]}{'…' if len(url)>55 else ''}{C.ENDC}")
        print(f"  {C.WARNING}{'━'*50}{C.ENDC}")
        spam_mode(ans, url)

    _session_url     = queue[-1][0]
    _session_answers = queue[-1][1]
    pause()

def opt_enter_answers():
    global _session_answers
    url = _session_url or input(f"\n  {C.HEADER}Form URL (needed to fetch questions): {C.ENDC}").strip()
    if not url: pause(); return
    qdict = parse_form(url)
    if not qdict: pause(); return
    display_parsed_questions(qdict)
    _session_answers = _collect_answers(qdict)
    pause()

def opt_save_answers():
    if not _session_answers:
        print(f"\n  {C.FAIL}No answers in session.{C.ENDC}"); pause(); return
    save_answers_json(_session_answers, ANSWERS_PATH)
    pause()

def opt_load_answers():
    global _session_answers
    data = load_answers_json(ANSWERS_PATH)
    if data is not None:
        _session_answers = data
    pause()

def opt_view_answers():
    if not _session_answers:
        print(f"\n  {C.DIM}Session answers are empty.{C.ENDC}"); pause(); return
    divider()
    header_line("CURRENT SESSION ANSWERS")
    divider()
    for k, v in _session_answers.items():
        if k == "__pages__":
            continue
        print(f"  {C.OKCYAN}{k}{C.ENDC}  →  {v}")
    pause()

def opt_clear_answers():
    global _session_answers
    c = input(f"  {C.FAIL}Clear all session answers? (y/n): {C.ENDC}").lower()
    if c == 'y':
        _session_answers = {}
        print(f"  {C.OKGREEN}Session answers cleared.{C.ENDC}")
    pause()

def opt_proxy_manager():
    print(f"\n  {C.OKCYAN}Proxy Manager{C.ENDC}")
    divider()
    print(f"  Proxies loaded : {C.WARNING}{len(proxies)}{C.ENDC}")
    print(f"  Proxy mode     : {'ON' if CONFIG['use_proxies'] else 'OFF'}")
    print(f"\n  {C.DIM}[1] Enable   [2] Disable   [3] Reload{C.ENDC}")
    ch = input(f"  {C.HEADER}Choice: {C.ENDC}").strip()
    if ch == "1":
        CONFIG["use_proxies"] = True
        print(f"  {C.OKGREEN}Proxy mode enabled.{C.ENDC}")
    elif ch == "2":
        CONFIG["use_proxies"] = False
        print(f"  {C.WARNING}Proxy mode disabled.{C.ENDC}")
    elif ch == "3":
        load_proxies(PROXIES_PATH)
    pause()

def opt_load_proxies():
    load_proxies(PROXIES_PATH)
    pause()

def opt_test_proxies():
    test_proxies()
    pause()

def opt_ip_check():
    print(f"\n  {C.OKCYAN}Checking public IP address...{C.ENDC}")
    try:
        resp = requests.get("https://api.ipify.org?format=json", timeout=8)
        ip   = resp.json()["ip"]
        print(f"  Public IP : {C.OKGREEN}{ip}{C.ENDC}")
        try:
            geo = requests.get(f"https://ipapi.co/{ip}/json/", timeout=6).json()
            print(f"  Country   : {geo.get('country_name', '?')}")
            print(f"  Region    : {geo.get('region', '?')}")
            print(f"  ISP       : {geo.get('org', '?')}")
        except Exception:
            pass
    except Exception as e:
        print(f"  {C.FAIL}Failed: {e}{C.ENDC}")
    pause()

def opt_ping_test():
    targets = ["google.com", "docs.google.com", "1.1.1.1"]
    print(f"\n  {C.OKCYAN}Ping Test{C.ENDC}")
    divider()
    for host in targets:
        try:
            start = time.time()
            socket.setdefaulttimeout(4)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 80))
            ms = int((time.time() - start) * 1000)
            print(f"  {C.OKGREEN}REACHABLE{C.ENDC}  {host:<25}  {ms}ms")
        except Exception:
            print(f"  {C.FAIL}UNREACHABLE{C.ENDC}  {host}")
    pause()

def opt_speed_test():
    print(f"\n  {C.OKCYAN}Network Speed Test (download){C.ENDC}")
    divider()
    url = "http://speedtest.ftp.otenet.gr/files/test1Mb.db"
    try:
        start = time.time()
        r = requests.get(url, timeout=20, stream=True)
        size = 0
        for chunk in r.iter_content(1024):
            size += len(chunk)
        elapsed = time.time() - start
        mbps = (size * 8 / elapsed) / 1_000_000
        print(f"  Downloaded : {size/1024:.1f} KB")
        print(f"  Time       : {elapsed:.2f}s")
        print(f"  Speed      : {C.OKGREEN}{mbps:.2f} Mbps{C.ENDC}")
    except Exception as e:
        print(f"  {C.FAIL}Speed test failed: {e}{C.ENDC}")
    pause()

def opt_settings():
    print(f"\n  {C.OKCYAN}Settings{C.ENDC}")
    divider()
    print(f"  {C.DIM}Leave blank to keep current value.{C.ENDC}\n")
    d = input(f"  Delay       [{CONFIG['delay']}s]:    ").strip()
    if d:
        try: CONFIG["delay"] = float(d)
        except Exception: print(f"  {C.FAIL}Invalid delay.{C.ENDC}")
    t = input(f"  Threads     [{CONFIG['threads']}]:   ").strip()
    if t:
        try: CONFIG["threads"] = int(t)
        except Exception: print(f"  {C.FAIL}Invalid threads.{C.ENDC}")
    to = input(f"  Timeout     [{CONFIG['timeout']}s]:  ").strip()
    if to:
        try: CONFIG["timeout"] = int(to)
        except Exception: print(f"  {C.FAIL}Invalid timeout.{C.ENDC}")
    ua = input(f"  User-Agent  [{CONFIG['user_agent']}] (random/fixed): ").strip()
    if ua in ("random", "fixed"):
        CONFIG["user_agent"] = ua
    print(f"\n  {C.OKGREEN}Settings updated.{C.ENDC}")
    pause()

def opt_save_settings():
    cfg = {
        "delay":       CONFIG["delay"],
        "threads":     CONFIG["threads"],
        "use_proxies": CONFIG["use_proxies"],
        "timeout":     CONFIG["timeout"],
        "user_agent":  CONFIG["user_agent"],
        "log_level":   "INFO",
        "auto_save_answers": True,
        "answers_file": "data/answers.json",
        "proxies_file": "data/proxies.txt"
    }
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"\n  {C.OKGREEN}Settings saved to config/config.json{C.ENDC}")
    pause()

def opt_load_settings():
    try:
        with open(CONFIG_PATH) as f:
            saved = json.load(f)
        for k in ("delay", "threads", "use_proxies", "timeout", "user_agent"):
            if k in saved:
                CONFIG[k] = saved[k]
        print(f"\n  {C.OKGREEN}Settings loaded from config/config.json{C.ENDC}")
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        print(f"\n  {C.FAIL}config.json is malformed.{C.ENDC}")

def opt_view_logs():
    log_dir = get_log_dir()
    print(f"\n  {C.OKCYAN}Log files in {log_dir}{C.ENDC}")
    divider()
    try:
        files = sorted(os.listdir(log_dir), reverse=True)
        if not files:
            print(f"  {C.DIM}No logs yet.{C.ENDC}")
        else:
            for i, f in enumerate(files[:15], 1):
                fpath = os.path.join(log_dir, f)
                size  = os.path.getsize(fpath)
                print(f"  {C.DIM}{i:>2}.{C.ENDC}  {C.WHITE}{f}{C.ENDC}  {C.DIM}({size/1024:.1f} KB){C.ENDC}")
    except Exception as e:
        print(f"  {C.FAIL}Error: {e}{C.ENDC}")
    pause()

def opt_clear_logs():
    log_dir = get_log_dir()
    c = input(f"  {C.FAIL}Delete ALL log files? (y/n): {C.ENDC}").lower()
    if c != 'y':
        pause(); return
    try:
        removed = 0
        for f in os.listdir(log_dir):
            fp = os.path.join(log_dir, f)
            if os.path.isfile(fp):
                os.remove(fp)
                removed += 1
        print(f"  {C.OKGREEN}{removed} log file(s) deleted.{C.ENDC}")
    except Exception as e:
        print(f"  {C.FAIL}Error: {e}{C.ENDC}")
    pause()

def opt_export_report():
    report_path = os.path.join(BASE_DIR, "logs", f"report_{int(time.time())}.txt")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    lines = [
        "FormForge v2.3 — Session Report",
        f"Generated : {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 50,
        f"URL        : {_session_url or 'N/A'}",
        f"Answers    : {len(_session_answers)}",
        f"Threads    : {CONFIG['threads']}",
        f"Delay      : {CONFIG['delay']}s",
        f"Timeout    : {CONFIG['timeout']}s",
        f"Proxies    : {'ON' if CONFIG['use_proxies'] else 'OFF'}",
        "=" * 50,
        "Answers dump:",
    ]
    for k, v in _session_answers.items():
        if k == "__pages__":
            continue
        lines.append(f"  {k}: {v}")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    print(f"\n  {C.OKGREEN}Report saved to {report_path}{C.ENDC}")
    pause()

def opt_system_info():
    print(f"\n  {C.OKCYAN}System Information{C.ENDC}")
    divider()
    print(f"  OS         : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  Python     : {platform.python_version()}")
    print(f"  Hostname   : {socket.gethostname()}")
    divider("·")
    print(f"  Threads    : {CONFIG['threads']}")
    print(f"  Delay      : {CONFIG['delay']}s")
    print(f"  Timeout    : {CONFIG['timeout']}s")
    print(f"  Proxies    : {len(proxies)} loaded  ({'enabled' if CONFIG['use_proxies'] else 'disabled'})")
    print(f"  Session URL: {_session_url or 'N/A'}")
    print(f"  Answers    : {len(_session_answers)} in memory")
    pause()

def opt_stress_test():
    print(f"\n  {C.WARNING}Thread Stress Test{C.ENDC}")
    divider()
    print(f"  {C.DIM}Measures how fast your system spawns and joins threads.{C.ENDC}")
    try:
        count = int(input(f"  Threads to spawn [{CONFIG['threads']}]: ").strip() or CONFIG['threads'])
    except ValueError:
        count = CONFIG['threads']
    results = []
    def dummy(n):
        time.sleep(0.05)
        results.append(n)
    print(f"  {C.OKCYAN}Spawning {count} threads...{C.ENDC}")
    start   = time.time()
    threads = [threading.Thread(target=dummy, args=(i,), daemon=True) for i in range(count)]
    for t in threads: t.start()
    for t in threads: t.join()
    elapsed = time.time() - start
    print(f"  {C.OKGREEN}Done!{C.ENDC}  {count} threads in {elapsed:.3f}s  "
          f"({count/elapsed:.0f} threads/sec)")
    pause()

def opt_legal():
    print(f"\n  {C.FAIL}{'═'*50}{C.ENDC}")
    print(f"  {C.BOLD}{C.FAIL}  LEGAL DISCLAIMER{C.ENDC}")
    print(f"  {C.FAIL}{'═'*50}{C.ENDC}")
    for line in [
        "FormForge is a research and automation tool.",
        "Submitting forms without the owner's consent may",
        "violate Google's Terms of Service and local laws.",
        "",
        "You are solely responsible for how you use this tool.",
        "The author accepts no liability for misuse.",
        "",
        "Only test forms you own or have explicit permission.",
    ]:
        print(f"  {line}")
    print(f"  {C.FAIL}{'═'*50}{C.ENDC}")
    pause()

def opt_credits():
    divider("═")
    print(f"\n  {C.BOLD}{C.OKCYAN}FormForge v2.3{C.ENDC}")
    print(f"  {C.DIM}Advanced Form Automation Engine{C.ENDC}\n")
    print(f"  {C.WHITE}Author      :{C.ENDC}  github.com/FormForge")
    print(f"  {C.WHITE}Version     :{C.ENDC}  2.3")
    print(f"  {C.WHITE}Language    :{C.ENDC}  Python 3.x")
    print(f"  {C.WHITE}Libraries   :{C.ENDC}  requests, beautifulsoup4, selenium")
    print(f"                 webdriver-manager, lxml")
    print(f"\n  {C.DIM}Do not resell or claim as your own.{C.ENDC}")
    divider("═")
    pause()

# ─────────────────────────────────────────────
#  DISPATCH TABLE
# ─────────────────────────────────────────────

DISPATCH = {
    "1":  opt_full_mode,
    "2":  opt_quick_spam,
    "3":  opt_single_test,
    "4":  opt_form_inspector,
    "5":  opt_batch_queue,
    "6":  opt_enter_answers,
    "7":  opt_save_answers,
    "8":  opt_load_answers,
    "9":  opt_view_answers,
    "10": opt_clear_answers,
    "11": opt_proxy_manager,
    "12": opt_load_proxies,
    "13": opt_test_proxies,
    "14": opt_ip_check,
    "15": opt_ping_test,
    "16": opt_speed_test,
    "17": opt_settings,
    "18": opt_save_settings,
    "19": opt_load_settings,
    "20": opt_view_logs,
    "21": opt_clear_logs,
    "22": opt_export_report,
    "23": opt_system_info,
    "24": opt_stress_test,
    "25": opt_legal,
    "26": opt_credits,
}

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    log_path = setup_logger()
    opt_load_settings()

    clear()
    banner()
    print(f"  {C.DIM}Session log → {log_path}{C.ENDC}")
    time.sleep(1.0)

    while True:
        try:
            choice = show_menu()
            if choice == "__NAV__":
                continue
            if choice == "0":
                clear()
                print(f"\n  {C.OKGREEN}Goodbye. Stay responsible.{C.ENDC}\n")
                break
            handler = DISPATCH.get(choice)
            if handler:
                handler()
            elif choice:
                print(f"  {C.FAIL}Invalid option '{choice}'.{C.ENDC}")
                time.sleep(0.8)
        except KeyboardInterrupt:
            print(f"\n\n  {C.WARNING}Interrupted. Returning to menu...{C.ENDC}")
            time.sleep(0.5)

if __name__ == "__main__":
    main()
