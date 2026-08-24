import os
import sys
import yaml
import msvcrt
import hashlib
import smtplib
import logging
import pystray
import threading
from PIL import Image
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox
from tkinter import scrolledtext
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(
    filename='main.log',
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

file_hash = None

def acquire_lock():
    """創建鎖 避免同時執行"""
    try:
        lock_file = open("app.lock", 'w')
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        return lock_file
    except IOError:
        sys.exit(1)

def release_lock(lock_file):
    """釋放鎖"""
    lock_file.close()
    os.remove("app.lock")

def calculate_hash(file_path):
    """計算文件的 hash"""
    hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash.update(chunk)
    return hash.hexdigest()

def check_file_change(file_path):
    """檢查 hash 是否變更"""
    global file_hash
    current_hash = calculate_hash(file_path)
    has_changed = (current_hash != file_hash)
    file_hash = current_hash
    return has_changed

def send_notification():
    """發送郵件通知"""

    # 提取郵件伺服器和發送者資訊
    with open("config.yml", "r", encoding="utf-8") as config_file:
        config_data = yaml.load(config_file, Loader=yaml.Loader)

        smtp_server = config_data.get('sender', {}).get('smtp_server', '')
        smtp_port = config_data.get('sender', {}).get('smtp_port', 0)
        sender_email = config_data.get('sender', {}).get('email', '')
        sender_password = config_data.get('sender', {}).get('password', '')

        # 提取收件者列表
        recipients = [email for recipient in config_data.get('recipients', []) for email in recipient.get('email', [])]

    # 連接郵件伺服器
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
    except Exception as e:
        logging.error(f"Error connecting to SMTP server: {e}")
        return False
    
    try:
        # 準備郵件內容
        msg = MIMEMultipart()
        msg['Subject'] = config_data.get('email_content', {}).get('subject', '')
        msg['From'] = sender_email
        msg['To'] = ", ".join(recipients)
        file_content = read_file_content(txt_file_path)
        message = f"Content of the {txt_file_path} has changed.\n\nCurrent file content:\n{file_content}"

        msg.attach(MIMEText(message, 'plain'))
        
        server.sendmail(sender_email, recipients, msg.as_string())
    except Exception as e:
        logging.error(f"Error sending mail: {e}")
    else:
        logging.info("Mail sending success.")
    finally:
        try:
            server.quit()
        except Exception as e:
            logging.error(f"Error quitting SMTP server: {e}")
            pass

def read_file_content(file_path):
    """讀取檔案內容"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
    
def open_settings_window():
    """顯示設定 config 視窗"""
    def exit_action():
        res = tk.messagebox.askokcancel('提示','確認關閉?')
        if res:
            win.attributes('-disabled', False)
            settings_win.grab_release()
            settings_win.destroy()
        else:
            return

    def update_recipients_email(*args):
        """顯示當前選取的收件者的郵件"""
        selected_index = recipients_listbox.curselection()
        recipients_email_text.config(state='normal')
        recipients_email_text.delete("1.0", tk.END)  # 清空之前的內容

        if selected_index:
            selected_recipient = config_data.get('recipients', [])[selected_index[0]]
            for email in selected_recipient.get('email', []):
                recipients_email_text.insert(tk.END, email + '\n')
        
        recipients_email_text.config(state='disable')

    with open("config.yml", "r", encoding="utf-8") as config_file:
        config_data = yaml.load(config_file, Loader=yaml.Loader)
        
        def save_settings():
            """儲存 setting 的更動"""
            config_data['sender']['email'] = email_bar.get()
            config_data['sender']['password'] = password_bar.get()
            config_data['sender']['smtp_server'] = smtp_server_bar.get()
            config_data['sender']['smtp_port'] = smtp_port_bar.get()
            config_data['email_content']['subject'] = subject_bar.get()
            config_data['system_set']['log_switch'] = log_switch_var.get()

            # 覆寫 config.yml
            with open("config.yml", "w", encoding="utf-8") as config_file:
                yaml.dump(config_data, config_file, default_flow_style=False, sort_keys=False)

            tk.messagebox.showinfo('提示','儲存成功')
            win.attributes('-disabled', False)
            settings_win.grab_release()
            settings_win.destroy()

            # 重新讀取 config
            try:
                with open("config.yml", "r", encoding="utf-8") as new_config_file:
                    return yaml.load(new_config_file, Loader=yaml.Loader)
            except Exception as e:
                logging.error(f"Error loading updated config.yml: {e}")

        # Create settings window
        settings_win = tk.Toplevel(win)
        settings_win.resizable(width=False, height=False)
        settings_win.iconbitmap("icon.ico")
        settings_win.title("Settings")
        settings_win.grab_set()
        win.attributes('-disabled', True)  # 限制對主視窗的操作

        settings_win.protocol("WM_DELETE_WINDOW", exit_action)

        left_frame = ttk.Frame(settings_win)
        left_frame.grid(row=0, column=0, sticky="nw", padx=5, pady=5)

        right_frame = ttk.Frame(settings_win)
        right_frame.grid(row=0, column=1, sticky="ne", padx=5, pady=5)

        # File settings
        group1 = ttk.LabelFrame(left_frame, text="File")
        group1.grid(row=0, column=0, sticky="nw", padx=5, pady=5)

        file_label = ttk.Label(group1, text="           name:")
        file_label.grid(row=1, column=0, sticky="e", padx=5, pady=5)

        default_file_name = config_data.get('file', {}).get('name', 'file.txt')
        file_bar = ttk.Entry(group1)
        file_bar.grid(row=1, column=1, sticky="e", padx=5, pady=5)
        file_bar.insert(0, default_file_name)
        file_bar.config(state="readonly")

        # Sender settings
        group2 = ttk.LabelFrame(left_frame, text="Sender")
        group2.grid(row=2, column=0, sticky="nw", padx=5, pady=5)

        email_label = ttk.Label(group2, text="email:")
        email_label.grid(row=3, column=0, sticky="e", padx=5, pady=5)

        password_label = ttk.Label(group2, text="password:")
        password_label.grid(row=4, column=0, sticky="e", padx=5, pady=5)

        smtp_server_label = ttk.Label(group2, text="smtp server:")
        smtp_server_label.grid(row=5, column=0, sticky="e", padx=5, pady=5)

        smtp_port_label = ttk.Label(group2, text="smtp port:")
        smtp_port_label.grid(row=6, column=0, sticky="e", padx=5, pady=5)

        default_email = config_data.get('sender', {}).get('email', '')
        email_bar = ttk.Entry(group2)
        email_bar.grid(row=3, column=1, sticky="e", padx=5, pady=5)
        email_bar.insert(0, default_email)

        default_password = config_data.get('sender', {}).get('password', '')
        password_bar = ttk.Entry(group2, show="*")
        password_bar.grid(row=4, column=1, sticky="e", padx=5, pady=5)
        password_bar.insert(0, default_password)

        default_smtp_server = config_data.get('sender', {}).get('smtp_server', '')
        smtp_server_bar = ttk.Entry(group2)
        smtp_server_bar.grid(row=5, column=1, sticky="e", padx=5, pady=5)
        smtp_server_bar.insert(0, default_smtp_server)

        default_smtp_port = config_data.get('sender', {}).get('smtp_port', '587')
        smtp_port_bar = ttk.Entry(group2)
        smtp_port_bar.grid(row=6, column=1, sticky="e", padx=5, pady=5)
        smtp_port_bar.insert(0, default_smtp_port)

        # Email content settings
        group3 = ttk.LabelFrame(left_frame, text="Email content")
        group3.grid(row=7, column=0, sticky="nw", padx=5, pady=5)

        subject_label = ttk.Label(group3, text="        subject:")
        subject_label.grid(row=8, column=0, sticky="e", padx=5, pady=5)

        default_subject = config_data.get('email_content', {}).get('subject', 'Content change reminder')
        subject_bar = ttk.Entry(group3)
        subject_bar.grid(row=8, column=1, sticky="e", padx=5, pady=5)
        subject_bar.insert(0, default_subject)

        # System settings
        group4 = ttk.LabelFrame(left_frame, text="System set")
        group4.grid(row=9, column=0, sticky="nw", padx=5, pady=5)

        log_switch_label = ttk.Label(group4, text=" log switch:")
        log_switch_label.grid(row=10, column=0, sticky="e", padx=5, pady=5)

        log_switch_var = tk.StringVar(value="on")
        log_switch_bar = ttk.Combobox(group4, textvariable=log_switch_var, values=["on", "off"])
        log_switch_bar.grid(row=10, column=1, sticky="e", padx=5, pady=5)

        # Recipients settings
        group5 = ttk.LabelFrame(right_frame, text="Recipients")
        group5.grid(row=0, column=0, padx=5, pady=5)

        recipients_label = ttk.Label(group5, text="name:")
        recipients_label.grid(row=0, column=0, sticky="nw", padx=5, pady=5)

        recipients_listbox = tk.Listbox(group5, selectmode=tk.SINGLE)
        recipients_listbox.grid(row=1, column=0, rowspan=1, padx=5, pady=5)

        for recipient in config_data.get('recipients', []):
            recipients_listbox.insert(tk.END, recipient['name'])

        recipients_listbox.bind('<<ListboxSelect>>', update_recipients_email)

        recipients_email_label = ttk.Label(group5, text="email:")
        recipients_email_label.grid(row=0, column=1, sticky="nw", padx=5, pady=5)

        recipients_email_text = tk.Text(group5, height=12, width=30)
        recipients_email_text.grid(row=1, column=1, sticky="nw", padx=5, pady=5)

        button_frame = ttk.Frame(settings_win)
        button_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="se")

        # save button
        save_button = ttk.Button(button_frame, text="Save", command=save_settings)
        save_button.grid(row=0, column=0, padx=5, pady=5)

        # exit button
        exit_button = ttk.Button(button_frame, text="Exit", command=exit_action)
        exit_button.grid(row=0, column=1, padx=5, pady=5)

def minimize_window():
    """最小化視窗"""
    win.withdraw()

    def show_action(icon):
        icon.stop()
        win.after(0, win.deiconify)

    def exit_action(icon):
        release_lock(lock_file)
        icon.stop()
        win.destroy()
        os._exit(0)

    menu = (pystray.MenuItem('Show', show_action),
            pystray.MenuItem('Exit', exit_action))

    image = Image.open('icon.ico')
    icon = pystray.Icon("ChangeNotifier", image, menu=menu)
    icon.run()

def exit():
    """離開應用程式"""
    res = tk.messagebox.askokcancel('提示','確認關閉?')
    if res:
        release_lock(lock_file)
        win.destroy()
        os._exit(0)
    else:
        return

def update_log():
    """更新 log 文本框內容"""
    with open('main.log', 'r', encoding='utf-8') as log_file:
        log_content = log_file.read()
        log_text.config(state='normal')
        log_text.delete(1.0, tk.END)  # 清空文本框
        log_text.insert(tk.END, log_content)
        log_text.see(tk.END)  # 移到 log 底端
        log_text.config(state='disable')

def clear_log():
    """清空log的事件處理"""
    res = tk.messagebox.askokcancel('提示','確認清空?')
    if res:
        with open('main.log', 'w', encoding='utf-8') as log_file:
            log_file.truncate(0)
        log_text.config(state='normal')
        log_text.delete(1.0, tk.END)  # 清空文本框
        log_text.config(state='disable')

        tk.messagebox.showinfo('提示','清空成功')
    else:
        return
    
def main_loop():
    # 檢查是否啟用logging
    try:
        with open("config.yml", "r", encoding="utf-8") as config_file:
            log_switch = yaml.load(config_file, Loader=yaml.Loader).get('system_set', {}).get('log_switch', 'on')
            
            if log_switch == 'off':
                logging.disable(logging.CRITICAL)
            else:
                logging.disable(logging.NOTSET)
                logging.getLogger().setLevel(logging.INFO)
    except Exception as e:
        logging.error(f"Error loading config.yml: {e}")
    else:
        # 檢查文件是否有變更
        has_changed = check_file_change(txt_file_path)

        if has_changed:
            # 發送郵件通知
            send_notification()

            # 更新 log 文本框
            update_log()

        win.after(5000, main_loop)
    
if __name__ == "__main__":
    lock_file = acquire_lock()

    # 紀錄程式開始
    logging.info("Program started.")

    # 創建主視窗
    win = tk.Tk()
    win.geometry("600x350")
    win.resizable(width=False, height=False)
    win.iconbitmap("icon.ico")
    win.title("ChangeNotifier")

    # 創建系統選單
    menubar = tk.Menu(win)
    win.config(menu=menubar)

    system_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=system_menu)

    system_menu.add_command(label="Setting", command=open_settings_window)
    system_menu.add_command(label="Minimize", command=minimize_window)
    system_menu.add_command(label="Exit", command=exit)

    # 創建清單框
    log_text = scrolledtext.ScrolledText(win, width=80, height=20, wrap=tk.WORD)
    log_text.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

    # 創建按鈕
    update_button = ttk.Button(win, text="Clear Log", command=clear_log)
    update_button.grid(row=1, column=0, padx=10, pady=10, sticky="e")

    win.protocol("WM_DELETE_WINDOW", minimize_window)

    logging.info("Mail sending success.")

    update_log()

    try:
        # 設定 txt 路徑
        with open("config.yml", "r", encoding="utf-8") as config_file:
            txt_file_path = yaml.load(config_file, Loader=yaml.Loader).get('file', {}).get('name', '')
            
        file_hash = calculate_hash(txt_file_path)
    except Exception as e:
        logging.error(f"Error getting initial status of file: {e}")
    else:
        threading.Thread(target=main_loop, daemon=True).start()
        win.mainloop()
