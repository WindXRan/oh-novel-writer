from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
for ctx in browser.contexts:
    for pg in ctx.pages:
        if 'wawawriter' in pg.url and 'submission/create' in pg.url:
            pg.set_viewport_size({"width": 1280, "height": 900})
            time.sleep(1)
            pg.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
            
            # 先检查"言情"标签的父元素结构
            result = pg.evaluate("""() => {
                let r = [];
                document.querySelectorAll('div, span').forEach(el => {
                    if (el.innerText.trim() === '言情' && el.children.length === 0 && el.offsetHeight > 0) {
                        let parent = el.parentElement;
                        let grandparent = parent ? parent.parentElement : null;
                        r.push({
                            el_cls: el.className,
                            parent_cls: parent ? parent.className.substring(0, 80) : '',
                            parent_tag: parent ? parent.tagName : '',
                            grandparent_cls: grandparent ? grandparent.className.substring(0, 80) : '',
                            el_style: el.getAttribute('style') || '',
                            parent_style: parent ? (parent.getAttribute('style') || '') : ''
                        });
                    }
                });
                return r;
            }""")
            print("言情标签结构:", flush=True)
            for r in result:
                print(f"  el: {r['el_cls']}", flush=True)
                print(f"  parent: {r['parent_tag']} {r['parent_cls']}", flush=True)
                print(f"  grandparent: {r['grandparent_cls']}", flush=True)
            
            # 点击言情标签
            print("\\n点击言情...", flush=True)
            pg.get_by_text('言情', exact=True).first.click(timeout=5000)
            time.sleep(1)
            
            # 检查点击后的状态
            result2 = pg.evaluate("""() => {
                let r = [];
                document.querySelectorAll('div, span').forEach(el => {
                    if (el.innerText.trim() === '言情' && el.children.length === 0 && el.offsetHeight > 0) {
                        r.push({
                            el_cls: el.className,
                            el_style: el.getAttribute('style') || '',
                            bg: window.getComputedStyle(el).backgroundColor,
                            parent_cls: el.parentElement ? el.parentElement.className.substring(0, 80) : ''
                        });
                    }
                });
                return r;
            }""")
            print("\\n点击后:", flush=True)
            for r in result2:
                print(f"  bg: {r['bg']}", flush=True)
                print(f"  cls: {r['el_cls']}", flush=True)
                print(f"  parent: {r['parent_cls']}", flush=True)
            
            break
p.stop()
