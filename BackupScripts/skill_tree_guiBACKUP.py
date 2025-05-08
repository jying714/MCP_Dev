import sys
import json
import os
import logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton, QGraphicsScene, QGraphicsView, QGraphicsEllipseItem, QGraphicsLineItem
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPen, QColor, QBrush

# Constants
DATA_FILE = os.path.join("output", "skill_tree_data.json")
WINDOW_TITLE = "Path of Exile 2 Passive Skill Tree"
MAX_POINTS = 123  # Total points for main tree
MAX_ASCENDANCY_POINTS = 8  # Total points for Ascendancy tree
LOG_FILE = os.path.join("output", "skill_tree_gui.log")

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

class SkillTreeGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(100, 100, 1200, 900)
        self.setStyleSheet("background-color: #1C2526;")

        # Load skill tree data
        self.skill_tree_data = self.load_skill_tree_data()

        # Points tracking
        self.allocated_points = 0
        self.allocated_ascendancy_points = 0
        self.allocated_nodes = set()  # Track allocated node IDs
        self.allocated_ascendancy_nodes = set()

        # Initialize UI
        self.init_ui()

        # Initialize scene
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene, self)
        self.view.setMinimumSize(1000, 750)  # Minimum size, will expand in full-screen
        self.view.setStyleSheet("background-color: #1C2526; border: none;")
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)  # Enable panning
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)  # Zoom relative to mouse position

        # Layout for scene
        self.scene_layout = QHBoxLayout()
        self.scene_layout.addStretch()
        self.scene_layout.addWidget(self.view)
        self.scene_layout.addStretch()
        self.central_widget.layout().addLayout(self.scene_layout)

        # Reset button
        self.reset_button = QPushButton("Reset Points")
        self.reset_button.clicked.connect(self.reset_points)
        self.reset_button.setFixedWidth(200)
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        reset_layout.addWidget(self.reset_button)
        reset_layout.addStretch()
        self.central_widget.layout().addLayout(reset_layout)

        # Node and connection items for interaction
        self.node_items = {}  # Map node ID to QGraphicsEllipseItem
        self.connection_items = {}  # Map (from, to) to QGraphicsLineItem
        self.ascendancy_node_items = {}
        self.ascendancy_connection_items = {}

        # Zoom tracking
        self.zoom_factor = 1.0
        self.view.wheelEvent = self.wheel_event  # Override wheel event for zooming

        # Load the skill tree once
        try:
            self.load_skill_tree_once()
            self.class_combo.setCurrentText("Warrior")
            self.update_ascendancy_options()
            self.ascendancy_combo.setCurrentText("No Ascendancy")
            self.center_on_class("Warrior")
        except Exception as e:
            logger.error(f"Error during initialization: {str(e)}")
            sys.exit(1)

    def resizeEvent(self, event):
        """Adjust view size in full-screen mode."""
        super().resizeEvent(event)
        try:
            # Adjust view size to fit window, maintaining aspect ratio
            window_size = self.central_widget.size()
            view_width = window_size.width() - 40  # Account for layout margins
            view_height = window_size.height() - 150  # Account for UI elements
            self.view.setFixedSize(view_width, view_height)
            self.center_on_class(self.class_combo.currentText())
        except Exception as e:
            logger.error(f"Error during resize: {str(e)}")

    def init_ui(self):
        """Initialize the GUI layout and widgets."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        # Class and Ascendancy selection
        selection_layout = QHBoxLayout()
        selection_layout.addStretch()
        self.class_label = QLabel("Class:")
        self.class_label.setStyleSheet("color: white;")
        self.class_combo = QComboBox()
        self.class_combo.addItems(sorted(self.skill_tree_data["classes"].keys()))
        self.class_combo.currentTextChanged.connect(self.update_ascendancy_options)
        self.class_combo.setFixedWidth(150)
        self.class_combo.setStyleSheet("background-color: #333; color: white;")

        self.ascendancy_label = QLabel("Ascendancy:")
        self.ascendancy_label.setStyleSheet("color: white;")
        self.ascendancy_combo = QComboBox()
        self.ascendancy_combo.currentTextChanged.connect(self.center_on_ascendancy)
        self.ascendancy_combo.setFixedWidth(150)
        self.ascendancy_combo.setStyleSheet("background-color: #333; color: white;")

        selection_layout.addWidget(self.class_label)
        selection_layout.addWidget(self.class_combo)
        selection_layout.addWidget(self.ascendancy_label)
        selection_layout.addWidget(self.ascendancy_combo)
        selection_layout.addStretch()
        layout.addLayout(selection_layout)

        # Points display
        self.points_label = QLabel(f"Points: 0/{MAX_POINTS}")
        self.points_label.setStyleSheet("color: white;")
        self.ascendancy_points_label = QLabel(f"Ascendancy Points: 0/{MAX_ASCENDANCY_POINTS}")
        self.ascendancy_points_label.setStyleSheet("color: white;")
        self.ascendancy_points_label.hide()  # Hidden until Ascendancy is selected

        points_layout = QHBoxLayout()
        points_layout.addWidget(self.points_label)
        points_layout.addStretch()
        layout.addLayout(points_layout)

        ascendancy_points_layout = QHBoxLayout()
        ascendancy_points_layout.addWidget(self.ascendancy_points_label)
        ascendancy_points_layout.addStretch()
        layout.addLayout(ascendancy_points_layout)

    def load_skill_tree_data(self) -> dict:
        """Load skill tree data from JSON file."""
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Successfully loaded skill tree data")
            return data
        except Exception as e:
            logger.error(f"Error loading skill tree data: {str(e)}")
            sys.exit(1)

    def update_ascendancy_options(self):
        """Update Ascendancy options based on selected class."""
        try:
            selected_class = self.class_combo.currentText()
            ascendancies = self.skill_tree_data["classes"][selected_class]["ascendancies"]
            self.ascendancy_combo.clear()
            self.ascendancy_combo.addItem("No Ascendancy")
            self.ascendancy_combo.addItems(ascendancies)
            self.center_on_class(selected_class)
        except Exception as e:
            logger.error(f"Error updating Ascendancy options: {str(e)}")
            self.ascendancy_combo.clear()

    def wheel_event(self, event):
        """Handle mouse wheel events for zooming."""
        try:
            zoom_in_factor = 1.1
            zoom_out_factor = 1 / zoom_in_factor

            # Zoom in or out based on wheel direction
            if event.angleDelta().y() > 0:
                zoom = zoom_in_factor
            else:
                zoom = zoom_out_factor

            self.zoom_factor *= zoom
            self.view.scale(zoom, zoom)
        except Exception as e:
            logger.error(f"Error during zooming: {str(e)}")

    def load_skill_tree_once(self):
        """Load and render the skill tree once during initialization."""
        try:
            # Clear previous items
            self.scene.clear()
            self.node_items.clear()
            self.connection_items.clear()
            self.ascendancy_node_items.clear()
            self.ascendancy_connection_items.clear()
            self.allocated_points = 0
            self.allocated_ascendancy_points = 0
            self.allocated_nodes.clear()
            self.allocated_ascendancy_nodes.clear()
            self.zoom_factor = 1.0
            self.view.resetTransform()
            self.update_points_display()

            # Load main tree
            main_nodes = self.skill_tree_data["main_tree"]["nodes"]
            main_connections = self.skill_tree_data["main_tree"]["connections"]

            # Normalize coordinates for rendering
            x_coords = [node["x"] for node in main_nodes]
            y_coords = [node["y"] for node in main_nodes]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)
            x_range = x_max - x_min if x_max != x_min else 1
            y_range = y_max - y_min if y_max != y_min else 1

            # Scale factor to fit the view (reduced to spread nodes)
            self.scale = min(self.view.width() / x_range, self.view.height() / y_range) * 0.3  # Further reduced scale to spread nodes

            # Store bounds for scene rect
            self.scene_x_min = (x_min - 100) * self.scale  # Add padding
            self.scene_x_max = (x_max + 100) * self.scale
            self.scene_y_min = (y_min - 100) * self.scale
            self.scene_y_max = (y_max + 100) * self.scale
            self.scene.setSceneRect(QRectF(self.scene_x_min, self.scene_y_min, self.scene_x_max - self.scene_x_min, self.scene_y_max - self.scene_y_min))

            # Center of the tree for initial positioning
            tree_center_x = (self.scene_x_max + self.scene_x_min) / 2
            tree_center_y = (self.scene_y_max + self.scene_y_min) / 2

            # Draw main tree connections (behind nodes)
            for conn in main_connections:
                from_node = next(node for node in main_nodes if node["id"] == conn["from"])
                to_node = next(node for node in main_nodes if node["id"] == conn["to"])
                x1 = (from_node["x"] * self.scale) - (x_min * self.scale) + tree_center_x - (x_range * self.scale) / 2
                y1 = (from_node["y"] * self.scale) - (y_min * self.scale) + tree_center_y - (y_range * self.scale) / 2
                x2 = (to_node["x"] * self.scale) - (x_min * self.scale) + tree_center_x - (x_range * self.scale) / 2
                y2 = (to_node["y"] * self.scale) - (y_min * self.scale) + tree_center_y - (y_range * self.scale) / 2
                line = QGraphicsLineItem(x1, y1, x2, y2)
                line.setPen(QPen(QColor("gray"), 1))
                self.connection_items[(conn["from"], conn["to"])] = line
                self.scene.addItem(line)

            # Draw main tree nodes
            for node in main_nodes:
                x = (node["x"] * self.scale) - (x_min * self.scale) + tree_center_x - (x_range * self.scale) / 2
                y = (node["y"] * self.scale) - (y_min * self.scale) + tree_center_y - (y_range * self.scale) / 2
                size = 20 if node["is_root"] else 15 if node["type"] == "Keystone" else 10 if node["type"] == "Notable" else 8 if node["type"] == "Mastery" else 5
                color = QColor("red") if node["is_root"] else QColor("gold") if node["type"] == "Keystone" else QColor("orange") if node["type"] == "Notable" else QColor("purple") if node["type"] == "Mastery" else QColor("gray")
                ellipse = QGraphicsEllipseItem(x - size / 2, y - size / 2, size, size)
                ellipse.setBrush(QBrush(color))
                ellipse.setPen(QPen(Qt.NoPen))
                ellipse.setToolTip(f"{node['name']}\nEffects: {node['effects']}")
                ellipse.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
                ellipse.mousePressEvent = lambda event, n=node: self.node_clicked(n, event)
                self.node_items[node["id"]] = ellipse
                self.scene.addItem(ellipse)

            # Load Ascendancy trees for all classes
            for class_name in self.skill_tree_data["classes"].keys():
                if class_name in self.skill_tree_data["ascendancy_trees"]:
                    ascendancy_nodes = self.skill_tree_data["ascendancy_trees"][class_name]["nodes"]
                    ascendancy_connections = self.skill_tree_data["ascendancy_trees"][class_name]["connections"]

                    # Normalize Ascendancy coordinates
                    ax_coords = [node["x"] for node in ascendancy_nodes]
                    ay_coords = [node["y"] for node in ascendancy_nodes]
                    ax_min, ax_max = min(ax_coords), max(ax_coords)
                    ay_min, ay_max = min(ay_coords), max(ay_coords)
                    ax_range = ax_max - ax_min if ax_max != ax_min else 1
                    ay_range = ay_max - ay_min if ay_max != ay_min else 1
                    asc_scale = min(200 / ax_range, 200 / ay_range) * 0.8  # Smaller scale for central placement

                    # Draw Ascendancy connections
                    for conn in ascendancy_connections:
                        from_node = next(node for node in ascendancy_nodes if node["id"] == conn["from"])
                        to_node = next(node for node in ascendancy_nodes if node["id"] == conn["to"])
                        x1 = (from_node["x"] - ax_min) * asc_scale
                        y1 = (from_node["y"] - ay_min) * asc_scale
                        x2 = (to_node["x"] - ax_min) * asc_scale
                        y2 = (to_node["y"] - ay_min) * asc_scale
                        line = QGraphicsLineItem(x1, y1, x2, y2)
                        line.setPen(QPen(QColor("gray"), 1))
                        line.setVisible(False)  # Hidden by default
                        self.ascendancy_connection_items[(class_name, conn["from"], conn["to"])] = line
                        self.scene.addItem(line)

                    # Draw Ascendancy nodes
                    for node in ascendancy_nodes:
                        x = (node["x"] - ax_min) * asc_scale
                        y = (node["y"] - ay_min) * asc_scale
                        size = 15 if node["type"] == "Keystone" else 10 if node["type"] == "Notable" else 5
                        color = QColor("gold") if node["type"] == "Keystone" else QColor("orange") if node["type"] == "Notable" else QColor("gray")
                        ellipse = QGraphicsEllipseItem(x - size / 2, y - size / 2, size, size)
                        ellipse.setBrush(QBrush(color))
                        ellipse.setPen(QPen(Qt.NoPen))
                        ellipse.setToolTip(f"{node['name']}\nEffects: {node['effects']}")
                        ellipse.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
                        ellipse.mousePressEvent = lambda event, n=node: self.ascendancy_node_clicked(n, event)
                        ellipse.setVisible(False)  # Hidden by default
                        self.ascendancy_node_items[(class_name, node["id"])] = ellipse
                        self.scene.addItem(ellipse)

        except Exception as e:
            logger.error(f"Error loading skill tree once: {str(e)}")
            self.scene.clear()

    def center_on_class(self, selected_class: str):
        """Center the view on the starting node of the selected class."""
        try:
            # Get starting nodes for the selected class
            starting_nodes = self.skill_tree_data["classes"][selected_class]["starting_nodes"]
            if not starting_nodes:
                raise ValueError(f"No starting nodes found for class {selected_class}")

            # Find a starting node to center on
            starting_node = next(node for node in self.skill_tree_data["main_tree"]["nodes"] if node["id"] in starting_nodes)
            x_coords = [node["x"] for node in self.skill_tree_data["main_tree"]["nodes"]]
            y_coords = [node["y"] for node in self.skill_tree_data["main_tree"]["nodes"]]
            x_min = min(x_coords)
            y_min = min(y_coords)
            x_range = max(x_coords) - x_min
            y_range = max(y_coords) - y_min

            tree_center_x = (self.scene_x_max + self.scene_x_min) / 2
            tree_center_y = (self.scene_y_max + self.scene_y_min) / 2

            # Calculate the position of the starting node in the scene
            start_x = (starting_node["x"] * self.scale) - (x_min * self.scale) + tree_center_x - (x_range * self.scale) / 2
            start_y = (starting_node["y"] * self.scale) - (y_min * self.scale) + tree_center_y - (y_range * self.scale) / 2

            # Update Ascendancy node positions to center around the starting node
            for class_name in self.skill_tree_data["classes"].keys():
                if class_name in self.skill_tree_data["ascendancy_trees"]:
                    ascendancy_nodes = self.skill_tree_data["ascendancy_trees"][class_name]["nodes"]
                    ax_coords = [node["x"] for node in ascendancy_nodes]
                    ay_coords = [node["y"] for node in ascendancy_nodes]
                    ax_min = min(ax_coords)
                    ay_min = min(ay_coords)
                    ax_range = max(ax_coords) - ax_min if max(ax_coords) != ax_min else 1
                    ay_range = max(ay_coords) - ay_min if max(ay_coords) != ay_min else 1
                    asc_scale = min(200 / ax_range, 200 / ay_range) * 0.8

                    # Update Ascendancy connections
                    for (cls, from_id, to_id), line in self.ascendancy_connection_items.items():
                        if cls == class_name:
                            from_node = next(node for node in ascendancy_nodes if node["id"] == from_id)
                            to_node = next(node for node in ascendancy_nodes if node["id"] == to_id)
                            x1 = (from_node["x"] - ax_min) * asc_scale + start_x - (ax_range * asc_scale) / 2
                            y1 = (from_node["y"] - ay_min) * asc_scale + start_y - (ay_range * asc_scale) / 2
                            x2 = (to_node["x"] - ax_min) * asc_scale + start_x - (ax_range * asc_scale) / 2
                            y2 = (to_node["y"] - ay_min) * asc_scale + start_y - (ay_range * asc_scale) / 2
                            line.setLine(x1, y1, x2, y2)

                    # Update Ascendancy nodes
                    for (cls, node_id), item in self.ascendancy_node_items.items():
                        if cls == class_name:
                            node = next(node for node in ascendancy_nodes if node["id"] == node_id)
                            x = (node["x"] - ax_min) * asc_scale + start_x - (ax_range * asc_scale) / 2
                            y = (node["y"] - ay_min) * asc_scale + start_y - (ay_range * asc_scale) / 2
                            size = item.rect().width()
                            item.setRect(x - size / 2, y - size / 2, size, size)

            # Center the view on the starting node
            self.view.centerOn(start_x, start_y)
        except Exception as e:
            logger.error(f"Error centering on class {selected_class}: {str(e)}")

    def center_on_ascendancy(self):
        """Show or hide the Ascendancy tree based on selection."""
        try:
            selected_class = self.class_combo.currentText()
            selected_ascendancy = self.ascendancy_combo.currentText()

            # Hide all Ascendancy nodes and connections
            for (cls, _, _), item in self.ascendancy_connection_items.items():
                item.setVisible(False)
            for (cls, _), item in self.ascendancy_node_items.items():
                item.setVisible(False)

            # Show root nodes if Ascendancy is not selected
            for node_id, item in self.node_items.items():
                node = next(n for n in self.skill_tree_data["main_tree"]["nodes"] if n["id"] == node_id)
                if node["is_root"]:
                    item.setVisible(selected_ascendancy == "No Ascendancy")

            # Show Ascendancy tree if selected
            if selected_ascendancy != "No Ascendancy":
                self.ascendancy_points_label.show()
                for (cls, _, _), item in self.ascendancy_connection_items.items():
                    if cls == selected_class:
                        item.setVisible(True)
                for (cls, node_id), item in self.ascendancy_node_items.items():
                    if cls == selected_class:
                        item.setVisible(True)
            else:
                self.ascendancy_points_label.hide()
                self.allocated_ascendancy_points = 0
                self.allocated_ascendancy_nodes.clear()
                for (cls, _), item in self.ascendancy_node_items.items():
                    if cls == selected_class:
                        node = next(n for n in self.skill_tree_data["ascendancy_trees"][cls]["nodes"] if n["id"] == node_id)
                        color = QColor("gold") if node["type"] == "Keystone" else QColor("orange") if node["type"] == "Notable" else QColor("gray")
                        item.setBrush(QBrush(color))
                for (cls, _, _), line in self.ascendancy_connection_items.items():
                    if cls == selected_class:
                        line.setPen(QPen(QColor("gray"), 1))

            self.update_points_display()
        except Exception as e:
            logger.error(f"Error centering on Ascendancy: {str(e)}")

    def node_clicked(self, node, event):
        """Handle clicks on main tree nodes."""
        try:
            if event.button() != Qt.LeftButton:
                return

            # Check if node can be allocated
            if self.allocated_points >= MAX_POINTS:
                return

            # Check if node is reachable
            if not self.can_allocate_node(node["id"]):
                return

            # Allocate the node
            self.allocated_nodes.add(node["id"])
            self.allocated_points += 1
            self.node_items[node["id"]].setBrush(QBrush(QColor("green")))
            self.update_connections()
            self.update_points_display()
        except Exception as e:
            logger.error(f"Error during node click: {str(e)}")

    def ascendancy_node_clicked(self, node, event):
        """Handle clicks on Ascendancy tree nodes."""
        try:
            if event.button() != Qt.LeftButton:
                return

            # Check if node can be allocated
            if self.allocated_ascendancy_points >= MAX_ASCENDANCY_POINTS:
                return

            # Check if node is reachable in Ascendancy tree
            if not self.can_allocate_ascendancy_node(node["id"]):
                return

            # Allocate the node
            self.allocated_ascendancy_nodes.add(node["id"])
            self.allocated_ascendancy_points += 1
            self.ascendancy_node_items[(self.class_combo.currentText(), node["id"])].setBrush(QBrush(QColor("green")))
            self.update_ascendancy_connections()
            self.update_points_display()
        except Exception as e:
            logger.error(f"Error during Ascendancy node click: {str(e)}")

    def can_allocate_node(self, node_id: int) -> bool:
        """Check if a main tree node can be allocated."""
        try:
            if node_id in self.allocated_nodes:
                return False

            selected_class = self.class_combo.currentText()
            starting_nodes = self.skill_tree_data["classes"][selected_class]["starting_nodes"]

            # If no points allocated, only starting nodes can be allocated
            if not self.allocated_nodes:
                return node_id in starting_nodes

            # Check if the node is connected to an allocated node
            connections = self.skill_tree_data["main_tree"]["connections"]
            for conn in connections:
                if conn["from"] == node_id and conn["to"] in self.allocated_nodes:
                    return True
                if conn["to"] == node_id and conn["from"] in self.allocated_nodes:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking main node allocation: {str(e)}")
            return False

    def can_allocate_ascendancy_node(self, node_id: int) -> bool:
        """Check if an Ascendancy node can be allocated."""
        try:
            if node_id in self.allocated_ascendancy_nodes:
                return False

            selected_class = self.class_combo.currentText()
            ascendancy_nodes = self.skill_tree_data["ascendancy_trees"][selected_class]["nodes"]
            ascendancy_connections = self.skill_tree_data["ascendancy_trees"][selected_class]["connections"]

            # Identify starting nodes in Ascendancy tree (nodes with no incoming connections)
            incoming_connections = {conn["to"] for conn in ascendancy_connections}
            starting_nodes = {node["id"] for node in ascendancy_nodes if node["id"] not in incoming_connections}

            # If no points allocated, only starting nodes can be allocated
            if not self.allocated_ascendancy_nodes:
                return node_id in starting_nodes

            # Check if the node is connected to an allocated node
            for conn in ascendancy_connections:
                if conn["from"] == node_id and conn["to"] in self.allocated_ascendancy_nodes:
                    return True
                if conn["to"] == node_id and conn["from"] in self.allocated_ascendancy_nodes:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking Ascendancy node allocation: {str(e)}")
            return False

    def update_connections(self):
        """Update main tree connection colors based on allocated nodes."""
        try:
            for (from_id, to_id), line in self.connection_items.items():
                if from_id in self.allocated_nodes and to_id in self.allocated_nodes:
                    line.setPen(QPen(QColor("blue"), 1))
                else:
                    line.setPen(QPen(QColor("gray"), 1))
        except Exception as e:
            logger.error(f"Error updating main tree connections: {str(e)}")

    def update_ascendancy_connections(self):
        """Update Ascendancy tree connection colors based on allocated nodes."""
        try:
            for (cls, from_id, to_id), line in self.ascendancy_connection_items.items():
                if cls == self.class_combo.currentText():
                    if from_id in self.allocated_ascendancy_nodes and to_id in self.allocated_ascendancy_nodes:
                        line.setPen(QPen(QColor("blue"), 1))
                    else:
                        line.setPen(QPen(QColor("gray"), 1))
        except Exception as e:
            logger.error(f"Error updating Ascendancy connections: {str(e)}")

    def reset_points(self):
        """Reset all allocated points."""
        try:
            self.allocated_points = 0
            self.allocated_ascendancy_points = 0
            for node_id, item in self.node_items.items():
                node = next(n for n in self.skill_tree_data["main_tree"]["nodes"] if n["id"] == node_id)
                color = QColor("red") if node["is_root"] else QColor("gold") if node["type"] == "Keystone" else QColor("orange") if node["type"] == "Notable" else QColor("purple") if node["type"] == "Mastery" else QColor("gray")
                item.setBrush(QBrush(color))
                # Show root node if Ascendancy is not selected
                selected_ascendancy = self.ascendancy_combo.currentText()
                if selected_ascendancy == "No Ascendancy" and node["is_root"]:
                    item.setVisible(True)
            for (cls, node_id), item in self.ascendancy_node_items.items():
                if cls == self.class_combo.currentText():
                    node = next(n for n in self.skill_tree_data["ascendancy_trees"][cls]["nodes"] if n["id"] == node_id)
                    color = QColor("gold") if node["type"] == "Keystone" else QColor("orange") if node["type"] == "Notable" else QColor("gray")
                    item.setBrush(QBrush(color))
            for line in self.connection_items.values():
                line.setPen(QPen(QColor("gray"), 1))
            for (cls, _, _), line in self.ascendancy_connection_items.items():
                if cls == self.class_combo.currentText():
                    line.setPen(QPen(QColor("gray"), 1))
            self.allocated_nodes.clear()
            self.allocated_ascendancy_nodes.clear()
            self.update_points_display()
        except Exception as e:
            logger.error(f"Error resetting points: {str(e)}")

    def update_points_display(self):
        """Update the points display labels."""
        try:
            self.points_label.setText(f"Points: {self.allocated_points}/{MAX_POINTS}")
            self.ascendancy_points_label.setText(f"Ascendancy Points: {self.allocated_ascendancy_points}/{MAX_ASCENDANCY_POINTS}")
        except Exception as e:
            logger.error(f"Error updating points display: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SkillTreeGUI()
    window.show()
    sys.exit(app.exec_())