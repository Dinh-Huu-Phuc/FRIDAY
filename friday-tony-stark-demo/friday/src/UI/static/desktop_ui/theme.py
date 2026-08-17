from friday.src.UI.static.desktop_ui.theme_tokens import COLORS


DESKTOP_STYLESHEET = f"""
QWidget {{
    color: {COLORS.text};
    background: {COLORS.canvas};
    font-family: "Segoe UI";
    font-size: 13px;
}}
#appRoot {{ background: {COLORS.canvas}; }}
QLabel {{ background: transparent; }}

#topBar {{
    background: rgba(3, 9, 18, 232);
    border: 0;
    border-bottom: 1px solid {COLORS.border};
}}
#brandMark {{
    color: {COLORS.cyan};
    background: #061622;
    border: 1px solid {COLORS.border_bright};
    border-radius: 16px;
    font-size: 16px;
    font-weight: 700;
}}
#brand {{ color: {COLORS.text}; font-size: 15px; font-weight: 700; }}
#brandMeta, #sectionMeta {{ color: {COLORS.text_muted}; font-size: 9px; font-weight: 600; }}
#sectionTitle {{ color: #cfe7f3; font-size: 10px; font-weight: 700; }}

#connectionPill, #voicePill {{
    background: rgba(5, 17, 27, 225);
    border: 1px solid {COLORS.border};
    border-radius: 15px;
}}
#connectionPill:hover, #voicePill:hover {{ border-color: {COLORS.border_bright}; }}
#connectionDot, #voiceDot, #healthDot {{
    background: {COLORS.success};
    border-radius: 3px;
}}
#connection, #voiceLink {{
    color: #b9d8e5;
    background: transparent;
    font-family: "Consolas";
    font-size: 9px;
    font-weight: 700;
}}

QPushButton {{
    background: {COLORS.surface_raised};
    border: 1px solid {COLORS.border};
    border-radius: 7px;
    color: #d8eaf2;
    padding: 7px 12px;
}}
QPushButton:hover {{
    background: {COLORS.surface_soft};
    border-color: {COLORS.cyan};
    color: #ffffff;
}}
QPushButton:pressed {{ background: #06101a; }}
QPushButton:focus {{ border-color: {COLORS.cyan}; }}
QPushButton:disabled {{
    color: #526a78;
    border-color: #142736;
    background: #06101a;
}}
#primaryButton {{
    background: #dffbff;
    color: #031019;
    border-color: #f4feff;
    font-weight: 700;
}}
#primaryButton:hover {{ background: #ffffff; border-color: {COLORS.cyan}; }}
#sendButton {{
    background: #071b2b;
    border: 1px solid {COLORS.cyan};
    border-radius: 23px;
    color: {COLORS.cyan};
    padding: 0;
}}
#sendButton:hover {{ background: #0c2a3c; border-color: #ffffff; }}
#ghostButton {{
    background: transparent;
    color: {COLORS.text_soft};
    border-color: #1c3749;
    padding: 5px 9px;
}}
#secondaryButton {{ background: #07131d; border-radius: 15px; padding: 7px 13px; }}

#historyPanel, #settingsPanel, #systemPanel {{
    background: rgba(6, 16, 25, 232);
    border: 1px solid {COLORS.border};
    border-radius: 8px;
}}
#historyPanel {{ background: rgba(4, 12, 21, 220); }}
#coreStage {{ background: transparent; border: 0; }}
#visualStack {{ background: {COLORS.canvas_deep}; border: 0; }}
#statusStrip {{
    background: rgba(5, 15, 24, 218);
    border: 1px solid {COLORS.border};
    border-radius: 6px;
}}
#kicker {{ color: {COLORS.cyan}; font-family: "Consolas"; font-size: 9px; font-weight: 700; }}
#status {{ color: #c9dce5; font-size: 11px; }}

#systemTitle {{ color: {COLORS.text}; font-size: 10px; font-weight: 700; }}
#healthLabel, #systemCaption {{ color: {COLORS.text_muted}; font-family: "Consolas"; font-size: 8px; }}
#systemMarker {{ color: {COLORS.blue}; font-family: "Consolas"; font-size: 9px; }}
#systemName {{ color: #9ab1be; font-family: "Consolas"; font-size: 9px; }}
#systemValue {{ color: {COLORS.success}; font-family: "Consolas"; font-size: 8px; font-weight: 700; }}
#runtimeState {{ color: {COLORS.cyan}; font-family: "Consolas"; font-size: 11px; font-weight: 700; }}
#activitySegmentOn {{ background: {COLORS.cyan}; border: 0; }}
#activitySegmentOff {{ background: #163346; border: 0; }}

#assistantBubble, #userBubble {{ border-radius: 7px; }}
#assistantBubble {{ background: rgba(8, 23, 34, 235); border: 1px solid #245069; }}
#userBubble {{ background: rgba(29, 21, 19, 235); border: 1px solid #674431; }}
#messageMeta {{ color: #6f91a3; font-family: "Consolas"; font-size: 8px; font-weight: 600; }}
#messageBody {{ background: transparent; color: #dcecf4; selection-background-color: #176c85; }}
#copyButton {{ background: transparent; border: 0; padding: 3px; }}
#copyButton:hover {{ background: #10293a; }}

#commandRow {{ background: transparent; }}
#commandBar {{
    background: rgba(5, 15, 25, 245);
    border: 1px solid {COLORS.cyan};
    border-radius: 28px;
}}
#micCore {{
    color: {COLORS.cyan};
    background: #082033;
    border: 1px solid {COLORS.cyan};
    border-radius: 21px;
    font-family: "Consolas";
    font-size: 8px;
    font-weight: 700;
}}
#micBlock {{ background: transparent; }}
#commandInput {{
    background: transparent;
    border: 0;
    color: #edf8fc;
    padding: 8px 8px;
    selection-background-color: #176c85;
}}
#commandInput:focus {{ border: 0; }}
#micStatus {{ color: {COLORS.cyan}; font-family: "Consolas"; font-size: 8px; font-weight: 700; }}

#panelHeading, #unlockTitle {{ color: {COLORS.text}; font-size: 17px; font-weight: 700; }}
#settingsFeedback {{ color: {COLORS.warning}; }}
#unlockError {{ color: {COLORS.danger}; }}
QRadioButton, QCheckBox {{ color: #c6d9e2; spacing: 7px; }}
QRadioButton::indicator, QCheckBox::indicator {{ width: 15px; height: 15px; }}
QRadioButton::indicator:unchecked, QCheckBox::indicator:unchecked {{
    background: #06111b;
    border: 1px solid #3b5667;
}}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
    background: {COLORS.cyan};
    border: 1px solid #d8fbff;
}}
QRadioButton::indicator {{ border-radius: 7px; }}
QCheckBox::indicator {{ border-radius: 3px; }}
QLineEdit, QSpinBox {{
    background: #06111b;
    border: 1px solid #29485b;
    border-radius: 6px;
    color: #e4f0f5;
    padding: 8px;
}}
QLineEdit:focus, QSpinBox:focus {{ border-color: {COLORS.cyan}; }}

QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 7px; margin: 2px 0; }}
QScrollBar::handle:vertical {{ background: #29485b; min-height: 36px; border-radius: 3px; }}
QScrollBar::handle:vertical:hover {{ background: #3c6a82; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 7px; }}
QScrollBar::handle:horizontal {{ background: #29485b; min-width: 36px; border-radius: 3px; }}
QToolTip {{
    background: #0b1822;
    color: #eaf5fa;
    border: 1px solid #31546a;
    padding: 5px;
}}
"""
