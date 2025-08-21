#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取Telegram Chat ID的工具

使用方法：
1. 先向您的机器人发送消息
2. 运行此脚本获取Chat ID
"""

import requests
import sys
import os

def get_chat_id(bot_token):
    """获取Chat ID"""
    if not bot_token:
        print("❌ 请提供Bot Token")
        return None
    
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                updates = data['result']
                
                if updates:
                    # 获取最新的消息
                    latest_message = updates[-1]
                    
                    if 'message' in latest_message:
                        chat = latest_message['message']['chat']
                        chat_id = chat['id']
                        chat_type = chat.get('type', 'unknown')
                        
                        print(f"✅ 找到Chat ID: {chat_id}")
                        print(f"📱 聊天类型: {chat_type}")
                        
                        if chat_type == 'private':
                            user_info = latest_message['message']['from']
                            print(f"👤 用户名: {user_info.get('first_name', 'N/A')}")
                            print(f"🔗 用户名: @{user_info.get('username', 'N/A')}")
                        elif chat_type == 'group':
                            print(f"👥 群组名称: {chat.get('title', 'N/A')}")
                        
                        return chat_id
                    else:
                        print("❌ 没有找到消息数据")
                        return None
                else:
                    print("❌ 没有找到任何更新")
                    print("💡 请先向您的机器人发送一条消息")
                    return None
            else:
                print(f"❌ API返回错误: {data}")
                return None
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def main():
    """主函数"""
    print("🔍 Telegram Chat ID 获取工具")
    print("=" * 40)
    
    # 获取Bot Token
    bot_token = input("请输入您的Bot Token: ").strip()
    
    if not bot_token:
        print("❌ Bot Token不能为空")
        return
    
    print(f"\n📡 正在获取Chat ID...")
    print("💡 请确保您已经向机器人发送过消息")
    
    chat_id = get_chat_id(bot_token)
    
    if chat_id:
        print(f"\n🎉 成功获取Chat ID!")
        print(f"📋 Chat ID: {chat_id}")
        print(f"\n📝 请将此Chat ID添加到您的配置中:")
        print(f"   TELEGRAM_CHAT_ID={chat_id}")
        print(f"\n🔧 或者在config.py中设置:")
        print(f"   'CHAT_ID': '{chat_id}'")
    else:
        print("\n❌ 获取Chat ID失败")
        print("💡 请检查:")
        print("   1. Bot Token是否正确")
        print("   2. 是否已向机器人发送消息")
        print("   3. 网络连接是否正常")

if __name__ == "__main__":
    main() 