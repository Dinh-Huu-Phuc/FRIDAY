DESKTOP_STYLESHEET = r"""
QWidget {
    color: #dce7ee;
    background: #05080b;
    font-family: "Segoe UI";
    font-size: 13px;
}
#appRoot { background: #05080b; }
#brand { color: #f3f7f9; font-size: 13px; font-weight: 650; }
#connection { color: #70f2b0; padding: 7px 10px; }
QPushButton {
    background: #141a20;
    border: 1px solid #34414c;
    border-radius: 6px;
    padding: 7px 12px;
}
QPushButton:hover { border-color: #59f7df; color: #ffffff; }
QPushButton:disabled { color: #65717a; border-color: #202a31; }
#primaryButton { background: #dce7ee; color: #071014; border-color: #ffffff; font-weight: 650; }
#historyPanel, #settingsPanel, #coreStage {
    background: #080d12;
    border: 1px solid #26313a;
    border-radius: 8px;
}
#assistantBubble, #userBubble { border-radius: 8px; }
#assistantBubble { background: #0c141b; border: 1px solid #33424d; }
#userBubble { background: #111920; border: 1px solid #202b34; }
#messageMeta { color: #81919d; font-size: 10px; }
#messageBody { background: transparent; color: #e5edf2; selection-background-color: #1c786e; }
#copyButton { background: transparent; border: 0; padding: 3px; }
#copyButton:hover { background: #17242a; }
#kicker { color: #89949d; font-size: 11px; }
#status { color: #d5dfe5; font-size: 16px; padding: 8px; }
#commandBar { background: #0a1015; border: 1px solid #34414c; border-radius: 8px; }
#commandInput { background: transparent; border: 0; color: #edf5f7; padding: 7px; }
#micStatus { color: #59f7df; font-size: 11px; font-weight: 650; padding: 0 8px; }
#panelHeading, #unlockTitle { color: #59f7df; font-size: 17px; font-weight: 700; }
#settingsFeedback { color: #f1ba62; }
#unlockError { color: #ff8d91; }
QLineEdit, QSpinBox {
    background: #0c1319;
    border: 1px solid #35434d;
    border-radius: 6px;
    padding: 8px;
}
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: 0; }
QScrollBar:vertical { background: #080d12; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #3b4851; min-height: 32px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
