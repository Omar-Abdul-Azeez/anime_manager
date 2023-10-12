# -*- encoding:utf-8 -*-
from anime import network

from PyQt5 import QtCore
from PyQt5.QtGui import QFont, QPixmap, QCursor, QClipboard
from PyQt5.QtWidgets import *


class Cover(QLabel):
    def __init__(self, link):
        super().__init__()
        self.bar = QToolBar(self)
        self.bar.setVisible(False)
        self.bar.setOrientation(QtCore.Qt.Vertical)
        self.copytxt = QToolButton()
        self.copylink = QToolButton()
        self.openlink = QToolButton()
        # self.copytxt.setMask()
        # self.copylink.setMask()
        # self.openlink.setMask()
        self.bar.addWidget(self.copytxt)
        self.bar.addWidget(self.copylink)
        self.bar.addWidget(self.openlink)
        #self.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        self.link = link

# TODO on hover show 2 buttons, 1 copy link, 1 open link
    def mousePressEvent(self, event):
        # open the link in browser
        network.open(self.link)

    def updateBarGeometry(self):
        # create a rectangle based on the sizeHint of the button, it will
        # be used to set its geometry
        geo = QtCore.QRect(QtCore.QPoint(), self.bar.sizeHint())
        # move the rectangle to the bottom right corner, using an offset
        # as a margin from the border
        offset = QtCore.QPoint(10, -10)
        geo.moveTopRight(self.rect().topRight() - offset)

        # apply the geometry
        self.bar.setGeometry(geo)

    def enterEvent(self, event):
        self.bar.setVisible(True)
        self.updateBarGeometry()

    def leaveEvent(self, event):
        self.bar.setVisible(False)

    def resizeEvent(self, event):
        self.updateBarGeometry()


class Anime(QFrame):
    def __init__(self, id, title, cover, link):
        super().__init__()
        self.linkText = link
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.cover = Cover(f'https://anilist.co/anime/{id}/')
        self.layout.addWidget(self.cover)
        self.cover.setFixedSize(230, 345)
        self.cover.setPixmap(QPixmap(cover).scaledToWidth(230))
        self.title = QLabel(self)
        self.title.setStyleSheet('color: #FFEEEE')
        self.layout.addWidget(self.title)
        self.title.setWordWrap(True)
        self.title.setText(title)
        self.title.setFont(QFont('しっぽり明朝', 20))
        self.title.setFixedWidth(230)
        self.title.setFixedHeight(self.title.maximumHeight())
        lo = QHBoxLayout()
        self.layout.addLayout(lo)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        self.link = QLineEdit(self)
        lo.addWidget(self.link)
        self.link.setText(link)
        self.link.setFixedWidth(215)
        self.link.setFont(QFont('Calibri', 20))
        self.link.setFixedHeight(self.link.height())
        self.resetButton = QPushButton()
        self.resetButton.setStyleSheet('background-color: #ffff00')
        self.resetButton.clicked.connect(self.reset)
        lo.addWidget(self.resetButton)
        self.resetButton.setFixedWidth(15)
        self.resetButton.setFixedHeight(self.link.height())

    def reset(self):
        self.link.setText(self.linkText)

    def get(self):
        return self.link.text().strip()


class RSS_Manger(QDialog):

    def __init__(self, ids, titles, covers, links):
        super().__init__()
        self.setWindowTitle('RSS Manager')
        self.setStyleSheet('QDialog { background-color: #222233; }')
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowMinimizeButtonHint & ~QtCore.Qt.WindowContextHelpButtonHint)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo2 = QHBoxLayout()
        lo.addLayout(lo2)
        confButton = QPushButton()
        cancelButton = QPushButton()
        confButton.setStyleSheet('background-color: #33ff33')
        confButton.setText('Confirm')
        cancelButton.setStyleSheet('background-color: #ff0000')
        cancelButton.setText('Cancel')
        confButton.clicked.connect(self.confirm)
        cancelButton.clicked.connect(self.cancel)
        confButton.setFont(QFont('しっぽり明朝', 20))
        cancelButton.setFont(QFont('しっぽり明朝', 20))
        lo2.addWidget(confButton)
        # TODO Space without a widget
        lo2.addWidget(QWidget())
        lo2.addWidget(cancelButton)
        # TODO Detach scrollbar and attach to mainWindow
        scroll = QScrollArea()
#         scroll.setStyleSheet('''QScrollBar:vertical {
#     border: 2px solid grey;
#     background: #32CC99;
#     width: 15px;
#     margin: 20px 0 20px 0;
# }
# QScrollBar::handle:vertical {
#     background: white;
#     min-height: 20px;
# }
# QScrollBar::add-line:vertical {
#     border: 2px solid grey;
#     background: #32CC99;
#     height: 20px;
#     subcontrol-position: down;
#     subcontrol-origin: margin;
# }
#
# QScrollBar::sub-line:vertical {
#     border: 2px solid grey;
#     background: #32CC99;
#     height: 20px;
#     subcontrol-position: top;
#     subcontrol-origin: margin;
# }''')
        lo.addWidget(scroll)
        group = QGroupBox()
        group.setStyleSheet('QGroupBox { background-color: #222233; }')
        scroll.setWidgetResizable(True)
        scroll.setWidget(group)
        layout = QGridLayout(group)
        lo2.setContentsMargins(*map(sum, zip(layout.getContentsMargins(), scroll.getContentsMargins())))

        self.links = []
        for i in range(len(ids)):
            anime = Anime(ids[i], titles[i], covers[i], links[i])
            self.links.append(anime)
            layout.addWidget(anime, int(i/3), i%3)

        self.setMinimumWidth(layout.totalMinimumSize().width() + 20)
        self.setMaximumWidth(layout.totalMinimumSize().width() + 20)
        self.setMinimumHeight(min(900, int(layout.totalMinimumSize().height() / layout.rowCount()) * min(2, len(ids))))

    def confirm(self):
        global answers
        answers = [anime.get() for anime in self.links]
        self.close()

    def cancel(self):
        global answers
        answers = None
        self.close()


def run(ids, titles, covers, links):
    app = QApplication([])
    dialog = RSS_Manger(ids, titles, covers, links)
    dialog.show()
    app.exec_()
    if 'answers' not in globals():
        return None
    else:
        global answers
        return answers
