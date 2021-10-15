from io import TextIOBase
import math, sys
from os import path
from types import CellType

from numpy.core.numeric import full_like
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, GameMap
from lux.game_objects import Unit
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import logging 
import numpy as np
import random
with open('basicLog.log', 'w'):
    pass

logging.basicConfig(filename="basicLog.log", level = logging.INFO)

game_state = None

class gs:
    build_location = None
    night_flag=False
    logging_str=[]
    clusterflag=True
    expandflag=False
    resource_clusters=[]
    cluster_city = {}
    city_tiles=[]
    opp_city_tiles=[]
    cell_highlight = []
    notes = []
    num_explorers = 0
    def __init__(self) -> None:
        pass

#Actually dont want to initialize, as 
class WorkerStatus(Unit):
    destination = Cell
    path = [Cell]
    builder = False
    build_new_cluster = None
    cluster_builder = False
    test_str = "TEST_STR_PRINT"
    def __init__(self, worker_obj) -> None:
        self.worker = worker_obj
        self.home_city = game_state.map.get_cell_by_pos(self.worker.pos)

class CityStatus:
    workers = []
    builders = []
    expand_city = True
    def __init__(self,city_obj) -> None:
        self.obj = city_obj
        self.tiles = self.obj.tiles

class ResourceCluster:
    def has_city(self):
        for c in self.cluster_list:
            for neighbour in get_build_grid(c, 1):
                if neighbour.citytile:
                    log_function(f"{self.first_cell, neighbour.citytile}")
                    return True
        return False
                    
    def __init__(self, cluster_list) -> None:
        self.first_cell = cluster_list[0]
        self.size = len(cluster_list)
        self.r_type = cluster_list[0].resource.type
        self.cluster_list = cluster_list
        self.city = self.has_city()

class Clusters:
    def __init__(self):
        self.clusters = {}


    def update_clusters(self,resource_clusters):
        for cluster in resource_clusters:
            first_cell = cluster[0]
            self.clusters[first_cell] = ResourceCluster(cluster)

    

resource_clusters = Clusters()

DIRECTIONS = Constants.DIRECTIONS

status = gs()

worker_dict = {}

def log_function(log_entry):
    global status
    status.logging_str.append(log_entry)
    logging.info(log_entry)
    #logging.info(f"{logging_str=}")
    
def annotatefunc(annotation):
    global status
    status.notes.append(annotation)

def get_resource_tiles(game_state, width, height):
    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
    return resource_tiles

def get_closest_resource(unit, resource_tiles, player):
    global status
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
    if status.clusterflag:
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
                curr_path_cor.append((n.pos.x, n.pos.y))
            current_cell = p[-1]
            #log_function(f" current cell = {current_cell.pos.x,current_cell.pos.y}")
            adj_cells = get_build_grid(current_cell,1)
            for i in adj_cells:
                try:
                    check_cell = i
                    if check_cell.pos.equals(dest.pos):
                        better_path = p + [check_cell]
                        #log_function(f"***** best path found ***** {better_path=}")
                        break
                    elif check_cell.citytile or check_cell in visited:
                        continue
                    else:
                        check_path = p
                        check_path= p + [check_cell]
                        new_path_list.append(check_path)
                        visited.append(check_cell)
                except Exception as e:
                    log_function(f"Better path ref out of index {str(e)}")
            for j in new_path_list:
                full_new_path_list.append(j)
            
        path_list = full_new_path_list
        
    #log_function(f"Best path from {(unit.pos.x,unit.pos.y)} to {dest.pos.x,dest.pos.y} is:")
    for i in better_path:
        #log_function(f" ({i.pos.x,i.pos.y})")
        continue
    if len(better_path) >= 2:
        #log_function(f"next pos ({better_path[1].pos.x,better_path[1].pos.y})")
        return better_path[1]
    else:
        #log_function(f"next pos ({better_path[0].pos.x,better_path[0].pos.y})")
        return better_path[0]

def night_move(player,unit):
    global game_state
    close_home = get_closest_city_tile(player,unit)
    if not close_home:
        return unit.move("C")
    else:
        return unit.move(unit.pos.direction_to(close_home.pos))
    
def build_city_action(game_state, player, unit):
    global status
    global worker_dict
    empty_near = get_closest_city_tile(player,unit)
    num_cities = len([city.citytile for city in list(player.cities.values()) for city.citytile in city.citytiles])
    #log_function(f"{player.cities=}")
    build_dist = 2
    cluster_loc = None
    if num_cities==0:
        empty_near = game_state.map.get_cell_by_pos(unit.pos)

    if status.resource_clusters:
        for i in [x[0] for x in status.resource_clusters]:
            if i.resource==Constants.RESOURCE_TYPES.WOOD:
                cluster_loc=i

    if status.build_location:
        log_function(f"build loc =  {status.build_location.pos.x, status.build_location.pos.y, status.build_location.citytile=}, ")
        log_function(f"{status.build_location,status.opp_city_tiles=}")
        if status.build_location.pos in [x.pos for x in status.opp_city_tiles]:
            log_function(f"Build location {status.build_location.pos.x, status.build_location.pos.y} now has a city tile")
            status.build_location = None   
        if unit.pos.distance_to(status.build_location.pos)>200:
            log_function(f"To FAR\n\n new build location {unit.pos.x,unit.pos.y=}")
            empty_near = game_state.map.get_cell_by_pos(unit.pos)
            status.build_location = None

    while status.build_location==None:
        if num_cities > 3 and cluster_loc:
            log_function(f"Expaning to largest cluster on {cluster_loc.pos.x,cluster_loc.pos.y}\n\n----------")
            empty_near = cluster_loc
        try:
            log_function(f"Nearest City is {[empty_near.pos.x, empty_near.pos.y]}")
        except Exception as e:
            return DIRECTIONS.EAST
        possible_build_cells = get_build_grid(empty_near, build_dist)
        status.build_location = get_best_build_cell(possible_build_cells, unit)
        if not status.build_location:
            log_function(f"No Possible build location, expanding search")
            build_dist += 1
            continue

    if (status.build_location) and unit.pos == status.build_location.pos:
        #log_function(f"{game_state.turn} build: At Location Building City")
        status.build_location=None
        return unit.build_city()
    elif (status.build_location):
        #log_function(f"{game_state.turn} Moving to  Build location = {status.build_location.pos}")
        #move_cell = get_simple_path(unit, status.build_location)
        move_cell = get_better_path(unit, status.build_location)
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
    global status
    global worker_dict
    best_loc = None
    best_loc_val = -1
    for c in cells:
        c_val = 0
        if not c.citytile and not c.has_resource():
            neighbours = get_build_grid(c, 1)
            close_cells = get_build_grid(c,3)
            log_function(f"{worker_dict[unit.id],unit.id, worker_dict[unit.id].cluster_builder=}")
            if not worker_dict[unit.id].cluster_builder:
                c_val = c_val - unit.pos.distance_to(c.pos)
            for n in neighbours:
                if n.citytile:
                    c_val += 5
                if n.has_resource():
                    c_val += 2
            for cc in close_cells:
                if cc.has_resource():
                    c_val += 1
        log_function(f"{c.pos.x,c.pos.y, c_val=}")
        if c_val > best_loc_val:
            best_loc = c
            best_loc_val = c_val
    log_function(f"best location is {best_loc.pos.x,best_loc.pos.y=} with {best_loc_val=}")
    status.cell_highlight.append(best_loc)
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
    
def move_manager(player, move_list):
    unit_dict = {}
    new_pos_list = []
    adjusted_move_list = []
    for unit in player.units:
        unit_dict[unit.id] = unit.pos
    for move in move_list:
        if move[0] == 'd':
            adjusted_move_list.append(move)
        act = move.split()[0]
        if act == "m":
            u_id = move.split()[1]
            dir = move.split()[2]
            new_pos = unit_dict[u_id].translate(dir,1)
            if (new_pos in list(unit_dict.values())) and new_pos != unit_dict[u_id]:
                logging.info(f"{move=} will result in an error")
                pass
                random_move = random.choice([DIRECTIONS.EAST,DIRECTIONS.WEST,DIRECTIONS.NORTH,DIRECTIONS.SOUTH,DIRECTIONS.CENTER])
                new_pos = unit_dict[u_id].translate(random_move,1)  
                adjusted_move_list.append(f'm {u_id} {random_move}')
                pass
            else:
                unit_dict[u_id] = new_pos
                new_pos_list.append(new_pos)
                adjusted_move_list.append(move)
        else: adjusted_move_list.append(move)
    return adjusted_move_list

def get_builder_workers(player):
    global worker_dict
    global status
    global game_state
    closest_dist = math.inf
    build_cluster = None
    closest_unit = None
    #log_function(f"{status.resource_clusters=}")
    for cluster in status.resource_clusters:
        log_function(f"Cluster location {cluster[0].pos.x,cluster[0].pos.y}, {cluster[0].resource}")
        if (cluster[0] not in status.cluster_city) and cluster[0].resource.type==Constants.RESOURCE_TYPES.WOOD:
            build_cluster = cluster[0]
            log_function(f"{build_cluster=}")
            break
            if unit.pos.distance_to(cluster[0].pos)>20:
                log_function(f"Distance to far")
            else:
                build_cluster = cluster[0]
                break
    if build_cluster:
        for unit in player.units:
            if not worker_dict[unit.id].build_new_cluster:
                dist = build_cluster.pos.distance_to(unit.pos)
                if dist < closest_dist and unit.get_cargo_space_left() == 0:
                    log_function(f"Best explorer found {unit.id=},\n {build_cluster.pos.x,build_cluster.pos.y=}")
                    closest_dist = dist
                    closest_unit = unit
                    break
        if closest_unit:
            possible_builds = get_build_grid(build_cluster, 3)
            worker_dict[closest_unit.id].cluster_builder = True
            log_function(f"here1 = {worker_dict[closest_unit.id],worker_dict[closest_unit.id].build_new_cluster,worker_dict[closest_unit.id].cluster_builder}")
            build_location = get_best_build_cell(possible_builds,closest_unit)
            log_function(f"explorer b {build_location.pos.x,build_location.pos.y=}")
            worker_dict[closest_unit.id].build_new_cluster = build_location
            
            
            log_function(f"here2 = {worker_dict[closest_unit.id],worker_dict[closest_unit.id].build_new_cluster,worker_dict[closest_unit.id].cluster_builder}")
            status.num_explorers += 1



def agent(observation, configuration):
    global game_state
    global status
    global worker_dict
    global resource_clusters
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
    if observation["step"]%2:
        log_function(f"----- turn = {observation['step'], game_state=} ----- ")

    #if observation["step"] >5:
    #    return None
    ### AI Code goes down here! ### 

    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height
    status.city_tiles = []
    resource_tiles = get_resource_tiles(game_state,width,height)

    #one liner to get list of city tiles
    status.city_tiles = [citytile.pos for city in list(player.cities.values()) for citytile in city.citytiles]
    status.opp_city_tiles = [citytile for city in list(opponent.cities.values()) for citytile in city.citytiles]

    if len(status.city_tiles) > 3 and len(status.city_tiles) < 6:
        status.clusterflag = False 

    ## Getting Resource Grid
    #
    if status.clusterflag:
        log_function("Getting Resource Grid")
        status.resource_clusters = get_resource_grid(game_state, width, height)
        status.resource_clusters.sort(key=len, reverse=True)
        status.resource_clusters = [x for x in status.resource_clusters if x]
        status.clusterflag = False
        log_function("Resource Clusters *******\n")
        for cluster in status.resource_clusters:
            coords = [(c.pos.x, c.pos.y) for c in cluster]
            log_function(f"{coords=}")
        resource_clusters.update_clusters(status.resource_clusters)
    

    if observation["step"]%40>=30:
        status.night_flag = True
    else:
        status.night_flag = False

    #for city in cities:
    #    for c_tile in city.citytiles:
    #        status.city_tiles.append(c_tile.pos)

    #Generates a WorkerStatus class for a worker
    workers = []
    for worker in player.units:
        if worker.is_worker:
            workers.append(worker)
            if worker.id not in worker_dict.keys():
                log_function(f"New worker Created {worker.id=}")
                new_worker = WorkerStatus(worker) 
                worker_dict[worker.id] = new_worker
                log_function(f"{new_worker.home_city.pos.x,new_worker.home_city.pos.y=}")

    #Gives worker a home city
    for worker in worker_dict.values():
        if not worker.home_city:
            worker.home_city = get_closest_city_tile(player,worker)

    #log_function(f"{worker_dict.values()=}")
    pop_list = []
    for key in worker_dict.keys():
        if key not in [worker.id for worker in workers]:
            #worker_dict.pop(key)
            log_function(f"Looks like {key=} has died")
            pop_list.append(key)
    for p in pop_list:
        worker_dict.pop(p)

    num_clusters = 2
    max_num_explorers = 2
    if len(status.city_tiles) > 3:
        for i in range(len(worker_dict)):
            if status.num_explorers < max_num_explorers:
                log_function(f"{status.num_explorers=}")
                get_builder_workers(player)




    build_city_flag = False
    builder_unit = []
    if (len(status.city_tiles) <= len(workers)) and len(workers):
        build_city_flag = True
        builder_unit.append(player.units[0].id)
        if len(player.cities.values())>=2:
            builder_unit.append(player.units[1].id)

    build_worker_flag = False
    if len(status.city_tiles)>len(workers):
        build_worker_flag = True

    move_pos_list = []

    # we iterate over all our units and do something with them
    for unit in player.units:
        if status.night_flag:
            log_function("Its night")
            if unit.pos in status.city_tiles:
                log_function(f"{unit.id} is home")
                continue
            elif builder_unit:
                if unit.id in builder_unit:
                    log_function("Worker be working")
            else:
                log_function("Moving Home")
                actions.append(night_move(player,unit))
        elif unit.is_worker() and unit.can_act():

            closest_resource_tile = get_closest_resource(unit, resource_tiles, player) 
            closest_city_tile = get_closest_city_tile(player,unit)
                     #and (unit.id == builder_unit.id or unit.id == b2unit.id):
            # if build_city_flag and (unit.cargo.wood == 100) and (int(unit.id[-1])%3==1 or unit.id == builder_unit.id):
            if (unit.cargo.wood == 100) and worker_dict[unit.id].build_new_cluster:
                if (unit.pos.x,unit.pos.y) == (worker_dict[unit.id].build_new_cluster.pos.x,worker_dict[unit.id].build_new_cluster.pos.y):
                    log_function("WE MADE IT BOIZ")
                    log_function(f"{(unit.pos.x,unit.pos.y)=}")
                    actions.append(unit.build_city())
                    worker_dict[unit.id].home_city=worker_dict[unit.id].build_new_cluster
                    worker_dict[unit.id].build_new_cluster=None

                else:
                    move_cell = get_better_path(unit,worker_dict[unit.id].build_new_cluster)
                    log_function(f"{move_cell=}")
                    move_dir = unit.pos.direction_to(move_cell.pos)
                    log_function(f"moving to cluster {(worker_dict[unit.id].build_new_cluster.pos.x,worker_dict[unit.id].build_new_cluster.pos.y)}")
                    log_function(f"Current loc {(unit.pos.x,unit.pos.y)=}")
                    actions.append(unit.move(move_dir))
            elif build_city_flag and unit.id in builder_unit and (unit.cargo.wood == 100):
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
            if ct.can_act() and not status.night_flag:
                if build_worker_flag:
                    log_function("Building Worker")
                    actions.append(ct.build_worker())
                elif player.research_points<201:
                    actions.append(ct.research())
    # you can add debug annotations using the functions in the annotate object
    for s in status.logging_str:
        actions.append(annotate.sidetext(f"{s}"))
    for c in status.cell_highlight:
        log_function(f"{c=}")
        if c:
            actions.append(annotate.x(c.pos.x,c.pos.y))
    status.logging_str = []
    status.cell_highlight = []

    actions = move_manager(player, actions)
    if observation["step"] >= 359:
        with open("statsfile", "a") as f:
            f.write(f"{len(status.city_tiles)}\n")
    #logging.info("Move this turn:\n")
    #for act in actions:
    #    annotatefunc(f"{}")
    return actions
