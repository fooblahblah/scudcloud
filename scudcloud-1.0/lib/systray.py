from PyQt5 import QtCore, QtGui, QtWidgets
from resources import Resources

class Systray(QtWidgets.QSystemTrayIcon):

    urgent = False

    def __init__(self, window):
        super(Systray, self).__init__(QtGui.QIcon.fromTheme("scudcloud", QtGui.QIcon("resources/scudcloud.png")), window)
        self.activated.connect(self.activatedEvent)
        self.window = window
        self.setToolTip(Resources.APP_NAME)
        self.menu = QtWidgets.QMenu(self.window)
        self.menu.addAction('Show', self.restore)
        self.menu.addSeparator()
        self.menu.addAction(self.window.menus["file"]["preferences"])
        self.menu.addAction(self.window.menus["help"]["about"])
        self.menu.addSeparator()
        self.menu.addAction(self.window.menus["file"]["exit"])
        self.setContextMenu(self.menu)

    def alert(self):
        if not self.urgent:
            self.urgent = True
            self.setIcon(QtGui.QIcon.fromTheme("scudcloud-attention", QtGui.QIcon("systray/hicolor/scudcloud-attention.svg")))

    def stopAlert(self):
        self.urgent = False
        self.setIcon(QtGui.QIcon.fromTheme("scudcloud", QtGui.QIcon("systray/hicolor/scudcloud.svg")))

    def setCounter(self, i):
        if 0 == i:
            if True == self.urgent:
                self.setIcon(QtGui.QIcon.fromTheme("scudcloud-attention", QtGui.QIcon("systray/hicolor/scudcloud-attention.svg")))
            else:
                self.setIcon(QtGui.QIcon.fromTheme("scudcloud", QtGui.QIcon("systray/hicolor/scudcloud.svg")))
        elif i > 0 and i < 10:
            self.setIcon(QtGui.QIcon.fromTheme("scudcloud-attention-" + str(int(i)), QtGui.QIcon("systray/hicolor/scudcloud-attention-" + str(int(i)) + ".svg")))
        elif i > 9:
            self.setIcon(QtGui.QIcon.fromTheme("scudcloud-attention-9-plus", QtGui.QIcon("systray/hicolor/scudcloud-9-plus.svg")))

    def restore(self):
        self.window.show()
        self.stopAlert()

    def activatedEvent(self, reason):
        if reason in [QtWidgets.QSystemTrayIcon.MiddleClick, QtWidgets.QSystemTrayIcon.Trigger]:
            if self.window.isHidden() or self.window.isMinimized() or not self.window.isActiveWindow():
                self.restore()
            else:
                self.window.hide()
