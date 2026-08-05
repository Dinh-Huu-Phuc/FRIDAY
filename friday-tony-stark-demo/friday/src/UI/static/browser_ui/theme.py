SECURE_BROWSER_STYLESHEET = """
QMainWindow {
    background: #05090c;
}

QToolBar#browserToolbar {
    background: #071014;
    border: 0;
    border-bottom: 1px solid #18333b;
    spacing: 6px;
    padding: 7px 10px;
}

QLabel#browserBrand {
    color: #7ff8ef;
    font-size: 13px;
    font-weight: 700;
    padding: 0 12px 0 4px;
}

QToolButton#navigationButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 5px;
}

QToolButton#navigationButton:hover {
    background: #102128;
    border-color: #29505a;
}

QToolButton#navigationButton:disabled {
    opacity: 0.35;
}

QLineEdit#addressBar {
    min-height: 34px;
    color: #dceff1;
    background: #0a1419;
    border: 1px solid #26434b;
    border-radius: 6px;
    padding: 0 12px;
    selection-background-color: #2bbfc4;
}

QLineEdit#addressBar:focus {
    border-color: #59e5df;
    background: #0c181e;
}

QToolButton#profileAvatar {
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
    color: #d7e7e9;
    background: #111c21;
    border: 1px solid #35515a;
    border-radius: 17px;
    font-size: 13px;
    font-weight: 700;
}

QToolButton#profileAvatar[signedIn="true"] {
    color: #031416;
    background: #65ebe3;
    border-color: #a8fff9;
}

QToolButton#profileAvatar:hover {
    border-color: #78f8ef;
}

QProgressBar#loadProgress {
    min-height: 2px;
    max-height: 2px;
    border: 0;
    background: #071014;
}

QProgressBar#loadProgress::chunk {
    background: #5dece3;
}
"""
