from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QCalendarWidget, QPushButton, QLabel, QGroupBox, QScrollArea, QFrame, QToolButton
from PyQt6.QtCore import Qt, QTimer, QDate, QRect, QEvent
from PyQt6.QtGui import QColor
import sys
import signal
import requests
from datetime import datetime

class CalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.API_URL = "http://localhost:9876"
        self.events_by_date = {}  # Store events by date
        self.initUI()
        self.set_window_properties()

    def set_window_properties(self):
        # Use Qt.Tool for tool window behavior
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnBottomHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        screen_geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(QRect(screen_geometry.width() - 300, 0, 300, screen_geometry.height()))

    def event(self, event):
        # Block any minimization or close attempts
        if event.type() in [QEvent.Type.WindowStateChange, QEvent.Type.DragEnter, QEvent.Type.MouseButtonPress]:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                # Always restore and show the window
                self.setWindowState(Qt.WindowState.WindowNoState)
                self.show()
                return True
        return super().event(event)

    def changeEvent(self, event):
        # Prevent state changes that could minimize the widget
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.setWindowState(Qt.WindowState.WindowNoState)
                self.show()
        super().changeEvent(event)

    def closeEvent(self, event):
        # Prevent window from being closed
        event.ignore()
        self.show()
        
    def focusOutEvent(self, event):
        # Ensure window remains active and visible
        self.activateWindow()
        self.raise_()
        self.show()
        super().focusOutEvent(event)

    def moveEvent(self, event):
        # Ensure window stays in place
        screen_geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(QRect(screen_geometry.width() - 300, 0, 300, screen_geometry.height()))
        event.accept()

    def initUI(self):
        self.calendar = QCalendarWidget(self)
        self.calendar.selectionChanged.connect(self.update_events_list)
        self.calendar.clicked.connect(self.update_events_list)

        self.calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: #34495E;  /* Background color of the calendar */
                color: white;  /* Text color */
            }
            QCalendarWidget QTableView {
                background-color: #34495E;  /* Background color of the cells */
                selection-background-color: #2980B9;  /* Selected date background */
                selection-color: white;  /* Selected date text color */
            }
            QCalendarWidget QHeaderView {
                background-color: #2C3E50;  /* Header background color */
                color: white;  /* Header text color */
            }
        """)

        add_btn = QPushButton("Add Event")
        add_btn.clicked.connect(self.show_event_dialog)

        events_label = QLabel("Events for Selected Date")
        events_label.setStyleSheet("font-weight: bold; margin-top: 10px;")

        # Create a layout for event details
        self.event_details_group = QGroupBox("Event Details")
        self.event_details_group.setStyleSheet("QGroupBox { border: none; }")  # Remove border
        self.event_details_layout = QVBoxLayout()
        self.event_details_group.setLayout(self.event_details_layout)

        # Toggle button for collapsing
        self.toggle_button = QToolButton()
        self.toggle_button.setText("Collapse")
        self.toggle_button.clicked.connect(self.toggle_event_details)

        # Scroll area for events
        self.events_layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        scroll_content = QWidget()
        scroll_content.setLayout(self.events_layout)  # Set the layout directly here
        self.events_layout.setSpacing(2)  # Decrease spacing between event widgets
        self.events_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins

        scroll.setWidget(scroll_content)

        container_layout = QVBoxLayout()
        container_layout.addWidget(self.calendar)
        container_layout.addWidget(self.toggle_button)
        container_layout.addWidget(add_btn)
        container_layout.addWidget(events_label)
        container_layout.addWidget(scroll)
        container_layout.addWidget(self.event_details_group)

        self.setLayout(container_layout)

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.fetch_events)
        self.refresh_timer.start(60000)  # Refresh every minute

        self.fetch_events()

    def toggle_event_details(self):
        # Toggle visibility of the event details group
        if self.event_details_group.isVisible():
            self.event_details_group.hide()
            self.toggle_button.setText("Expand")
        else:
            self.event_details_group.show()
            self.toggle_button.setText("Collapse")

    def show_event_dialog(self):
        dialog = EventDialog(self)
        if dialog.exec():
            event_data = dialog.get_event_data(self.calendar.selectedDate().toPyDate())
            self.add_event(event_data)

    def add_event(self, event_data):
        try:
            response = requests.post(f"{self.API_URL}/add_event", json=event_data)
            if response.status_code == 201:
                self.fetch_events()
        except requests.exceptions.RequestException as e:
            print(f"Error adding event: {e}")

    def fetch_events(self):
        try:
            response = requests.get(f"{self.API_URL}/events")
            if response.status_code == 200:
                events = response.json()
                self.organize_events_by_date(events)
                self.update_calendar()
                self.update_events_list()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching events: {e}")

    def organize_events_by_date(self, events):
        self.events_by_date = {}
        for event in events:
            try:
                date = datetime.fromisoformat(event['start'].replace('Z', '+00:00')).date()
                if date not in self.events_by_date:
                    self.events_by_date[date] = []
                self.events_by_date[date].append(event)
            except Exception as e:
                print(f"Error parsing date for event: {event.get('summary', 'Unknown')} - {e}")

    def update_calendar(self):
        self.calendar.updateCells()

    def update_events_list(self):
        while self.events_layout.count():
            child = self.events_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        selected_date = self.calendar.selectedDate().toPyDate()

        if selected_date in self.events_by_date:
            for event in self.events_by_date[selected_date]:
                event_widget = self.create_event_widget(event)
                self.events_layout.addWidget(event_widget)

    def create_event_widget(self, event):
        event_widget = QFrame()
        event_widget.setStyleSheet("background-color: #2C3E50; margin: 5px; border-radius: 5px;")
        layout = QVBoxLayout(event_widget)

        title = QLabel(f"Title: {event['summary']}")
        start_time = datetime.fromisoformat(event['start'].replace('Z', '+00:00')).strftime("%H:%M")
        end_time = datetime.fromisoformat(event['end'].replace('Z', '+00:00')).strftime("%H:%M")
        time_label = QLabel(f"Time: {start_time} - {end_time}")
        location = QLabel(f"Location: {event.get('location', 'N/A')}")
        notes = QLabel(f"Notes: {event.get('notes', 'N/A')}")

        layout.addWidget(title)
        layout.addWidget(time_label)
        layout.addWidget(location)
        layout.addWidget(notes)

        event_widget.setLayout(layout)

        return event_widget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalendarWidget()
    window.show()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(app.exec())
