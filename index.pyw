import os
import time
import smtplib
import threading
import cv2
import pyttsx3
import keyboard
import wmi
import pythoncom
import imaplib
import email
from email.message import EmailMessage
from ctypes import windll
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import tkinter as tk

# Configuration
LOCKER_FOLDER = "" #real folder path
DECOY_FOLDER = "" #fakefolder path
LOCKER_PASSWORD = "" # a passwork type anywhere
USB_SERIAL_ALLOWED = "" #usb serial number
GMAIL_ADDRESS = "" 
GMAIL_APP_PASSWORD = "" #go to google app password
VOICE_UNLOCK_MSG = "" #voice after unlock
VOICE_INTRUDER_MSG = "" #a voice someone try to click ctrl+m without usb or verification gmail reply(No)

locker_locked = True
tray_visible = False
tray_icon = None

def detect_usb():
    try:
        pythoncom.CoInitialize()
        c = wmi.WMI()
        for disk in c.Win32_LogicalDisk():
            if disk.DriveType == 2:
                volume_serial = disk.VolumeSerialNumber
                return volume_serial == USB_SERIAL_ALLOWED
        return False
    except Exception as e:
        print("Error detecting USB:", e)
        return False

def lock_folder():
    global locker_locked
    if os.path.exists(LOCKER_FOLDER):
        windll.kernel32.SetFileAttributesW(LOCKER_FOLDER, 0x02)  # Hidden
        locker_locked = True
        print("[LOCKED] Folder hidden.")

def unlock_folder():
    global locker_locked
    if os.path.exists(LOCKER_FOLDER):
        windll.kernel32.SetFileAttributesW(LOCKER_FOLDER, 0x80)  # Normal
        locker_locked = False
        print("[UNLOCKED] Folder visible.")
        speak(VOICE_UNLOCK_MSG)

def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def capture_photo():
    if not os.path.exists(DECOY_FOLDER):
        os.makedirs(DECOY_FOLDER)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not access webcam.")
        return None
    ret, frame = cap.read()
    if ret:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        img_path = os.path.join(DECOY_FOLDER, f"intruder_{timestamp}.png")
        cv2.imwrite(img_path, frame)
        cap.release()
        return img_path
    cap.release()
    return None

def send_email_with_photo(img_path):
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Intruder Alert 🚨'
        msg['From'] = GMAIL_ADDRESS
        msg['To'] = GMAIL_ADDRESS
        msg.set_content('Someone tried to access your folder without permission. See attached image.')

        with open(img_path, 'rb') as f:
            img_data = f.read()
            msg.add_attachment(img_data, maintype='image', subtype='png', filename=os.path.basename(img_path))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        print("📧 Intruder photo emailed.")
    except Exception as e:
        print("❌ Email sending failed:", e)

def send_verification_email():
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Folder Unlock Verification'
        msg['From'] = GMAIL_ADDRESS
        msg['To'] = GMAIL_ADDRESS
        msg.set_content('Reply with "Yes" to unlock or "No" to trigger intruder alarm.')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        print("Verification email sent.")
    except Exception as e:
        print("❌ Verification email failed:", e)
        
def read_verification_reply():
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select('inbox')

        status, data = mail.search(None, f'(FROM "{GMAIL_ADDRESS}")')
        mail_ids = data[0].split()
        if not mail_ids:
            return None

        latest_email_id = mail_ids[-1]
        status, msg_data = mail.fetch(latest_email_id, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode().strip()
                    break
        else:
            body = msg.get_payload(decode=True).decode().strip()

        # Clean the body and check for 'yes' or 'no' only (ignore extra parts)
        body_cleaned = body.splitlines()[0].strip().lower()
        print("📨 Gmail reply content:", body_cleaned)

        if "yes" in body_cleaned:
            return "Yes"
        elif "no" in body_cleaned:
            return "No"
        else:
            return None
    except Exception as e:
        print("❌ Error reading Gmail reply:", e)
        return None


def handle_verification():
    send_verification_email()
    print("Waiting for reply...")
    time.sleep(30)  # Adjust as needed
    reply = read_verification_reply()
    if reply == "Yes":
        unlock_folder()
    elif reply == "No":
        speak(VOICE_INTRUDER_MSG)
        img = capture_photo()
        if img:
            send_email_with_photo(img)
            os.startfile(DECOY_FOLDER)
    else:
        print("❌ No valid response received.")

def manual_intruder_check():
    if not detect_usb():
        speak(VOICE_INTRUDER_MSG)
        img = capture_photo()
        if img:
            send_email_with_photo(img)
            os.startfile(DECOY_FOLDER)


def toggle_folder():
    if detect_usb():
        handle_verification()
    else:
        manual_intruder_check()

def toggle_tray_icon():
    global tray_visible
    tray_visible = not tray_visible
    print(f"Tray icon {'shown' if tray_visible else 'hidden'} (simulated).")

def quit_app(icon=None, item=None):
    print("Quitting...")
    os._exit(0)

def show_connected_usb():
    pythoncom.CoInitialize()
    c = wmi.WMI()
    for disk in c.Win32_LogicalDisk():
        if disk.DriveType == 2:
            print("Connected USB Serial:", disk.VolumeSerialNumber)
            return
    print("No USB connected.")

def open_decoy():
    if not os.path.exists(DECOY_FOLDER):
        os.makedirs(DECOY_FOLDER)
    os.startfile(DECOY_FOLDER)

def tray_icon_thread():
    global tray_icon
    icon = pystray.Icon("test")
    image = Image.new('RGB', (64, 64), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 64, 64], fill=(255, 0, 0))
    icon.icon = image
    icon.menu = pystray.Menu(item('Quit', quit_app))
    tray_icon = icon
    icon.run()

def start_gui():
    def gui_thread():
        root = tk.Tk()
        root.title("Folder Locker")
        root.geometry("250x80")
        root.protocol("WM_DELETE_WINDOW", lambda: root.withdraw())
        label = tk.Label(root, text="🔐 Folder Locker Active", font=("Arial", 12))
        label.pack(pady=20)
        root.mainloop()
    threading.Thread(target=gui_thread, daemon=True).start()

def register_shortcuts():
    keyboard.add_hotkey('ctrl+shift+l', toggle_tray_icon)
    keyboard.add_hotkey('ctrl+shift+m', manual_intruder_check)
    keyboard.add_hotkey('ctrl+shift+a', lock_folder)
    keyboard.add_hotkey('ctrl+alt+d', open_decoy)
    keyboard.add_hotkey('ctrl+shift+u', show_connected_usb)
    keyboard.add_hotkey('ctrl+p', quit_app)
    keyboard.add_hotkey('alt+p', quit_app)
    keyboard.add_hotkey('ctrl+m', toggle_folder)

if __name__ == "__main__":
    print("🔐 Starting Folder Locker...")
    lock_folder()
    start_gui()
    register_shortcuts()
    threading.Thread(target=tray_icon_thread, daemon=True).start()
    keyboard.wait()
