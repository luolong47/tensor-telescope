import requests
import ddddocr
import os
import sys
import json
import time
import random

# 配置信息
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')
UA = os.getenv('UA', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

session = requests.Session()
session.headers.update({
    "User-Agent": UA,
    "Origin": "https://www.ip2free.com",
    "Referer": "https://www.ip2free.com/",
    "webname": "IP2FREE",
    "lang": "cn",
    "content-type": "text/plain;charset=UTF-8"
})

TOKEN_FILE = "token_cache.txt"

def load_token():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                token = f.read().strip()
                if token:
                    print(f"📖 发现本地缓存 Token: {token[:10]}***")
                    return token
        except:
            pass
    return None

def save_token(token):
    try:
        with open(TOKEN_FILE, 'w') as f:
            f.write(token)
        print("💾 Token 已缓存到本地文件")
    except Exception as e:
        print(f"⚠️ 缓存 Token 失败: {e}")

def is_token_valid():
    """通过请求任务列表校验当前 Token 是否有效"""
    url = "https://api.ip2free.com/api/account/taskList?"
    try:
        resp = session.post(url, json={}, timeout=10)
        res_json = resp.json()
        # 如果 code 为 0，说明 token 有效
        return res_json.get('code') == 0
    except:
        return False

def login():
    # 1. 尝试从缓存加载
    cached_token = load_token()
    if cached_token:
        session.headers.update({"x-token": cached_token})
        if is_token_valid():
            print("✨ 缓存 Token 有效，跳过登录步骤")
            return True
        else:
            print("♻️ 缓存 Token 已过期或失效，准备重新登录...")

    # 2. 正式登录逻辑
    print("🚀 [Step 1] 正在模拟用户登录...")
    url = "https://api.ip2free.com/api/account/login?"
    log_data = {"email": EMAIL, "password": "***HIDDEN***"}
    print(f"📤 发送登录请求 | URL: {url} | Payload: {json.dumps(log_data)}")
    
    data = {"email": EMAIL, "password": PASSWORD}
    try:
        resp = session.post(url, json=data)
        res_json = resp.json()
        print(f"📥 登录响应内容: {json.dumps(res_json, ensure_ascii=False)}")
        
        token = res_json.get('data', {}).get('token')
        if token:
            session.headers.update({"x-token": token})
            save_token(token)
            print("✅ 登录成功，新 Token 已保存")
            return True
        else:
            print(f"❌ 登录失败！服务器返回: {res_json.get('msg', '未知错误')}")
            return False
    except Exception as e:
        print(f"❌ 登录过程中出现异常: {e}")
        return False

def get_task_id():
    # 模拟用户点击进入任务页面的时间间隔
    human_delay(3, 7, "正在浏览任务中心...")
    
    print("🔍 [Step 2] 正在获取任务列表...")
    url = "https://api.ip2free.com/api/account/taskList?"
    print(f"📤 发送任务列表请求 | URL: {url} | Payload: {{}}")
    
    try:
        resp = session.post(url, json={})
        res_json = resp.json()
        print(f"📥 任务列表响应内容: {json.dumps(res_json, ensure_ascii=False)}")
        
        tasks = res_json.get('data', {}).get('list', [])
        for task in tasks:
            if "点击就送" in task.get('task_name', ''):
                task_id = task.get('id')
                print(f"🎯 成功匹配任务: '{task.get('task_name')}' | ID: {task_id}")
                return task_id
        
        print("⚠️ 未能在列表中发现匹配任务，尝试使用兜底 ID 49130")
        return 49130
    except Exception as e:
        print(f"⚠️ 获取任务列表失败: {e}，将尝试使用兜底 ID")
        return 49130

def handle_captcha():
    print("🖼️ [Step 3] 发现需要验证码，正在准备识别...")
    ocr = ddddocr.DdddOcr(show_ad=False)
    
    for i in range(3):
        human_delay(2, 4, "正在加载验证码图片...")
        captcha_url = "https://api.ip2free.com/api/account/captcha?"
        print(f"📤 获取验证码图片 | URL: {captcha_url}")
        
        img_resp = session.get(captcha_url)
        if img_resp.status_code != 200:
            print(f"❌ 验证码下载失败，状态码: {img_resp.status_code}")
            continue
            
        # OCR 识别
        res = ocr.classification(img_resp.content)
        print(f"🔢 OCR 识别完成 | 识别结果: {res} (尝试次序: {i+1}/3)")
        
        # 模拟人类“看图并输入”的时间
        human_delay(2, 4, "正在输入验证码并点击校验...")
        
        check_url = "https://api.ip2free.com/api/account/checkCaptcha?"
        check_payload = {"code": res}
        print(f"📤 发送校验请求 | URL: {check_url} | Payload: {json.dumps(check_payload)}")
        
        check_resp = session.post(check_url, json=check_payload)
        check_res_json = check_resp.json()
        print(f"📥 校验响应内容: {json.dumps(check_res_json, ensure_ascii=False)}")
        
        if check_res_json.get('code') == 0:
            print("✅ 验证码校验通过，安全校验已完成")
            return True
        else:
            print(f"❌ 验证码错误: {check_res_json.get('msg')}，正在刷新验证码重试...")
            
    print("❌ 连续 3 次验证码校验失败，放弃任务")
    return False

def finish_task(task_id):
    human_delay(3, 6, "正在点击‘立即领取’按钮...")
    
    print(f"🎁 [Step 4] 正在执行最终领取操作 (TaskID: {task_id})...")
    url = "https://api.ip2free.com/api/account/finishTask?"
    payload = {"id": task_id}
    print(f"📤 发送领取请求 | URL: {url} | Payload: {json.dumps(payload)}")
    
    try:
        resp = session.post(url, json=payload)
        res_json = resp.json()
        msg = res_json.get('msg', '').lower()
        code = res_json.get('code')
        
        print(f"📥 领取结果响应内容: {json.dumps(res_json, ensure_ascii=False)}")
        
        if code == 0:
            print(f"🎉 任务圆满完成！服务器消息: {res_json.get('msg')}")
            return True
        elif "invalid" in msg or "已经完成" in msg or "重复领取" in msg:
            print(f"⚠️ 提示: {res_json.get('msg')}。由于任务可能已在其他地方完成，本次视为成功退出。")
            return True
        else:
            print(f"❌ 领取失败！原因: {res_json.get('msg')} (Code: {code})")
            return False
    except Exception as e:
        print(f"❌ 请求过程中出现异常: {e}")
        return False

def human_delay(min_s, max_s, action="正在等待..."):
    s = random.uniform(min_s, max_s)
    print(f"⏱️ {action} (拟人化延迟: {s:.2f}秒)")
    time.sleep(s)

if __name__ == "__main__":
    print("==========================================")
    print("🌟 IP2Free 自动化助手 - 增强调试模式启动")
    print("==========================================")
    
    if not EMAIL or not PASSWORD:
        print("❌ 错误: 环境变量 EMAIL 或 PASSWORD 未设置，请检查 GitHub Secrets/Vars")
        sys.exit(1)
        
    # 初始入口延迟
    human_delay(5, 15, "正在打开首页...")
    
    if login():
        task_id = get_task_id()
        if handle_captcha():
            if finish_task(task_id):
                print("\n🏁 [DONE] 所有步骤已成功执行，奖励已到账。")
                print("==========================================")
                sys.exit(0)
    
    print("\n🚫 [FAILED] 任务未能完成，请检查上述详细日志进行排查。")
    print("==========================================")
    sys.exit(1)
