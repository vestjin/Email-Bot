import os
import time
import jwt
import requests
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# 从环境变量读取配置信息
class Config:
    # 和风天气配置
    QWEATHER_PRIVATE_KEY = os.environ.get('QWEATHER_PRIVATE_KEY')
    QWEATHER_API_HOST = "https://n84nmtek7c.re.qweatherapi.com"
    QWEATHER_LOCATION = os.environ.get('QWEATHER_LOCATION', '114.58,37.51')  
    QWEATHER_SUB = os.environ.get('QWEATHER_SUB')
    QWEATHER_KID = os.environ.get('QWEATHER_KID')
    
    # 邮箱配置
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
    SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD')
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.qq.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    
    # 收件人列表
    RECIPIENTS = os.environ.get('RECIPIENT_EMAILS', '').split(',')
    
    @classmethod
    def validate(cls):
        """验证必要的配置是否存在"""
        required_vars = [
            'QWEATHER_PRIVATE_KEY',
            'SENDER_EMAIL', 
            'SENDER_PASSWORD'
        ]
        
        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"缺少必要的环境变量: {', '.join(missing)}")


def generate_JWT():
    """通过和风天气的private_key生成JWT token"""
    if not Config.QWEATHER_PRIVATE_KEY:
        raise ValueError("和风天气私钥未配置")
    
    payload = {
        'iat': int(time.time()) - 30,
        'exp': int(time.time()) + 300,
        'sub': Config.QWEATHER_SUB
    }
    headers = {
        'kid': Config.QWEATHER_KID
    }

    # Generate JWT
    encoded_jwt = jwt.encode(payload, Config.QWEATHER_PRIVATE_KEY, algorithm='EdDSA', headers=headers)
    return encoded_jwt


def request_weather_json():
    """根据生成的jwt request天气数据并返回json数据"""
    JWT_TOKEN = generate_JWT()

    # 构建完整URL
    url = f"{Config.QWEATHER_API_HOST}/v7/weather/3d?location={Config.QWEATHER_LOCATION}"
    headers = {
        'Authorization': f'Bearer {JWT_TOKEN}'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API请求失败，状态码: {response.status_code}")


def parse_weather_data(raw_data):
    """解析原始天气数据为邮件生成所需的格式"""
    daily_data = raw_data['daily']
    parsed_list = []

    for day in daily_data:
        parsed_list.append({
            "日期": day['fxDate'],
            "白天天气": day['textDay'],
            "夜晚天气": day['textNight'],
            "最高温度": day['tempMax'],
            "最低温度": day['tempMin'],
            "白天风向": day['windDirDay'],
            "白天风力等级": day['windScaleDay'],
            "白天风速": f"{day['windSpeedDay']}公里/小时",
            "夜晚风向": day['windDirNight'],
            "夜晚风力等级": day['windScaleNight'],
            "夜晚风速": f"{day['windSpeedNight']}公里/小时",
            "当天总降水量": day['precip'],
            "紫外线强度": day['uvIndex'],
            "相对湿度": day['humidity'],
            "能见度": day['vis'],
            "月相": day['moonPhase'],
            "大气压强": day['pressure'],
            "云量": day['cloud']
        })

    return parsed_list


def generate_weather_email(data):
    """
    根据天气数据生成美化的HTML邮件内容
    """
    # HTML模板
    html_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: 'Arial', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f7fa;
            margin: 0;
            padding: 20px;
        }
        .weather-container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: bold;
        }
        .date-range {
            margin-top: 10px;
            font-size: 18px;
            opacity: 0.9;
        }
        .days-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            padding: 30px;
        }
        .day-card {
            background: #fff;
            border-radius: 10px;
            border: 1px solid #e1e8ed;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .day-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        .card-header {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-bottom: 1px solid #e1e8ed;
        }
        .date {
            font-size: 18px;
            font-weight: bold;
            color: #2d3436;
            margin-bottom: 5px;
        }
        .moon-phase {
            font-size: 14px;
            color: #636e72;
        }
        .card-content {
            padding: 20px;
        }
        .temperature-section {
            text-align: center;
            margin-bottom: 20px;
        }
        .temp-high {
            font-size: 32px;
            font-weight: bold;
            color: #e17055;
        }
        .temp-low {
            font-size: 24px;
            color: #74b9ff;
            margin-left: 10px;
        }
        .weather-icon {
            font-size: 36px;
            margin: 15px 0;
        }
        .weather-details {
            display            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            font-size: 14px;
        }
        .detail-item {
            display            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px dashed #eee;
        }
        .detail-label {
            color: #636e72;
            font-weight: normal;
        }
        .detail-value {
            font-weight: bold;
            color: #2d3436;
        }
        .day-night-section {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        .time-label {
            font-size: 12px;
            color: #636e72;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #e1e8ed;
            color: #636e72;
            font-size: 14px;
        }
        
        /* 特殊样式 */
        .rainy-day {
            border-left: 4px solid #74b9ff;
        }
        .sunny-day {
            border-left: 4px solid #fdcb6e;
        }
        .cloudy-day {
            border-left: 4px solid #b2bec3;
        }
        .clear-day {
            border-left: 4px solid #00cec9;
        }
    </style>
</head>
<body>
    <div class="weather-container">
        <div class="header">
            <h1>📊 天气预报报告</h1>
            <div class="date-range">{start_date} - {end_date}</div>
        </div>
        
        <div class="days-container">
            {days_content}
        </div>
        
        <div class="footer">
            数据更新时间: {update_time} | 祝你度过愉快的一天! 🌈
        </div>
    </div>
</body>
</html>
'''

    # 配置映射字典
    WEATHER_ICONS = {
        '晴': '☀️',
        '多云': '⛅',
        '小雨': '🌦️',
        '中雨': '🌧️',
        '大雨': '💦',
        '阴': '☁️'
    }

    MOON_ICONS = {
        '下弦月': '🌗',
        '残月': '🌘',
        '新月': '🌑',
        '上弦月': '🌓',
        '满月': '🌕'
    }

    UV_LEVELS = {
        0: '很低', 1: '很低', 2: '低', 3: '中等', 4: '中等', 
        5: '中等', 6: '高', 7: '高', 8: '很高', 9: '很高', 
        10: '极高', 11: '极高'
    }

    def get_weather_icon(weather):
        """根据天气状况返回对应的图标"""
        return WEATHER_ICONS.get(weather, '🌈')

    def get_moon_icon(moon_phase):
        """根据月相返回图标"""
        return MOON_ICONS.get(moon_phase, '🌙')

    def get_uv_description(uv_index):
        """根据紫外线指数返回描述"""
        level_text = UV_LEVELS.get(int(uv_index), '未知')
        return f"{level_text} ({uv_index})"

    def get_day_class(day_data):
        """根据天气状况返回对应的CSS类名"""
        weather_conditions = [
            ('雨', 'rainy-day'),
            ('晴', 'sunny-day'),
            ('多云', 'cloudy-day')
        ]
        
        for condition, css_class in weather_conditions:
            if condition in day_data['白天天气'] or condition in day_data['夜晚天气']:
                return css_class
        return 'clear-day'

    def format_day_card(day_data):
        """格式化单天天气卡片"""
        day_class = get_day_class(day_data)
        moon_icon = get_moon_icon(day_data["月相"])
        
        # 定义要显示的详情项
        detail_items = [
            ("白天天气", f"{day_data['白天天气']} {get_weather_icon(day_data['白天天气'])}"),
            ("夜晚天气", f"{day_data['夜晚天气']} {get_weather_icon(day_data['夜晚天气'])}"),
            ("降水量", f"{day_data['当天总降水量']} mm"),
            ("紫外线", get_uv_description(day_data["紫外线强度"])),
            ("湿度", f"{day_data['相对湿度']}% 💧"),
            ("能见度", f"{day_data['能见度']} km 👁️")
        ]
        
        # 生成详情项HTML
        details_html = ""
        for label, value in detail_items:
            details_html += f'''
                        <div class="detail-item">
                            <span class="detail-label">{label}</span>
                            <span class="detail-value">{value}</span>
                        </div>'''
        
        return f'''
            <div class="day-card {day_class}">
                <div class="card-header">
                    <div class="date">{day_data["日期"]}</div>
                    <div class="moon-phase">{moon_icon} {day_data["月相"]}</div>
                </div>
                <div class="card-content">
                    <div class="temperature-section">
                        <span class="temp-high">{day_data["最高温度"]}°C</span>
                        <span class="temp-low">{day_data["最低温度"]}°C</span>
                        <div class="weather-icon">
                            {get_weather_icon(day_data["白天天气"])}
                        </div>
                    </div>
                    
                    <div class="weather-details">
                        {details_html}
                    </div>
                    
                    <div class="day-night-section">
                        <div class="time-label">🌅 白天风向</div>
                        <div>{day_data["白天风向"]} {day_data["白天风力等级"]} ({day_data["白天风速"]})</div>
                        
                        <div class="time-label" style="margin-top: 10px;">🌙 夜晚风向</div>
                        <div>{day_data["夜晚风向"]} {day_data["夜晚风力等级"]} ({day_data["夜晚风速"]})</div>
                    </div>
                </div>
            </div>
        '''

    # 生成每一天的内容
    days_content = "".join([format_day_card(day_data) for day_data in data])
    
    # 计算日期范围
    start_date = data[0]["日期"]
    end_date = data[-1]["日期"]
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 填充模板
    final_html = html_template.format(
        start_date=start_date,
        end_date=end_date,
        days_content=days_content,
        update_time=update_time
    )

    return final_html


def send_weather_email(recipient_email, weather_data):
    """
    发送天气邮件
    """
    
    # 生成HTML内容
    html_content = generate_weather_email(weather_data)
    
    # 创建纯文本备选内容
    text_content = f"""天气预报报告 ({weather_data[0]['日期']} - {weather_data[-1]['日期']})"""
    for day in weather_data:
        text_content += f"""
                        {day['日期']}:
                        天气: {day['白天天气']} / {day['夜晚天气']}
                        温度: {day['最高温度']}°C / {day['最低温度']}°C
                        降水: {day['当天总降水量']}mm
                        湿度: {day['相对湿度']}%
                        紫外线: {day['紫外线强度']}
                        风向: 白天{day['白天风向']}{day['白天风力等级']}, 夜晚{day['夜晚风向']}{day['夜晚风力等级']}
                        
                        """
    
    # 创建邮件对象
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📊 天气预报 {weather_data[0]['日期']} - {weather_data[-1]['日期']}"
    msg['From'] = Config.SENDER_EMAIL
    msg['To'] = recipient_email
    
    # 添加两种格式的内容
    part1 = MIMEText(text_content, 'plain', 'utf-8')
    part2 = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        # 连接SMTP服务器并发送
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
        server.starttls()
        server.login(Config.SENDER_EMAIL, Config.SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ 天气邮件已成功发送至 {recipient_email}")
    except Exception as e:
        print(f"❌ 发送失败: {e}")


def main():
    """主函数"""
    try:
        print("🚀 开始获取天气数据...")
        
        # 验证配置
        Config.validate()
        
        # 获取真实天气数据
        raw_weather_data = request_weather_json()
        weather_data_for_email = parse_weather_data(raw_weather_data)
        
        print("📊 天气数据获取成功!")
        print(f"📅 预报日期: {weather_data_for_email[0]['日期']} - {weather_data_for_email[-1]['日期']}")
        
        # 发送给所有收件人
        for recipient in Config.RECIPIENTS:
            if recipient.strip():
                print(f"📨 正在发送邮件给: {recipient.strip()}")
                send_weather_email(recipient.strip(), weather_data_for_email)
                
        print("🎉 所有邮件发送完成!")
        
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        raise


if __name__ == "__main__":
    main()