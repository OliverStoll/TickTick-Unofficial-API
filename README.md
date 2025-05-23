# 📦 TickTick-Unofficial-Api

TickTick-Unofficial-Api is a Python wrapper for the unofficial TickTick API (v2). 
It provides access to task, focus, and habit data, and currently supports reading and writing habit entries. 
Authentication is handled via cookies retrieved either through Selenium or manually extracted browser sessions.

## ✨ Features

- Retrieve and add TickTick habit entries
- Retrieve TickTick focus time data
- Retrieve TickTick tasks (also supported by the official v1 API)

Planned features:
- Add support for writing focus sessions
- Add support for creating and updating tasks

## 📥 Installation

To install the package:  
`pip install ticktick-py-v2`

## 🚀 Usage

You can use the module by importing `ticktick_v2`:
`from ticktick_v2.habits import TicktickHabitHandler, TickTickHabitEntry` 
`from ticktick_v2.focus import TicktickFocusHandler, TickTickFocusTime`
`from ticktick_v2.tasks import TicktickTaskHandler, TickTickTask`

All return values use pydantic BaseModel for data validation. 
To use data as dict, simply convert via `.dict()`

### 🔐 Authentication

To access your TickTick data, you must authenticate using one of two methods:

#### Method 1: Environment Variables + Selenium

Set the following environment variables:  
`TICKTICK_USERNAME="your_email@example.com"`  
`TICKTICK_PASSWORD="your_password"`

The package will use a headless Selenium session to retrieve the necessary cookies for API access.

#### Method 2: Pre-saved Cookies

Create a file named `.ticktick-cookies` in your working directory. 
This file should contain cookies exported from a logged-in TickTick browser session (e.g., using browser developer tools).

## 🗂️ Project Structure

```
src/  
└── ticktick_v2/  
    ├── utils/                 utility functions  
    ├── web/                   web-related functionality (e.g., Selenium login)  
    ├── cookies_login.py       handles cookie retrieval via Selenium  
    ├── focus.py               focus session access  
    ├── habits.py              habit access and writing  
    └── tasks.py               task access
```

## 🤝 Contributing

Contributions are welcome. Please open issues or pull requests for new features, improvements, or bug fixes.

## 🪪 License

This project is licensed under the Apache License 2.0. See the [LICENSE] file for details.
