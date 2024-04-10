import random
from enum import Enum
import time
import numpy as np
import pyasge

from game.Pathfinding.AStar import AStarPathing
from game.gamedata import GameData
from game.gamestates.gamestate import GameState
from game.gamestates.gamestate import GameStateID

class PowerUpType(Enum):
    EXTRA_LIFE = 'extra_life'
    SCORE_MULTIPLIER = 'score_multiplier'
    FREEZE = 'freeze'

class PowerUp:
    def __init__(self, powerup_type: PowerUpType):
        self.sprite = pyasge.Sprite()
        self.active = False
        self.type = powerup_type
        self.duration = 5
        self.collect_time = None

        texture_paths = {
            PowerUpType.EXTRA_LIFE: "data/textures/powerup_life.png",
            PowerUpType.SCORE_MULTIPLIER: "data/textures/powerup_multiplier.png",
            PowerUpType.FREEZE: "data/textures/powerup_freeze.png"
        }

        scale_values = {
            PowerUpType.EXTRA_LIFE: 0.1,
            PowerUpType.SCORE_MULTIPLIER: 0.05,
            PowerUpType.FREEZE: 0.01
        }

        self.sprite.loadTexture(texture_paths[self.type])
        self.sprite.scale = scale_values[self.type]

class LeaderboardEntry:
    def __init__(self, name, score):
        self.name = name
        self.score = score

class Coin:
    def __init__(self):
        self.sprite = pyasge.Sprite()
        self.collected = False
        self.sprite.loadTexture("data/textures/Coin.png")
        self.sprite.scale = 0.1

class Player:
    def __init__(self):
        self.sprite = pyasge.Sprite()
        self.tile_position = pyasge.Point2D(1, 1)
        self.navigation_path = []
        self.current_path_step = 0
        self.movement_speed = 3
        self.current_speed_tick = 0
        self.sprite.loadTexture("data/textures/survivor-idle_knife_0.png")
        self.sprite.scale = 0.3
        self.sprite.x = 100
        self.sprite.y = 100
        self.lives = 3
        self.score_multiplier_active = False
        self.score_multiplier_time = 0

class Enemy:
    def __init__(self):
        self.sprite = pyasge.Sprite()
        self.tile_position = pyasge.Point2D(1, 1)
        self.logic_state = 0
        self.navigation_path = []
        self.current_path_step = 0
        self.detection_range = 5
        self.movement_speed = 9
        self.current_speed_tick = 0
        self.frozen = False
        self.freeze_time = 0

class GamePlay(GameState):

    def __init__(self, data: GameData) -> None:

        super().__init__(data)

        map_mid = [
            self.data.game_map.width * self.data.game_map.tile_size[0] * 0.5,
            self.data.game_map.height * self.data.game_map.tile_size[1] * 0.5
        ]
        self.astar = AStarPathing(self.data)
        self.enemy = Enemy()
        self.init_enemies(2)
        self.player = Player()
        self.enemies = []
        self.coins = []
        self.player_score = 0
        self.init_coins(20)
        map_choice = random.choice(["./data/map/Maze.tmx", "./data/map/Maze2.tmx", "./data/map/Maze3.tmx"])
        self.level = 1
        self.setup_level()
        self.id = GameStateID.START_MENU
        self.data.renderer.setClearColour(pyasge.COLOURS.CORAL)
        self.init_ui()
        self.camera = pyasge.Camera(map_mid, self.data.game_res[0], self.data.game_res[1])
        self.camera.zoom = .8
        self.ui_label = pyasge.Text(self.data.renderer.getDefaultFont(), "UI Label", 10, 50)
        self.ui_label.z_order = 120
        self.leaderboard = []

    def init_powerups(self, count=3):
        self.powerups = []

        for _ in range(count):
            powerup_type = random.choice(list(PowerUpType))
            powerup = PowerUp(powerup_type)
            placed = False

            while not placed:
                tile_x = random.randint(0, self.data.game_map.width - 1)
                tile_y = random.randint(0, self.data.game_map.height - 1)

                if self.data.game_map.costs[tile_y][tile_x] == 0:
                    world_pos = self.data.game_map.world((tile_x, tile_y))
                    powerup.sprite.x, powerup.sprite.y = (world_pos.x - self.data.game_map.tile_size[0] / 2,
                                                          world_pos.y - self.data.game_map.tile_size[1] / 2)
                    placed = True

            self.powerups.append(powerup)

    def generate_unique_leaderboard_entry(self, base_name):
        count = 1
        new_name = base_name
        while any(entry.name == new_name for entry in self.leaderboard):
            count += 1
            new_name = f"{base_name}{count}"
        return new_name

    def generate_random_leaderboard_entries(self):
        possible_names = ["Alice", "Bob", "Charlie", "David", "Eve", "Steve", "Quinn", "Richard", "Wojciech"]
        for _ in range(5):
            name = random.choice(possible_names)
            unique_name = self.generate_unique_leaderboard_entry(name)
            score = random.randint(5, 20)
            self.leaderboard.append(LeaderboardEntry(unique_name, score))

    def bubble_sort_leaderboard(self):

        n = len(self.leaderboard)
        for i in range(n):
            for j in range(0, n - i - 1):
                if self.leaderboard[j].score < self.leaderboard[j + 1].score:
                    self.leaderboard[j], self.leaderboard[j + 1] = self.leaderboard[j + 1], self.leaderboard[j]
                elif self.leaderboard[j].score == self.leaderboard[j + 1].score:

                    if self.leaderboard[j].name > self.leaderboard[j + 1].name:
                        self.leaderboard[j], self.leaderboard[j + 1] = self.leaderboard[j + 1], self.leaderboard[j]

    def end_game(self):

        self.leaderboard.clear()

        self.leaderboard.append(LeaderboardEntry("YOU", self.player_score))

        self.generate_random_leaderboard_entries()

        self.bubble_sort_leaderboard()

    def init_enemies(self, count=3):
        self.enemies = []

        for _ in range(count):
            enemy = Enemy()
            enemy.sprite.loadTexture("data/textures/survivor-idle_shotgun_0.png")
            enemy.sprite.scale = .5
            enemy.sprite.width = enemy.sprite.texture.width * enemy.sprite.scale
            enemy.sprite.height = enemy.sprite.texture.height * enemy.sprite.scale

            max_x = self.data.game_map.width * self.data.game_map.tile_size[0] - enemy.sprite.width
            max_y = self.data.game_map.height * self.data.game_map.tile_size[1] - enemy.sprite.height

            start_pos = pyasge.Point2D(
                random.randint(0, int(max_x)),
                random.randint(0, int(max_y))
            )
            enemy.sprite.x, enemy.sprite.y = start_pos.x, start_pos.y

            self.enemies.append(enemy)

    def setup_level(self):
        self.new_level = True
        self.enemies.clear()
        self.coins.clear()
        self.init_powerups(5)
        self.player.lives = 3

        num_enemies = 1 + self.level
        num_coins = 10 + 10 * self.level

        self.init_enemies(num_enemies)
        self.init_coins(num_coins)

        self.reset_player()

    def reset_player(self):

        self.player.sprite.x = 100
        self.player.sprite.y = 100
        self.player.navigation_path.clear()
        self.player.current_path_step = 0
        self.player.current_speed_tick = 0

    def init_coins(self, count=20):
        for _ in range(count):
            coin = Coin()
            placed = False

            while not placed:

                tile_x = random.randint(0, self.data.game_map.width - 1)
                tile_y = random.randint(0, self.data.game_map.height - 1)

                if self.data.game_map.costs[tile_y][tile_x] == 0:
                    world_pos = self.data.game_map.world((tile_x, tile_y))

                    coin.sprite.x, coin.sprite.y = world_pos.x - self.data.game_map.tile_size[0] / 2, world_pos.y - \
                                                   self.data.game_map.tile_size[1] / 2
                    placed = True

            self.coins.append(coin)

    def init_ui(self):

        pass

    def click_handler(self, event: pyasge.ClickEvent) -> None:

        cursor_hotspot_offset_x = 0
        cursor_hotspot_offset_y = 0

        if event.button == pyasge.MOUSE.MOUSE_BTN1 and event.action == pyasge.MOUSE.BUTTON_PRESSED:
            corrected_click_x = event.x + cursor_hotspot_offset_x
            corrected_click_y = event.y + cursor_hotspot_offset_y

            target_tile_pos = self.data.game_map.tile(pyasge.Point2D(corrected_click_x, corrected_click_y))

            start_tile_pos = self.data.game_map.tile(pyasge.Point2D(self.player.sprite.x, self.player.sprite.y))

            start_tile = pyasge.Point2D(start_tile_pos[0], start_tile_pos[1])
            target_tile = pyasge.Point2D(target_tile_pos[0], target_tile_pos[1])

            self.astar.find_path(start_tile, target_tile)

            self.player.navigation_path = self.astar.path
            self.player.current_path_step = 0

    def move_handler(self, event: pyasge.MoveEvent) -> None:
        pass

    def key_handler(self, event: pyasge.KeyEvent) -> None:
        super().key_handler(event)

        if self.id == GameStateID.START_MENU and event.key == pyasge.KEYS.KEY_ENTER and event.action == pyasge.KEYS.KEY_PRESSED:
            self.id = GameStateID.GAMEPLAY
        elif self.id == GameStateID.WINNER_WINNER and event.key == pyasge.KEYS.KEY_SPACE and event.action == pyasge.KEYS.KEY_PRESSED:
            self.level += 1
            self.setup_level()
            self.id = GameStateID.GAMEPLAY
        elif self.id == GameStateID.GAME_OVER and event.key == pyasge.KEYS.KEY_SPACE and event.action == pyasge.KEYS.KEY_PRESSED:
            self.level = 1
            self.player_score = 0
            self.player.lives = 3
            self.setup_level()
            self.id = GameStateID.GAMEPLAY
        pass

    def fixed_update(self, game_time: pyasge.GameTime) -> None:

        pass

    def update(self, game_time: pyasge.GameTime) -> GameStateID:
        self.update_enemies()
        self.update_camera()
        self.update_inputs()
        self.update_player()
        self.update_powerups()
        if all(coin.collected for coin in self.coins):
            self.id = GameStateID.WINNER_WINNER
        elif self.player.lives <= 0 and self.id != GameStateID.GAME_OVER:
            self.end_game()
            self.id = GameStateID.GAME_OVER

        return self.id

    def check_collision(self, sprite1: pyasge.Sprite, sprite2: pyasge.Sprite) -> bool:

        x1_min = sprite1.x
        x1_max = sprite1.x + sprite1.width * sprite1.scale
        y1_min = sprite1.y
        y1_max = sprite1.y + sprite1.height * sprite1.scale

        x2_min = sprite2.x
        x2_max = sprite2.x + sprite2.width * sprite2.scale
        y2_min = sprite2.y
        y2_max = sprite2.y + sprite2.height * sprite2.scale

        overlap_x = x1_min < x2_max and x1_max > x2_min
        overlap_y = y1_min < y2_max and y1_max > y2_min

        return overlap_x and overlap_y

    def update_player(self):
        if len(self.player.navigation_path) > 0:
            self.player.current_speed_tick += 1
            if self.player.current_speed_tick >= self.player.movement_speed:
                if self.player.current_path_step < len(self.player.navigation_path):
                    next_pos = self.player.navigation_path[self.player.current_path_step]
                    self.player.sprite.x, self.player.sprite.y = next_pos.x * self.data.game_map.tile_size[
                        0], next_pos.y * self.data.game_map.tile_size[1]
                    self.player.current_path_step += 1
                    self.player.current_speed_tick = 0

                    for enemy in self.enemies:
                        if self.check_collision(self.player.sprite, enemy.sprite) and not enemy.frozen:
                            self.player.lives -= 1

                            self.reset_player()
                            if self.player.lives <= 0:
                                return GameStateID.GAME_OVER

                    for coin in self.coins:
                        if not coin.collected and self.check_collision(self.player.sprite, coin.sprite):
                            points = 1
                            if self.player.score_multiplier_active:
                                points *= 2
                            self.player_score += points
                            coin.collected = True
                for powerup in self.powerups:
                    if self.check_collision(self.player.sprite, powerup.sprite) and not powerup.active:
                        self.apply_powerup(powerup)
                        powerup.active = True

    def apply_powerup(self, powerup: PowerUp):

        current_time = time.time()

        if powerup.type == PowerUpType.EXTRA_LIFE:
            self.player.lives += 1

        elif powerup.type == PowerUpType.SCORE_MULTIPLIER:
            self.player.score_multiplier_active = True

            self.player.score_multiplier_time = current_time + powerup.duration

        elif powerup.type == PowerUpType.FREEZE:
            for enemy in self.enemies:
                enemy.frozen = True

                enemy.freeze_time = current_time + powerup.duration

    def update_powerups(self):
        current_time = time.time()

        if self.player.score_multiplier_active and current_time > self.player.score_multiplier_time:
            self.player.score_multiplier_active = False
            print("Score multiplier ended.")

        for enemy in self.enemies:
            if enemy.frozen and current_time > enemy.freeze_time:
                enemy.frozen = False
                print("Enemy unfrozen.")

    def update_enemies(self):
        current_time = time.time()

        for enemy in self.enemies:

            if enemy.frozen and current_time > enemy.freeze_time:
                enemy.frozen = False
                print("Enemy unfrozen.")

            if enemy.frozen:
                continue

            distance_to_player = pyasge.Point2D.distance(
                pyasge.Point2D(enemy.sprite.x, enemy.sprite.y),
                pyasge.Point2D(self.player.sprite.x, self.player.sprite.y)
            )

            if distance_to_player <= enemy.detection_range * self.data.game_map.tile_size[0]:
                enemy.logic_state = 0
            else:
                if random.randint(0, 100) > 98:
                    enemy.logic_state = 0

            if enemy.logic_state == 0:
                if len(enemy.navigation_path) <= 0 or enemy.current_path_step >= len(enemy.navigation_path):
                    target_pos = pyasge.Point2D(random.randint(1, self.data.game_map.width - 1),
                                                random.randint(1, self.data.game_map.height - 1))
                    start_pos = self.data.game_map.tile(pyasge.Point2D(enemy.sprite.x, enemy.sprite.y))
                    self.astar.find_path(pyasge.Point2D(start_pos[0], start_pos[1]), target_pos)
                    enemy.navigation_path = self.astar.path.copy()
                    enemy.current_path_step = 0

            elif enemy.logic_state == 1:
                if len(enemy.navigation_path) <= 0 or enemy.current_path_step >= len(enemy.navigation_path):
                    player_pos = self.data.game_map.tile(pyasge.Point2D(self.player.sprite.x, self.player.sprite.y))
                    start_pos = self.data.game_map.tile(pyasge.Point2D(enemy.sprite.x, enemy.sprite.y))
                    self.astar.find_path(pyasge.Point2D(start_pos[0], start_pos[1]),
                                         pyasge.Point2D(player_pos[0], player_pos[1]))
                    enemy.navigation_path = self.astar.path.copy()
                    enemy.current_path_step = 0

            if len(enemy.navigation_path) > 0:
                enemy.current_speed_tick += 1
                if enemy.current_speed_tick >= enemy.movement_speed:
                    if enemy.current_path_step < len(enemy.navigation_path):
                        move_to_position = enemy.navigation_path[enemy.current_path_step]
                        enemy.sprite.x, enemy.sprite.y = move_to_position.x * self.data.game_map.tile_size[
                            0], move_to_position.y * self.data.game_map.tile_size[1]
                        enemy.current_path_step += 1
                        enemy.current_speed_tick = 0

                    if enemy.current_path_step >= len(enemy.navigation_path):
                        enemy.navigation_path.clear()
                        enemy.current_path_step = 0

    def update_camera(self):

        if self.data.gamepad.connected:
            self.camera.translate(
                self.data.inputs.getGamePad().AXIS_LEFT_X * 10,
                self.data.inputs.getGamePad().AXIS_LEFT_Y * 10, 0.0)

    def update_inputs(self):

        if self.data.gamepad.connected:
            if self.data.gamepad.A and not self.data.prev_gamepad.A:

                pass
            elif self.data.gamepad.A and self.data.prev_gamepad.A:

                pass
            elif not self.data.gamepad.A and self.data.prev_gamepad.A:

                pass

    def render_powerups(self):
        for powerup in self.powerups:
            if not powerup.active:
                self.data.renderer.render(powerup.sprite)

    def render(self, game_time: pyasge.GameTime) -> None:
        self.data.renderer.setViewport(pyasge.Viewport(0, 0, self.data.game_res[0], self.data.game_res[1]))

        if self.id == GameStateID.GAMEPLAY:
            self.data.renderer.setProjectionMatrix(self.camera.view)
            self.data.shaders["example"].uniform("rgb").set([1.0, 1.0, 0])
            self.data.renderer.shader = self.data.shaders["example"]
            self.data.game_map.render(self.data.renderer, game_time)
            self.data.renderer.render(self.player.sprite)

            for enemy in self.enemies:
                self.data.renderer.render(enemy.sprite)
            for coin in self.coins:
                if not coin.collected:
                    self.data.renderer.render(coin.sprite)

            self.render_powerups()
            self.render_ui()

        elif self.id == GameStateID.WINNER_WINNER:
            self.render_winner_screen(game_time)
        elif self.id == GameStateID.GAME_OVER:
            self.render_loser_screen(game_time)
        elif self.id == GameStateID.START_MENU:
            self.render_main_menu(game_time)

    def render_loser_screen(self, game_time: pyasge.GameTime) -> None:

        loser_text = pyasge.Text(self.data.renderer.getDefaultFont(), f"You Lose! Your Score Was: {self.player_score}",
                                 400, 300)
        loser_text.colour = pyasge.COLOURS.RED
        self.data.renderer.render(loser_text)

        leaderboard_text = pyasge.Text(self.data.renderer.getDefaultFont(), "Leaderboard", 400, 350)
        leaderboard_text.colour = pyasge.COLOURS.WHITE
        self.data.renderer.render(leaderboard_text)

        y_offset = 400
        for idx, entry in enumerate(self.leaderboard[:5]):
            entry_text = pyasge.Text(self.data.renderer.getDefaultFont(), f"{idx + 1}. {entry.name}: {entry.score}",
                                     400, y_offset)
            entry_text.colour = pyasge.COLOURS.WHITE
            self.data.renderer.render(entry_text)
            y_offset += 50

        restart_text = pyasge.Text(self.data.renderer.getDefaultFont(), "Press SPACE to restart", 450, 650)
        restart_text.colour = pyasge.COLOURS.WHITE
        self.data.renderer.render(restart_text)

    def render_main_menu(self, game_time: pyasge.GameTime) -> None:
        main_menu_text2 = pyasge.Text(self.data.renderer.getDefaultFont(), "The Maze Raider", 550, 350)
        main_menu_text = pyasge.Text(self.data.renderer.getDefaultFont(), "Press Enter to Start", 450, 450)
        self.data.renderer.render(main_menu_text)
        self.data.renderer.render(main_menu_text2)
    def render_winner_screen(self, game_time: pyasge.GameTime) -> None:

        winner_text = pyasge.Text(self.data.renderer.getDefaultFont(), "You Win! Congratulations!", 400, 300)
        winner_text.colour = pyasge.COLOURS.GREENYELLOW
        self.data.renderer.render(winner_text)

        continue_text = pyasge.Text(self.data.renderer.getDefaultFont(), "Press SPACE to continue", 450, 350)
        continue_text.colour = pyasge.COLOURS.WHITE
        self.data.renderer.render(continue_text)

    def render_ui(self) -> None:

        self.ui_label.string = f"Score: {self.player_score}  Lives: {self.player.lives}  Level: {self.level}"
        self.ui_label.position = pyasge.Point2D(10, 10)
        self.data.renderer.render(self.ui_label)

    def to_world(self, pos: pyasge.Point2D) -> pyasge.Point2D:

        view = self.camera.view
        x = (view.max_x - view.min_x) / self.data.game_res[0] * pos.x
        y = (view.max_y - view.min_y) / self.data.game_res[1] * pos.y
        x = view.min_x + x
        y = view.min_y + y

        return pyasge.Point2D(x, y)