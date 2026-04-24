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

def login():
    print("🚀 正在登录...")
    url = "https://api.ip2free.com/api/account/login?"
    data = {"email": EMAIL, "password": PASSWORD}
    try:
        resp = session.post(url, json=data)
        res_json = resp.json()
        token = res_json.get('data', {}).get('token')
        if token:
            session.headers.update({"x-token": token})
            print("✅ 登录成功")
            return True
        else:
            print(f"❌ 登录失败: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return False

def get_task_id():
    print("🔍 正在获取任务 ID...")
    url = "https://api.ip2free.com/api/account/taskList?"
    try:
        resp = session.post(url, json={})
        res_json = resp.json()
        tasks = res_json.get('data', {}).get('list', [])
        for task in tasks:
            if "点击就送" in task.get('task_name', ''):
                print(f"🎯 发现任务 ID: {task.get('id')}")
                return task.get('id')
        print("⚠️ 未能获取到动态任务 ID，使用默认 ID 49130")
        return 49130
    except Exception as e:
        print(f"⚠️ 获取任务列表失败，使用默认 ID 49130. 错误: {e}")
        return 49130

def handle_captcha():
    print("🖼️ 正在获取并识别验证码...")
    ocr = ddddocr.DdddOcr(show_ad=False)
    
    # 多次尝试，防止识别错误
    for i in range(3):
        captcha_url = "https://api.ip2free.com/api/account/captcha?"
        img_resp = session.get(captcha_url)
        if img_resp.status_code != 200:
            print("❌ 获取验证码图片失败")
            continue
            
        res = ocr.classification(img_resp.content)
        print(f"🔢 第 {i+1} 次识别结果: {res}")
        
        # 校验验证码
        check_url = "https://api.ip2free.com/api/account/checkCaptcha?"
        check_resp = session.post(check_url, json={"code": res})
        if check_resp.json().get('code') == 0:
            print("✅ 验证码校验通过")
            return True
        else:
            print(f"❌ 验证码校验失败: {check_resp.text}，准备重试...")
            time.sleep(1)
            
    return False

def finish_task(task_id):
    print(f"🎁 正在领取奖励 (ID: {task_id})...")
    url = "https://api.ip2free.com/api/account/finishTask?"
    try:
        resp = session.post(url, json={"id": task_id})
        res_json = resp.json()
        if res_json.get('code') == 0:
            print(f"🎉 领取成功！消息: {res_json.get('msg')}")
            return True
        else:
            print(f"❌ 领取失败: {res_json.get('msg')} (Code: {res_json.get('code')})")
            return False
    except Exception as e:
        print(f"❌ 领取异常: {e}")
        return False

if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        print("❌ 错误: 环境变量 EMAIL 或 PASSWORD 未设置")
        sys.exit(1)
        
    # 随机延迟
    delay = random.randint(0, 10)
    print(f"⏱️ 随机延迟 {delay} 秒...")
    time.sleep(delay)
    
    if login():
        task_id = get_task_id()
        if handle_captcha():
            if finish_task(task_id):
                print("🏁 任务完成")
                sys.exit(0)
    
    sys.exit(1)
