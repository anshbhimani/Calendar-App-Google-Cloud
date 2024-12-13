import sys
import requests
from datetime import datetime
import signal
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QLineEdit, QCalendarWidget,
                            QTimeEdit, QScrollArea, QFrame, QDialog, QTextEdit,
                            QFileDialog, QGroupBox, QToolButton)
from PyQt6.QtCore import Qt, QTime, QTimer, QDate, QRect,QEvent
from PyQt6.QtGui import QColor

class EventDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Event")
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #2C3E50;
                border-radius: 15px;
                border: 2px solid #34495E;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit, QTextEdit, QTimeEdit {
                padding: 5px;
                border-radius: 5px;
                background-color: #34495E;
                color: white;
                border: 1px solid #445566;
            }
            QPushButton {
                background-color: #3498DB;
                border-radius: 5px;
                padding: 5px;
                color: white;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Event Title
        title_layout = QHBoxLayout()
        title_label = QLabel("Title:")
        self.title_input = QLineEdit()
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_input)
        
        # Event Time
        time_layout = QHBoxLayout()
        self.start_time = QTimeEdit()
        self.start_time.setTime(QTime.currentTime())
        self.end_time = QTimeEdit()
        self.end_time.setTime(QTime.currentTime().addSecs(3600))
        
        time_layout.addWidget(QLabel("Start:"))
        time_layout.addWidget(self.start_time)
        time_layout.addWidget(QLabel("End:"))
        time_layout.addWidget(self.end_time)
        
        # Location
        location_layout = QHBoxLayout()
        location_label = QLabel("Location:")
        self.location_input = QLineEdit()
        location_layout.addWidget(location_label)
        location_layout.addWidget(self.location_input)
        
        # Notes
        notes_label = QLabel("Notes:")
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        
        # Attachment
        attachment_layout = QHBoxLayout()
        self.attachment_path = QLineEdit()
        self.attachment_path.setReadOnly(True)
        attachment_btn = QPushButton("Add Attachment")
        attachment_btn.clicked.connect(self.select_attachment)
        attachment_layout.addWidget(self.attachment_path)
        attachment_layout.addWidget(attachment_btn)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        # Add all layouts
        layout.addLayout(title_layout)
        layout.addLayout(time_layout)
        layout.addLayout(location_layout)
        layout.addWidget(notes_label)
        layout.addWidget(self.notes_input)
        layout.addLayout(attachment_layout)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def select_attachment(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Attachment")
        if file_name:
            self.attachment_path.setText(file_name)
            
    def get_event_data(self, selected_date):
        start_time = self.start_time.time().toPyTime()
        end_time = self.end_time.time().toPyTime()
        
        start_datetime = datetime.combine(selected_date, start_time).isoformat() + 'Z'
        end_datetime = datetime.combine(selected_date, end_time).isoformat() + 'Z'
        
        return {
            'summary': self.title_input.text(),
            'start': start_datetime,
            'end': end_datetime,
            'location': self.location_input.text(),
            'notes': self.notes_input.toPlainText(),
            'attachment': self.attachment_path.text(),
            'timeZone': 'Asia/Kolkata'
        }

class CustomCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)  # Call the base class method to draw the cell

        # Use the same color for all events
        if date.toPyDate() in self.parent().events_by_date:
            painter.setBrush(QColor('#3498DB'))  # Blue color for events
            painter.setPen(Qt.PenStyle.NoPen)  # No outline for the marker
            marker_size = 6
            
            # Ensure all coordinates are cast to int
            x = int(rect.center().x() - marker_size / 2)
            y = int(rect.bottom() - marker_size - 2)
            width = int(marker_size)
            height = int(marker_size)

            painter.drawEllipse(x, y, width, height)  # Draw the event marker


class CalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.API_URL = "http://localhost:9876"
        self.events_by_date = {}  # Store events by date
        self.initUI()
        self.set_window_properties()
        
    def set_window_properties(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.Tool | 
                            Qt.WindowType.WindowStaysOnBottomHint)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        screen_geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(QRect(screen_geometry.width() - 300, 0, 300, screen_geometry.height()))

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                # Prevent minimizing by restoring the window state
                self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        super().changeEvent(event)
    
    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.Tool)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.calendar = CustomCalendarWidget(self)
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
            self.events_layout.parentWidget().setFixedHeight(self.height() - 150)
        else:
            self.event_details_group.show()
            self.toggle_button.setText("Collapse")
            self.events_layout.parentWidget().setFixedHeight(self.height() - 300)

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
    
    def paintCell(self, painter, rect, date):
        if date.toPyDate() in self.events_by_date:
            painter.setBrush(QColor('#3498DB'))  # Use the same color for all events
            painter.setPen(Qt.PenStyle.NoPen)  # No outline for the marker
            marker_size = 6

            # Ensure all coordinates are cast to int
            x = int(rect.center().x() - marker_size / 2)
            y = int(rect.bottom() - marker_size - 2)
            width = int(marker_size)
            height = int(marker_size)

            painter.drawEllipse(x, y, width, height)



        
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