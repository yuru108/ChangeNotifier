# ChangeNotifier

ChangeNotifier is a Windows desktop utility that monitors a configured text file and sends an email notification when the file content changes.

## Features

- Monitors file content changes by hash.
- Sends SMTP email notifications to configured recipients.
- Provides a Tkinter settings window for sender, SMTP, subject, and logging options.
- Runs in the system tray when minimized.
- Writes optional runtime logs to `main.log`.

## Setup

1. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

2. Copy the example configuration:

   ```powershell
   Copy-Item config.example.yml config.yml
   ```

3. Edit `config.yml` with your SMTP server, sender account, recipients, and monitored file name.

4. Run the app:

   ```powershell
   python change_notifier.py
   ```

## Configuration

`config.yml` controls the monitored file, SMTP account, email subject, recipient list, and log switch. The local `config.yml` file is ignored by Git so credentials are not committed.
