"""Explicit Qt and Matplotlib colors, independent of OS text-color inheritance."""
from PySide6 import QtGui


def colors(dark):
    return dict(bg='#171e29' if dark else '#fafafa',fg='#edf2f7' if dark else '#182432',
                panel='#243244' if dark else '#ffffff',grid='#506078' if dark else '#bec8d4',
                iron='#3d5066' if dark else '#cbd1d6',rotor='#34485d' if dark else '#b4bec8',
                flux='#d5eaff' if dark else '#374c60',accent='#70d5ff' if dark else '#006a99',
                magnet_n='#864849' if dark else '#f5aaa6',magnet_s='#365c85' if dark else '#a3c5ed')


def set_widget_theme(widget,dark):
    c=colors(dark)
    palette=QtGui.QPalette()
    for role,color in [('Window',c['bg']),('WindowText',c['fg']),('Base',c['panel']),
                       ('AlternateBase',c['bg']),('Text',c['fg']),('Button',c['panel']),
                       ('ButtonText',c['fg']),('ToolTipBase',c['panel']),('ToolTipText',c['fg']),
                       ('Highlight','#2876a7'),('HighlightedText','#ffffff'),('PlaceholderText',c['grid'])]:
        palette.setColor(getattr(QtGui.QPalette.ColorRole,role),QtGui.QColor(color))
    widget.setPalette(palette)
    widget.setAutoFillBackground(True)
    widget.setStyleSheet(f'''
        QWidget {{ color: {c['fg']}; background-color: {c['bg']}; }}
        QLineEdit, QAbstractSpinBox, QComboBox, QTableWidget, QAbstractItemView {{
            background-color: {c['panel']}; color: {c['fg']};
            selection-background-color: #2876a7; selection-color: white;
        }}
        QPushButton, QTabBar::tab, QHeaderView::section {{
            background-color: {c['panel']}; color: {c['fg']};
            border: 1px solid {c['grid']}; padding: 5px;
        }}
        QPushButton:hover, QTabBar::tab:selected {{ border: 1px solid {c['accent']}; }}
        QToolTip {{ color: {c['fg']}; background: {c['panel']}; border: 1px solid {c['grid']}; }}
    ''')


def style_axes(figure,ax,dark):
    c=colors(dark)
    figure.set_facecolor(c['bg'])
    ax.set_facecolor(c['bg'])
    ax.tick_params(colors=c['fg'])
    for spine in ax.spines.values():
        spine.set_color(c['grid'])
    for item in [ax.title,ax.xaxis.label,ax.yaxis.label,ax.xaxis.get_offset_text(),ax.yaxis.get_offset_text()]:
        item.set_color(c['fg'])
