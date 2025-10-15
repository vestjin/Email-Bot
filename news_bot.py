import http.client
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# 从环境变量读取配置
class Config:
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.qq.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
    SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
    RECEIVER_EMAILS = os.getenv('RECEIVER_EMAILS', '')  # 逗号分隔的邮箱列表
    NEWS_COUNT = int(os.getenv('NEWS_COUNT', '15'))
    LINE_WIDTH = int(os.getenv('LINE_WIDTH', '36'))
    ENABLE_EMAIL = os.getenv('ENABLE_EMAIL', 'true').lower() == 'true'


class ChineseTextFormatter:
    """中文文本格式化工具类"""
    
    @staticmethod
    def get_display_length(text):
        """计算文本的显示长度（中文算2个字符，英文算1个）"""
        length = 0
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                length += 2  # 中文字符
            else:
                length += 1  # 英文字符和数字
        return length
    
    @staticmethod
    def pad_text(text, width, align='left'):
        """填充文本到指定宽度（考虑中英文字符差异）"""
        display_length = ChineseTextFormatter.get_display_length(text)
        padding = width - display_length
        
        if padding <= 0:
            return text
        
        if align == 'left':
            return text + ' ' * padding
        elif align == 'right':
            return ' ' * padding + text
        else:  # center
            left_padding = padding // 2
            right_padding = padding - left_padding
            return ' ' * left_padding + text + ' ' * right_padding
    
    @staticmethod
    def wrap_text(text, width):
        """智能换行文本（考虑中英文字符差异）"""
        if ChineseTextFormatter.get_display_length(text) <= width:
            return [text]
        
        lines = []
        current_line = ""
        
        for char in text:
            char_length = 2 if '\u4e00' <= char <= '\u9fff' else 1
            
            # 如果当前行加上这个字符不会超宽
            if ChineseTextFormatter.get_display_length(current_line) + char_length <= width:
                current_line += char
            else:
                # 如果当前行有内容，先保存
                if current_line:
                    lines.append(current_line)
                    current_line = char
                else:
                    # 单个字符就超宽的情况（理论上不会发生）
                    lines.append(char)
                    current_line = ""
        
        if current_line:
            lines.append(current_line)
        
        return lines


class Daily60s:
    """每日60秒资讯类"""
    
    def __init__(self):
        self.base_url = "60s.viki.moe"
        self.endpoint = "/v2/60s"
    
    def fetch_data(self):
        """获取60秒资讯数据"""
        try:
            conn = http.client.HTTPSConnection(self.base_url)
            payload = ''
            headers = {}
            conn.request("GET", self.endpoint, payload, headers)
            res = conn.getresponse()
            data = res.read()
            data_json = data.decode("utf-8")
            dic_data = json.loads(data_json)
            conn.close()
            return dic_data
        except Exception as e:
            print(f"获取60秒资讯失败: {e}")
            return None
    
    def format_data(self, data):
        """格式化60秒资讯数据 - 中文排版优化版"""
        if not data or 'data' not in data:
            return self._create_error_template("60秒资讯")
        
        news_data = data['data']
        
        # 创建中文优化模板
        template = self._create_chinese_news_template(news_data)
        return template
    
    def _create_chinese_news_template(self, news_data):
        """创建中文优化资讯模板"""
        line_width = Config.LINE_WIDTH
        
        # 头部区域
        header = self._create_chinese_header(news_data, line_width)
        
        # 新闻内容区域
        news_content = self._create_chinese_news_content(news_data, line_width)
        
        return header + news_content
    
    def _create_chinese_header(self, news_data, line_width):
        """创建中文头部区域"""
        date_info = f"{news_data['date']} {news_data['lunar_date']} {news_data['day_of_week']}"
        
        header = f"""
🌅 每日60秒早报
{"=" * line_width}
📅 {date_info}
📊 共{len(news_data['news'])}条新闻
{"=" * line_width}
📰 今日要闻
"""
        return header
    
    def _create_chinese_news_content(self, news_data, line_width):
        """创建中文新闻内容区域"""
        news_content = ""
        
        news_list = news_data['news'][:Config.NEWS_COUNT]
        
        for i, news in enumerate(news_list, 1):
            # 处理中文新闻文本
            formatted_news = self._format_chinese_news_text(news, i, line_width)
            news_content += formatted_news
        
        # 底部信息
        footer = f"""
{"=" * line_width}
💡 每天60秒，知晓天下事
"""
        return news_content + footer
    
    def _format_chinese_news_text(self, news, index, line_width):
        """格式化中文单条新闻文本"""
        # 清理文本
        news = news.strip()
        
        # 编号部分（考虑中英文混合）
        number_part = f"{index:2d}. "
        number_length = ChineseTextFormatter.get_display_length(number_part)
        
        # 内容可用宽度
        content_width = line_width - number_length
        
        # 检查是否需要换行
        if ChineseTextFormatter.get_display_length(news) <= content_width:
            # 单行显示
            return f"{number_part}{news}\n"
        else:
            # 多行显示
            lines = ChineseTextFormatter.wrap_text(news, content_width)
            result = ""
            
            # 第一行带编号
            result += f"{number_part}{lines[0]}\n"
            
            # 后续行缩进（考虑中英文对齐）
            indent = " " * number_length
            for line in lines[1:]:
                # 对缩进行进行填充，确保对齐
                padded_indent = ChineseTextFormatter.pad_text(indent, number_length)
                result += f"{padded_indent}{line}\n"
            
            return result
    
    def _create_error_template(self, service_name):
        """创建错误信息模板"""
        return f"""
❌ {service_name}获取失败
请检查网络连接或稍后重试
"""


class AnswerBook:
    """答案之书类"""
    
    def __init__(self):
        self.base_url = "60s.viki.moe"
        self.endpoint = "/v2/answer"
    
    def fetch_data(self):
        """获取答案之书数据"""
        try:
            conn = http.client.HTTPSConnection(self.base_url)
            payload = ''
            headers = {}
            conn.request("GET", self.endpoint, payload, headers)
            res = conn.getresponse()
            data = res.read()
            data_json = data.decode("utf-8")
            dic_data = json.loads(data_json)
            conn.close()
            return dic_data
        except Exception as e:
            print(f"获取答案之书失败: {e}")
            return None
    
    def format_data(self, data):
        """格式化答案之书数据 - 中文优化版"""
        if not data or 'data' not in data:
            return self._create_error_template("答案之书")
        
        answer_data = data['data']
        return self._create_chinese_answer_template(answer_data)
    
    def _create_chinese_answer_template(self, answer_data):
        """创建中文优化答案模板"""
        line_width = Config.LINE_WIDTH
        
        # 处理长英文答案
        chinese_answer = answer_data['answer']
        english_answer = answer_data['answer_en']
        
        # 对英文进行换行处理
        english_lines = ChineseTextFormatter.wrap_text(english_answer, line_width - 4)
        english_display = "\n".join([f"    {line}" for line in english_lines])
        
        template = f"""
📖 答案之书
{"=" * line_width}
{chinese_answer}

{english_display}
{"=" * line_width}
💫 让答案指引你今天的方向
"""
        return template
    
    def _create_error_template(self, service_name):
        """创建错误信息模板"""
        return f"""
❌ {service_name}获取失败
请检查网络连接或稍后重试
"""


class EmailSender:
    """邮件发送类"""
    
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.port = Config.SMTP_PORT
        self.sender_email = Config.SENDER_EMAIL
        self.sender_password = Config.SENDER_PASSWORD
    
    def send_email_to_list(self, receiver_emails_str, subject, content):
        """发送邮件到多个收件人"""
        try:
            # 检查必要的配置
            if not self.sender_email or not self.sender_password:
                print("❌ 邮箱配置不完整，无法发送邮件")
                return False
            
            # 解析收件人列表
            receiver_emails = [email.strip() for email in receiver_emails_str.split(',') if email.strip()]
            
            if not receiver_emails:
                print("❌ 未配置收件人邮箱")
                return False
            
            print(f"📧 准备发送邮件给 {len(receiver_emails)} 个收件人: {', '.join(receiver_emails)}")
            
            success_count = 0
            for receiver_email in receiver_emails:
                try:
                    # 创建邮件对象
                    message = MIMEMultipart()
                    message["From"] = self.sender_email
                    message["To"] = receiver_email
                    message["Subject"] = subject
                    
                    # 使用纯文本格式，确保中文显示正常
                    message.attach(MIMEText(content, "plain", "utf-8"))
                    
                    # 连接SMTP服务器并发送邮件
                    server = smtplib.SMTP(self.smtp_server, self.port)
                    server.starttls()  # 启用TLS加密
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(self.sender_email, receiver_email, message.as_string())
                    server.quit()
                    
                    print(f"✅ 邮件发送成功给: {receiver_email}")
                    success_count += 1
                    
                except Exception as e:
                    print(f"❌ 发送给 {receiver_email} 失败: {e}")
            
            print(f"🎉 邮件发送完成！成功发送给 {success_count}/{len(receiver_emails)} 个收件人")
            return success_count > 0
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False


class DailyReport:
    """每日报告生成类"""
    
    def __init__(self):
        self.daily_60s = Daily60s()
        self.answer_book = AnswerBook()
    
    def generate_report(self):
        """生成中文优化报告"""
        print("🔄 正在获取每日数据...")
        
        # 获取数据
        daily_data = self.daily_60s.fetch_data()
        answer_data = self.answer_book.fetch_data()
        
        # 格式化数据
        daily_content = self.daily_60s.format_data(daily_data) if daily_data else "❌ 无法获取60秒资讯"
        answer_content = self.answer_book.format_data(answer_data) if answer_data else "❌ 无法获取答案之书"
        
        # 生成完整报告
        template = self._create_complete_template(daily_content, answer_content)
        
        return template
    
    def _create_complete_template(self, daily_content, answer_content):
        """创建完整报告模板"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        template = f"""
✨ 每日智慧报告 ✨
生成时间: {current_time}

{daily_content}

{answer_content}

🌟 祝您有美好的一天！ 🌟
"""
        return template


def main():
    """主函数"""
    # 创建报告生成器
    report_generator = DailyReport()
    
    # 生成报告
    report_content = report_generator.generate_report()
    
    # 在控制台打印结果
    print("\n" + "=" * 50)
    print("每日报告内容:")
    print("=" * 50)
    print(report_content)
    
    # 发送邮件
    if Config.ENABLE_EMAIL and Config.SENDER_EMAIL and Config.SENDER_PASSWORD and Config.RECEIVER_EMAILS:
        email_sender = EmailSender()
        subject = f"📰 每日资讯 - {datetime.now().strftime('%Y-%m-%d')}"
        success = email_sender.send_email_to_list(Config.RECEIVER_EMAILS, subject, report_content)
        
        if not success:
            print("❌ 邮件发送失败，请检查配置")
    else:
        print("ℹ️  邮件功能未启用或配置不完整")
        if not Config.ENABLE_EMAIL:
            print("💡 设置 ENABLE_EMAIL=true 启用邮件发送")
        if not Config.SENDER_EMAIL:
            print("💡 请配置 SENDER_EMAIL")
        if not Config.SENDER_PASSWORD:
            print("💡 请配置 SENDER_PASSWORD")
        if not Config.RECEIVER_EMAILS:
            print("💡 请配置 RECEIVER_EMAILS (多个邮箱用逗号分隔)")


if __name__ == "__main__":
    main()