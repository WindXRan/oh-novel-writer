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
            
            # 强制显示所有popper
            pg.evaluate("""() => {
                document.querySelectorAll('.el-popper, .el-select-dropdown, .el-select__popper').forEach(el => {
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                    el.style.width = '200px';
                    el.style.height = 'auto';
                    el.style.minHeight = '50px';
                    el.style.position = 'fixed';
                    el.style.top = '200px';
                    el.style.left = '400px';
                    el.style.zIndex = '99999';
                    el.style.background = '#fff';
                    el.style.border = '1px solid #ccc';
                    el.style.pointerEvents = 'auto';
                });
                document.querySelectorAll('.el-select-dropdown__item').forEach(el => {
                    el.style.display = 'block';
                    el.style.width = '100%';
                    el.style.height = 'auto';
                    el.style.padding = '8px 12px';
                    el.style.cursor = 'pointer';
                });
            }""")
            time.sleep(1)
            
            # 点击女频并触发事件
            result = pg.evaluate("""() => {
                let items = document.querySelectorAll('.el-select-dropdown__item');
                for (let item of items) {
                    if (item.innerText.trim() === '女频') {
                        // 触发各种事件
                        item.dispatchEvent(new MouseEvent('mouseenter', {bubbles:true}));
                        item.dispatchEvent(new MouseEvent('mouseover', {bubbles:true}));
                        item.dispatchEvent(new MouseEvent('mousedown', {bubbles:true}));
                        item.dispatchEvent(new MouseEvent('mouseup', {bubbles:true}));
                        item.dispatchEvent(new MouseEvent('click', {bubbles:true}));
                        return 'clicked with events';
                    }
                }
                return 'not found';
            }""")
            time.sleep(1)
            print(result, flush=True)
            
            # 检查值
            val = pg.evaluate("document.querySelectorAll('.el-select')[0].querySelector('input').value")
            print(f"频道值: [{val}]", flush=True)
            
            # 也检查input的dispatchEvent
            pg.evaluate("""() => {
                let inp = document.querySelectorAll('.el-select')[0].querySelector('input');
                inp.dispatchEvent(new Event('input', {bubbles:true}));
                inp.dispatchEvent(new Event('change', {bubbles:true}));
            }""")
            time.sleep(0.5)
            val = pg.evaluate("document.querySelectorAll('.el-select')[0].querySelector('input').value")
            print(f"频道值after event: [{val}]", flush=True)
            
            break
p.stop()
