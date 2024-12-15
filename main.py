import math
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple
import pygame

class Tool(Enum):
    SELECT = "select"
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    POLYGON = "polygon"

@dataclass
class Shape:
    type: Tool
    points: List[Tuple[float, float]]
    selected: bool = False
    color: Tuple[int, int, int] = (0, 0, 0)
    line_width: int = 2

class Command:
    def execute(self):
        pass
    
    def undo(self):
        pass

class AddShapeCommand(Command):
    def __init__(self, cad_app, shape):
        self.cad_app = cad_app
        self.shape = shape
        
    def execute(self):
        self.cad_app.shapes.append(self.shape)
        
    def undo(self):
        self.cad_app.shapes.remove(self.shape)

class DeleteShapeCommand(Command):
    def __init__(self, cad_app, shapes):
        self.cad_app = cad_app
        self.shapes = shapes
        
    def execute(self):
        for shape in self.shapes:
            self.cad_app.shapes.remove(shape)
            
    def undo(self):
        for shape in self.shapes:
            self.cad_app.shapes.append(shape)

class CADApp:
    def __init__(self):
        pygame.init()
        self.width = 800
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Pygame CAD")
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        
        self.shapes: List[Shape] = []
        self.current_tool = Tool.SELECT
        self.drawing = False
        self.start_point = None
        self.current_point = None
        self.selected_shapes: List[Shape] = []
        self.selection_rect = None
        
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        
        self.panning = False
        self.last_mouse_pos = None
        
        self.snap_to_grid = True
        self.grid_size = 50
        self.show_grid = True
        self.polygon_points: List[Tuple[float, float]] = []
        
    def execute_command(self, command: Command):
        command.execute()
        self.undo_stack.append(command)
        self.redo_stack.clear()
        
    def undo(self):
        if self.undo_stack:
            command = self.undo_stack.pop()
            command.undo()
            self.redo_stack.append(command)
            
    def redo(self):
        if self.redo_stack:
            command = self.redo_stack.pop()
            command.execute()
            self.undo_stack.append(command)
            
    def screen_to_world(self, pos):
        x, y = pos
        wx = (x - self.pan_x) / self.scale
        wy = (y - self.pan_y) / self.scale
        return (wx, wy)
        
    def world_to_screen(self, pos):
        x, y = pos
        sx = x * self.scale + self.pan_x
        sy = y * self.scale + self.pan_y
        return (int(sx), int(sy))
        
    def snap_point(self, point):
        if not self.snap_to_grid:
            return point
        x, y = point
        return (round(x / self.grid_size) * self.grid_size,
                round(y / self.grid_size) * self.grid_size)
                
    def draw_grid(self):
        if not self.show_grid:
            return
            
        # Calculate visible grid range
        start_x = -int(self.pan_x / self.scale / self.grid_size) * self.grid_size
        end_x = start_x + int(self.width / self.scale / self.grid_size + 2) * self.grid_size
        start_y = -int(self.pan_y / self.scale / self.grid_size) * self.grid_size
        end_y = start_y + int(self.height / self.scale / self.grid_size + 2) * self.grid_size
        
        for x in range(start_x, end_x, self.grid_size):
            start = self.world_to_screen((x, start_y))
            end = self.world_to_screen((x, end_y))
            pygame.draw.line(self.screen, (200, 200, 200), start, end)
            
        for y in range(start_y, end_y, self.grid_size):
            start = self.world_to_screen((start_x, y))
            end = self.world_to_screen((end_x, y))
            pygame.draw.line(self.screen, (200, 200, 200), start, end)
            
    def draw_shape(self, shape: Shape):
        color = (255, 0, 0) if shape.selected else shape.color
        
        if shape.type == Tool.LINE:
            start = self.world_to_screen(shape.points[0])
            end = self.world_to_screen(shape.points[1])
            pygame.draw.line(self.screen, color, start, end, shape.line_width)
            
        elif shape.type == Tool.RECTANGLE:
            p1 = self.world_to_screen(shape.points[0])
            p2 = self.world_to_screen(shape.points[1])
            rect = pygame.Rect(min(p1[0], p2[0]), min(p1[1], p2[1]),
                             abs(p2[0] - p1[0]), abs(p2[1] - p1[1]))
            pygame.draw.rect(self.screen, color, rect, shape.line_width)
            
        elif shape.type == Tool.CIRCLE:
            center = self.world_to_screen(shape.points[0])
            edge = self.world_to_screen(shape.points[1])
            radius = int(math.sqrt((edge[0] - center[0])**2 + 
                                 (edge[1] - center[1])**2))
            pygame.draw.circle(self.screen, color, center, radius, shape.line_width)
            
        elif shape.type == Tool.POLYGON:
            points = [self.world_to_screen(p) for p in shape.points]
            if len(points) >= 2:
                pygame.draw.lines(self.screen, color, True, points, shape.line_width)
                
    def draw_preview(self):
        if not self.drawing or not self.current_point:
            return
            
        if self.current_tool == Tool.POLYGON:
            points = [self.world_to_screen(p) for p in self.polygon_points]
            current = self.world_to_screen(self.current_point)
            points.append(current)
            if len(points) >= 2:
                pygame.draw.lines(self.screen, (0, 0, 255), False, points, 2)
        elif self.start_point:
            p1 = self.world_to_screen(self.start_point)
            p2 = self.world_to_screen(self.current_point)
            
            if self.current_tool == Tool.LINE:
                pygame.draw.line(self.screen, (0, 0, 255), p1, p2, 2)
            elif self.current_tool == Tool.RECTANGLE:
                rect = pygame.Rect(min(p1[0], p2[0]), min(p1[1], p2[1]),
                                 abs(p2[0] - p1[0]), abs(p2[1] - p1[1]))
                pygame.draw.rect(self.screen, (0, 0, 255), rect, 2)
            elif self.current_tool == Tool.CIRCLE:
                radius = int(math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2))
                pygame.draw.circle(self.screen, (0, 0, 255), p1, radius, 2)
                
    def draw_selection_rect(self):
        if not self.selection_rect:
            return
            
        p1 = self.world_to_screen(self.selection_rect[0])
        p2 = self.world_to_screen(self.selection_rect[1])
        rect = pygame.Rect(min(p1[0], p2[0]), min(p1[1], p2[1]),
                         abs(p2[0] - p1[0]), abs(p2[1] - p1[1]))
        pygame.draw.rect(self.screen, (0, 120, 255), rect, 1)
        
    def draw_status(self):
        tool_text = self.font.render(f"Tool: {self.current_tool.value}", True, (0, 0, 0))
        self.screen.blit(tool_text, (10, 10))
        
        if self.current_point:
            pos_text = self.font.render(
                f"Pos: ({self.current_point[0]:.1f}, {self.current_point[1]:.1f})",
                True, (0, 0, 0))
            self.screen.blit(pos_text, (10, 40))
            
    def point_in_rect(self, point, rect):
        """Check if a point is inside a rectangle defined by two points."""
        x, y = point
        x1, y1 = min(rect[0][0], rect[1][0]), min(rect[0][1], rect[1][1])
        x2, y2 = max(rect[0][0], rect[1][0]), max(rect[0][1], rect[1][1])
        return x1 <= x <= x2 and y1 <= y <= y2
        
    def point_on_line(self, point, line_start, line_end, tolerance=5.0):
        """Check if a point is near a line segment."""
        x, y = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Calculate the distance from point to line segment
        line_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if line_length == 0:
            return math.sqrt((x - x1)**2 + (y - y1)**2) <= tolerance
            
        t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / (line_length**2)))
        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)
        
        distance = math.sqrt((x - proj_x)**2 + (y - proj_y)**2)
        return distance <= tolerance / self.scale
        
    def point_in_circle(self, point, center, edge):
        """Check if a point is near a circle's circumference."""
        radius = math.sqrt((edge[0] - center[0])**2 + (edge[1] - center[1])**2)
        dist = math.sqrt((point[0] - center[0])**2 + (point[1] - center[1])**2)
        tolerance = 5.0 / self.scale
        return abs(dist - radius) <= tolerance
        
    def shape_intersects_rect(self, shape: Shape, rect: List[Tuple[float, float]]) -> bool:
        """Check if a shape intersects with the selection rectangle."""
        rect_x1, rect_y1 = min(rect[0][0], rect[1][0]), min(rect[0][1], rect[1][1])
        rect_x2, rect_y2 = max(rect[0][0], rect[1][0]), max(rect[0][1], rect[1][1])
        
        if shape.type == Tool.LINE:
            # Check if line endpoints are in rectangle
            for point in shape.points:
                if self.point_in_rect(point, rect):
                    return True
            # Check if line intersects rectangle edges
            x1, y1 = shape.points[0]
            x2, y2 = shape.points[1]
            rect_lines = [
                ((rect_x1, rect_y1), (rect_x2, rect_y1)),
                ((rect_x2, rect_y1), (rect_x2, rect_y2)),
                ((rect_x2, rect_y2), (rect_x1, rect_y2)),
                ((rect_x1, rect_y2), (rect_x1, rect_y1))
            ]
            for rect_line in rect_lines:
                if self.lines_intersect(shape.points[0], shape.points[1], rect_line[0], rect_line[1]):
                    return True
            return False
            
        elif shape.type == Tool.RECTANGLE:
            shape_x1, shape_y1 = min(shape.points[0][0], shape.points[1][0]), min(shape.points[0][1], shape.points[1][1])
            shape_x2, shape_y2 = max(shape.points[0][0], shape.points[1][0]), max(shape.points[0][1], shape.points[1][1])
            return not (shape_x2 < rect_x1 or shape_x1 > rect_x2 or
                       shape_y2 < rect_y1 or shape_y1 > rect_y2)
                       
        elif shape.type == Tool.CIRCLE:
            center = shape.points[0]
            edge = shape.points[1]
            radius = math.sqrt((edge[0] - center[0])**2 + (edge[1] - center[1])**2)
            circle_x, circle_y = center
            
            # Check if circle intersects or contains rectangle
            closest_x = max(rect_x1, min(circle_x, rect_x2))
            closest_y = max(rect_y1, min(circle_y, rect_y2))
            distance = math.sqrt((circle_x - closest_x)**2 + (circle_y - closest_y)**2)
            return distance <= radius
            
        elif shape.type == Tool.POLYGON:
            # Check if any polygon point is in rectangle
            for point in shape.points:
                if self.point_in_rect(point, rect):
                    return True
            # Check if any polygon edge intersects rectangle
            for i in range(len(shape.points)):
                p1 = shape.points[i]
                p2 = shape.points[(i + 1) % len(shape.points)]
                rect_lines = [
                    ((rect_x1, rect_y1), (rect_x2, rect_y1)),
                    ((rect_x2, rect_y1), (rect_x2, rect_y2)),
                    ((rect_x2, rect_y2), (rect_x1, rect_y2)),
                    ((rect_x1, rect_y2), (rect_x1, rect_y1))
                ]
                for rect_line in rect_lines:
                    if self.lines_intersect(p1, p2, rect_line[0], rect_line[1]):
                        return True
            return False
            
        return False
        
    def lines_intersect(self, p1, p2, p3, p4):
        """Check if two line segments intersect."""
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
        
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)
        
    def select_shapes_in_rect(self):
        """Select all shapes that intersect with the selection rectangle."""
        if not self.selection_rect:
            return
            
        for shape in self.shapes:
            if self.shape_intersects_rect(shape, self.selection_rect):
                if shape not in self.selected_shapes:
                    self.selected_shapes.append(shape)
                shape.selected = True
            elif not pygame.key.get_mods() & pygame.KMOD_SHIFT:
                if shape in self.selected_shapes:
                    self.selected_shapes.remove(shape)
                shape.selected = False
            
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        pos = self.screen_to_world(event.pos)
                        if self.snap_to_grid:
                            pos = self.snap_point(pos)
                            
                        if self.current_tool == Tool.SELECT:
                            self.selection_rect = [pos, pos]
                            if not pygame.key.get_mods() & pygame.KMOD_SHIFT:
                                self.selected_shapes.clear()
                        elif self.current_tool == Tool.POLYGON:
                            if not self.drawing:
                                self.drawing = True
                                self.polygon_points = [pos]
                            else:
                                self.polygon_points.append(pos)
                        else:
                            self.drawing = True
                            self.start_point = pos
                            self.current_point = pos
                            
                    elif event.button == 2:  # Middle click
                        self.panning = True
                        self.last_mouse_pos = event.pos
                        
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.current_tool == Tool.SELECT:
                            self.select_shapes_in_rect()
                            self.selection_rect = None
                        elif self.drawing and self.current_tool != Tool.POLYGON:
                            shape = Shape(
                                type=self.current_tool,
                                points=[self.start_point, self.current_point]
                            )
                            command = AddShapeCommand(self, shape)
                            self.execute_command(command)
                            self.drawing = False
                            
                    elif event.button == 2:
                        self.panning = False
                        
                elif event.type == pygame.MOUSEMOTION:
                    pos = self.screen_to_world(event.pos)
                    if self.snap_to_grid:
                        pos = self.snap_point(pos)
                        
                    if self.panning and self.last_mouse_pos:
                        dx = event.pos[0] - self.last_mouse_pos[0]
                        dy = event.pos[1] - self.last_mouse_pos[1]
                        self.pan_x += dx
                        self.pan_y += dy
                        self.last_mouse_pos = event.pos
                    elif self.drawing or self.selection_rect:
                        self.current_point = pos
                        if self.selection_rect:
                            self.selection_rect[1] = pos
                            
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_s:
                        self.current_tool = Tool.SELECT
                    elif event.key == pygame.K_l:
                        self.current_tool = Tool.LINE
                    elif event.key == pygame.K_r:
                        self.current_tool = Tool.RECTANGLE
                    elif event.key == pygame.K_o:
                        self.current_tool = Tool.CIRCLE
                    elif event.key == pygame.K_p:
                        self.current_tool = Tool.POLYGON
                    elif event.key == pygame.K_g:
                        self.show_grid = not self.show_grid
                    elif event.key == pygame.K_TAB:
                        self.snap_to_grid = not self.snap_to_grid
                    elif event.key == pygame.K_RETURN:
                        if self.current_tool == Tool.POLYGON:
                            if len(self.polygon_points) >= 3:
                                shape = Shape(
                                    type=Tool.POLYGON,
                                    points=self.polygon_points.copy()
                                )
                                command = AddShapeCommand(self, shape)
                                self.execute_command(command)
                            self.polygon_points.clear()
                            self.drawing = False
                    elif event.key == pygame.K_DELETE:
                        if self.selected_shapes:
                            command = DeleteShapeCommand(self, self.selected_shapes.copy())
                            self.execute_command(command)
                            self.selected_shapes.clear()
                    elif event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.undo()
                    elif event.key == pygame.K_y and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.redo()
                        
            # Update display
            self.screen.fill((255, 255, 255))
            self.draw_grid()
            
            for shape in self.shapes:
                self.draw_shape(shape)
                
            self.draw_preview()
            
            if self.selection_rect:
                self.draw_selection_rect()
                
            self.draw_status()
            
            pygame.display.flip()
            self.clock.tick(60)
            
        pygame.quit()
        
def main():
    app = CADApp()
    
    print("Controls:")
    print("  s: Select tool")
    print("  l: Line tool")
    print("  r: Rectangle tool")
    print("  o: Circle tool")
    print("  p: Polygon tool")
    print("  g: Toggle grid")
    print("  Tab: Toggle grid snap")
    print("  Enter: Complete polygon")
    print("  Delete: Delete selected shapes")
    print("  Ctrl+Z: Undo")
    print("  Ctrl+Y: Redo")
    print("  Middle mouse: Pan view")
    print("  Shift+Select: Add to selection")
    print("  Esc: Exit")
    
    app.run()

if __name__ == "__main__":
    main()
