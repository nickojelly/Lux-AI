from io import TextIOBase
import math, sys
from os import path
from types import CellType

from numpy.core.numeric import full_like
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, GameMap
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import logging 
import numpy as np

with open('basicLog.log', 'w'):
    pass

logging.basicConfig(filename="basicLog.log", level = logging.INFO)

DIRECTIONS = Constants.DIRECTIONS
game_state = None
build_location = None
night_flag = False
logging_str = []
clusterflag = True
resource_clusters = []
city_tiles = []
opp_city_tiles = []

def log_function(log_entry):
    global logging_str
    logging_str.append(log_entry)
    logging.info(log_entry)
    #logging.info(f"{logging_str=}")
    

def get_resource_tiles(game_state, width, height):
    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
    return resource_tiles

def get_closest_resource(unit, resource_tiles, player):
    global clusterflag
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
    if clusterflag:
        get_rescoure_cluster(closest_resource_tile, [])            
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
    log_function(f"Unit pos list {unit_pos_list}")
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            dist = city_tile.pos.distance_to(unit.pos)
            if (dist < closest_dist) and (city_tile.pos not in unit_pos_list):
                closest_dist = dist
                closest_city_tile = city_tile
    return closest_city_tile


def get_burn_rate(player):
    burn_rate = 0
    for key,city in player.cities:
        burn_rate = burn_rate + city.get_light_upkeep()
    return burn_rate

def get_simple_path(unit, dest):
    global game_state
    (dx, dy) = (dest.pos.x-unit.pos.x, dest.pos.y-unit.pos.y)
    sign = lambda a: (a>0) - (a<0)
    log_function(f"unit pos = {unit.pos.x, unit.pos.y}, dx = {dx}, dy = {dy}")
    cell_x_dir = game_state.map.get_cell(unit.pos.x+sign(dx), unit.pos.y)
    cell_y_dir = game_state.map.get_cell(unit.pos.x, unit.pos.y+sign(dy))
    if (not dx) or cell_x_dir.citytile:
        log_function(f"moving to {[cell_y_dir.pos.x,cell_y_dir.pos.y]}")
        return cell_y_dir
    elif dx:
        log_function(f"moving to {[cell_x_dir.pos.x,cell_x_dir.pos.y-sign(dy)]}")
        return cell_x_dir



def get_better_path(unit, dest):
    global game_state
    (dx, dy) = (dest.pos.x-unit.pos.x, dest.pos.y-unit.pos.y)
    better_path = None
    path_list = [[game_state.map.get_cell_by_pos(unit.pos)]]
    visited = []
    log_function(f"---- get_better_path ----\nunit pos = {(unit.pos.x,unit.pos.y)} to {dest.pos.x,dest.pos.y}")
    while not better_path:
        full_new_path_list = []

        for p in path_list:
            new_path_list = []

            curr_path_cor = []
            for n in p:
                #log_function(f"n pos = {n.pos.x, n.pos.y}")
                curr_path_cor.append((n.pos.x, n.pos.y))
            #log_function(f"{curr_path_cor=}")
            current_cell = p[-1]
            #log_function(f" current cell = {current_cell.pos.x,current_cell.pos.y}")
            adj_cells = get_build_grid(current_cell,1)

            for i in adj_cells:
                #log_function(f"i={i.pos.x,i.pos.y}")
                try:
                    check_cell = i
                    #log_function(f"check cell = {check_cell.pos.x, check_cell.pos.y}")
                    if check_cell.pos.equals(dest.pos):
                        better_path = p + [check_cell]
                        log_function(f"***** best path found ***** {better_path=}")
                        break
                    elif check_cell.citytile or check_cell in visited:
                        continue
                    else:
                        check_path = p
                        #log_function(f"1{check_path[0].pos.x,check_path[0].pos.y}")
                        check_path= p + [check_cell]
                        #log_function(f"2{check_path=}")
                        new_path_list.append(check_path)
                        visited.append(check_cell)
                except Exception as e:
                    log_function(f"Better path ref out of index {str(e)}")
            for j in new_path_list:
                full_new_path_list.append(j)
            
        path_list = full_new_path_list
        
        #log_function("end of it\n\n")
    log_function(f"Best path from {(unit.pos.x,unit.pos.y)} to {dest.pos.x,dest.pos.y} is:")
    for i in better_path:
        log_function(f" ({i.pos.x,i.pos.y})")
    if len(better_path) >= 2:
        log_function(f"next pos ({better_path[1].pos.x,better_path[1].pos.y})")
        return better_path[1]
    else:
        log_function(f"next pos ({better_path[0].pos.x,better_path[0].pos.y})")
        return better_path[0]



def night_move(player,unit):
    global game_state
    close_home = get_closest_city_tile(player,unit)
    
    if not close_home:
        log_function(f"No Home available for {unit}")
        return unit.move("C")
    else:
        log_function(f"Closest home for unit {unit} is {close_home.pos}")
        return unit.move(unit.pos.direction_to(close_home.pos))
    

def build_city_action(game_state, player, unit):
    global build_location
    global resource_clusters
    global opp_city_tiles
    empty_near = get_closest_city_tile(player,unit)
    num_cities = len([citytile for city in list(player.cities.values()) for citytile in city.citytiles])
    log_function(f"{len(player.cities)=}")
    build_dist = 2
    cluster_loc = None
    if resource_clusters:
        for i in [x[0] for x in resource_clusters]:
            if i.resource==Constants.RESOURCE_TYPES.WOOD:
                cluster_loc=i

    if build_location:
        log_function(f"build loc =  {build_location.pos.x, build_location.pos.y, build_location.citytile=}, ")
        log_function(f"{build_location,opp_city_tiles=}")
        if build_location.pos in [x.pos for x in opp_city_tiles]:
            log_function(f"Build location {build_location.pos.x, build_location.pos.y} now has a city tile")
            build_location = None   
        if unit.pos.distance_to(build_location.pos)>3:
            log_function(f"To FAR\n\n new build location {unit.pos.x,unit.pos.y=}")
            empty_near = game_state.map.get_cell_by_pos(unit.pos)
            build_location = None

    while build_location==None:
        if num_cities > 3 and cluster_loc:
            log_function(f"Expaning to largest cluster on {cluster_loc.pos.x,cluster_loc.pos.y}\n\n----------")
            empty_near = cluster_loc
        try:
            log_function(f"Nearest City is {[empty_near.pos.x, empty_near.pos.y]}")
        except Exception as e:
            return DIRECTIONS.EAST
        possible_build_cells = get_build_grid(empty_near, build_dist)
        build_location = get_best_build_cell(possible_build_cells, unit)
        if not build_location:
            log_function(f"No Possible build location, expanding search")
            build_dist += 1
            continue

    if (build_location) and unit.pos == build_location.pos:
        #log_function(f"{game_state.turn} build: At Location Building City")
        build_location=None
        return unit.build_city()
    elif (build_location):
        #log_function(f"{game_state.turn} Moving to  Build location = {build_location.pos}")
        #move_cell = get_simple_path(unit, build_location)
        move_cell = get_better_path(unit, build_location)
        move_dir = unit.pos.direction_to(move_cell.pos)


        #log_function(f"build: Moving in Dir {[move_dir]}")
        return unit.move(move_dir)

def resource_sum(unit):
    return unit.cargo.wood+unit.cargo.coal+unit.cargo.uranium

def get_cell_build_value(game_state, centre_cell):
    close_c_list = get_build_grid(centre_cell, 1)
    cell_build_val = 0
    for c in close_c_list:
            if c.has_resource():
                cell_build_val += 1
    return cell_build_val

def get_build_grid(cell, dist):
    global game_state
    close_c_list = []
    cell_build_val = 0
    for r in game_state.map.map:
        for c in r:
            if cell.pos.distance_to(c.pos)<=dist and cell.pos.distance_to(c.pos):
                close_c_list.append(c)
    return close_c_list

def get_best_build_cell(cells,unit):
    global game_state
    best_loc = None
    best_loc_val = -1

    for c in cells:
        c_val = 0
        if not c.citytile and not c.has_resource():
            neighbours = get_build_grid(c, 1)
            close_cells = get_build_grid(c,3)
            c_val = c_val - unit.pos.distance_to(c.pos)
            for n in neighbours:
                if n.citytile:
                    c_val += 5
                if n.has_resource():
                    c_val += 2
            for cc in close_cells:
                if cc.has_resource():
                    c_val += 1
        if c_val > best_loc_val:
            best_loc = c
            best_loc_val = c_val
    log_function(f"best location is {best_loc.pos=} with {best_loc_val=}")
    return best_loc

def city_stats(player):
    city_dict = player.cities
    city_stats_np = np.array()
    for id,city in city_dict:
        city_stats = []
        city_stats[0] = id
        city_stats[1] = city.fuel
        city_stats_np = np.insert(city_stats_np,0,city_stats)

def get_rescoure_cluster(cell, cluster):
    global game_state
    global clusterflag
    adjacent = get_build_grid(cell, 1)
    for c in adjacent:
        if c in cluster:
            continue
        elif c.has_resource():
            cluster.append(c)
            cluster = get_rescoure_cluster(c, cluster)
    return cluster
        


def get_resource_grid(game_state, width, height):
    resource_tiles = get_resource_tiles(game_state, width, height)
    resource_packets = []
    for tile in resource_tiles:
        if tile not in [item for sublist in resource_packets for item in sublist]:
            resource_packets.append(get_rescoure_cluster(tile, []))
    if resource_packets:
        return resource_packets
    



def agent(observation, configuration):
    global game_state
    global build_location
    global night_flag
    global logging_str
    global clusterflag
    global resource_clusters
    global opp_city_tiles
    global city_tiles
    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []
    #step = observation["step"]
    log_function(f"----- turn = {observation['step']} ----- ")


    ### AI Code goes down here! ### 
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height
    cities = list(player.cities.values())
    log_function(f"{cities=}")
    city_tiles = []

    if len(player.cities) > 3 and len(player.cities) < 6:
        clusterflag = False 

    #one liner to get list of city tiles
    city_tiles = [citytile.pos for city in list(player.cities.values()) for citytile in city.citytiles]
    opp_city_tiles = [citytile for city in list(opponent.cities.values()) for citytile in city.citytiles]

    if len(city_tiles) > 3 and len(city_tiles) < 6:
        clusterflag = False 

    ## Getting Resource Grid
    #
    if clusterflag:
        log_function("Getting Resource Grid")
        resource_clusters = get_resource_grid(game_state, width, height)
        resource_clusters.sort(key=len, reverse=True)
        resource_clusters = [x for x in resource_clusters if x]
        clusterflag = False
        log_function("Resource Clusters *******\n")
        for cluster in resource_clusters:
            coords = [(c.pos.x, c.pos.y) for c in cluster]
            log_function(f"{coords=}")


    if observation["step"]%40>=29:
        night_flag = True
    else:
        night_flag = False

    #for city in cities:
    #    for c_tile in city.citytiles:
    #        city_tiles.append(c_tile.pos)

    workers = []
    for worker in player.units:
        if worker.is_worker:
            workers.append(worker)

    resource_tiles = get_resource_tiles(game_state,width,height)

    build_city_flag = False
    builder_unit = None
    if (len(city_tiles) <= len(workers)) and len(workers):
        build_city_flag = True
        builder_unit = player.units[0]

    build_worker_flag = False
    if len(city_tiles)>len(workers):
        build_worker_flag = True

    move_pos_list = []

    # we iterate over all our units and do something with them
    for unit in player.units:
        if night_flag:
            log_function("Its night")
            if unit.pos in city_tiles:
                continue
            elif builder_unit:
                if builder_unit == unit.id:
                    log_function("Worker be working")
            else:
                actions.append(night_move(player,unit))
        elif unit.is_worker() and unit.can_act():
            closest_resource_tile = get_closest_resource(unit, resource_tiles, player) 
            closest_city_tile = get_closest_city_tile(player,unit)

            if build_city_flag and (resource_sum(unit) == 100) and unit.id == builder_unit.id:
                log_function(f"Attempt City Build")
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
                    log_function("Building Worker")
                    actions.append(ct.build_worker())
                elif player.research_points<70:
                    actions.append(ct.research())
    # you can add debug annotations using the functions in the annotate object
    #for s in logging_str:
    #    actions.append(annotate.sidetext(f"{s}"))
    logging_str = []
    #logging.info("Move this turn:\n")
    #for act in actions:
    #    logging.info(f"{act}")
    return actions
