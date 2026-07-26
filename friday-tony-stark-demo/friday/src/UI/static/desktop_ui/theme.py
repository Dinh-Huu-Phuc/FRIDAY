DESKTOP_STYLESHEET = r"""
QWidget {
    color: #dce7ec;
    background: #04080b;
    font-family: "Segoe UI";
    font-size: 13px;
}
#appRoot { background: #04080b; }
#topBar { background: transparent; border: 0; border-bottom: 1px solid #1b2b32; }
#brand { color: #f4fafb; font-size: 14px; font-weight: 700; }
#brandMeta, #sectionMeta { color: #637983; font-size: 9px; font-weight: 600; }
#sectionTitle { color: #cfe1e6; font-size: 11px; font-weight: 700; }
#connectionPill { background: #07130f; border: 1px solid #1d4636; border-radius: 8px; }
#connectionDot { background: #5ff0a5; border-radius: 3px; }
#connection { color: #8df5bd; background: transparent; font-size: 10px; font-weight: 700; }
QPushButton {
    background: #10181d;
    border: 1px solid #2b3d45;
    border-radius: 7px;
    color: #dce8ec;
    padding: 7px 12px;
}
QPushButton:hover { background: #142229; border-color: #52dbe2; color: #ffffff; }
QPushButton:pressed { background: #0c1418; }
QPushButton:disabled { color: #5c6b72; border-color: #1b282e; background: #0a1013; }
#primaryButton { background: #d9f4f3; color: #061013; border-color: #f0ffff; font-weight: 700; }
#primaryButton:hover { background: #ffffff; border-color: #59e4e9; }
#ghostButton { background: transparent; color: #8da0a8; border-color: #26363d; padding: 5px 10px; }
#historyPanel, #settingsPanel, #coreStage {
    background: #071015;
    border: 1px solid #21333b;
    border-radius: 8px;
}
#coreStage { background: #060d11; }
#visualStack { background: #020608; border: 0; }
#statusStrip { background: #081318; border: 1px solid #1b3038; border-radius: 6px; }
#kicker { color: #69dfe4; background: transparent; font-size: 9px; font-weight: 700; }
#status { color: #d5e2e6; background: transparent; font-size: 12px; }
#assistantBubble, #userBubble { border-radius: 7px; }
#assistantBubble { background: #0a151b; border: 1px solid #2b4650; }
#userBubble { background: #15140f; border: 1px solid #4b4025; }
#messageMeta { color: #718891; background: transparent; font-size: 9px; font-weight: 600; }
#messageBody { background: transparent; color: #e5eef1; selection-background-color: #1b6f70; }
#copyButton { background: transparent; border: 0; padding: 3px; }
#copyButton:hover { background: #14242a; }
#commandBar { background: #081116; border: 1px solid #2a414a; border-radius: 8px; }
#micBlock { background: transparent; }
#commandInput {
    background: #050b0f;
    border: 1px solid #1f323a;
    border-radius: 7px;
    color: #edf6f7;
    padding: 8px 11px;
    selection-background-color: #236a6c;
}
#commandInput:focus { border-color: #4bcbd1; }
#micStatus { color: #5ce0df; background: transparent; font-size: 9px; font-weight: 700; }
#panelHeading, #unlockTitle { color: #eaf7f7; font-size: 17px; font-weight: 700; }
#settingsFeedback { color: #edbf6b; }
#unlockError { color: #ff9298; }
QLabel { background: transparent; }
QRadioButton, QCheckBox { color: #c8d6da; spacing: 7px; }
QRadioButton::indicator, QCheckBox::indicator { width: 15px; height: 15px; }
QRadioButton::indicator:unchecked, QCheckBox::indicator:unchecked {
    background: #071015;
    border: 1px solid #40545d;
}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background: #55dce0;
    border: 1px solid #a5fbfb;
}
QRadioButton::indicator { border-radius: 7px; }
QCheckBox::indicator { border-radius: 3px; }
QLineEdit, QSpinBox {
    background: #071015;
    border: 1px solid #31464f;
    border-radius: 6px;
    color: #e4eef0;
    padding: 8px;
}
QLineEdit:focus, QSpinBox:focus { border-color: #50d3d8; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: 0; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 2px 0; }
QScrollBar::handle:vertical { background: #33464e; min-height: 36px; border-radius: 3px; }
QScrollBar::handle:vertical:hover { background: #4d6973; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #111b20; color: #eaf2f4; border: 1px solid #344950; padding: 5px; }
"""
