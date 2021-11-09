import math, sys
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, GameMap
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import logging 

with open('basicLog.log', 'w'):
    pass

logging.basicConfig(filename="basicLog.log", level = logging.INFO)

DIRECTIONS = Constants.DIRECTIONS
game_state = None
build_location = None
night_flag = False

def get_resource_tiles(game_state, width, height):
    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
    return resource_tiles

def get_closest_resource(unit, resource_tiles, player):
    closest_dist = math.inf
    closest_resource_tile = None

    unit_pos_list = []
    for u in player.units:
        unit_pos_list.append(u.pos)

    if unit.get_cargo_space_left() > 0:
        # if the unit is a worker and we have space in cargo, lets find the nearest resource tile and try to mine it
        for resource_tile in resource_tiles:
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
            dist = resource_tile.pos.distance_to(unit.pos)
            if dist < closest_dist and resource_tile.pos not in unit_pos_list:
                closest_dist = dist
                closest_resource_tile = resource_tile
                
    return closest_resource_tile

def get_closest_city_tile(player,unit):
    closest_dist = math.inf
    closest_city_tile = None
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            dist = city_tile.pos.distance_to(unit.pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_city_tile = city_tile
    return closest_city_tile

def get_closest_empty_city_tile(player,unit):
    closest_dist = math.inf
    closest_city_tile = None

    unit_pos_list = []
    for u in player.units:
        unit_pos_list.append(u.pos)
    logging.info(f"Unit pos list {unit_pos_list}")
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            dist = city_tile.pos.distance_to(unit.pos)
            if (dist < closest_dist) and (city_tile.pos not in unit_pos_list):
                closest_dist = dist
                closest_city_tile = city_tile
    return closest_city_tile

def get_best_build_loc(game_state,closest_city_tile):
    p = 1

def get_burn_rate(player):
    burn_rate = 0
    for key,city in player.cities:
        burn_rate = burn_rate + city.get_light_upkeep()
    return burn_rate

def get_simple_path(unit, dest):
    global game_state
    (dx, dy) = (dest.pos.x-unit.pos.x, dest.pos.y-unit.pos.y)
    sign = lambda a: (a>0) - (a<0)
    logging.info(f"unit pos = {unit.pos.x, unit.pos.y}, dx = {dx}, dy = {dy}")
    cell_x_dir = game_state.map.get_cell(unit.pos.x+sign(dx), unit.pos.y)
    cell_y_dir = game_state.map.get_cell(unit.pos.x, unit.pos.y+sign(dy))
    if (not dx) or cell_x_dir.citytile:
        logging.info(f"moving to {[cell_y_dir.pos.x,cell_y_dir.pos.y]}")
        return cell_y_dir
    elif dx:
        logging.info(f"moving to {[cell_x_dir.pos.x,cell_x_dir.pos.y-sign(dy)]}")
        return cell_x_dir



def night_move(player,unit):
    global game_state
    close_home = get_closest_city_tile(player,unit)
    
    if not close_home:
        logging.info(f"No Home available for {unit}")
        return unit.move("C")
    else:
        logging.info(f"Closest home for unit {unit} is {close_home.pos}")
        return unit.move(unit.pos.direction_to(close_home.pos))
    

def get_build_location(game_state, position):    
    pass

def build_city_action(game_state, player, unit):
    global build_location
    empty_near = get_closest_city_tile(player,unit)
    while build_location==None:
        logging.info(f"Nearest City is {[empty_near.pos.x, empty_near.pos.y]}")
        dirs = [(1,0),(-1,0),(0,1),(0,-1)]
        for d in dirs:
            try:
                check_tile = game_state.map.get_cell(empty_near.pos.x+d[0],empty_near.pos.y+d[1])
                logging.info(f": Checking {[check_tile.pos.x,check_tile.pos.y]}")

                if check_tile.resource == None and check_tile.road == 0 and check_tile.citytile == None:
                    build_location = check_tile
                    logging.info(f"{game_state.turn} Found {[check_tile.pos.x,check_tile.pos.y]}")
                    break
            except Exception as e:
                logging.warning(f"{game_state.turn} broke")
        if not build_location:
            empty_near = game_state.map.get_cell(empty_near.pos.x+d[0]*2,empty_near.pos.y+d[1]*2)

    if (build_location) and unit.pos == build_location.pos:
        logging.info(f"{game_state.turn} build: At Location Building City")
        build_location=None
        return unit.build_city()
    elif (build_location):
        logging.info(f"{game_state.turn} Moving to  Build location = {build_location}")
        move_cell = get_simple_path(unit, build_location)
        move_dir = unit.pos.direction_to(move_cell.pos)


        logging.info(f"build: Moving in Dir {[move_dir]}")
        return unit.move(move_dir)

def resource_sum(unit):
    return unit.cargo.wood+unit.cargo.coal+unit.cargo.uranium

def agent(observation, configuration):
    global game_state
    global build_location
    global night_flag
    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []
    step = observation["step"]
    logging.info(f"----- turn = {observation['step']} ----- \n")

    ### AI Code goes down here! ### 
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height
    cities = player.cities.values()
    city_tiles = []

    if observation["step"]%40>30:
        night_flag = True
    else:
        night_flag = False

    for city in cities:
        for c_tile in city.citytiles:
            city_tiles.append(c_tile.pos)

    workers = []
    for worker in player.units:
        if worker.is_worker:
            workers.append(worker)

    resource_tiles = get_resource_tiles(game_state,width,height)
    
    #logging.info(f"{cities}")
    #logging.info(f"{city_tiles}")

    build_city_flag = False
    if len(city_tiles) <= len(workers):
        build_city_flag = True
        builder_unit = player.units[0]

    build_worker_flag = False
    if len(city_tiles)>len(workers):
        build_worker_flag = True

    move_pos_list = []

    # we iterate over all our units and do something with them
    for unit in player.units:
        if night_flag:
            logging.info("Its night")
            if unit.pos in city_tiles:
                continue
            else:
                actions.append(night_move(player,unit))
        elif unit.is_worker() and unit.can_act():
            closest_resource_tile = get_closest_resource(unit, resource_tiles, player) 
            closest_city_tile = get_closest_city_tile(player,unit)
            new_city_loc = get_best_build_loc(game_state, closest_city_tile)

            if build_city_flag and (resource_sum(unit) == 100) and unit == builder_unit:
                logging.info(f"Attempt City Build")
                actions.append(build_city_action(game_state,player,unit))
            elif closest_resource_tile is not None:
                if closest_resource_tile not in move_pos_list:
                    move_pos_list.append(closest_resource_tile)
                    actions.append(unit.move(unit.pos.direction_to(closest_resource_tile.pos)))
                else:
                    continue

            else:
            # if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                if len(player.cities) > 0:
                    
                    if closest_city_tile is not None:
                        move_dir = unit.pos.direction_to(closest_city_tile.pos)
                        actions.append(unit.move(move_dir))

    for k,c in player.cities.items():
        for ct in c.citytiles:
            if ct.can_act() and not night_flag:
                if build_worker_flag:
                    logging.info("Building Worker")
                    actions.append(ct.build_worker())
                else:
                    actions.append(ct.research())
    # you can add debug annotations using the functions in the annotate object
    actions.append(annotate.sidetext("helloworld"))
    
    return actions
