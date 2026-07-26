CODE_MAP_STYLESHEET = r"""
QMainWindow, QWidget {
    background: #05080b;
    color: #dce7ee;
    font-family: "Segoe UI";
    font-size: 12px;
}
QToolBar {
    background: #080d12;
    border: 0;
    border-bottom: 1px solid #26313a;
    spacing: 4px;
    padding: 7px 10px;
}
QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 6px;
}
QToolButton:hover {
    background: #121c22;
    border-color: #35505a;
}
QToolButton:disabled { color: #4c5961; }
#codeMapBrand { color: #59f7df; font-weight: 700; padding: 0 10px 0 4px; }
#codeMapStatus { color: #91a0aa; padding: 0 10px; }
#codeMapClose:hover { background: #602329; border-color: #a84952; }
"""
