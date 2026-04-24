import requests
import ddddocr
import os
import sys
import json
import time
import random
import base64

# 配置信息
ACCOUNTS_STR = os.getenv('IP2FREE_ACCOUNTS', "")
SHARE_KEY = os.getenv('SHARE_KEY')
UPDATE_URL = os.getenv('UPDATE_URL')
UA = os.getenv('UA', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

def create_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": UA,
        "Origin": "https://www.ip2free.com",
        "Referer": "https://www.ip2free.com/",
        "webname": "IP2FREE",
        "lang": "cn",
        "content-type": "text/plain;charset=UTF-8"
    })
    return session

def get_token_file(email):
    safe_email = email.replace("@", "_").replace(".", "_")
    return f"token_cache_{safe_email}.txt"

def load_token(email):
    token_file = get_token_file(email)
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                token = f.read().strip()
                if token:
                    print(f"📖 [{email}] 发现本地缓存 Token: {token[:10]}***")
                    return token
        except:
            pass
    return None

def save_token(email, token):
    token_file = get_token_file(email)
    try:
        with open(token_file, 'w') as f:
            f.write(token)
        print(f"💾 [{email}] Token 已缓存到本地文件")
    except Exception as e:
        print(f"⚠️ [{email}] 缓存 Token 失败: {e}")

def is_token_valid(session, email):
    """通过请求任务列表校验当前 Token 是否有效"""
    url = "https://api.ip2free.com/api/account/taskList?"
    try:
        resp = session.post(url, json={}, timeout=10)
        res_json = resp.json()
        return res_json.get('code') == 0
    except:
        return False

def login(session, email, password):
    cached_token = load_token(email)
    if cached_token:
        session.headers.update({"x-token": cached_token})
        if is_token_valid(session, email):
            print(f"✨ [{email}] 缓存 Token 有效，跳过登录步骤")
            return True
        else:
            print(f"♻️ [{email}] 缓存 Token 已过期或失效，准备重新登录...")

    print(f"🚀 [{email}] [Step 1] 正在模拟用户登录...")
    url = "https://api.ip2free.com/api/account/login?"
    log_data = {"email": email, "password": "***HIDDEN***"}
    print(f"📤 发送登录请求 | URL: {url} | Payload: {json.dumps(log_data)}")
    
    data = {"email": email, "password": password}
    try:
        resp = session.post(url, json=data)
        res_json = resp.json()
        token = res_json.get('data', {}).get('token')
        if token:
            session.headers.update({"x-token": token})
            save_token(email, token)
            print(f"✅ [{email}] 登录成功，新 Token 已保存")
            return True
        else:
            print(f"❌ [{email}] 登录失败！服务器返回: {res_json.get('msg', '未知错误')}")
            return False
    except Exception as e:
        print(f"❌ [{email}] 登录过程中出现异常: {e}")
        return False

def update_online_subscription(content_list):
    """自动更新在线分享的内容"""
    if not SHARE_KEY or not UPDATE_URL:
        print("⚠️ 未配置在线订阅环境变量，跳过同步。")
        return

    print("📤 [Final Step] 正在同步到在线订阅服务...")
    url = UPDATE_URL
    proxy_content = "\n".join(content_list)
    payload = {"editToken": SHARE_KEY, "content": proxy_content}
    
    try:
        # 这里用一个干净的 session
        temp_session = requests.Session()
        resp = temp_session.post(url, json=payload, timeout=15)
        res_json = resp.json()
        
        if res_json.get('code') == 200 or res_json.get('success') is True:
            print("✅ 在线订阅更新成功！")
        else:
            print("❌ 在线订阅更新失败！")
    except Exception as e:
        print("❌ 在线订阅同步异常。")

def fetch_proxy_links(session, email):
    """获取活动代理列表并生成链接"""
    print(f"🔗 [{email}] [Step 5] 正在提取可用代理节点链接...")
    url = "https://api.ip2free.com/api/ip/taskIpList?"
    payload = {"keyword":"","country":"","city":"","page":1,"page_size":10}
    
    try:
        resp = session.post(url, json=payload)
        if resp.status_code != 200:
             print(f"❌ [{email}] 请求失败，状态码: {resp.status_code}")
             return []

        res_json = resp.json()
        items = res_json.get('data', {}).get('page', {}).get('list', [])
        
        if not items:
            print(f"ℹ️ [{email}] 活动代理列表中暂无可用节点。")
            return []
            
        link_list = [] 
        for item in items:
            user = item.get('username', '')
            pw = item.get('password', '')
            ip = item.get('ip', '')
            port = item.get('port', '')
            country = item.get('country_code', 'Proxy')
            
            if not all([user, pw, ip, port]):
                continue

            auth_str = f"{user}:{pw}"
            auth_b64 = base64.b64encode(auth_str.encode()).decode()
            link = f"socks://{auth_b64}@{ip}:{port}#{country}-{ip}"
            link_list.append(link)
            
        print(f"✨ [{email}] 成功提取到 {len(link_list)} 个可用代理节点。")
        return link_list
        
    except Exception as e:
        print(f"❌ [{email}] 提取代理链接过程中出现异常: {e}")
        return []

def print_proxy_details(task):
    task_name = task.get('task_name', '未知任务')
    items = task.get('items', [])
    print("\n" + "="*40)
    print(f"📊 【代理奖励详情】")
    print(f"任务名称: {task_name}")
    print("-" * 20)
    if not items:
        print("ℹ️ 暂无具体的代理明细数据。")
    else:
        for item in items:
            country = item.get('country_code', '未知')
            qty = item.get('quantity', 0)
            print(f"📍 国家/地区: {country.ljust(6)} | 数量: {qty} 条/天")
    finish_at = task.get('finished_at')
    if finish_at:
        print(f"⏰ 领取时间: {finish_at}")
    print("="*40 + "\n")

def get_task_id(session, email):
    human_delay(3, 7, f"[{email}] 正在浏览任务中心...")
    print(f"🔍 [{email}] [Step 2] 正在获取任务列表...")
    url = "https://api.ip2free.com/api/account/taskList?"
    
    try:
        resp = session.post(url, json={})
        res_json = resp.json()
        tasks = res_json.get('data', {}).get('list', [])
        for task in tasks:
            task_name = task.get('task_name', '')
            if "点击就送" in task_name:
                task_id = task.get('id')
                is_finished = task.get('is_finished') or task.get('is_finish')
                
                print(f"🎯 [{email}] 发现目标任务: '{task_name}' | ID: {task_id} | 状态码: {is_finished}")
                if is_finished == 1:
                    print(f"✨ [{email}] 检测到该任务已经处于完成状态（页面显示‘查看奖励’），无需继续操作。")
                    print_proxy_details(task)
                    return -1 
                return task_id
        
        print(f"⚠️ [{email}] 未能在列表中发现匹配任务，尝试使用兜底 ID 49130")
        return 49130
    except Exception as e:
        print(f"⚠️ [{email}] 获取任务列表失败: {e}，将尝试使用兜底 ID")
        return 49130

def handle_captcha(session, email):
    print(f"🖼️ [{email}] [Step 3] 发现需要验证码，正在准备识别...")
    ocr = ddddocr.DdddOcr(show_ad=False)
    
    for i in range(3):
        human_delay(2, 4, f"[{email}] 正在加载验证码图片...")
        captcha_url = "https://api.ip2free.com/api/account/captcha?"
        
        img_resp = session.get(captcha_url)
        if img_resp.status_code != 200:
            print(f"❌ [{email}] 验证码下载失败，状态码: {img_resp.status_code}")
            continue
            
        res = ocr.classification(img_resp.content)
        print(f"🔢 [{email}] OCR 识别完成 | 识别结果: {res} (尝试次序: {i+1}/3)")
        
        if len(res) < 4:
            print(f"⚠️ [{email}] 识别结果异常 (长度为 {len(res)}，不足 4 位)，将自动刷新重试...")
            continue

        human_delay(2, 4, f"[{email}] 正在输入验证码并点击校验...")
        
        check_url = "https://api.ip2free.com/api/account/checkCaptcha?"
        check_payload = {"code": res}
        
        check_resp = session.post(check_url, json=check_payload)
        check_res_json = check_resp.json()
        
        if check_res_json.get('code') == 0:
            print(f"✅ [{email}] 验证码校验通过，安全校验已完成")
            return True
        else:
            print(f"❌ [{email}] 验证码错误: {check_res_json.get('msg')}，正在刷新验证码重试...")
            
    print(f"❌ [{email}] 连续 3 次验证码校验失败或格式错误，放弃任务")
    return False

def finish_task(session, email, task_id):
    human_delay(3, 6, f"[{email}] 正在点击‘立即领取’按钮...")
    
    print(f"🎁 [{email}] [Step 4] 正在执行最终领取操作 (TaskID: {task_id})...")
    url = "https://api.ip2free.com/api/account/finishTask?"
    payload = {"id": task_id}
    
    try:
        resp = session.post(url, json=payload)
        res_json = resp.json()
        msg = res_json.get('msg', '').lower()
        code = res_json.get('code')
        
        if code == 0:
            print(f"🎉 [{email}] 任务圆满完成！服务器消息: {res_json.get('msg')}")
            print(f"🔄 [{email}] 正在刷新奖励详情以展示...")
            human_delay(2, 4, f"[{email}] 正在同步服务器状态...")
            get_task_id(session, email) 
            return True
        elif "invalid" in msg or "已经完成" in msg or "重复领取" in msg:
            print(f"⚠️ [{email}] 提示: {res_json.get('msg')}。由于任务可能已在其他地方完成，本次视为成功退出。")
            return True
        else:
            print(f"❌ [{email}] 领取失败！原因: {res_json.get('msg')} (Code: {code})")
            return False
    except Exception as e:
        print(f"❌ [{email}] 请求过程中出现异常: {e}")
        return False

def human_delay(min_s, max_s, action="正在等待..."):
    s = random.uniform(min_s, max_s)
    print(f"⏱️ {action} (拟人化延迟: {s:.2f}秒)")
    time.sleep(s)

if __name__ == "__main__":
    print("==========================================")
    print("🌟 IP2Free 多账号自动助手启动")
    print("==========================================")
    
    if not ACCOUNTS_STR:
        print("❌ 错误: 环境变量 IP2FREE_ACCOUNTS 未设置")
        sys.exit(1)
        
    accounts = [a.split(',') for a in ACCOUNTS_STR.split(';') if ',' in a]
    random.shuffle(accounts)
    print(f"📝 共有 {len(accounts)} 个账号待执行，已随机化顺序。")
    
    all_links = []

    for i, (email, password) in enumerate(accounts):
        print("\n" + "="*40)
        print(f"▶️ [账号 {i+1}/{len(accounts)}] 开始执行: {email}")
        print("="*40)
        
        # 为每个账号创建一个独立的 Session
        session = create_session()
        
        if login(session, email, password):
            task_id = get_task_id(session, email)
            
            if task_id == -1:
                print(f"🎉 [{email}] 今日任务之前已经完成了。")
            else:
                if handle_captcha(session, email):
                    finish_task(session, email, task_id)
                else:
                    print(f"🚫 [{email}] 验证码处理失败，跳过领取环节。")
            
            # 获取该账号下的所有节点
            links = fetch_proxy_links(session, email)
            all_links.extend(links)
        else:
            print(f"🚫 [{email}] 登录失败，跳过该账号。")
            
        # 账号之间的间隔
        if i < len(accounts) - 1:
            human_delay(10, 20, "账号切换中，等待一段时间...")

    print("\n" + "="*40)
    print(f"🏁 [ALL DONE] 所有账号执行完毕，共收集到 {len(all_links)} 个节点。")
    print("="*40)
    
    if all_links:
        # 去重并更新订阅
        unique_links = list(set(all_links))
        update_online_subscription(unique_links)
    
    sys.exit(0)
