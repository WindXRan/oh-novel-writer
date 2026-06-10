"""
story-submit: 自动投稿到蛙蛙写作平台
用pyautogui操作浏览器窗口填写表单。
"""
import os, re, sys, time, argparse, subprocess, socket
from pathlib import Path

DEFAULT_PEN_NAME = "一盏清酒"
QUARK_EXE = r"C:\Users\Administrator\AppData\Local\Programs\Quark\quark.exe"
QUARK_USER_DATA = r"C:\Users\Administrator\AppData\Local\Quark\User Data"
CDP_PORT = 9222


def parse_book_info(txt_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    info = {}
    m = re.search(r'书名[：:]\s*(.+)', content)
    if m: info['title'] = m.group(1).strip()
    m = re.search(r'简介[：:]\n(.+?)(?:\n={10,}|\Z)', content, re.DOTALL)
    if m: info['blurb'] = m.group(1).strip()
    m = re.search(r'标签[：:]\s*(.+)', content)
    if m: info['tags'] = [t.strip() for t in m.group(1).strip().split('|') if t.strip()]
    m = re.search(r'(?:字数|总字数)[：:]\s*(\d+)', content)
    if m: info['word_count'] = int(m.group(1))
    return info


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0


def is_quark_running():
    try:
        r = subprocess.run('tasklist /FI "IMAGENAME eq quark.exe"', capture_output=True, text=True, shell=True)
        return "quark.exe" in r.stdout.lower()
    except: return False


def find_and_click_text(text, region=None):
    """用pyautogui找文字并点击"""
    import pyautogui
    try:
        location = pyautogui.locateOnScreen(text, confidence=0.8, region=region)
        if location:
            pyautogui.click(pyautogui.center(location))
            return True
    except:
        pass
    return False


def type_chinese(text):
    """用剪贴板输入中文"""
    import pyautogui, pyperclip
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)


def submit_to_wawawriter(txt_path, headless=False, dry_run=False):
    from playwright.sync_api import sync_playwright
    import pyautogui

    book_info = parse_book_info(txt_path)
    txt_abs = str(Path(txt_path).resolve())
    if not book_info.get('title'):
        print("无法提取书名", flush=True); return False

    print(f"书名: {book_info['title']}", flush=True)
    print(f"笔名: {DEFAULT_PEN_NAME}", flush=True)
    print(f"字数: {book_info.get('word_count','?')}", flush=True)
    print(f"标签: {book_info.get('tags',[])}", flush=True)

    if not is_port_open(CDP_PORT):
        if is_quark_running():
            print("夸克已运行但未开调试端口。请关闭夸克后重新运行。", flush=True)
            return False
        print("启动夸克...", flush=True)
        subprocess.Popen([
            QUARK_EXE, f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={QUARK_USER_DATA}", "--no-sandbox",
            "https://wawawriter.com/app/submission/create"
        ])
        for i in range(30):
            time.sleep(1)
            if is_port_open(CDP_PORT): print("已启动!", flush=True); break
        else: print("启动超时", flush=True); return False
        time.sleep(5)

    with sync_playwright() as p:
        print("连接浏览器...", flush=True)
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")

        page = None
        for ctx in browser.contexts:
            for pg in ctx.pages:
                if "wawawriter" in pg.url:
                    page = pg
        if not page:
            page = browser.contexts[0].new_page()

        print("打开投稿页...", flush=True)
        try: page.goto("https://wawawriter.com/app/submission/create", timeout=30000)
        except: pass
        time.sleep(8)
        print(f"URL={page.url}", flush=True)

        if "/login" in page.url:
            print("请在浏览器中登录...", flush=True)
            for i in range(300):
                time.sleep(1)
                if "/login" not in page.url: print("登录成功!", flush=True); break
                if i % 10 == 0: print(f"  等待 {i}s ...", flush=True)
            time.sleep(3)
            page.goto("https://wawawriter.com/app/submission/create", timeout=30000)
            time.sleep(5)
        else:
            print("已登录", flush=True)

        print("[1] 上传文件...", flush=True)
        try:
            page.locator('input[type="file"]').first.set_input_files(txt_abs)
            print("[OK] 已上传", flush=True)
            time.sleep(8)
        except Exception as e:
            print(f"[X] 上传失败: {e}", flush=True)

        print("[2] 关闭预览弹窗...", flush=True)
        page.evaluate("""(text) => {
            for (let b of document.querySelectorAll('button')) {
                if (b.innerText.includes(text)) { b.click(); return true; }
            }
            return false;
        }""", "下一步")
        time.sleep(3)
        print("[OK]", flush=True)

        # 设置viewport
        page.set_viewport_size({"width": 1280, "height": 900})
        time.sleep(1)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)

        # 用pyautogui填写文本字段
        print("[3] 作品名称...", flush=True)
        # 找到作品名称input的位置
        rect = page.evaluate("""() => {
            let inp = document.querySelector('input[placeholder*="作品名称"]');
            if (!inp) return null;
            let r = inp.getBoundingClientRect();
            return {x: r.x + r.width/2, y: r.y + r.height/2};
        }""")
        if rect:
            pyautogui.click(rect['x'], rect['y'])
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a')
            type_chinese(book_info['title'].replace('《','').replace('》',''))
            print(f"[OK]", flush=True)

        print("[4] 笔名...", flush=True)
        rect = page.evaluate("""() => {
            let inp = document.querySelector('input[placeholder*="笔名"]');
            if (!inp) return null;
            let r = inp.getBoundingClientRect();
            return {x: r.x + r.width/2, y: r.y + r.height/2};
        }""")
        if rect:
            pyautogui.click(rect['x'], rect['y'])
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a')
            type_chinese(DEFAULT_PEN_NAME)
            print(f"[OK]", flush=True)

        print("[5] 字数...", flush=True)
        rect = page.evaluate("""() => {
            let inp = document.querySelector('input[placeholder*="作品字数"]');
            if (!inp) return null;
            let r = inp.getBoundingClientRect();
            return {x: r.x + r.width/2, y: r.y + r.height/2};
        }""")
        if rect:
            pyautogui.click(rect['x'], rect['y'])
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a')
            type_chinese(str(book_info.get('word_count','')))
            print("[OK]", flush=True)

        print("[6] 作品频道...", flush=True)
        # 点击频道select
        rect = page.evaluate("""() => {
            let s = document.querySelectorAll('.el-select')[0];
            if (!s) return null;
            let r = s.getBoundingClientRect();
            return {x: r.x + r.width/2, y: r.y + r.height/2};
        }""")
        if rect:
            pyautogui.click(rect['x'], rect['y'])
            time.sleep(1)
            # 找女频选项并点击
            # 需要在屏幕上找到"女频"文字
            # 用pyautogui的locateOnScreen或手动定位
            # 先试试用键盘选择
            pyautogui.press('down')
            time.sleep(0.2)
            pyautogui.press('down')  # 女频是第二个选项
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(0.5)
            print("[OK]", flush=True)

        print("[7] 作品状态...", flush=True)
        rect = page.evaluate("""() => {
            let s = document.querySelectorAll('.el-select')[1];
            if (!s) return null;
            let r = s.getBoundingClientRect();
            return {x: r.x + r.width/2, y: r.y + r.height/2};
        }""")
        if rect:
            pyautogui.click(rect['x'], rect['y'])
            time.sleep(1)
            pyautogui.press('enter')  # 第一个选项就是连载中
            time.sleep(0.5)
            print("[OK]", flush=True)

        print("[8] 小说类目...", flush=True)
        rect = page.evaluate("""() => {
            let c = document.querySelector('.el-cascader, [class*=cascader]');
            if (!c) return null;
            let r = c.getBoundingClientRect();
            return {x: r.x + r.width/2, y: r.y + r.height/2};
        }""")
        if rect:
            pyautogui.click(rect['x'], rect['y'])
            time.sleep(1)
            # 选择现代
            pyautogui.press('down')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(1)
            # 选择言情
            pyautogui.press('enter')
            time.sleep(1)
            print("[OK]", flush=True)

        print("[9] 标签...", flush=True)
        for tag in book_info.get('tags', []):
            tag = tag.strip()
            if not tag: continue
            preset = ['言情','现实情感','悬疑','惊悚','科幻','武侠','权谋','脑洞','纯爱','大女主','病娇','青梅竹马','豪门霸总','女神','女王','草根','真假千金','学霸','校霸','出轨','婚姻','家庭','校园','职场','娱乐圈','重生','穿越','犯罪','丧尸','太空歌剧','赛博朋克','游戏','探险','宫斗宅斗','仙侠','克苏鲁','系统','规则怪谈','团宠','囤物资','HE','BE','甜宠','虐恋','暗恋','先婚后爱','先虐后甜','追妻火葬场','破镜重圆','沙雕','爽文','复仇','反转','逆袭','励志','烧脑','热血','争霸','求生','打脸','多视角反转','治愈','古代','现代','历史','未来','架空','民国','哥哥','凤凰男','校草','小奶狗','恶毒婆婆','扶弟魔','黑莲花','偏执','腹黑','全能','杀伐果断','锦鲤','毒舌','傲娇','迪化','听心声','读心术','倒计时文学','五零年代','六零年代','七零年代','八零年代','兽世','日久生情','一见钟情','强取豪夺','欢喜冤家','无系统']
            if tag in preset:
                # 找到标签按钮的位置
                rect = page.evaluate(f"""(tag) => {{
                    let btns = document.querySelectorAll('button, [role=button], [class*=tag]');
                    for (let b of btns) {{
                        if (b.innerText.trim() === tag && b.offsetHeight > 0) {{
                            let r = b.getBoundingClientRect();
                            return {{x: r.x + r.width/2, y: r.y + r.height/2}};
                        }}
                    }}
                    return null;
                }}""", tag)
                if rect:
                    pyautogui.click(rect['x'], rect['y'])
                    time.sleep(0.3)
                    print(f"  [OK] {tag}", flush=True)
                else:
                    print(f"  [X] {tag}", flush=True)
            else:
                # 自定义标签
                rect = page.evaluate("""() => {
                    let inp = document.querySelector('input[placeholder*="自定义标签"]');
                    if (!inp) return null;
                    let r = inp.getBoundingClientRect();
                    return {x: r.x + r.width/2, y: r.y + r.height/2};
                }""")
                if rect:
                    pyautogui.click(rect['x'], rect['y'])
                    time.sleep(0.3)
                    type_chinese(tag)
                    time.sleep(0.3)
                    # 点击添加按钮
                    add_rect = page.evaluate("""() => {
                        let btns = document.querySelectorAll('button');
                        for (let b of btns) {
                            if (b.innerText.trim() === '添加' && b.offsetHeight > 0) {
                                let r = b.getBoundingClientRect();
                                return {x: r.x + r.width/2, y: r.y + r.height/2};
                            }
                        }
                        return null;
                    }""")
                    if add_rect:
                        pyautogui.click(add_rect['x'], add_rect['y'])
                        time.sleep(0.3)
                        print(f"  [OK] 自定义: {tag}", flush=True)

        print("[10] 简介...", flush=True)
        rect = page.evaluate("""() => {
            let ta = document.querySelector('textarea');
            if (!ta) return null;
            let r = ta.getBoundingClientRect();
            return {x: r.x + r.width/2, y: r.y + r.height/2};
        }""")
        if rect:
            pyautogui.click(rect['x'], rect['y'])
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a')
            type_chinese(book_info.get('blurb', ''))
            print(f"[OK] {len(book_info.get('blurb',''))}字", flush=True)

        if dry_run:
            print("\n[DRY RUN] 已填写，未提交。", flush=True)

        print("\n完成! 请在浏览器中检查并提交。", flush=True)

    return True


def main():
    parser = argparse.ArgumentParser(description='自动投稿到蛙蛙写作平台')
    parser.add_argument('--book', required=True, help='导出的txt文件路径')
    parser.add_argument('--headless', action='store_true', help='无头模式')
    parser.add_argument('--dry-run', action='store_true', help='试运行')
    args = parser.parse_args()

    if not os.path.exists(args.book):
        print(f"文件不存在: {args.book}", flush=True); sys.exit(1)

    try:
        success = submit_to_wawawriter(args.book, args.headless, args.dry_run)
        if not success: sys.exit(1)
    except Exception as e:
        print(f"投稿失败: {e}", flush=True); sys.exit(1)


if __name__ == '__main__':
    main()
