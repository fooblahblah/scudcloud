#!/usr/bin/env python3
import sys, os, time
from cookiejar import PersistentCookieJar
from leftpane import LeftPane
from notifier import Notifier
from resources import Resources
from systray import Systray
from wrapper import Wrapper
from os.path import expanduser
from threading import Thread
from PyQt5 import QtCore, QtGui, QtWebKit, QtWidgets, QtWebKitWidgets
from PyQt5.Qt import QApplication, QKeySequence, QTimer
from PyQt5.QtCore import QUrl, QSettings
from PyQt5.QtNetwork import QNetworkDiskCache
from PyQt5.QtWebKit import QWebSettings

# Auto-detection of Unity and Dbusmenu in gi repository
try:
    from gi.repository import Unity, Dbusmenu
except ImportError:
    Unity = None
    Dbusmenu = None
    from launcher import DummyLauncher

class ScudCloud(QtWidgets.QMainWindow):

    plugins = True
    debug = False
    forceClose = False
    messages = 0

    def __init__(self, parent = None, settings_path = ""):
        super(ScudCloud, self).__init__(parent)
        self.setWindowTitle('ScudCloud')
        self.settings_path = settings_path
        self.notifier = Notifier(Resources.APP_NAME, Resources.get_path('scudcloud.png'))
        self.settings = QSettings(self.settings_path + '/scudcloud.cfg', QSettings.IniFormat)
        self.identifier = self.settings.value("Domain")
        if Unity is not None:
            self.launcher = Unity.LauncherEntry.get_for_desktop_id("scudcloud.desktop")
        else:
            self.launcher = DummyLauncher(self)
        self.webSettings()
        self.leftPane = LeftPane(self)
        webView = Wrapper(self)
        webView.page().networkAccessManager().setCookieJar(self.cookiesjar)
        self.stackedWidget = QtWidgets.QStackedWidget()
        self.stackedWidget.addWidget(webView)
        centralWidget = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.leftPane)
        layout.addWidget(self.stackedWidget)
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)
        self.addMenu()
        self.tray = Systray(self)
        self.systray(ScudCloud.minimized)
        self.installEventFilter(self)
        if self.identifier is None:
            webView.load(QtCore.QUrl(Resources.SIGNIN_URL))
        else:
            webView.load(QtCore.QUrl(self.domain()))
        webView.show()
        # Starting unread msgs counter
        self.setupTimer()

    def setupTimer(self):
        timer = QTimer(self)
        timer.timeout.connect(self.count)
        timer.setInterval(2000)
        timer.start()

    def webSettings(self):
        self.cookiesjar = PersistentCookieJar(self)
        self.zoom = self.readZoom()
        # Required by Youtube videos (HTML5 video support only on Qt5)
        QWebSettings.globalSettings().setAttribute(QWebSettings.PluginsEnabled, self.plugins)
        # We don't want Java
        QWebSettings.globalSettings().setAttribute(QWebSettings.JavaEnabled, False)
        # We don't need History
        QWebSettings.globalSettings().setAttribute(QWebSettings.PrivateBrowsingEnabled, True)
        # Enabling Local Storage (now required by Slack)
        QWebSettings.globalSettings().setAttribute(QWebSettings.LocalStorageEnabled, True)
        # Enabling Cache
        self.diskCache = QNetworkDiskCache(self)
        self.diskCache.setCacheDirectory(self.settings_path)
        # Required for copy and paste clipboard integration
        QWebSettings.globalSettings().setAttribute(QWebSettings.JavascriptCanAccessClipboard, True)
        # Enabling Inspeclet only when --debug=True (requires more CPU usage)
        QWebSettings.globalSettings().setAttribute(QWebSettings.DeveloperExtrasEnabled, self.debug)

    def toggleFullScreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def restore(self):
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        windowState = self.settings.value("windowState")
        if windowState is not None:
            self.restoreState(windowState)
        else:
            self.showMaximized()

    def systray(self, show=None):
        if show is None:
            show = self.settings.value("Systray") == "True"
        if show:
            self.tray.show()
            self.menus["file"]["close"].setEnabled(True)
            self.settings.setValue("Systray", "True")
        else:
            self.tray.setVisible(False)
            self.menus["file"]["close"].setEnabled(False)
            self.settings.setValue("Systray", "False")

    def readZoom(self):
        default = 1
        if self.settings.value("Zoom") is not None:
            default = float(self.settings.value("Zoom"))
        return default

    def setZoom(self, factor=1):
        if factor > 0:
            for i in range(0, self.stackedWidget.count()):
                widget = self.stackedWidget.widget(i)
                widget.setZoomFactor(factor)
            self.settings.setValue("Zoom", factor)

    def zoomIn(self):
        self.setZoom(self.current().zoomFactor() + 0.1)

    def zoomOut(self):
        self.setZoom(self.current().zoomFactor() - 0.1)

    def zoomReset(self):
        self.setZoom()

    def addMenu(self):
        self.menus = {
            "file": {
                "preferences": self.createAction("Preferences", lambda : self.current().preferences()),
                "systray":     self.createAction("Close to Tray", self.systray, None, True),
                "addTeam":     self.createAction("Sign in to Another Team", lambda : self.current().addTeam()),
                "signout":     self.createAction("Signout", lambda : self.current().logout()),
                "close":       self.createAction("Close", self.close, QKeySequence.Close),
                "exit":        self.createAction("Quit", self.exit, QKeySequence.Quit)
            },
            "edit": {
                "undo":        self.current().pageAction(QtWebKitWidgets.QWebPage.Undo),
                "redo":        self.current().pageAction(QtWebKitWidgets.QWebPage.Redo),
                "cut":         self.current().pageAction(QtWebKitWidgets.QWebPage.Cut),
                "copy":        self.current().pageAction(QtWebKitWidgets.QWebPage.Copy),
                "paste":       self.current().pageAction(QtWebKitWidgets.QWebPage.Paste),
                "back":        self.current().pageAction(QtWebKitWidgets.QWebPage.Back),
                "forward":     self.current().pageAction(QtWebKitWidgets.QWebPage.Forward),
                "reload":      self.current().pageAction(QtWebKitWidgets.QWebPage.Reload)
            },
            "view": {
                "zoomin":      self.createAction("Zoom In", self.zoomIn, QKeySequence.ZoomIn),
                "zoomout":     self.createAction("Zoom Out", self.zoomOut, QKeySequence.ZoomOut),
                "reset":       self.createAction("Reset", self.zoomReset, QtCore.Qt.CTRL + QtCore.Qt.Key_0),
                "fullscreen":  self.createAction("Toggle Full Screen", self.toggleFullScreen, QtCore.Qt.Key_F11)        
            },
            "help": {
                "help":       self.createAction("Help and Feedback", self.current().help, QKeySequence.HelpContents),
                "center":     self.createAction("Slack Help Center", self.current().helpCenter),
                "about":      self.createAction("About", lambda : self.current().about())
             }
        }
        menu = self.menuBar()
        fileMenu = menu.addMenu("&File")
        fileMenu.addAction(self.menus["file"]["preferences"])
        fileMenu.addAction(self.menus["file"]["systray"])
        fileMenu.addSeparator()
        fileMenu.addAction(self.menus["file"]["addTeam"])
        fileMenu.addAction(self.menus["file"]["signout"])
        fileMenu.addSeparator()
        fileMenu.addAction(self.menus["file"]["close"])
        fileMenu.addAction(self.menus["file"]["exit"])
        editMenu = menu.addMenu("&Edit")
        editMenu.addAction(self.menus["edit"]["undo"])
        editMenu.addAction(self.menus["edit"]["redo"])
        editMenu.addSeparator()
        editMenu.addAction(self.menus["edit"]["cut"])
        editMenu.addAction(self.menus["edit"]["copy"])
        editMenu.addAction(self.menus["edit"]["paste"])
        editMenu.addSeparator()
        editMenu.addAction(self.menus["edit"]["back"])
        editMenu.addAction(self.menus["edit"]["forward"])
        editMenu.addAction(self.menus["edit"]["reload"])
        viewMenu = menu.addMenu("&View")
        viewMenu.addAction(self.menus["view"]["zoomin"])
        viewMenu.addAction(self.menus["view"]["zoomout"])
        viewMenu.addAction(self.menus["view"]["reset"])
        viewMenu.addSeparator()
        viewMenu.addAction(self.menus["view"]["fullscreen"])
        helpMenu = menu.addMenu("&Help")
        helpMenu.addAction(self.menus["help"]["help"])
        helpMenu.addAction(self.menus["help"]["center"])
        helpMenu.addSeparator()
        helpMenu.addAction(self.menus["help"]["about"])
        self.enableMenus(False)
        showSystray = self.settings.value("Systray") == "True"
        self.menus["file"]["systray"].setChecked(showSystray)
        self.menus["file"]["close"].setEnabled(showSystray)

    def enableMenus(self, enabled):
        self.menus["file"]["preferences"].setEnabled(enabled == True)
        self.menus["file"]["addTeam"].setEnabled(enabled == True)
        self.menus["file"]["signout"].setEnabled(enabled == True)
        self.menus["help"]["help"].setEnabled(enabled == True)

    def createAction(self, text, slot, shortcut=None, checkable=False):
        action = QtWidgets.QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        if checkable:
            action.setCheckable(True)
        return action

    def domain(self):
        if self.identifier.endswith(".slack.com"):
            return self.identifier
        else:
            return "https://"+self.identifier+".slack.com"

    def current(self):
        return self.stackedWidget.currentWidget()

    def teams(self, teams):
        if teams is not None and len(teams) > 1:
            self.leftPane.show()
            for t in teams:
                try:
                    self.leftPane.addTeam(t['id'], t['team_name'], t['team_url'], t['team_icon']['image_88'], t == teams[0])
                except:
                    self.leftPane.addTeam(t['id'], t['team_name'], t['team_url'], '', t == teams[0])

    def switchTo(self, url):
        qUrl = QtCore.QUrl(url)
        index = -1
        for i in range(0, self.stackedWidget.count()):
            if self.stackedWidget.widget(i).url().toString().startswith(url):
                index = i
                break
        if index != -1:
            self.stackedWidget.setCurrentIndex(index)
        else:
            webView = Wrapper(self)
            webView.page().networkAccessManager().setCookieJar(self.cookiesjar)
            webView.load(qUrl)
            webView.show()
            self.stackedWidget.addWidget(webView)
            self.stackedWidget.setCurrentWidget(webView)
        self.quicklist(self.current().listChannels())
        self.enableMenus(self.current().isConnected())
        # Save the last used team as default
        self.settings.setValue("Domain", 'https://'+qUrl.host())

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ActivationChange and self.isActiveWindow():
            self.focusInEvent(event)
        if event.type() == QtCore.QEvent.KeyPress:
            # Ctrl + <n>
            if QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
                if event.key() == QtCore.Qt.Key_1:   self.leftPane.click(0)
                elif event.key() == QtCore.Qt.Key_2: self.leftPane.click(1)
                elif event.key() == QtCore.Qt.Key_3: self.leftPane.click(2)
                elif event.key() == QtCore.Qt.Key_4: self.leftPane.click(3)
                elif event.key() == QtCore.Qt.Key_5: self.leftPane.click(4)
                elif event.key() == QtCore.Qt.Key_6: self.leftPane.click(5)
                elif event.key() == QtCore.Qt.Key_7: self.leftPane.click(6)
                elif event.key() == QtCore.Qt.Key_8: self.leftPane.click(7)
                elif event.key() == QtCore.Qt.Key_9: self.leftPane.click(8)
                # ctrl + tab
                elif event.key() == QtCore.Qt.Key_Tab: self.leftPane.clickNext(1)
  
            # ctrl + backtab
            if (QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier) and (QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
                if event.key() == QtCore.Qt.Key_Backtab: self.leftPane.clickNext(-1)
                        
            # Ctrl + Shift + <key>
            if (QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier) and (QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
                if event.key() == QtCore.Qt.Key_V: self.current().createSnippet()
        return QtWidgets.QMainWindow.eventFilter(self, obj, event);

    def focusInEvent(self, event):
        self.launcher.set_property("urgent", False)
        self.tray.stopAlert()

    def titleChanged(self):
        self.setWindowTitle(self.current().title())

    def closeEvent(self, event):
        if not self.forceClose and self.settings.value("Systray") == "True":
            self.hide()
            event.ignore()
        else:
            self.cookiesjar.save()
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())

    def show(self):
        self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        self.activateWindow()
        self.setVisible(True)

    def exit(self):
        self.forceClose = True
        self.close()

    def quicklist(self, channels):
        if Dbusmenu is not None:
            ql = Dbusmenu.Menuitem.new()
            self.launcher.set_property("quicklist", ql)
            if channels is not None:
                for c in channels:
                    if c['is_member']:
                        item = Dbusmenu.Menuitem.new ()
                        item.property_set (Dbusmenu.MENUITEM_PROP_LABEL, "#"+c['name'])
                        item.property_set ("id", c['name'])
                        item.property_set_bool (Dbusmenu.MENUITEM_PROP_VISIBLE, True)
                        item.connect(Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED, self.current().openChannel)
                        ql.child_append(item)
                self.launcher.set_property("quicklist", ql)

    def notify(self, title, message):
        self.notifier.notify(title, message)
        self.alert()

    def alert(self):
        if not self.isActiveWindow():
            self.launcher.set_property("urgent", True)
            self.tray.alert()

    def count(self):
        total = 0
        for i in range(0, self.stackedWidget.count()):
            widget = self.stackedWidget.widget(i)
            widget.count()
            if widget.messages == 0:
                self.leftPane.stopAlert(widget.team())
            else:
                self.leftPane.alert(widget.team())
            if widget.messages is not None:
                total+=widget.messages
        if total > self.messages:
            self.alert()
        if 0 == total:
            self.launcher.set_property("count_visible", False)
            self.tray.setCounter(0)
        else:
            self.tray.setCounter(total)
            self.launcher.set_property("count", total)
            self.launcher.set_property("count_visible", True)
        self.messages = total
