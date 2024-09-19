import os
import json
import subprocess
import sys
import urllib.request
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QToolBar, QLineEdit, QLabel,
    QDockWidget, QTextEdit, QListWidget, QListWidgetItem, QPushButton,
    QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QMenu, QMessageBox, QDialog,
    QShortcut, QFileDialog, QInputDialog
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineDownloadItem, QWebEngineProfile
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import QUrl, Qt, QTimer
import requests
from PyQt5.QtWidgets import *
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for cx_Freeze """
    if hasattr(sys, '_MEIPASS'):
        # The application is frozen (packaged)
        base_path = sys._MEIPASS
    else:
        # The application is not frozen (development mode)
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


CONFIG_FILE = 'config.json'
BOOKMARKS_FILE = 'bookmarks.json'
HISTORY_FILE = 'history.json'
class HistoryDialog(QDialog):
    def __init__(self, history_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("History")
        self.resize(600, 400)
        self.history_list = history_list
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget(self)
        layout.addWidget(self.list_widget)

        for title in self.history_list:
            item_widget = QListWidgetItem(title)
            self.list_widget.addItem(item_widget)

        button_layout = QHBoxLayout()
        delete_btn = QPushButton("Delete", self)
        delete_btn.clicked.connect(self.delete_selected_item)
        button_layout.addWidget(delete_btn)
        layout.addLayout(button_layout)

    def delete_selected_item(self):
        selected_item = self.list_widget.currentItem()
        if selected_item:
            self.history_list.remove(selected_item.text())
            self.list_widget.takeItem(self.list_widget.row(selected_item))

class BookmarkDialog(QDialog):
    def __init__(self, bookmarks, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bookmarks")
        self.resize(600, 400)
        self.bookmarks = bookmarks
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget(self)
        layout.addWidget(self.list_widget)

        for bookmark in self.bookmarks:
            item_widget = QListWidgetItem(bookmark)
            self.list_widget.addItem(item_widget)

        button_layout = QHBoxLayout()
        delete_btn = QPushButton("Delete", self)
        delete_btn.clicked.connect(self.delete_selected_item)
        button_layout.addWidget(delete_btn)
        layout.addLayout(button_layout)

    def delete_selected_item(self):
        selected_item = self.list_widget.currentItem()
        if selected_item:
            self.bookmarks.remove(selected_item.text())
            self.list_widget.takeItem(self.list_widget.row(selected_item))

class BrowserWindow(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.loadFinished.connect(self.on_page_load_finished)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setup_settings()
        self.page().profile().downloadRequested.connect(self.on_download_requested)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_time_spent)
        self.timer.start(1000)  # Check every second
        self.start_time = None
        self.time_spent = 0
        self.time_limit = None  # New attribute for time limit

        # Connect urlChanged signal to update history
        self.urlChanged.connect(self.update_history)

    def setup_settings(self):
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.AutoLoadIconsForPage, True)

    def on_page_load_finished(self, success):
        if success:
            if isinstance(self.main_window, MainWindow):
                self.main_window.update_tab_title(self.page().title())
                self.main_window.update_url(self.url())
                self.main_window.update_security_indicator()
            self.start_time = time.time()
            self.time_spent = 0
            self.prompt_for_time_limit()  # Prompt for time limit when a page loads

    def show_context_menu(self, pos):
        menu = QMenu(self)
        dev_tools_action = QAction('Developer Tools', self)
        dev_tools_action.triggered.connect(self.main_window.toggle_developer_tools)
        menu.addAction(dev_tools_action)
        menu.exec_(self.mapToGlobal(pos))

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def adjust_zoom_factor(self, factor):
        current_zoom = self.zoomFactor()
        new_zoom = current_zoom * factor
        self.setZoomFactor(new_zoom)

    def resize_viewport(self, width, height):
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
        self.resize(width, height)

    def on_download_requested(self, download_item):
        download_path, _ = QFileDialog.getSaveFileName(self, "Save File", download_item.path())
        if download_path:
            download_item.setPath(download_path)
            download_item.accept()

    def check_time_spent(self):
        current_url = self.url().toString()
        if ("instagram.com" in current_url or "youtube.com" in current_url or "facebook.com" in current_url or "x.com" in current_url or "threads.net" in current_url or "www.snapchat.com" in current_url) and self.time_limit:
            self.time_spent += 1
            if self.time_spent > self.time_limit * 60:  # Convert minutes to seconds
                QMessageBox.information(self, 'Take a Break', 'You have reached your time limit on Instagram or YouTube. Please take a break.')
                self.time_spent = 0
        else:
            self.time_spent = 0

    def update_history(self, url):
     history_item = url.toString()
     if history_item not in self.main_window.history:
        self.main_window.history.append(history_item)
        self.main_window.save_history()  # Save the updated history


    def prompt_for_time_limit(self):
        current_url = self.url().toString()
        if "instagram.com" in current_url or "youtube.com" in current_url or "facebook.com" in current_url or "x.com" in current_url or "threads.net" in current_url or "www.snapchat.com" in current_url:
            self.time_limit, ok = QInputDialog.getInt(self, 'Set Time Limit', 'Enter time limit in minutes:', min=1)
            if not ok:
                self.time_limit = None

class MainWindow(QMainWindow):
    HISTORY_FILE = 'history.json'  # Define the class attribute for history file
    BOOKMARKS_FILE = 'bookmarks.json'
    def __init__(self):
        super(MainWindow, self).__init__()
        self.current_version = "X1"  # Set your current version
        self.check_for_updates()
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
    QTabWidget::tab-bar {
        alignment: center;
        background-color: #2e2e2e;
        border: none; /* Remove border from tab bar */
    }
    QTabBar::tab {
        background: #1c1c1c;
        padding: 10px 20px;
        font-size: 14px;
        color: #dcdcdc;
        margin-top: 10px; /* Adjusted margin */
        border-radius: 5px; /* Rounded corners */
        transition: background-color 0.3s ease, border-bottom 0.3s ease, padding 0.3s ease; /* Smooth transitions */
        border: 1px solid transparent; /* Add a border to improve hover effect */
    }
    QTabBar::tab:selected {
        background-color: #0078d4;
        color: white; /* Ensure text color is white on selected tab */
        border: 1px solid #0078d4; /* Add border to selected tab */
        padding: 12px 22px; /* Slightly increased padding for selected tab */
    }
    QTabBar::tab:hover {
    color: white; /* Ensure text color is white on hover */
    border-bottom: 2px solid #ff4500; /* Orange bottom border on hover */
    padding: 12px 22px; /* Slightly increased padding on hover */
    border-radius: 16px; /* Rounded corners */
    transition: background-color 0.3s ease, border-bottom 0.3s ease, padding 0.3s ease, border-radius 0.3s ease; /* Smooth transitions */
   }

""")


        self.setWindowTitle("Nexus Browse BETA")
        self.setGeometry(100, 100, 800, 600)

        # Set the window icon
        self.setWindowIcon(QIcon(resource_path("browse.png")))
        self.setup_ui()
         # Load history and bookmarks
        self.history = self.load_history()
        self.bookmarks = self.load_bookmarks()

    def setup_ui(self):
        self.tab1 = QWidget()
        self.tabs.addTab(self.tab1, QIcon('E:/nexusbrowseproject/icon1.png'), "Tab 1")
        self.tab1.setLayout(QVBoxLayout())
        self.browser = BrowserWindow(parent=self)
        self.tab1.layout().addWidget(self.browser)
        self.setCentralWidget(self.tabs)

        self.setup_toolbar()

        self.security_label = QLabel()
        self.statusBar().addWidget(self.security_label)
        self.update_security_indicator()

        self.history = []
        self.bookmarks = self.load_bookmarks()

        self.setup_shortcuts()

        self.developer_tools_dock = QDockWidget("Developer Tools", self)
        self.developer_tools_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.developer_tools_dock)

        self.dev_tools_browser = QTextEdit()
        self.developer_tools_dock.setWidget(self.dev_tools_browser)
        self.developer_tools_dock.hide()

        if self.is_first_time():
            self.show_welcome_page()
        else:
            self.navigate_home()

    def setup_toolbar(self):
        bottom_toolbar = QToolBar()
        bottom_toolbar.setMovable(False)
        self.addToolBar(Qt.BottomToolBarArea, bottom_toolbar)

        home_btn = QAction(QIcon(resource_path("home.png")), 'Home', self)
        home_btn.triggered.connect(self.navigate_home)
        bottom_toolbar.addAction(home_btn)

        back_btn = QAction(QIcon(resource_path("back.png")), 'Back', self)
        back_btn.triggered.connect(self.browser.back)
        bottom_toolbar.addAction(back_btn)
        

        forward_btn = QAction(QIcon(resource_path("forward.png")), 'Forward', self)
        forward_btn.triggered.connect(self.browser.forward)
        bottom_toolbar.addAction(forward_btn)
 
        reload_btn = QAction(QIcon(resource_path("reload.png")), 'Reload', self)
        reload_btn.triggered.connect(self.browser.reload)
        bottom_toolbar.addAction(reload_btn)
        self.url_bar = QLineEdit()
        self.url_bar.setStyleSheet("""
            border-radius: 20px;
            border: 1px solid #ccc;
            padding: 10px;
            background-color: white;
        """)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        bottom_toolbar.addWidget(self.url_bar)

        # Create a three dots button
        three_dots_btn = QPushButton("⋮")
        three_dots_btn.setFixedSize(50, 50)
        three_dots_btn.setStyleSheet("background-color: transparent; border: none; font-size: 50px;")
        three_dots_btn.clicked.connect(self.show_three_dots_menu)
        bottom_toolbar.addWidget(three_dots_btn)

        security_check_btn = QAction(QIcon(resource_path("secure.png")), 'Check Security', self)
        security_check_btn.triggered.connect(self.check_security)
        bottom_toolbar.addAction(security_check_btn)

    def show_three_dots_menu(self):
        menu = QMenu(self)

        history_action = QAction(QIcon(resource_path("history.png")), 'History', self)
        history_action.triggered.connect(self.show_history)
        menu.addAction(history_action)

        bookmark_action = QAction(QIcon(resource_path("bookmark.png")), 'Bookmark', self)
        bookmark_action.triggered.connect(self.add_bookmark)
        menu.addAction(bookmark_action)

        view_bookmarks_action = QAction(QIcon(resource_path("watch.png")), 'View Bookmarks', self)
        view_bookmarks_action.triggered.connect(self.show_bookmarks)
        menu.addAction(view_bookmarks_action)

        downloads_action = QAction(QIcon(resource_path("downloads.png")), 'Downloads', self)
        downloads_action.triggered.connect(self.show_downloads)
        menu.addAction(downloads_action)

        about_action = QAction(QIcon(resource_path("info.png")), 'About', self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)

        menu.setStyleSheet("""
        QMenu {
            background-color: #0078d4; /* Highlight color on hover */
            border: none; /* Remove default border */
            border-radius: 8px; /* Slightly more rounded corners */
            padding: 5px; /* Padding to ensure proper spacing */
            margin: 0px; /* Remove any margin */
        }
        QMenu::item {
            padding: 12px 24px; /* Increased spacing for each item */
            color: #fff; /* Lighter text color */
            font-size: 15px; /* Slightly larger font size */
            font-family: 'Segoe UI', sans-serif; /* Modern font */
        }
        QMenu::item:selected {
            background-color: #0078d4; /* Highlight color on hover */
            color: white; /* Text color when selected */
        }
        QMenu::item:hover {
            background-color: #0078d4; /* Highlight color on hover */
            color: white; /* Text color on hover */
        }
        QMenu::separator {
            height: 1px; /* Height of the separator */
            background-color: #0078d4; /* Highlight color on hover */
            margin: 4px 0; /* Margin for the separator */
        }
    """)

    # Ensure the global position of the menu is correctly calculated
        menu_position = self.mapToGlobal(self.sender().pos())
        menu.exec_(menu_position)
    def check_security(self):
        current_url = self.browser.url().toString()
        if current_url.startswith('https://'):
            QMessageBox.information(self, 'Security Check', 'The connection seems safe.')
        else:
            QMessageBox.warning(self, 'Security Check', 'Alerit connection seems unsafe.')
     
    def show_downloads(self):
        dialog = DownloadManagerDialog(self)
        dialog.exec_()

    def show_about(self):
        QMessageBox.information(self, 'About', 'Nexus Browse BETA\nVersion: Beta X1')

    def update_tab_title(self, title):
        self.tabs.setTabText(self.tabs.currentIndex(), title)

    def update_url(self, url):
        self.url_bar.setText(url.toString())

    def update_security_indicator(self):
        url = self.browser.url().toString()
        if url.startswith('https://'):
            self.security_label.setText("Secure")
        else:
            self.security_label.setText("Not Secure")

    def navigate_home(self):
        self.browser.setUrl(QUrl("https://nexusintell.com/search"))

    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith('http'):
            url = 'http://' + url
        self.browser.setUrl(QUrl(url))
    def load_history(self):
        if os.path.exists(self.HISTORY_FILE):
            with open(self.HISTORY_FILE, 'r') as file:
                return json.load(file)
        return []

    def load_history(self):
        if os.path.exists(self.HISTORY_FILE):
            with open(self.HISTORY_FILE, 'r') as file:
                return json.load(file)
        return []

    def save_history(self):
        with open(self.HISTORY_FILE, 'w') as file:
            json.dump(self.history, file)

    def show_history(self):
        dialog = HistoryDialog(self.history, self)
        dialog.exec_()

    def show_bookmarks(self):
        dialog = BookmarkDialog(self.bookmarks, self)
        dialog.exec_()

    def add_bookmark(self):
        current_url = self.browser.url().toString()
        if current_url not in self.bookmarks:
            self.bookmarks.append(current_url)
            self.save_bookmarks()
            QMessageBox.information(self, 'Bookmark Added', 'Bookmark added successfully!')

    def load_bookmarks(self):
        if os.path.exists(BOOKMARKS_FILE):
            with open(BOOKMARKS_FILE, 'r') as file:
                return json.load(file)
        return []

    def save_bookmarks(self):
        with open(BOOKMARKS_FILE, 'w') as file:
            json.dump(self.bookmarks, file)

    def is_first_time(self):
        if not os.path.exists(CONFIG_FILE):
            config = {'first_time': False}
            with open(CONFIG_FILE, 'w') as file:
                json.dump(config, file)
            return True
        return False

    def show_welcome_page(self):
        welcome_page_url = 'https://nexusintell.com/nexusbrowsewelcome'
        self.browser.setUrl(QUrl(welcome_page_url))

    def toggle_developer_tools(self):
        if self.developer_tools_dock.isVisible():
            self.developer_tools_dock.hide()
        else:
            self.developer_tools_dock.show()

    def setup_shortcuts(self):
        zoom_in_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in_shortcut.activated.connect(lambda: self.browser.adjust_zoom_factor(1.25))

        zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out_shortcut.activated.connect(lambda: self.browser.adjust_zoom_factor(0.8))
    def update_security_indicator(self):
        url = self.browser.url().toString()
        if url.startswith('https://'):
            self.security_label.setText("The connection seems safe")
        else:
            self.security_label.setText("Alert, The connection seems unsafe.")
    def check_internet(self):
        try:
            urllib.request.urlopen("https://nexusintell.com/search", timeout=1)
            return True
        except urllib.error.URLError:
            return False

    def navigate_home(self):
        if self.check_internet():
            self.browser.setUrl(QUrl("https://nexusintell.com/search"))
        else:
            self.browser.setUrl(QUrl("E:/nexusbrowseproject/flappy_bird.html"))
    HISTORY_FILE = 'history.json'

    def load_history(self):
     if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as file:
            return json.load(file)
     return []

    def save_history(self):
     with open(HISTORY_FILE, 'w') as file:
        json.dump(self.history, file)
    def check_for_updates(self):
     try:
        response = requests.get("https://nexusintell.com/latestbrowse.txt")
        response.raise_for_status()
        latest_version = response.text.strip()

        print(f"Fetched latest version: '{latest_version}'")

        latest_version_int = int(latest_version[1:])  # 'X2' -> 2
        current_version_int = int(self.current_version[1:])  # 'X1' -> 1


        if latest_version_int > current_version_int:
            self.prompt_for_update(latest_version)
        else:
            print("No update needed. Current version is up to date.")
     except requests.RequestException as e:
        print(f"Failed to check for updates: {e}")
     except Exception as e:
        print(f"Unexpected error: {e}")


    def prompt_for_update(self, latest_version):
        reply = QMessageBox.question(self, 'Update Available',
                                     f"A new version {latest_version} is available. Do you want to update?,\nNexusintell recommends to download the update!",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.download_update()

    def download_update(self):
        try:
            update_url = "https://nexusintell.com/NexusBrowse.exe"
            local_filename = "Aethonupdate.exe"
            
            # Create and show the progress dialog
            progress_dialog = QProgressDialog("Updating...", None, 0, 0, self)
            progress_dialog.setWindowTitle('Update')
            progress_dialog.setCancelButton(None)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()

            with requests.get(update_url, stream=True) as r:
                r.raise_for_status()
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            progress_dialog.close()
            self.run_update_executable(local_filename)
        except requests.RequestException as e:
            progress_dialog.close()
            QMessageBox.critical(self, 'Update Failed', f"Failed to download the update: {e}")
        except Exception as e:
            progress_dialog.close()
            QMessageBox.critical(self, 'Update Canceled', f"Update canceled: {e}")

    def run_update_executable(self, update_executable):
        try:
            # Ensure the update executable exists
            if os.path.exists(update_executable):
                # Prompt user to close the application if necessary
                QMessageBox.warning(self, 'Update Required', 'Please close the application before proceeding with the update.')

                # Run the update executable
                subprocess.Popen(update_executable, shell=True)
                self.close()  # Close the application to allow the update executable to proceed

            else:
                QMessageBox.critical(self, 'Update Failed', "The downloaded update file is missing.")
        except Exception as e:
            QMessageBox.critical(self, 'Update Failed', f"Failed to run the update executable: {e}")

    def restart_application(self):
        try:
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            QMessageBox.critical(self, 'Restart Failed', f"Failed to restart the application: {e}")
class DownloadManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloads")
        self.resize(600, 400)
        self.setup_ui()

        # Connect to downloadRequested signal to handle download requests
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self.download_requested)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.downloads_list = QListWidget(self)
        layout.addWidget(self.downloads_list)

        button_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear Downloads", self)
        clear_btn.clicked.connect(self.clear_downloads)
        button_layout.addWidget(clear_btn)
        layout.addLayout(button_layout)

    def download_requested(self, download):
        # Handle download request
        url = download.url().toString()
        download_item = QListWidgetItem(QIcon('E:/nexusbrowseproject/downloads.png'), url, self.downloads_list)
        download_item.setData(Qt.UserRole, download)
        self.downloads_list.addItem(download_item)

    def clear_downloads(self):
        self.downloads_list.clear()

    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())