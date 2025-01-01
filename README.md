# ZenInbox

ZenInbox is a Python-powered bot designed to revolutionize how you manage your inbox. With automated filtering, prioritization, and categorization, ZenInbox helps you maintain a clutter-free inbox and focus on what truly matters.

## Features

- **Smart Filtering**: Automatically sorts incoming messages based on customizable rules.
- **Prioritization**: Highlights important messages to ensure you never miss critical emails.
- **Automation**: Reduces manual work with a bot that learns your preferences over time.
- **Customizable Rules**: Tailor the bot's behavior to match your specific workflow.

## Requirements

- Python 3.8 or higher
- Required libraries (install via `requirements.txt`):

## Installation

1. Clone the repository:
```bash
git clone https://github.com/NotBeCursed/ZenInbox.git
cd ZenInbox
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

3. Get Gmail credentials:
Place Gmail credentials in the repository.

4. Run main script:
```bash
python ZenInbox.py
```

## Optional

Run in crontab :
```bash
0 */3 * * * /usr/bin/python3 /path/to/ZenInbox/main.py --cron >> /path/to/ZenInbox/zeninbox.log 2>&1
```
